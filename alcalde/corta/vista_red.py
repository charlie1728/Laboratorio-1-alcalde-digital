"""Cómo se dibuja la red social de Civitas: cada persona cerca de su barrio (la red se apoya en el mapa).

La usan la alerta viral (la publicación avanzando salto por salto) y la página «Mi red» del álbum.
"""
from __future__ import annotations

import math

import pygame

from ..modelo.mapa import ZONAS
from ..ui import personajes
from ..ui.dibujo import BLANCO, LILA, MANGO, TINTA, ancho_texto, circulo, pildora, texto

MARGEN_X, MARGEN_Y = 60, 46


def centro_zona(z, area, U):
    nx, ny = ZONAS[z]["pos"] if z in ZONAS else (0.5, 0.5)
    return (area.x + MARGEN_X * U + nx * (area.w - 2 * MARGEN_X * U),
            area.y + MARGEN_Y * U + ny * (area.h - 2 * MARGEN_Y * U))


def posiciones(red, area, U) -> dict:
    """Vértice -> (x, y): los vecinos de un mismo barrio quedan en ronda alrededor del barrio."""
    por_zona = {}
    for v in red.vertices():
        por_zona.setdefault(red.dato(v).zona, []).append(v)
    pos = {}
    for z, gente in por_zona.items():
        cx, cy = centro_zona(z, area, U)
        radio = 0 if len(gente) == 1 else (26 + 6 * len(gente)) * U
        for i, v in enumerate(sorted(gente)):
            ang = i * math.tau / len(gente) + 0.6
            pos[v] = (cx + math.cos(ang) * radio, cy + math.sin(ang) * radio * 0.8)
    return pos


def nombres_barrios(sup, area, U):
    for z, info in ZONAS.items():
        cx, cy = centro_zona(z, area, U)
        texto(sup, info["nombre"], (cx, cy - 46 * U if info["pos"][1] > 0.2 else cy + 52 * U), 11 * U,
              (176, 178, 206), 900)


def aristas_suaves(sup, red, pos, area, U, alfa=60):
    capa = pygame.Surface(area.size, pygame.SRCALPHA)
    for u, v, _ in red.aristas():
        if u in pos and v in pos:
            pygame.draw.line(capa, (150, 140, 210, alfa), (pos[u][0] - area.x, pos[u][1] - area.y),
                             (pos[v][0] - area.x, pos[v][1] - area.y), max(1, round(1.5 * U)))
    sup.blit(capa, area)


COLOR_SALTO = [LILA, (0, 168, 120), (40, 132, 230), (255, 150, 30)]


def mi_red(sup, red, area, U, yo, rol):
    """La red vista desde el jugador: BFS desde él. Cada anillo de color es un salto (1, 2, 3...)."""
    pos = posiciones(red, area, U)
    nombres_barrios(sup, area, U)
    aristas_suaves(sup, red, pos, area, U, 50)
    _, nivel, padre = red.bfs(yo) if yo in red else ([], {}, {})
    for v, p in padre.items():
        if p is not None and nivel.get(v, 9) <= 3:
            pygame.draw.line(sup, COLOR_SALTO[min(3, nivel[v])], pos[p], pos[v], max(2, round(3 * U)))
    superp = [v for v, _ in red.centralidad_grado() if red.dato(v).jugador is None][:2]
    for v, (x, y) in pos.items():
        d = red.dato(v)
        n = nivel.get(v)
        es_yo = v == yo
        tam = round((46 if es_yo else 30) * U)
        borde = COLOR_SALTO[min(3, n)] if n is not None and n <= 3 else None
        img = personajes.avatar(d.look or {}, tam, (236, 231, 255), rol if es_yo else "npc",
                                "feliz" if es_yo else "neutral", borde=borde, grosor=max(2, round(4 * U)))
        sup.blit(img, img.get_rect(center=(x, y)))
        if n is None or n > 3:
            circulo(sup, (x, y), tam / 2, BLANCO, 130)
        if es_yo or v in superp:
            etiqueta = "Tú" if es_yo else v
            w = ancho_texto(etiqueta, 12 * U, 900) + 14 * U
            rr = pildora(sup, (x - w / 2, y + tam / 2 + 2 * U, w, 20 * U), LILA if es_yo else MANGO, con_sombra=False)
            texto(sup, etiqueta, rr.center, 12 * U, BLANCO if es_yo else TINTA, 900)
    return nivel, superp
