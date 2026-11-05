"""Preparar la partida, elegir personajes y la pantalla de relevo entre turnos."""
import math

import pygame

from .. import personajes
from ..config import ALTO, ANCHO, TINTA
from ..mundo import ROLES
from ..partida import MOMENTOS, Partida
from ..personajes import ORDEN, PELOS, PERSONAJES, PIELES
from ..recursos import escalar
from ..ui import panel, parrafo, render, tecla, texto
from .base import Escena, FondoCiudad, es_aceptar, es_volver, pie, titulo_pantalla
from .menu import SI_NO, Formulario, Selector, Titulo


class Preparar(Formulario):
    titulo = "Nueva partida"

    def __init__(self, app):
        op = app.op
        filas = [
            Selector("Jugadores", [("1 jugador", 1), ("2 jugadores", 2), ("3 jugadores", 3), ("4 jugadores", 4)], 1,
                     "Juegan en el mismo computador por turnos: cada uno juega su barrio y luego le pasa el teclado al siguiente."),
            Selector("Rondas", [("1 (mañana)", 1), ("2 (mañana y tarde)", 2), ("3 (mañana, tarde y noche)", 3)],
                     max(0, min(2, op.get("rondas", 2) - 1)),
                     "En cada ronda todos juegan el mismo barrio con los mismos eventos. Gana quien sume más."),
            Selector("Tiempo por turno", [("60 segundos", 60), ("90 segundos", 90), ("2 minutos", 120)],
                     {60: 0, 90: 1, 120: 2}.get(op.get("duracion", 90), 1)),
            Selector("Modo tranquilo (para peques)", SI_NO, 0 if op["tranquilo"] else 1,
                     "Los Bulos van más despacio y las peleas duran más."),
        ]
        super().__init__(app, filas, [("Elegir personajes", self.seguir), ("Volver", self.volver)])

    def seguir(self):
        op = self.app.op
        op["rondas"], op["duracion"], op["tranquilo"] = self.filas[1].valor, self.filas[2].valor, self.filas[3].valor
        self.app.guardar_opciones()
        self.app.cambiar(Seleccion(self.app, self.filas[0].valor, self.filas[1].valor, self.filas[2].valor, self.filas[3].valor))


def tarjeta_personaje(pant, clave, rect, t, activo=False, tomado=None, piel=None, pelo=None, escala=6):
    p = PERSONAJES[clave]
    color = p["color"] if not tomado else (90, 86, 110)
    panel(pant, rect, (40, 30, 84) if activo else (26, 20, 52), 240, 18, color if activo else None, 4)
    foco = pygame.Rect(rect.x + 14, rect.y + 14, rect.w - 28, 210)
    pygame.draw.rect(pant, tuple(int(c * 0.45) for c in color), foco, border_radius=14)
    if activo:
        for k in range(8):
            a = t * 0.8 + k * math.pi / 4
            cx, cy = foco.centerx, foco.bottom - 30
            pts = [(cx, cy), (cx + math.cos(a) * 260, cy + math.sin(a) * 260), (cx + math.cos(a + 0.18) * 260, cy + math.sin(a + 0.18) * 260)]
            s = pygame.Surface(foco.size, pygame.SRCALPHA)
            pygame.draw.polygon(s, (*color, 40), [(x - foco.x, y - foco.y) for x, y in pts])
            pant.blit(s, foco)
    cs = personajes.cuadros(clave, piel, pelo)
    cuadro = int(t * 7) % 4 if activo else 0
    img = cs["abajo"][cuadro]
    if tomado:
        from ..recursos import gris
        img = gris(img)
    grande = pygame.transform.scale(img, (16 * escala, 24 * escala))
    pygame.draw.ellipse(pant, (0, 0, 0), (foco.centerx - 50, foco.bottom - 26, 100, 18))
    pant.blit(grande, grande.get_rect(midbottom=(foco.centerx, foco.bottom - 14 + (-4 if activo and cuadro in (1, 3) else 0))))
    texto(pant, p["nombre"], (rect.centerx, foco.bottom + 10), 34, color, "midtop")
    texto(pant, p["rol"], (rect.centerx, foco.bottom + 50), 20, (235, 230, 250), "midtop", 600)
    rol = ROLES[clave]
    y = parrafo(pant, rol["pasivo"], (rect.centerx, foco.bottom + 82), 16, rect.w - 30, (220, 214, 240), ancla="midtop")
    texto(pant, f"Poder: {rol['poder']}", (rect.centerx, y + 8), 18, color, "midtop")
    parrafo(pant, rol["poder_txt"], (rect.centerx, y + 32), 15, rect.w - 30, (200, 196, 225), ancla="midtop")
    if tomado:
        texto(pant, tomado, (rect.centerx, foco.centery), 22, (255, 255, 255), "center")


