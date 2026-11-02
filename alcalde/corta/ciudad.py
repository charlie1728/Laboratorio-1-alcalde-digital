"""El horizonte de Ciudad Nova al fondo de la pantalla: un barrio por zona del mapa.

Cada barrio se dibuja dos veces: sano y enfermo (gris, con las ventanas apagadas). En el juego
se mezclan según qué tan enfermo esté.
"""
from __future__ import annotations

import math
import random

import pygame
import pygame.gfxdraw

from ..modelo.mapa import ZONAS

SS = 2


def _oscuro(c, f):
    return tuple(max(0, min(255, round(v * f))) for v in c[:3])


def _gris(c):
    g = round(0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])
    return tuple(round(g * 0.55 + v * 0.15) for v in c[:3])


def _edificio(s, x, base, w, h, color, techo=None, ventanas=True, k=1.0, apagadas=False, rng=None):
    r = pygame.Rect(round(x), round(base - h), round(w), round(h))
    pygame.draw.rect(s, _oscuro(color, 0.8), r.move(round(6 * k), 0))
    pygame.draw.rect(s, color, r)
    pygame.draw.rect(s, _oscuro(color, 0.86), (r.right - round(w * 0.22), r.y, round(w * 0.22), r.h))
    if techo == "dos_aguas":
        pygame.draw.polygon(s, _oscuro(color, 0.7) if apagadas else (232, 96, 72),
                            [(r.x - 6 * k, r.y), (r.right + 6 * k, r.y), (r.centerx, r.y - w * 0.42)])
    elif techo == "plano":
        pygame.draw.rect(s, _oscuro(color, 0.75), (r.x - 4 * k, r.y - 8 * k, r.w + 8 * k, 10 * k))
    if ventanas:
        vw, vh = 12 * k, 15 * k
        cols = max(1, int((w - 14 * k) // (vw + 9 * k)))
        filas = max(1, int((h - 24 * k) // (vh + 12 * k)))
        for f in range(filas):
            for c in range(cols):
                vx = r.x + 10 * k + c * (vw + 9 * k)
                vy = r.y + 14 * k + f * (vh + 12 * k)
                encendida = rng.random() < 0.55 if rng else True
                col = (70, 70, 90) if apagadas else ((255, 226, 140) if encendida else (150, 200, 240))
                pygame.draw.rect(s, col, (round(vx), round(vy), round(vw), round(vh)), border_radius=max(1, round(2 * k)))
    return r


def _arbol(s, x, base, k=1.0, color=(108, 187, 82)):
    pygame.draw.rect(s, (126, 86, 58), (x - 3 * k, base - 22 * k, 6 * k, 22 * k))
    for dy, rad, f in ((30, 18, 0.86), (42, 15, 1.0), (52, 10, 1.12)):
        pygame.gfxdraw.filled_circle(s, round(x), round(base - dy * k), round(rad * k), _oscuro(color, f))
        pygame.gfxdraw.aacircle(s, round(x), round(base - dy * k), round(rad * k), _oscuro(color, f))


def _barrio(s, tipo, x0, ancho, base, k, enfermo, semilla):
    rng = random.Random(semilla)
    g = _gris if enfermo else (lambda c: c)
    verde = g((108, 187, 82))
    if tipo in ("barrio", "barrio2"):
        cols = [(255, 214, 150), (180, 220, 250), (250, 190, 210)] if tipo == "barrio" else \
            [(210, 236, 200), (255, 230, 160), (220, 210, 250)]
        x = x0 + 8 * k
        for i, c in enumerate(cols):
            w = ancho * 0.27
            _edificio(s, x, base, w, (70 + 18 * (i % 2)) * k, g(c), "dos_aguas", True, k, enfermo, rng)
            x += w + 6 * k
    elif tipo == "colegio":
        _edificio(s, x0 + 8 * k, base, ancho * 0.85, 110 * k, g((236, 120, 96)), "plano", True, k, enfermo, rng)
        r = _edificio(s, x0 + ancho * 0.38, base - 110 * k, ancho * 0.2, 40 * k, g((236, 120, 96)), "dos_aguas", False, k, enfermo)
        pygame.draw.line(s, (80, 80, 100), (r.centerx, r.y - 30 * k), (r.centerx, r.y - 64 * k), max(1, round(2 * k)))
        pygame.draw.polygon(s, g((255, 194, 61)), [(r.centerx, r.y - 64 * k), (r.centerx + 20 * k, r.y - 58 * k),
                                                   (r.centerx, r.y - 52 * k)])
    elif tipo == "parque":
        for i in range(5):
            _arbol(s, x0 + (14 + i * ancho / 5.2) * 1, base, k * (1.1 + 0.3 * (i % 2)), verde)
        pygame.draw.ellipse(s, g((100, 196, 236)), (x0 + ancho * 0.3, base - 14 * k, ancho * 0.4, 18 * k))
    elif tipo == "terminal":
        _edificio(s, x0 + 6 * k, base, ancho * 0.9, 64 * k, g((233, 236, 245)), "plano", True, k, enfermo, rng)
        pygame.draw.rect(s, g((108, 77, 245)), (x0, base - 74 * k, ancho, 12 * k), border_radius=round(4 * k))
        bus = pygame.Rect(x0 + 16 * k, base - 34 * k, ancho * 0.6, 30 * k)
        pygame.draw.rect(s, g((255, 194, 61)), bus, border_radius=round(6 * k))
        for i in range(4):
            pygame.draw.rect(s, (60, 70, 110), (bus.x + 8 * k + i * 20 * k, bus.y + 5 * k, 14 * k, 10 * k),
                             border_radius=max(1, round(2 * k)))
        for dx in (0.2, 0.8):
            pygame.gfxdraw.filled_circle(s, round(bus.x + bus.w * dx), bus.bottom, round(7 * k), (40, 40, 60))
    elif tipo == "alcaldia":
        r = _edificio(s, x0 + 6 * k, base, ancho * 0.9, 96 * k, g((250, 246, 236)), None, False, k, enfermo)
        for i in range(6):
            pygame.draw.rect(s, g((236, 230, 214)), (r.x + 8 * k + i * (r.w - 16 * k) / 6, r.y + 30 * k, 8 * k, r.h - 30 * k))
        pygame.draw.polygon(s, g((200, 190, 170)), [(r.x - 6 * k, r.y), (r.right + 6 * k, r.y), (r.centerx, r.y - 34 * k)])
        pygame.draw.circle(s, g((108, 77, 245)), (r.centerx, round(r.y - 34 * k)), round(24 * k), draw_top_left=True,
                           draw_top_right=True)
        pygame.draw.line(s, (80, 80, 100), (r.centerx, r.y - 58 * k), (r.centerx, r.y - 88 * k), max(1, round(2 * k)))
        pygame.draw.polygon(s, g((255, 194, 61)), [(r.centerx, r.y - 88 * k), (r.centerx + 22 * k, r.y - 82 * k),
                                                   (r.centerx, r.y - 76 * k)])
    elif tipo == "plaza":
        cols = [(232, 72, 72), (255, 194, 61), (0, 158, 115), (108, 77, 245)]
        for i, c in enumerate(cols):
            x = x0 + 6 * k + i * ancho / 4.1
            pygame.draw.rect(s, g((240, 226, 200)), (x, base - 34 * k, ancho / 4.6, 34 * k))
            pygame.draw.polygon(s, g(c), [(x - 4 * k, base - 34 * k), (x + ancho / 4.6 + 4 * k, base - 34 * k),
                                          (x + ancho / 9.2, base - 52 * k)])
    elif tipo == "hospital":
        r = _edificio(s, x0 + 10 * k, base, ancho * 0.8, 150 * k, g((244, 246, 252)), "plano", True, k, enfermo, rng)
        cr = (232, 72, 72) if not enfermo else (120, 110, 110)
        pygame.draw.rect(s, cr, (r.centerx - 6 * k, r.y + 10 * k, 12 * k, 34 * k), border_radius=max(1, round(3 * k)))
        pygame.draw.rect(s, cr, (r.centerx - 17 * k, r.y + 21 * k, 34 * k, 12 * k), border_radius=max(1, round(3 * k)))
    elif tipo == "estadio":
        e = pygame.Rect(x0 + 6 * k, base - 70 * k, ancho - 12 * k, 70 * k)
        pygame.draw.ellipse(s, g((214, 218, 236)), e)
        pygame.draw.ellipse(s, g((92, 180, 90)), e.inflate(-40 * k, -34 * k).move(0, -10 * k))
        pygame.draw.rect(s, g((214, 218, 236)), (e.x, e.centery, e.w, e.h / 2))
        for dx in (0.12, 0.88):
            x = e.x + e.w * dx
            pygame.draw.line(s, (90, 96, 130), (x, e.y + 10 * k), (x, e.y - 40 * k), max(1, round(3 * k)))
            pygame.draw.rect(s, (255, 240, 170), (x - 8 * k, e.y - 46 * k, 16 * k, 8 * k), border_radius=max(1, round(2 * k)))


class Fondo:
    """El barrio donde se juega: su edificio en grande al centro y casas de relleno a los lados.

    Se dibuja dos veces (sano y enfermo) y en el juego se mezclan según la confianza del barrio.
    """

    def __init__(self, zona: str, ancho: int, alto: int, U: float, semilla: int = 0):
        self.zona, self.U = zona, U
        self.base = alto - 70 * U
        self.alto_fila = round(440 * U)
        self.sano = self._fila(ancho, False, semilla)
        self.enfermo = self._fila(ancho, True, semilla)
        self.calle = pygame.Surface((ancho, round(alto - self.base) + 2))
        self.calle.fill((96, 104, 136))
        pygame.draw.rect(self.calle, (226, 226, 236), (0, 0, ancho, round(16 * U)))
        for x in range(0, ancho, round(60 * U)):
            pygame.draw.rect(self.calle, (250, 238, 210), (x, round(40 * U), round(30 * U), round(5 * U)))

    def _fila(self, ancho, enfermo, semilla):
        U = self.U
        h = self.alto_fila
        s = pygame.Surface((ancho * SS, h * SS), pygame.SRCALPHA)
        base = h * SS - 2
        rng = random.Random(semilla)
        tipo = ZONAS[self.zona]["tipo"]
        centro_w = 460 * U * SS
        x_centro = ancho * SS / 2 - centro_w / 2
        k = U * SS * 2.3
        # relleno a la izquierda y a la derecha
        otros = [t for t in ("barrio", "barrio2", "plaza", "terminal", "colegio") if t != tipo]
        x = x_centro - 20 * U * SS
        i = 0
        while x > -200 * U * SS:
            w = rng.uniform(190, 250) * U * SS
            _barrio(s, otros[i % len(otros)], x - w, w, base, U * SS * 1.5, enfermo, semilla + i)
            x -= w + 10 * U * SS
            i += 1
        x = x_centro + centro_w + 20 * U * SS
        while x < ancho * SS + 200 * U * SS:
            w = rng.uniform(190, 250) * U * SS
            _barrio(s, otros[(i + 2) % len(otros)], x, w, base, U * SS * 1.5, enfermo, semilla + i)
            x += w + 10 * U * SS
            i += 1
        _barrio(s, tipo, x_centro, centro_w, base, k, enfermo, semilla + 99)
        return pygame.transform.smoothscale(s, (ancho, h)).convert_alpha()

    def dibujar(self, sup, enfermedad: float, temblor=(0, 0)):
        sx, sy = temblor
        y = self.base - self.alto_fila + sy
        sup.blit(self.sano, (sx, y))
        if enfermedad > 0.02:
            self.enfermo.set_alpha(round(255 * min(1, enfermedad)))
            sup.blit(self.enfermo, (sx, y))
            self.enfermo.set_alpha(255)
        sup.blit(self.calle, (sx, self.base + sy))
