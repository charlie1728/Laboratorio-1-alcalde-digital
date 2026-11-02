"""Piezas comunes de las pantallas: escala, botones, paneles y textos en varias líneas."""
from __future__ import annotations

import math

import pygame

from ..ui.dibujo import (BLANCO, LILA, MANGO, TINTA, TINTA2, ancho_texto, icono, pildora, rebote, sombra, texto)

ANCHO, ALTO = 1280, 720


class Escala:
    """Todo se diseña en 1280 x 720 y se dibuja al tamaño real de la ventana, centrado a lo ancho."""

    def __init__(self, sup):
        self.W, self.H = sup.get_size()
        self.U = self.H / ALTO
        self.ox = (self.W - ANCHO * self.U) / 2

    def x(self, v):
        return self.ox + v * self.U

    def y(self, v):
        return v * self.U

    def r(self, x, y, w, h):
        return pygame.Rect(round(self.x(x)), round(self.y(y)), round(w * self.U), round(h * self.U))

    def s(self, v):
        return v * self.U


def partir(s, tam, ancho, peso=800):
    palabras, lineas, actual = str(s).split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if ancho_texto(prueba, tam, peso) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def parrafo(sup, s, x, y, ancho, tam, color, peso=800, interlineado=1.32, centrado=False, max_lineas=None):
    lineas = partir(s, tam, ancho, peso)
    if max_lineas:
        lineas = lineas[:max_lineas]
    for i, l in enumerate(lineas):
        if centrado:
            texto(sup, l, (x + ancho / 2, y + i * tam * interlineado + tam * 0.6), tam, color, peso)
        else:
            texto(sup, l, (x, y + i * tam * interlineado + tam * 0.6), tam, color, peso, ancla="midleft")
    return y + len(lineas) * tam * interlineado


class Boton:
    """Botón grueso con sombra de juego. Se dibuja y luego se pregunta si lo tocaron."""

    def __init__(self, etiqueta, accion, color=MANGO, icono=None, tecla=None, color_texto=TINTA):
        self.etiqueta, self.accion, self.color, self.icono = etiqueta, accion, color, icono
        self.tecla, self.color_texto = tecla, color_texto
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.activo = True
        self.latir = False

    def dibujar(self, sup, rect, t=0.0):
        r = pygame.Rect(rect)
        if self.latir and self.activo:
            k = 1 + 0.03 * math.sin(t * 5)
            r = r.inflate(r.w * (k - 1), r.h * (k - 1))
        self.rect = r
        hover = self.activo and r.collidepoint(pygame.mouse.get_pos())
        radio = round(min(r.h / 2.6, 28 * r.h / 70))
        color = self.color if self.activo else (214, 216, 230)
        sombra(sup, r, radio)
        pygame.draw.rect(sup, tuple(round(c * 0.76) for c in color), r.move(0, round(r.h * 0.09)), border_radius=radio)
        pygame.draw.rect(sup, tuple(min(255, c + 16) for c in color) if hover else color,
                         r.move(0, -round(r.h * 0.03) if hover else 0), border_radius=radio)
        col = self.color_texto if self.activo else TINTA2
        tam = r.h * 0.36
        if self.icono:
            w = ancho_texto(self.etiqueta, tam, 700, "titulo") + tam * 1.5
            x0 = r.centerx - w / 2
            icono(sup, self.icono, (x0 + tam * 0.55, r.centery), tam * 1.1, col, 2.6)
            texto(sup, self.etiqueta, (x0 + tam * 1.5, r.centery), tam, col, 700, "titulo", "midleft")
        else:
            texto(sup, self.etiqueta, r.center, tam, col, 700, "titulo")
        return r

    def toca(self, e) -> bool:
        if not self.activo:
            return False
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.rect.collidepoint(e.pos):
            return True
        return e.type == pygame.KEYDOWN and self.tecla is not None and e.key in (
            self.tecla if isinstance(self.tecla, (list, tuple)) else [self.tecla])


def panel(sup, rect, color=BLANCO, radio=None, borde=None, grosor=4):
    r = pygame.Rect(rect)
    radio = round(r.h * 0.06) if radio is None else radio
    pildora(sup, r, color, radio)
    if borde:
        pygame.draw.rect(sup, borde, r, grosor, border_radius=radio)
    return r


def velo(sup, alfa=170, color=(30, 20, 80)):
    s = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
    s.fill((*color, alfa))
    sup.blit(s, (0, 0))


def estrellas(sup, centro, tam, n, total=3, t=None, color_vacia=(220, 222, 236)):
    """Fila de estrellas (rellenas las ganadas)."""
    x0 = centro[0] - (total - 1) * tam * 0.6
    for i in range(total):
        k = 1.0 if t is None else rebote(min(1, max(0, t - i * 0.35) / 0.35))
        col = (255, 196, 40) if i < n and k > 0 else color_vacia
        icono(sup, "star", (x0 + i * tam * 1.2, centro[1]), tam * (k if i < n and t is not None else 1), col,
              3.2 if i < n else 2.4)


def titulo_grande(sup, s, centro, tam, color=BLANCO, sombra_color=(40, 20, 110)):
    texto(sup, s, (centro[0] + tam * 0.05, centro[1] + tam * 0.06), tam, sombra_color, 700, "titulo")
    texto(sup, s, centro, tam, color, 700, "titulo")


__all__ = ["Escala", "Boton", "panel", "velo", "estrellas", "titulo_grande", "partir", "parrafo", "ANCHO", "ALTO",
           "BLANCO", "LILA", "MANGO", "TINTA", "TINTA2"]
