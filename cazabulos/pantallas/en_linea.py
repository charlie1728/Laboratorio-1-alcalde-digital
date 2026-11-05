"""Modo en línea: crear o unirse a una sala, elegir personaje y esperar entre rondas."""
import math

import pygame

from .. import personajes
from ..config import ALTO, ANCHO
from ..partida import Partida
from ..personajes import ORDEN, PERSONAJES
from ..recursos import escalar
from ..red.protocolo import PUERTO, ips_locales
from ..ui import barra, panel, parrafo, texto
from .base import Botonera, Escena, FondoCiudad, es_aceptar, es_volver, titulo_pantalla
from .seleccion import tarjeta_personaje


def partida_desde(msg, rondas_previas=None):
    jugadores = [{"id": j["id"], "clave": j["clave"], "piel": j.get("piel"), "pelo": j.get("pelo"),
                  "nombre": PERSONAJES[j["clave"]]["nombre"]} for j in msg["jugadores"] if j.get("clave")]
    pa = Partida(jugadores, msg.get("rondas", 1), msg.get("duracion", 90), msg.get("tranquilo", False))
    return pa


class EnLinea(Escena):
    inactividad = None

    def __init__(self, app):
        super().__init__(app)
        self.fondo = FondoCiudad(app)
        self.paso = "menu"
        self.ip = ""
        self.error = ""
        self.cliente = None
        self.sala = []
        self.cursor = 2
        self.botones = Botonera([("Crear sala", self._crear), ("Unirme a una sala", self._unirme),
                                 ("Volver", self._volver)], centro=(ANCHO // 2, 400), ancho=420)

    # ------------------------------------------------------------- pasos
    def _volver(self):
        if self.cliente:
            self.cliente.cerrar()
            self.cliente = None
            self.app.red = None
        from .menu import Titulo
        self.app.cambiar(Titulo(self.app))

    def _crear(self):
        from ..red.cliente import Cliente
        from ..red.servidor import Servidor
        try:
            srv = Servidor(PUERTO)
        except OSError as e:
            self.error = f"No se pudo crear la sala ({e}). ¿Ya hay otra abierta?"
            return
        try:
            self.cliente = Cliente("127.0.0.1", PUERTO, servidor=srv)
        except OSError as e:
            srv.cerrar()
            self.error = f"No se pudo conectar: {e}"
            return
        self._entrar_sala()

    def _unirme(self):
        self.paso = "ip"
        self.error = ""

    def _conectar(self):
        from ..red.cliente import Cliente
        ip = self.ip.strip() or "127.0.0.1"
        try:
            self.cliente = Cliente(ip, PUERTO)
        except OSError:
            self.error = f"No encontré una sala en {ip}. Revisa la dirección y que estén en la misma red."
            return
        self._entrar_sala()

    def _entrar_sala(self):
        self.app.red = self.cliente
        self.paso = "sala"
        self.error = ""
        self.cliente.enviar({"t": "hola", "nombre": PERSONAJES[ORDEN[self.cursor]]["nombre"], "clave": ORDEN[self.cursor]})

    # ------------------------------------------------------------- eventos
    def evento(self, e):
        if self.paso == "menu":
            if es_volver(e):
                self._volver()
            else:
                self.botones.evento(e, self.app)
        elif self.paso == "ip":
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.paso = "menu"
                elif e.key == pygame.K_BACKSPACE:
                    self.ip = self.ip[:-1]
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._conectar()
                elif e.unicode and (e.unicode.isdigit() or e.unicode == ".") and len(self.ip) < 15:
                    self.ip += e.unicode
        elif self.paso == "sala":
            if es_volver(e) and e.key == pygame.K_ESCAPE:
                self._volver()
            elif e.type == pygame.KEYDOWN and e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
                d = 1 if e.key in (pygame.K_RIGHT, pygame.K_d) else -1
                usados = {j["clave"] for j in self.sala if j["id"] != self.cliente.id}
                for _ in range(4):
                    self.cursor = (self.cursor + d) % 4
                    if ORDEN[self.cursor] not in usados:
                        break
                self.app.son.tocar("mover")
                self.cliente.enviar({"t": "elegir", "clave": ORDEN[self.cursor]})
            elif es_aceptar(e) and self.cliente.anfitrion:
                op = self.app.op
                self.app.son.tocar("listo")
                self.cliente.enviar({"t": "empezar", "rondas": op.get("rondas", 2), "duracion": op.get("duracion", 90),
                                     "tranquilo": op.get("tranquilo", False)})

    def actualizar(self, dt):
        super().actualizar(dt)
        if not self.cliente:
            return
        for msg in self.cliente.recibir():
            t = msg.get("t")
            if t == "sala":
                self.sala = msg["jugadores"]
                for j in self.sala:
                    if j["id"] == self.cliente.id and j.get("clave") in ORDEN:
                        self.cursor = ORDEN.index(j["clave"])
                    if j["id"] == self.cliente.id:
                        self.cliente.anfitrion = j.get("anfitrion", False)
            elif t == "error":
                self.error = msg.get("texto", "")
            elif t == "ronda":
                empezar_ronda(self.app, self.cliente, msg, None)
                return
            elif t == "desconectado":
                self.error = "Se perdió la conexión con la sala."
                self.paso = "menu"
                self.cliente = None
                self.app.red = None
                return

    # ------------------------------------------------------------- dibujo
    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        titulo_pantalla(pant, "Jugar en línea", 30)
        if self.paso == "menu":
            parrafo(pant, "Cada uno en su computador, en la misma red (wifi). Uno crea la sala y los demás se unen. "
                          "Todos juegan a la vez el mismo barrio y ven el marcador en vivo.", (ANCHO // 2, 120), 22, 800,
                    (240, 240, 250), ancla="midtop")
            self.botones.dibujar(pant, self.t)
        elif self.paso == "ip":
            texto(pant, "Escribe la dirección que aparece en la pantalla del que creó la sala", (ANCHO // 2, 220), 24,
                  (240, 240, 250), "midtop", 600)
            r = panel(pant, (ANCHO // 2 - 260, 290, 520, 90), borde=(255, 205, 50))
            cursor = "|" if int(self.t * 2) % 2 else " "
            texto(pant, (self.ip or "") + cursor, r.center, 48, (255, 255, 255), "center")
            texto(pant, "ENTER para conectar  ·  ESC para volver  ·  vacío = este computador", (ANCHO // 2, 410), 20,
                  (220, 214, 240), "midtop", 600)
        elif self.paso == "sala":
            self._sala(pant)
        if self.error:
            texto(pant, self.error, (ANCHO // 2, ALTO - 80), 20, (255, 140, 140), "center", 600)

    def _sala(self, pant):
        c = self.cliente
        if c.servidor:
            ips = ", ".join(ips_locales())
            r = panel(pant, (ANCHO // 2 - 420, 90, 840, 60), borde=(120, 230, 140))
            texto(pant, f"Los demás se unen con:  {ips}", r.center, 28, (140, 240, 160), "center")
        usados = {j["clave"]: j for j in self.sala}
        w = 250
        x0 = ANCHO // 2 - (4 * w + 3 * 14) // 2
        for i, clave in enumerate(ORDEN):
            r = pygame.Rect(x0 + i * (w + 14), 170, w, 420)
            dueno = usados.get(clave)
            mio = dueno and dueno["id"] == c.id
            tomado = None if (not dueno or mio) else f"Lo tiene {dueno['nombre']}"
            tarjeta_personaje(pant, clave, r, self.t, bool(mio), tomado, escala=5)
            if mio:
                texto(pant, "¡TÚ!", (r.centerx, r.y - 6), 22, PERSONAJES[clave]["color"], "midbottom")
        n = len(self.sala)
        if c.anfitrion:
            msg = f"{n} jugador{'es' if n != 1 else ''} en la sala  ·  ENTER para empezar"
        else:
            msg = f"{n} jugador{'es' if n != 1 else ''} en la sala  ·  esperando a que el anfitrión empiece..."
        sube = math.sin(self.t * 4) * 3
        texto(pant, msg, (ANCHO // 2, ALTO - 40 + sube), 24, (255, 255, 255), "center")
        texto(pant, "Izquierda/derecha: cambiar de personaje", (ANCHO // 2, 610), 18, (220, 214, 240), "midtop", 600)


def empezar_ronda(app, cliente, msg, partida):
    """Llega el mensaje 'ronda' del servidor: se arma (o actualiza) la partida y empieza el juego."""
    if partida is None:
        partida = partida_desde(msg)
    else:
        nueva = partida_desde(msg)
        partida.jugadores = nueva.jugadores
    r = msg["ronda"]
    while len(partida.semillas) < r:
        partida.semillas.append(0)
    partida.semillas[r - 1] = msg["semilla"]
    partida.ronda = r
    partida.rondas = msg.get("rondas", partida.rondas)
    indice = next((i for i, j in enumerate(partida.jugadores) if j["id"] == cliente.id), 0)
    from .juego import PantallaJuego
    app.cambiar(PantallaJuego(app, partida, en_linea=cliente, indice=indice))


class EsperaRed(Escena):
    inactividad = None

    """Después de tu turno en línea: esperas a los demás y ves la tabla de la ronda."""

    def __init__(self, app, partida, cliente):
        super().__init__(app)
        self.partida = partida
        self.cliente = cliente
        self.fondo = FondoCiudad(app, 175)
        self.estado = "esperando"        # esperando, tabla, listo
        self.final = False
        self.error = ""

    def evento(self, e):
        if es_aceptar(e) and self.estado == "tabla":
            self.app.son.tocar("click")
            if self.final:
                from .final import Eleccion
                self.app.cambiar(Eleccion(self.app, self.partida))
            else:
                self.cliente.enviar({"t": "listo"})
                self.estado = "listo"
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.cliente.cerrar()
            self.app.red = None
            from .menu import Titulo
            self.app.cambiar(Titulo(self.app))

    def _cargar(self, resultados):
        ids = {j["id"]: i for i, j in enumerate(self.partida.jugadores)}
        for clave, res in resultados.items():
            ronda, ident = clave.split(":")
            if int(ident) in ids:
                self.partida.resultados[(int(ronda), ids[int(ident)])] = res

    def actualizar(self, dt):
        super().actualizar(dt)
        for msg in self.cliente.recibir():
            t = msg.get("t")
            if t == "fin_ronda":
                self._cargar(msg["resultados"])
                self.final = msg.get("ultima", False)
                self.estado = "tabla"
                self.app.son.tocar("fanfarria")
            elif t == "fin":
                self._cargar(msg["resultados"])
                self.final = True
            elif t == "ronda":
                empezar_ronda(self.app, self.cliente, msg, self.partida)
                return
            elif t == "desconectado":
                self.error = "Se perdió la conexión con la sala. ESC para volver."

    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        pa = self.partida
        if self.estado == "esperando":
            titulo_pantalla(pant, "Esperando a los demás...", 60)
            filas = sorted(self.cliente.marcador(), key=lambda f: -f[2])
            for k, (nombre, clave, pts) in enumerate(filas):
                y = 180 + k * 90
                r = panel(pant, (ANCHO // 2 - 340, y, 680, 74), borde=PERSONAJES[clave]["color"])
                img = escalar(personajes.retrato(clave), 4)
                pant.blit(img, img.get_rect(midleft=(r.x + 20, r.centery)))
                texto(pant, nombre, (r.x + 110, r.centery), 28, PERSONAJES[clave]["color"], "midleft")
                texto(pant, str(pts), (r.right - 24, r.centery), 30, (255, 255, 255), "midright")
            puntos = "." * (1 + int(self.t * 2) % 3)
            texto(pant, f"Cuando todos terminen, sale la tabla{puntos}", (ANCHO // 2, ALTO - 60), 22, (230, 226, 245), "center")
        else:
            titulo_pantalla(pant, f"Tabla de la ronda {pa.ronda} de {pa.rondas}", 40, tam=44)
            orden = pa.ranking()
            maximo = max(1, max(pa.total(i) for i in orden))
            for k, i in enumerate(orden):
                j = pa.jugadores[i]
                p = PERSONAJES[j["clave"]]
                y = 150 + k * 110
                r = panel(pant, (140, y, ANCHO - 280, 92), borde=p["color"] if k == 0 else None)
                texto(pant, f"{k + 1}°", (r.x + 24, r.centery), 38, (255, 205, 50) if k == 0 else (255, 255, 255), "midleft")
                img = escalar(personajes.retrato(j["clave"], j["piel"], j["pelo"]), 4)
                pant.blit(img, img.get_rect(midleft=(r.x + 90, r.centery)))
                texto(pant, j["nombre"], (r.x + 180, r.y + 16), 28, p["color"])
                texto(pant, f"{pa.salvados(i)} vecinos salvados", (r.x + 180, r.y + 52), 18, (220, 214, 240), peso=600)
                barra(pant, (r.x + 500, r.y + 32, 380 * pa.total(i) / maximo + 1, 28), 1, p["color"])
                texto(pant, str(pa.total(i)), (r.right - 24, r.centery), 32, (255, 255, 255), "midright")
            if self.estado == "listo":
                s = "Esperando a que todos estén listos..."
            else:
                s = "ENTER: ¡a la elección!" if self.final else "ENTER cuando estés listo para la siguiente ronda"
            texto(pant, s, (ANCHO // 2, ALTO - 44), 24, (255, 255, 255), "center")
        if self.error:
            texto(pant, self.error, (ANCHO // 2, ALTO - 90), 20, (255, 140, 140), "center", 600)
