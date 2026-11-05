"""Piezas comunes de las pantallas: escena base, lista de botones y fondo de ciudad animado."""
import math

import pygame

from ..config import ALTO, ANCHO
from ..ui import boton, texto


class Escena:
    musica = True

    def __init__(self, app):
        self.app = app
        self.t = 0.0

    def evento(self, e):
        pass

    def actualizar(self, dt):
        self.t += dt

    def dibujar(self, pant):
        pass

    def al_entrar(self):
        pass


def es_aceptar(e):
    return e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER)


def es_volver(e):
    return e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)


class Botonera:
    """Botones en columna que se manejan con flechas + Enter/Espacio o con el mouse."""

    def __init__(self, opciones, centro=(ANCHO // 2, 380), ancho=380, alto=64, sep=16, tam=28, color=(255, 205, 50)):
        self.opciones = opciones        # [(texto, función)]
        self.sel = 0
        self.centro = centro
        self.ancho, self.alto, self.sep, self.tam, self.color = ancho, alto, sep, tam, color
        self.rects = []
        self._colocar()

    def _colocar(self):
        cx, cy = self.centro
        total = len(self.opciones) * self.alto + (len(self.opciones) - 1) * self.sep
        y = cy - total // 2
        self.rects = []
        for _ in self.opciones:
            self.rects.append(pygame.Rect(cx - self.ancho // 2, y, self.ancho, self.alto))
            y += self.alto + self.sep

    def evento(self, e, app=None):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.opciones)
                if app:
                    app.son.tocar("mover")
                return True
            if e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.opciones)
                if app:
                    app.son.tocar("mover")
                return True
            if es_aceptar(e):
                if app:
                    app.son.tocar("click")
                self.opciones[self.sel][1]()
                return True
        elif e.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects):
                if r.collidepoint(e.pos):
                    self.sel = i
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(e.pos):
                    self.sel = i
                    if app:
                        app.son.tocar("click")
                    self.opciones[i][1]()
                    return True
        return False

    def dibujar(self, pant, t=0.0):
        for i, ((txt, _), r) in enumerate(zip(self.opciones, self.rects)):
            boton(pant, r, txt, i == self.sel, self.color, self.tam, t)


class FondoCiudad:
    """El barrio de fondo moviéndose despacio, oscurecido para que se lea el menú.
    El reloj es compartido: al pasar de una pantalla a otra el fondo sigue donde iba."""
    reloj = 0.0

    def __init__(self, app, oscuro=150):
        from ..mundo import mapa_compartido
        from ..render import suelo_escalado
        mapa, _ = mapa_compartido()
        self.suelo = suelo_escalado(mapa)
        self.velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        for y in range(0, ALTO, 4):
            a = int(oscuro * (0.7 + 0.3 * y / ALTO))
            self.velo.fill((20, 14, 46, a), (0, y, ANCHO, 4))

    def dibujar(self, pant, dt):
        FondoCiudad.reloj += dt
        t = FondoCiudad.reloj
        w, h = self.suelo.get_size()
        x = (math.sin(t * 0.05) * 0.5 + 0.5) * (w - ANCHO)
        y = (math.cos(t * 0.037) * 0.5 + 0.5) * (h - ALTO)
        pant.blit(self.suelo, (0, 0), pygame.Rect(int(x), int(y), ANCHO, ALTO))
        pant.blit(self.velo, (0, 0))


def titulo_pantalla(pant, s, y=40, color=(255, 205, 50), tam=52):
    texto(pant, s, (ANCHO // 2, y), tam, color, "midtop", grosor=3)


# Con un control USB en la mano, los avisos dicen sus botones en vez de las teclas.
_BOTONES = (("ESPACIO", "A"), ("ENTER", "A"), ("ESC", "B"), ("TAB", "Y"), ("R:", "Y:"), ("Flechas y", "Cruceta y"),
            ("Arriba/abajo", "Cruceta arriba/abajo"), ("Izquierda/derecha", "Cruceta izquierda/derecha"))


def con_mando(app, s):
    if app is None or not app.mando.en_uso:
        return s
    for tecla_, boton_ in _BOTONES:
        s = s.replace(tecla_, boton_)
    return s


def pie(pant, s, app=None):
    texto(pant, con_mando(app, s), (ANCHO // 2, ALTO - 30), 18, (220, 214, 240), "center", 600)


def instrucciones(pant, centro, t=0.0, mando=False):
    """Todo el juego en tres dibujos (se ve en la cuenta regresiva, antes de empezar a jugar):
    atrapa los Bulos, cura a los morados y recoge las estrellas."""
    from .. import sprites
    from ..recursos import escalar
    from ..ui import panel, tecla
    cx, cy = centro
    w, h, sep = 270, 190, 26
    x0 = cx - (3 * w + 2 * sep) // 2
    bulo = escalar(sprites.bulo(int(t * 4) % 2, False, False, (0, 1)), 5)
    vecino = escalar(sprites.morado(sprites.vecino(1, 0, "abajo", 0)), 5)
    cabeza = escalar(sprites.bulo(int(t * 3) % 2, False, False, (0, 1)), 3)
    estrella = escalar(sprites.estrella(brillo=int(t * 2) % 2), 5)
    tarjetas = [("¡Atrápalos!", (190, 130, 255)), ("¡Cura a los morados!", (220, 160, 255)),
                ("Recoge las estrellas", (255, 214, 70))]
    for k, (txt, color) in enumerate(tarjetas):
        r = pygame.Rect(x0 + k * (w + sep), cy - h // 2, w, h)
        panel(pant, r, (30, 22, 60), 235, 18, color, 3)
        icono_y = r.y + 96 + math.sin(t * 4 + k) * 4
        if k == 0:
            pant.blit(bulo, bulo.get_rect(midbottom=(r.centerx, icono_y)))
        elif k == 1:
            pant.blit(vecino, vecino.get_rect(midbottom=(r.centerx, r.y + 112)))
            pant.blit(cabeza, cabeza.get_rect(midbottom=(r.centerx, r.y + 112 - 62 + math.sin(t * 5) * 2)))
        else:
            pant.blit(estrella, estrella.get_rect(midbottom=(r.centerx, icono_y)))
        texto(pant, txt, (r.centerx, r.bottom - 50), 24, color, "midtop")
    filas = ((("A", "lanzar"), ("B / X", "poder")) if mando else (("ESPACIO", "lanzar"), ("X", "poder")))
    x = cx - 150
    for t_, d in filas:
        rr = tecla(pant, t_, (x, cy + h // 2 + 22), 18)
        texto(pant, d, (rr.right + 10, cy + h // 2 + 26), 22, (255, 255, 255))
        x = rr.right + 120
