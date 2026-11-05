"""Los dos grafos del barrio: el de la ciudad (lugares) y el social (vecinos).

Grafo de la ciudad: vértices = lugares y esquinas, aristas = tramos de calle que se pueden
caminar en línea recta (se comprueba contra las colisiones del mapa). Dijkstra da la ruta más
corta para la flecha guía del jugador y para que los vecinos vayan de una zona a otra.

Grafo social: vértices = vecinos, aristas = amistad/seguimiento con peso de confianza (1 a 3).
Por ahí se contagian los Bulos y viajan las noticias del Influencer.
"""
import math

import pygame

from .config import TILE
from .estructuras.grafo import Grafo
from .mapa import ARISTAS, NODOS


def px(nodo):
    x, y = NODOS[nodo]
    return x * TILE, y * TILE


def linea_libre(mapa, a, b, paso=3, w=6, h=4):
    (x0, y0), (x1, y1) = a, b
    n = max(1, int(math.hypot(x1 - x0, y1 - y0) / paso))
    for k in range(n + 1):
        f = k / n
        x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        if not mapa.libre(pygame.Rect(int(x - w / 2), int(y - h / 2), w, h)):
            return False
    return True


def grafo_ciudad(mapa):
    g = Grafo()
    for nombre in NODOS:
        g.agregar_vertice(nombre, pos=px(nombre))
    descartadas = []
    for a, b in ARISTAS:
        pa, pb = px(a), px(b)
        if linea_libre(mapa, pa, pb):
            g.agregar_arista(a, b, round(math.dist(pa, pb), 1))
        else:
            descartadas.append((a, b))
    g.descartadas = descartadas
    return g


def nodo_cercano(g, mapa, pos, visible=True):
    """El lugar del grafo más cercano a pos (si visible, al que se llega en línea recta)."""
    mejor, dmin = None, float("inf")
    for v in g.vertices():
        p = g.datos[v]["pos"]
        d = math.dist(p, pos)
        if d < dmin and (not visible or linea_libre(mapa, pos, p)):
            mejor, dmin = v, d
    if mejor is None and visible:
        return nodo_cercano(g, mapa, pos, visible=False)
    return mejor


def ruta(g, mapa, desde, hasta):
    """Puntos (px) para ir de 'desde' a 'hasta' por la ciudad. Si se ven, va derecho."""
    if linea_libre(mapa, desde, hasta):
        return [hasta]
    a = nodo_cercano(g, mapa, desde)
    b = nodo_cercano(g, mapa, hasta)
    camino = g.camino(a, b)
    puntos = [g.datos[v]["pos"] for v in camino]
    # atajo: si desde un punto ya se ve el siguiente, se salta el anterior
    if len(puntos) >= 2 and linea_libre(mapa, desde, puntos[1]):
        puntos = puntos[1:]
    return puntos + [hasta]


# ----------------------------------------------------------------- los vecinos
# nombre, tipo de sprite (0-5), variante de color, zona, posición inicial (tiles)
VECINOS = [
    ("Rosa", 1, 0, "Plaza", (21, 14)), ("Luis", 2, 0, "Plaza", (31, 15)),
    ("Pedro", 4, 0, "Alcaldia", (25, 10)), ("Maria", 0, 1, "Alcaldia", (33, 11)),
    ("Carlos", 5, 0, "Plaza", (36, 13)), ("Sofia", 0, 0, "Colegio", (5, 11)),
    ("Mateo", 2, 1, "Colegio", (11, 13)), ("Profe Ines", 1, 1, "Colegio", (8, 10)),
    ("Don Tito", 4, 1, "Mercado", (54, 8)), ("Paola", 1, 2, "Mercado", (58, 12)),
    ("Juan", 3, 0, "Mercado", (61, 16)), ("Camila", 0, 2, "Parque", (24, 31)),
    ("Nico", 2, 2, "Parque", (19, 34)), ("Abuela Gloria", 4, 2, "Parque", (34, 32)),
    ("Valeria", 5, 1, "Parque", (8, 40)), ("Samuel", 3, 1, "Terminal", (55, 31)),
    ("Lina", 5, 2, "Terminal", (60, 32)), ("Ramiro", 3, 2, "Parque", (29, 40)),
]
ZONAS_VECINO = {
    "Plaza": (17, 9, 38, 17), "Alcaldia": (17, 8, 38, 12), "Colegio": (2, 9, 13, 16),
    "Mercado": (50, 6, 63, 17), "Parque": (2, 26, 40, 44), "Terminal": (50, 29, 63, 35),
}
# amistades (peso = confianza). Rosa es la "del grupo de chat": muy conectada.
AMISTADES = [
    ("Rosa", "Luis", 3), ("Rosa", "Pedro", 2), ("Rosa", "Maria", 2), ("Rosa", "Camila", 2),
    ("Rosa", "Don Tito", 1), ("Rosa", "Carlos", 2), ("Rosa", "Samuel", 1),
    ("Luis", "Carlos", 2), ("Pedro", "Maria", 3), ("Maria", "Carlos", 1), ("Pedro", "Luis", 1),
    ("Sofia", "Mateo", 3), ("Sofia", "Profe Ines", 2), ("Mateo", "Profe Ines", 2), ("Mateo", "Nico", 2),
    ("Profe Ines", "Pedro", 1), ("Don Tito", "Paola", 3), ("Paola", "Juan", 2), ("Juan", "Don Tito", 1),
    ("Paola", "Maria", 1), ("Camila", "Nico", 2), ("Camila", "Abuela Gloria", 2), ("Nico", "Valeria", 1),
    ("Abuela Gloria", "Ramiro", 3), ("Valeria", "Ramiro", 2), ("Juan", "Samuel", 2),
    ("Samuel", "Lina", 3), ("Lina", "Ramiro", 1), ("Sofia", "Camila", 1),
]


def grafo_social():
    g = Grafo()
    for nombre, tipo, var, zona, pos in VECINOS:
        g.agregar_vertice(nombre, tipo=tipo, variante=var, zona=zona)
    for a, b, p in AMISTADES:
        g.agregar_arista(a, b, p)
    return g
