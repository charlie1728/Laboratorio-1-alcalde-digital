"""Utilidades de dibujo para el juego en vivo (todo escalado al tamaño real de la ventana)."""
from __future__ import annotations

import math

import pygame
import pygame.gfxdraw

from . import recursos

TINTA = (35, 33, 74)
TINTA2 = (84, 88, 130)
BLANCO = (255, 255, 255)
LILA = (108, 77, 245)
LILA2 = (236, 231, 255)
MANGO = (255, 194, 61)
ROJO = (232, 72, 72)
AZUL = (40, 132, 230)
VERDE = (0, 168, 120)
GRIS = (154, 160, 186)
COLOR_TIPO = {"falso": ROJO, "veraz": AZUL, "correccion": VERDE, "oculto": LILA}

_sombras = {}


def mezclar(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def oscuro(c, f):
    return tuple(max(0, min(255, round(v * f))) for v in c[:3])


def suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def rebote(t):
    """Sube rápido, se pasa un poco y se asienta (para cosas que aparecen)."""
    t = max(0.0, min(1.0, t))
    return 1 + 2.2 * (t - 1) ** 3 + 1.2 * (t - 1) ** 2 if t < 1 else 1.0


def texto(sup, s, pos, tam, color, peso=800, fam="texto", ancla="center", alfa=255):
    tam = max(6, round(tam))
    img = recursos.render_texto(str(s), tam, color, peso, fam)
    if alfa < 255:
        img = img.copy()
        img.set_alpha(alfa)
    r = img.get_rect(**{ancla: (round(pos[0]), round(pos[1]))})
    sup.blit(img, r)
    return r


def ancho_texto(s, tam, peso=800, fam="texto"):
    return recursos.fuente(max(6, round(tam)), peso, fam).size(str(s))[0]


def sombra(sup, rect, radio, alfa=70, desp=None):
    r = pygame.Rect(rect)
    desp = desp if desp is not None else max(2, r.h // 12)
    clave = (r.w, r.h, radio, alfa)
    if clave not in _sombras:
        pad = max(8, r.h // 3)
        s = pygame.Surface((r.w + pad * 2, r.h + pad * 2), pygame.SRCALPHA)
        pygame.draw.rect(s, (20, 18, 60, alfa), (pad, pad, r.w, r.h), border_radius=radio)
        w, h = s.get_size()
        s = pygame.transform.smoothscale(pygame.transform.smoothscale(s, (max(1, w // 6), max(1, h // 6))), (w, h))
        if len(_sombras) > 300:
            _sombras.clear()
        _sombras[clave] = (s, pad)
    s, pad = _sombras[clave]
    sup.blit(s, (r.x - pad, r.y - pad + desp))


def pildora(sup, rect, color, radio=None, borde=None, ancho_borde=2, con_sombra=True, alfa=255):
    r = pygame.Rect(rect)
    radio = r.h // 2 if radio is None else radio
    if con_sombra:
        sombra(sup, r, radio)
    if alfa < 255:
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*color[:3], alfa), (0, 0, r.w, r.h), border_radius=radio)
        sup.blit(s, r)
    else:
        pygame.draw.rect(sup, color, r, border_radius=radio)
    if borde:
        pygame.draw.rect(sup, borde, r, ancho_borde, border_radius=radio)
    return r


def circulo(sup, centro, radio, color, alfa=255):
    x, y, radio = round(centro[0]), round(centro[1]), max(1, round(radio))
    if alfa >= 255:
        pygame.gfxdraw.filled_circle(sup, x, y, radio, color)
        pygame.gfxdraw.aacircle(sup, x, y, radio, color)
    else:
        pygame.gfxdraw.filled_circle(sup, x, y, radio, (*color[:3], alfa))


def anillo(sup, centro, radio, color, ancho, fraccion=1.0, alfa=255):
    """Arco que empieza arriba y avanza en sentido horario (para relojes y cargas)."""
    if fraccion <= 0:
        return
    x, y = centro
    r = pygame.Rect(0, 0, radio * 2, radio * 2)
    r.center = (round(x), round(y))
    if alfa < 255:
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        rr = pygame.Rect(0, 0, r.w, r.h)
        if fraccion >= 1:
            pygame.draw.circle(s, (*color, alfa), rr.center, radio, max(1, round(ancho)))
        else:
            pygame.draw.arc(s, (*color, alfa), rr, math.pi / 2 - 2 * math.pi * fraccion, math.pi / 2, max(1, round(ancho)))
        sup.blit(s, r)
        return
    if fraccion >= 1:
        pygame.draw.circle(sup, color, r.center, radio, max(1, round(ancho)))
    else:
        pygame.draw.arc(sup, color, r, math.pi / 2 - 2 * math.pi * fraccion, math.pi / 2, max(1, round(ancho)))


def icono(sup, nombre, centro, tam, color, grosor=2.4):
    img = recursos.icono(nombre, max(4, round(tam)), color, grosor)
    sup.blit(img, img.get_rect(center=(round(centro[0]), round(centro[1]))))


def tecla(sup, letra, centro, tam, fondo=BLANCO, color=TINTA):
    """Una tecla dibujada (para enseñar los controles)."""
    w = max(tam, ancho_texto(letra, tam * 0.55, 900) + tam * 0.45)
    r = pygame.Rect(0, 0, round(w), round(tam))
    r.center = (round(centro[0]), round(centro[1]))
    pygame.draw.rect(sup, oscuro(fondo, 0.78), r.move(0, max(1, round(tam * 0.1))), border_radius=round(tam * 0.25))
    pygame.draw.rect(sup, fondo, r, border_radius=round(tam * 0.25))
    texto(sup, letra, r.center, tam * 0.55, color, 900)
    return r


def bezier(a, b, alto, t):
    (x0, y0), (x1, y1) = a, b
    cx, cy = (x0 + x1) / 2, min(y0, y1) - alto
    return ((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1,
            (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1)


def curva(sup, a, b, alto, color, ancho, alfa=255, pasos=18):
    pts = [bezier(a, b, alto, i / pasos) for i in range(pasos + 1)]
    if alfa < 255:
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        r = pygame.Rect(min(xs) - ancho, min(ys) - ancho, max(xs) - min(xs) + 2 * ancho + 1,
                        max(ys) - min(ys) + 2 * ancho + 1)
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.lines(s, (*color, alfa), False, [(x - r.x, y - r.y) for x, y in pts], max(1, round(ancho)))
        sup.blit(s, r)
    else:
        pygame.draw.lines(sup, color, False, pts, max(1, round(ancho)))
    return pts
