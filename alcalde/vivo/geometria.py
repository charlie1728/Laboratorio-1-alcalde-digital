"""Dónde queda cada cosa en la isla de Ciudad Nova (coordenadas del mundo, en baldosas).

La isla es de N x N baldosas. Cada zona del grafo de la ciudad tiene un centro, unos
edificios que no se pueden atravesar y unos puntos donde se para la gente.
"""
from __future__ import annotations

import math

from ..modelo.mapa import CALLES, ZONAS

N = 13
BORDE = 0.35


def _centro(z):
    px, py = ZONAS[z]["pos"]
    return 1.3 + px * 10.2, 1.3 + py * 10.2


CENTRO = {z: _centro(z) for z in ZONAS}

# Huellas de los edificios (x, y, ancho, fondo) relativas al centro de la zona.
_HUELLAS = {
    "barrio": [(-1.1, -0.6, 0.8, 0.8), (0.1, -1.1, 0.8, 0.8), (-0.5, 0.4, 0.8, 0.8)],
    "barrio2": [(-1.1, -0.6, 0.8, 0.8), (0.1, -1.1, 0.8, 0.8), (-0.5, 0.4, 0.8, 0.8)],
    "terminal": [(-1.2, -0.7, 2.2, 1.0), (-0.9, 0.55, 1.3, 0.45)],
    "estadio": [(-1.35, -1.05, 2.7, 2.1)],
    "colegio": [(-1.1, -0.6, 2.0, 1.0)],
    "parque": [(-0.65, -0.65, 1.3, 1.3)],
    "hospital": [(-0.9, -0.7, 1.8, 1.3)],
    "plaza": [(-0.9, -0.9, 0.7, 0.7), (0.1, -0.9, 0.7, 0.7), (-0.9, 0.1, 0.7, 0.7), (0.1, 0.1, 0.7, 0.7)],
    "alcaldia": [(-1.3, -0.7, 2.4, 1.2)],
}

HUELLAS = []
for _z, (_cx, _cy) in CENTRO.items():
    for dx, dy, w, d in _HUELLAS[ZONAS[_z]["tipo"]]:
        HUELLAS.append((_cx + dx, _cy + dy, w, d))


def libre(x: float, y: float, radio: float = 0.22) -> bool:
    """¿Se puede estar en (x, y)? Dentro de la isla y fuera de los edificios."""
    if not (BORDE <= x <= N - BORDE and BORDE <= y <= N - BORDE):
        return False
    for hx, hy, w, d in HUELLAS:
        if hx - radio < x < hx + w + radio and hy - radio < y < hy + d + radio:
            return False
    return True


def mover(x: float, y: float, dx: float, dy: float, radio: float = 0.22) -> tuple[float, float]:
    """Avanza (dx, dy) deslizándose por los bordes de los edificios."""
    if libre(x + dx, y + dy, radio):
        return x + dx, y + dy
    if libre(x + dx, y, radio):
        return x + dx, y
    if libre(x, y + dy, radio):
        return x, y + dy
    return x, y


def _puntos_de_espera(z, cuantos=5):
    """Lugares de la zona donde se para la gente: delante de los edificios (del lado de la cámara)."""
    cx, cy = CENTRO[z]
    puntos = []
    for k in range(40):
        ang = math.radians(-30 + k * 9)            # del lado de la cámara (x e y crecen)
        for r in (1.55, 1.85, 2.15):
            x, y = cx + r * math.cos(ang) * 0.95, cy + r * math.sin(ang) * 0.95
            if libre(x, y, 0.35) and all(math.hypot(x - a, y - b) > 0.55 for a, b in puntos):
                puntos.append((x, y))
                break
        if len(puntos) >= cuantos:
            break
    return puntos or [(cx + 1.6, cy + 1.6)]


ESPERA = {z: _puntos_de_espera(z) for z in ZONAS}
PUERTA = {z: ESPERA[z][0] for z in ZONAS}

VECINAS = {z: set() for z in ZONAS}
for _a, _b, _ in CALLES:
    VECINAS[_a].add(_b)
    VECINAS[_b].add(_a)


def zona_de(x: float, y: float) -> str:
    """La zona más cercana a un punto (para saber en qué barrio está alguien)."""
    return min(CENTRO, key=lambda z: math.hypot(CENTRO[z][0] - x, CENTRO[z][1] - y))


def celdas_calle() -> set[tuple[int, int]]:
    """Baldosas de calle: cada calle del grafo de la ciudad se traza en forma de L."""
    c = set()
    for a, b, _ in CALLES:
        (x0, y0), (x1, y1) = [tuple(map(round, CENTRO[k])) for k in (a, b)]
        x, y = x0, y0
        while x != x1:
            c.add((x, y))
            x += 1 if x1 > x else -1
        while y != y1:
            c.add((x, y))
            y += 1 if y1 > y else -1
        c.add((x1, y1))
    return c


CALLE = celdas_calle()
