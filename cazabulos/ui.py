"""Ayudas de dibujo para la interfaz: textos con borde, paneles redondeados, teclas y barras."""
import math

import pygame

from .config import BLANCO, TINTA
from .recursos import fuente

_textos = {}


def render(s, tam, color=BLANCO, peso=700, borde=None, grosor=2):
    clave = (s, tam, color, peso, borde, grosor)
    img = _textos.get(clave)
    if img is None:
        f = fuente(tam, peso)
        base = f.render(s, True, color)
        if borde:
            sil = f.render(s, True, borde)
            img = pygame.Surface((base.get_width() + grosor * 2, base.get_height() + grosor * 2), pygame.SRCALPHA)
            for dx in range(-grosor, grosor + 1):
                for dy in range(-grosor, grosor + 1):
                    if dx * dx + dy * dy <= grosor * grosor + 1:
                        img.blit(sil, (grosor + dx, grosor + dy))
            img.blit(base, (grosor, grosor))
        else:
            img = base
        if len(_textos) > 900:
            _textos.clear()
        _textos[clave] = img
    return img


def texto(surf, s, pos, tam=22, color=BLANCO, ancla="topleft", peso=700, borde=TINTA, grosor=2, alfa=255):
    img = render(s, tam, color, peso, borde, grosor)
    r = img.get_rect(**{ancla: pos})
    if alfa < 255:
        img = img.copy()
        img.set_alpha(alfa)
    surf.blit(img, r)
    return r


def ajustar(s, tam, ancho, peso=600):
    """Parte un texto en líneas que caben en 'ancho' pixeles."""
    f = fuente(tam, peso)
    lineas, actual = [], ""
    for palabra in s.split():
        prueba = (actual + " " + palabra).strip()
        if f.size(prueba)[0] <= ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def parrafo(surf, s, pos, tam, ancho, color=BLANCO, peso=600, interlinea=1.2, borde=None, ancla="topleft"):
    x, y = pos
    lineas = ajustar(s, tam, ancho, peso)
    for ln in lineas:
        if ancla == "midtop":
            texto(surf, ln, (x, y), tam, color, "midtop", peso, borde)
        else:
            texto(surf, ln, (x, y), tam, color, "topleft", peso, borde)
        y += int(tam * interlinea)
    return y


def panel(surf, rect, color=(26, 20, 52), alfa=225, radio=16, borde=None, grosor=3, sombra=True):
    rect = pygame.Rect(rect)
    if sombra:
        s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 70), s.get_rect(), border_radius=radio)
        surf.blit(s, (rect.x + 4, rect.y + 6))
    s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alfa), s.get_rect(), border_radius=radio)
    if borde:
        pygame.draw.rect(s, borde if len(borde) == 4 else (*borde, 255), s.get_rect(), grosor, border_radius=radio)
    surf.blit(s, rect)
    return rect


def tecla(surf, etiqueta, pos, tam=18, ancla="topleft", color=(250, 248, 240)):
    img = render(etiqueta, tam, TINTA, 700, None)
    w = max(img.get_width() + 18, int(tam * 1.9))
    h = int(tam * 1.7)
    r = pygame.Rect(0, 0, w, h)
    setattr(r, ancla, pos)
    pygame.draw.rect(surf, (120, 116, 140), r.move(0, 4), border_radius=8)
    pygame.draw.rect(surf, color, r, border_radius=8)
    pygame.draw.rect(surf, (200, 196, 210), r, 2, border_radius=8)
    surf.blit(img, img.get_rect(center=(r.centerx, r.centery - 1)))
    return r


def barra(surf, rect, frac, color, fondo=(40, 34, 70), radio=6):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, fondo, rect, border_radius=radio)
    if frac > 0:
        r = rect.copy()
        r.w = max(radio * 2, int(rect.w * max(0.0, min(1.0, frac))))
        pygame.draw.rect(surf, color, r, border_radius=radio)
        brillo = r.copy()
        brillo.h = max(2, r.h // 3)
        brillo.y += 2
        brillo.x += 3
        brillo.w = max(0, brillo.w - 6)
        claro = tuple(min(255, c + 60) for c in color)
        pygame.draw.rect(surf, claro, brillo, border_radius=radio)


def boton(surf, rect, etiqueta, activo=False, color=(255, 205, 50), tam=30, t=0.0, icono=None):
    rect = pygame.Rect(rect)
    sube = int(math.sin(t * 6) * 2) if activo else 0
    r = rect.move(0, -sube)
    base = color if activo else (64, 56, 104)
    pygame.draw.rect(surf, tuple(int(c * 0.6) for c in base), r.move(0, 6), border_radius=18)
    pygame.draw.rect(surf, base, r, border_radius=18)
    if activo:
        pygame.draw.rect(surf, BLANCO, r, 4, border_radius=18)
    txt_color = TINTA if activo else BLANCO
    img = render(etiqueta, tam, txt_color, 700, None)
    surf.blit(img, img.get_rect(center=(r.centerx + (14 if icono else 0), r.centery - 2)))
    if icono:
        surf.blit(icono, icono.get_rect(midright=(r.centerx - img.get_width() // 2 + 4, r.centery)))
    return r


def degradado(surf, arriba, abajo):
    w, h = surf.get_size()
    for y in range(0, h, 4):
        f = y / h
        c = tuple(int(arriba[i] + (abajo[i] - arriba[i]) * f) for i in range(3))
        surf.fill(c, (0, y, w, 4))
