"""Servidor de Alcalde Digital: mantiene la partida y la sincroniza con los clientes.

Un hilo acepta conexiones, otro hilo por cliente lee sus mensajes y los pone en una
cola, y un único hilo de juego los procesa en orden: así la Partida nunca se modifica
desde dos hilos a la vez. Después de cada jugada se envía el estado completo a todos.
"""
from __future__ import annotations

import json
import queue
import socket
import threading
import time
from typing import Optional

from ..modelo.apariencia import normalizar
from ..modelo.partida import Partida
from ..modelo.roles import ORDEN_ROLES
from ..modelo.serializacion import partida_a_dict
from .protocolo import PUERTO, Lector, codificar

from ..modelo.apariencia import COLORES_JUGADOR as COLORES
ESPERA_DESCONECTADO = 20


class Conexion:
    def __init__(self, sock, direccion, cid):
        self.sock = sock
        self.direccion = direccion
        self.id = cid
        self.perfil = dict(nombre=f"Jugador {cid + 1}", rol=ORDEN_ROLES[cid % 4], look=None, mas_tiempo=False)
        self.vivo = True
        self.bloqueo = threading.Lock()

    def enviar(self, datos: bytes) -> None:
        if not self.vivo:
            return
        try:
            with self.bloqueo:
                self.sock.sendall(datos)
        except OSError:
            self.vivo = False