class Seleccion(Escena):
    def __init__(self, app, n, rondas, duracion, tranquilo):
        super().__init__(app)
        self.fondo = FondoCiudad(app)
        self.n, self.rondas, self.duracion, self.tranquilo = n, rondas, duracion, tranquilo
        self.elegidos = []
        self.cursor = 0
        self.piel = {c: None for c in ORDEN}
        self.pelo = {c: None for c in ORDEN}
        self._rects = []

    @property
    def tomados(self):
        return {e["clave"]: i for i, e in enumerate(self.elegidos)}

    def _libre(self, d):
        for _ in range(4):
            self.cursor = (self.cursor + d) % 4
            if ORDEN[self.cursor] not in self.tomados:
                return

    def al_entrar(self):
        if ORDEN[self.cursor] in self.tomados:
            self._libre(1)

    def evento(self, e):
        clave = ORDEN[self.cursor]
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_LEFT, pygame.K_a):
                self._libre(-1)
                self.app.son.tocar("mover")
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                self._libre(1)
                self.app.son.tocar("mover")
            elif e.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
                d = 1 if e.key in (pygame.K_DOWN, pygame.K_s) else -1
                actual = PERSONAJES[clave]["piel"] if self.piel[clave] is None else self.piel[clave]
                self.piel[clave] = (actual + d) % len(PIELES)
                self.app.son.tocar("mover")
            elif e.key == pygame.K_c:
                actual = PERSONAJES[clave]["pelo"] if self.pelo[clave] is None else self.pelo[clave]
                self.pelo[clave] = (actual + 1) % len(PELOS)
                self.app.son.tocar("mover")
            elif es_aceptar(e):
                self._elegir()
            elif es_volver(e):
                if self.elegidos:
                    self.elegidos.pop()
                else:
                    self.app.cambiar(Preparar(self.app))
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self._rects):
                if r.collidepoint(e.pos) and ORDEN[i] not in self.tomados:
                    if self.cursor == i:
                        self._elegir()
                    self.cursor = i

    def _elegir(self):
        clave = ORDEN[self.cursor]
        if clave in self.tomados:
            return
        self.app.son.tocar("listo")
        self.elegidos.append({"clave": clave, "piel": self.piel[clave], "pelo": self.pelo[clave],
                              "nombre": PERSONAJES[clave]["nombre"]})
        if len(self.elegidos) >= self.n:
            partida = Partida(self.elegidos, self.rondas, self.duracion, self.tranquilo, self.app.semilla)
            self.app.cambiar(Relevo(self.app, partida))
        else:
            self._libre(1)

    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        k = len(self.elegidos)
        titulo_pantalla(pant, f"Jugador {k + 1}, elige tu personaje" if self.n > 1 else "Elige tu personaje", 24, tam=44)
        texto(pant, "Todos tienen la misma fuerza: cada uno ayuda distinto", (ANCHO // 2, 82), 20, (230, 226, 245), "midtop", 600)
        self._rects = []
        w, h = 290, 500
        x0 = ANCHO // 2 - (4 * w + 3 * 16) // 2
        tomados = self.tomados
        for i, clave in enumerate(ORDEN):
            r = pygame.Rect(x0 + i * (w + 16), 120 + (-8 if i == self.cursor else 0), w, h)
            tomado = f"Jugador {tomados[clave] + 1}" if clave in tomados else None
            tarjeta_personaje(pant, clave, r, self.t, i == self.cursor, tomado, self.piel[clave], self.pelo[clave])
            self._rects.append(r)
        x = ANCHO // 2 - 380
        for t_, d in (("< >", "elegir"), ("ARRIBA/ABAJO", "color de piel"), ("C", "color de pelo"), ("ENTER", "¡listo!")):
            rr = tecla(pant, t_, (x, ALTO - 66), 16)
            texto(pant, d, (rr.right + 8, ALTO - 62), 18, (240, 240, 250), peso=600)
            x = rr.right + 26 + render(d, 18, peso=600).get_width()


class Relevo(Escena):
    """Pantalla entre turnos: el jugador que sigue, de cuerpo entero y bien grande."""

    def __init__(self, app, partida):
        super().__init__(app)
        self.partida = partida
        self.fondo = FondoCiudad(app, 170)

    def evento(self, e):
        if es_aceptar(e) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            from .juego import PantallaJuego
            self.app.son.tocar("click")
            self.app.cambiar(PantallaJuego(self.app, self.partida))
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.cambiar(Titulo(self.app))

    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        pa = self.partida
        j = pa.jugadores[pa.actual]
        p = PERSONAJES[j["clave"]]
        color = p["color"]
        cx, cy = 400, 400
        for k in range(12):
            a = self.t * 0.5 + k * math.pi / 6
            pts = [(cx, cy), (cx + math.cos(a) * 700, cy + math.sin(a) * 700), (cx + math.cos(a + 0.2) * 700, cy + math.sin(a + 0.2) * 700)]
            s = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            pygame.draw.polygon(s, (*color, 26), pts)
            pant.blit(s, (0, 0))
        cs = personajes.cuadros(j["clave"], j["piel"], j["pelo"])
        cuadro = int(self.t * 6) % 4
        img = pygame.transform.scale(cs["abajo"][cuadro], (16 * 13, 24 * 13))
        pygame.draw.ellipse(pant, (0, 0, 0), (cx - 110, cy + 190, 220, 40))
        pygame.draw.ellipse(pant, color, (cx - 130, cy + 182, 260, 56), 6)
        pant.blit(img, img.get_rect(midbottom=(cx, cy + 214 + (-6 if cuadro in (1, 3) else 0))))
        x = 700
        texto(pant, f"Ronda {pa.ronda} de {pa.rondas} · {MOMENTOS.get(pa.ronda, '')}", (x, 90), 26, (230, 226, 245))
        texto(pant, f"¡Te toca, {j['nombre']}!", (x, 130), 60, color, grosor=3)
        texto(pant, p["rol"], (x, 210), 30, (255, 255, 255))
        if len(pa.jugadores) > 1:
            texto(pant, f"Pásale el teclado a {j['nombre']}", (x, 254), 22, (255, 230, 150), peso=600)
        r = panel(pant, (x, 300, 520, 240), borde=color)
        rol = ROLES[j["clave"]]
        filas = [("FLECHAS", "moverte por el barrio"), ("ESPACIO", "lanzar a los Bulos y entregar noticias"),
                 ("X", f"poder: {rol['poder']}")]
        for k, (t_, d) in enumerate(filas):
            rr = tecla(pant, t_, (r.x + 20, r.y + 20 + k * 50), 16)
            texto(pant, d, (rr.right + 12, r.y + 24 + k * 50), 20, (240, 240, 250), peso=600)
        parrafo(pant, "Salva a los vecinos: atrapa los Bulos, mira las noticias antes de compartirlas y apaga la antena del Bot.",
                (r.x + 20, r.y + 172), 18, r.w - 40, (220, 214, 240))
        # orden de turnos de esta ronda
        orden = pa.orden()
        y = 580
        texto(pant, "Turnos:", (x, y + 8), 18, (220, 214, 240), peso=600)
        for k, i in enumerate(orden):
            jj = pa.jugadores[i]
            img = escalar(personajes.retrato(jj["clave"], jj["piel"], jj["pelo"]), 3)
            xx = x + 90 + k * 70
            if i == pa.actual:
                pygame.draw.rect(pant, PERSONAJES[jj["clave"]]["color"], (xx - 4, y - 4, 56, 50), border_radius=10)
            elif k < pa.paso:
                img = img.copy()
                img.set_alpha(110)
            pant.blit(img, (xx, y))
        sube = math.sin(self.t * 4) * 4
        texto(pant, "Pulsa ESPACIO cuando tengas el teclado", (ANCHO // 2, ALTO - 40 + sube), 26, (255, 255, 255), "center")
