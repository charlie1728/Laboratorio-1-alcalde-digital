"""Servidor de Cazabulos en línea.

Mantiene y sincroniza: la sala (jugadores y personajes), las rondas (semilla, duración, turno
de juego), las posiciones y puntajes en vivo, los avisos que se comparten, los resultados de
cada ronda y los resultados finales con la elección. Cada cliente juega su propio barrio con la
misma semilla, así la partida es justa y nadie depende de otro.
"""
import random
import socket
import threading
import time

from .protocolo import PUERTO, Lector, codificar

PERSONAJES = ["ana", "beto", "caro", "dani"]


class _Conexion:
    def __init__(self, sock, ident):
        self.sock = sock
        self.id = ident
        self.nombre = f"Jugador {ident}"
        self.clave = None
        self.piel = None
        self.pelo = None
        self.estado = {}
        self.vivo = True
        self.lock = threading.Lock()

    def enviar(self, msg):
        try:
            with self.lock:
                self.sock.sendall(codificar(msg))
        except OSError:
            self.vivo = False


class Servidor:
    def __init__(self, puerto=PUERTO, max_jugadores=4):
        self.puerto = puerto
        self.max = max_jugadores
        self.conexiones = []
        self.lock = threading.RLock()
        self.sig_id = 1
        self.fase = "sala"          # sala, jugando, entre_rondas, fin
        self.ronda = 0
        self.config = {"rondas": 2, "duracion": 90, "tranquilo": False}
        self.semillas = []
        self.resultados = {}        # "ronda:id" -> resumen
        self.listos = set()
        self.t_fin_ronda = None
        self.activo = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", puerto))
        self.sock.listen(8)
        self.sock.settimeout(0.5)
        threading.Thread(target=self._aceptar, daemon=True).start()
        threading.Thread(target=self._latido, daemon=True).start()

    # ------------------------------------------------------------- conexiones
    def _aceptar(self):
        while self.activo:
            try:
                s, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with self.lock:
                if len(self.conexiones) >= self.max or self.fase != "sala":
                    try:
                        s.sendall(codificar({"t": "error", "texto": "La sala está llena o ya empezó"}))
                        s.close()
                    except OSError:
                        pass
                    continue
                c = _Conexion(s, self.sig_id)
                self.sig_id += 1
                self.conexiones.append(c)
            threading.Thread(target=self._leer, args=(c,), daemon=True).start()

    def _leer(self, c):
        lector = Lector()
        c.sock.settimeout(1.0)
        while self.activo and c.vivo:
            try:
                datos = c.sock.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                break
            if not datos:
                break
            for msg in lector.agregar(datos):
                self._mensaje(c, msg)
        c.vivo = False
        with self.lock:
            if c in self.conexiones:
                self.conexiones.remove(c)
            self._difundir({"t": "aviso", "texto": f"{c.nombre} se desconectó"})
            self._enviar_sala()
            self._revisar_ronda()

    def _anfitrion(self):
        return self.conexiones[0] if self.conexiones else None

    def _difundir(self, msg, excepto=None):
        for c in list(self.conexiones):
            if c is not excepto:
                c.enviar(msg)

    def _jugadores(self):
        return [{"id": c.id, "nombre": c.nombre, "clave": c.clave, "piel": c.piel, "pelo": c.pelo,
                 "anfitrion": c is self._anfitrion()} for c in self.conexiones]

    def _enviar_sala(self):
        self._difundir({"t": "sala", "jugadores": self._jugadores(), "fase": self.fase, "config": self.config})

    # ------------------------------------------------------------- mensajes
    def _mensaje(self, c, msg):
        t = msg.get("t")
        with self.lock:
            if t == "hola":
                c.nombre = str(msg.get("nombre", c.nombre))[:14]
                c.piel, c.pelo = msg.get("piel"), msg.get("pelo")
                c.enviar({"t": "bienvenida", "id": c.id, "anfitrion": c is self._anfitrion()})
                self._tomar(c, msg.get("clave"))
                self._enviar_sala()
            elif t == "elegir" and self.fase == "sala":
                c.piel, c.pelo = msg.get("piel", c.piel), msg.get("pelo", c.pelo)
                self._tomar(c, msg.get("clave"))
                self._enviar_sala()
            elif t == "empezar" and c is self._anfitrion() and self.fase == "sala":
                for k in ("rondas", "duracion", "tranquilo"):
                    if k in msg:
                        self.config[k] = msg[k]
                base = random.randrange(1, 10 ** 6)
                self.semillas = [base + 1013 * r for r in range(int(self.config["rondas"]))]
                self._empezar_ronda(1)
            elif t == "estado" and self.fase == "jugando":
                c.estado = {k: msg.get(k) for k in ("x", "y", "dir", "paso", "puntos", "salvados")}
            elif t == "aviso":
                self._difundir({"t": "aviso", "texto": str(msg.get("texto", ""))[:80]}, excepto=c)
            elif t == "resultado":
                self.resultados[f"{self.ronda}:{c.id}"] = msg.get("res", {})
                self._difundir({"t": "aviso", "texto": f"{c.nombre} terminó su turno"}, excepto=c)
                self._revisar_ronda()
            elif t == "listo" and self.fase == "entre_rondas":
                self.listos.add(c.id)
                if all(x.id in self.listos for x in self.conexiones):
                    self._siguiente()

    def _tomar(self, c, clave):
        usados = {x.clave for x in self.conexiones if x is not c}
        if clave in PERSONAJES and clave not in usados:
            c.clave = clave
        elif c.clave is None or c.clave in usados:
            libres = [p for p in PERSONAJES if p not in usados]
            c.clave = libres[0] if libres else "caro"
            if clave and clave != c.clave:
                c.enviar({"t": "error", "texto": "Ese personaje ya lo tiene otro jugador"})

    def _empezar_ronda(self, r):
        self.ronda = r
        self.fase = "jugando"
        self.listos = set()
        self.t_fin_ronda = time.time() + float(self.config["duracion"]) + 30
        self._difundir({"t": "ronda", "ronda": r, "rondas": int(self.config["rondas"]), "semilla": self.semillas[r - 1],
                        "duracion": self.config["duracion"], "tranquilo": self.config["tranquilo"],
                        "jugadores": self._jugadores()})

    def _revisar_ronda(self):
        if self.fase != "jugando":
            return
        faltan = [c for c in self.conexiones if f"{self.ronda}:{c.id}" not in self.resultados]
        if faltan and (self.t_fin_ronda is None or time.time() < self.t_fin_ronda):
            return
        ronda_res = {k: v for k, v in self.resultados.items() if k.startswith(f"{self.ronda}:")}
        ultima = self.ronda >= int(self.config["rondas"])
        self.fase = "fin" if ultima else "entre_rondas"
        self._difundir({"t": "fin_ronda", "ronda": self.ronda, "resultados": ronda_res, "ultima": ultima,
                        "jugadores": self._jugadores()})
        if ultima:
            self._difundir({"t": "fin", "resultados": self.resultados, "jugadores": self._jugadores()})
        self.t_entre = time.time() + 40

    def _siguiente(self):
        if self.fase == "entre_rondas":
            self._empezar_ronda(self.ronda + 1)

    def _latido(self):
        """Marcador en vivo (6 veces por segundo) y relojes de seguridad."""
        while self.activo:
            time.sleep(1 / 6)
            with self.lock:
                if self.fase == "jugando":
                    jugadores = []
                    for c in self.conexiones:
                        d = {"id": c.id, "nombre": c.nombre, "clave": c.clave}
                        d.update(c.estado)
                        jugadores.append(d)
                    self._difundir({"t": "marcador", "jugadores": jugadores})
                    self._revisar_ronda()
                elif self.fase == "entre_rondas" and time.time() > getattr(self, "t_entre", 1e18):
                    self._siguiente()

    def cerrar(self):
        self.activo = False
        try:
            self.sock.close()
        except OSError:
            pass
        for c in list(self.conexiones):
            try:
                c.sock.close()
            except OSError:
                pass


def principal():
    """Servidor dedicado (sin ventana): python -m cazabulos.red.servidor [--puerto 5070]
    Los jugadores abren el juego, eligen "En línea" > "Unirme a una sala" y escriben la dirección que
    muestra este servidor. El primero que se une es el anfitrión y es quien empieza la partida."""
    import argparse
    from .protocolo import PUERTO, ips_locales
    ap = argparse.ArgumentParser(description="Servidor de Cazabulos en línea")
    ap.add_argument("--puerto", type=int, default=PUERTO)
    args = ap.parse_args()
    srv = Servidor(args.puerto)
    print(f"Sala lista en el puerto {args.puerto}. Los jugadores se unen con: {', '.join(ips_locales())}")
    print("Ctrl+C para cerrar.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        srv.cerrar()


if __name__ == "__main__":
    principal()