class Servidor:
    def __init__(self, host: str = "0.0.0.0", puerto: int = PUERTO, semilla: Optional[int] = None,
                 registro=print):
        self.host, self.puerto, self.semilla = host, puerto, semilla
        self.registro = registro
        self.clientes: list[Conexion] = []
        self.cola: queue.Queue = queue.Queue()
        self.partida: Optional[Partida] = None
        self.indices: dict[int, int] = {}
        self.estado = "lobby"
        self.viral_fin: Optional[float] = None
        self.corriendo = False
        self._sig_id = 0
        self._sock: Optional[socket.socket] = None
        self._desconectado_desde: dict[int, float] = {}

    # ------------------------------------------------------------------ ciclo de vida
    def iniciar(self) -> "Servidor":
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.puerto))
        self._sock.listen(8)
        self._sock.settimeout(0.5)
        self.corriendo = True
        threading.Thread(target=self._aceptar, daemon=True, name="aceptar").start()
        threading.Thread(target=self._juego, daemon=True, name="juego").start()
        self.registro(f"Servidor escuchando en el puerto {self.puerto}")
        return self

    def detener(self) -> None:
        self.corriendo = False
        for c in list(self.clientes):
            try:
                c.sock.close()
            except OSError:
                pass
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def _aceptar(self) -> None:
        while self.corriendo:
            try:
                sock, dire = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if self.estado != "lobby" or len(self.clientes) >= 4:
                try:
                    sock.sendall(codificar(dict(t="aviso", tipo="malo",
                                                texto="La partida está llena o ya empezó.")))
                    sock.close()
                except OSError:
                    pass
                continue
            c = Conexion(sock, dire, self._sig_id)
            self._sig_id += 1
            self.clientes.append(c)
            self.registro(f"Se conectó {dire[0]} (cliente {c.id})")
            c.enviar(codificar(dict(t="bienvenida", id=c.id)))
            threading.Thread(target=self._leer, args=(c,), daemon=True, name=f"cliente-{c.id}").start()

    def _leer(self, c: Conexion) -> None:
        lector = Lector()
        try:
            while self.corriendo and c.vivo:
                datos = c.sock.recv(65536)
                if not datos:
                    break
                for m in lector.alimentar(datos):
                    self.cola.put((c.id, m))
        except (OSError, ValueError):
            pass
        c.vivo = False
        self.cola.put((c.id, dict(t="_desconexion")))

    # ------------------------------------------------------------------ hilo de juego
    def _juego(self) -> None:
        while self.corriendo:
            try:
                cid, m = self.cola.get(timeout=0.1)
            except queue.Empty:
                self._revisar_tiempos()
                continue
            try:
                self._procesar(cid, m)
            except Exception as ex:  # un mensaje malo no debe tumbar el servidor
                self.registro(f"Error procesando {m.get('t')}: {ex!r}")
                self._a(cid, dict(t="aviso", tipo="malo", texto="El servidor no pudo procesar esa jugada."))
            self._revisar_tiempos()

    def _cliente(self, cid: int) -> Optional[Conexion]:
        return next((c for c in self.clientes if c.id == cid), None)

    def _a(self, cid: int, obj) -> None:
        c = self._cliente(cid)
        if c:
            c.enviar(codificar(obj))

    def _todos(self, obj) -> None:
        datos = codificar(obj)
        for c in self.clientes:
            c.enviar(datos)

    def _anfitrion(self) -> Optional[int]:
        vivos = [c for c in self.clientes if c.vivo]
        return vivos[0].id if vivos else None

    def _lobby(self) -> None:
        jugadores = [dict(id=c.id, color=list(COLORES[i % 4]), **c.perfil)
                     for i, c in enumerate(self.clientes) if c.vivo]
        self._todos(dict(t="lobby", jugadores=jugadores, anfitrion=self._anfitrion()))

    def _difundir_estado(self) -> None:
        p = self.partida
        cuerpo = json.dumps(partida_a_dict(p), ensure_ascii=False, separators=(",", ":"))
        restante = None
        if p.evento_viral and self.viral_fin:
            restante = round(max(0.0, self.viral_fin - time.monotonic()), 2)
        desconectados = [self.indices[c.id] for c in self.clientes if not c.vivo and c.id in self.indices]
        for c in self.clientes:
            tu = self.indices.get(c.id, -1)
            cab = json.dumps(dict(t="estado", tu=tu, viral=restante, desconectados=desconectados))
            c.enviar((cab[:-1] + ',"partida":' + cuerpo + "}\n").encode("utf-8"))

    def _procesar(self, cid: int, m: dict) -> None:
        t = m.get("t")
        c = self._cliente(cid)
        if t == "_desconexion":
            self.registro(f"Se desconectó el cliente {cid}")
            if self.estado == "lobby":
                self.clientes = [x for x in self.clientes if x.id != cid]
                self._lobby()
            else:
                self._desconectado_desde[cid] = time.monotonic()
                j = self.indices.get(cid)
                if j is not None:
                    self._todos(dict(t="aviso", tipo="malo",
                                     texto=f"{self.partida.jugadores[j].nombre} se desconectó."))
                self._difundir_estado()
            return
        if t in ("hola", "perfil") and self.estado == "lobby" and c:
            rol = m.get("rol") if m.get("rol") in ORDEN_ROLES else c.perfil["rol"]
            nombre = str(m.get("nombre") or c.perfil["nombre"]).strip()[:14] or c.perfil["nombre"]
            c.perfil = dict(nombre=nombre, rol=rol, look=normalizar(m.get("look") or {}),
                            mas_tiempo=bool(m.get("mas_tiempo")))
            self._lobby()
            return
        if t == "reaccion" and c:
            j = self.indices.get(cid)
            nombre = self.partida.jugadores[j].nombre if (self.partida and j is not None) else c.perfil["nombre"]
            self._todos(dict(t="reaccion", de=nombre, emoji=str(m.get("emoji", ""))[:12]))
            return
        if t == "iniciar" and self.estado == "lobby":
            if cid != self._anfitrion():
                return self._a(cid, dict(t="aviso", tipo="malo", texto="Solo el anfitrión puede comenzar."))
            vivos = [x for x in self.clientes if x.vivo]
            if not 2 <= len(vivos) <= 4:
                return self._a(cid, dict(t="aviso", tipo="malo", texto="Se necesitan de 2 a 4 jugadores."))
            cfg = [dict(nombre=x.perfil["nombre"], rol=x.perfil["rol"], color=COLORES[i % 4],
                        look=x.perfil["look"]) for i, x in enumerate(vivos)]
            rondas = int(m.get("rondas", 8))
            self.partida = Partida(cfg, rondas=max(4, min(12, rondas)), semilla=self.semilla)
            self.indices = {x.id: i for i, x in enumerate(vivos)}
            self.clientes = vivos
            self.estado = "juego"
            self.registro(f"Comienza la partida con {len(vivos)} jugadores")
            self._difundir_estado()
            return
        if self.estado != "juego" or self.partida is None:
            return
        p = self.partida
        j = self.indices.get(cid)
        if t == "viral":
            if p.evento_viral and j == p.jugadores.index(p.evento_viral.jugador):
                p.resolver_viral(m.get("clave"))
                self.viral_fin = None
                self._despues_de_jugada()
            return
        if j != p.turno_idx or p.evento_viral or p.terminada:
            return self._a(cid, dict(t="aviso", tipo="info", texto="Espera tu turno."))
        if t == "accion":
            caso = p.caso_por_id(m.get("caso"))
            nodo = caso.arbol.buscar(m.get("nodo")) if caso else None
            if caso is None or nodo is None or not caso.abierto:
                return self._difundir_estado()
            p.ejecutar(str(m.get("clave")), caso, nodo)
        elif t == "mover":
            msgs = p.mover(str(m.get("zona")))
            if msgs and msgs[0].tipo == "malo" and not p.ultimo_resaltado.get("ruta"):
                self._a(cid, dict(t="aviso", tipo="malo", texto=msgs[0].texto))
        elif t == "conversar":
            msgs = p.conversar()
            if msgs and msgs[0].tipo == "malo" and "charla" not in p.ultimo_resaltado:
                self._a(cid, dict(t="aviso", tipo="malo", texto=msgs[0].texto))
        elif t == "siguiente":
            msgs = p.siguiente_publicacion()
            if msgs and msgs[0].tipo == "malo":
                self._a(cid, dict(t="aviso", tipo="malo", texto=msgs[0].texto))
        elif t == "fin_turno":
            p.terminar_turno()
        else:
            return
        self._despues_de_jugada()

    def _despues_de_jugada(self) -> None:
        p = self.partida
        if p.evento_viral and self.viral_fin is None:
            decide = p.jugadores.index(p.evento_viral.jugador)
            extra = 0
            for c in self.clientes:
                if self.indices.get(c.id) == decide and c.perfil.get("mas_tiempo"):
                    extra = 10
            self.viral_fin = time.monotonic() + p.evento_viral.segundos + extra + 1.5
        if p.terminada:
            self.estado = "fin"
        self._difundir_estado()

    def _revisar_tiempos(self) -> None:
        p = self.partida
        if self.estado != "juego" or p is None:
            return
        ahora = time.monotonic()
        if p.evento_viral and self.viral_fin and ahora >= self.viral_fin:
            p.resolver_viral(None)
            self.viral_fin = None
            self._despues_de_jugada()
            return
        actual = next((c for c in self.clientes if self.indices.get(c.id) == p.turno_idx), None)
        if actual and not actual.vivo and not p.evento_viral:
            desde = self._desconectado_desde.get(actual.id, ahora)
            if ahora - desde > ESPERA_DESCONECTADO:
                p.log(f"{p.jugador_actual.nombre} sigue desconectado: se pasa su turno.", "evento")
                p.terminar_turno()
                self._desconectado_desde[actual.id] = ahora
                self._despues_de_jugada()


def main(argv=None) -> None:
    import argparse
    from .protocolo import ips_locales
    ap = argparse.ArgumentParser(description="Servidor de Alcalde Digital")
    ap.add_argument("--puerto", type=int, default=PUERTO)
    ap.add_argument("--semilla", type=int, default=None)
    a = ap.parse_args(argv)
    s = Servidor(puerto=a.puerto, semilla=a.semilla).iniciar()
    print("Los jugadores se conectan desde el juego con: " + ", ".join(ips_locales()) + f" (puerto {a.puerto})")
    print("Ctrl+C para cerrar.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        s.detener()
