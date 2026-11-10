"""Hierba alta (como la de los juegos de Pokémon) en los prados del barrio.

- Cada mata ocupa un tile y se mece con el viento: la ola recorre el campo.
- Cuando alguien entra (el jugador o un vecino) se abre hacia los lados, suelta hojitas y, al salir,
  tiembla un momento antes de quedarse quieta.
- La parte de adelante de la mata se dibuja encima de los pies de quien está adentro: así parece
  que camina entre la hierba.

Es solo de adorno: no frena a nadie ni cambia el juego. Usa su propio azar.
"""
import math
import random

import pygame

from .config import ESC, TILE
from .recursos import borde, escalar

OSCURO = (30, 98, 62)
MEDIO = (54, 142, 84)
CLARO = (104, 192, 104)
PUNTA = (156, 222, 122)
HOJITAS = ((104, 192, 104), (156, 222, 122), (200, 220, 110), (80, 168, 92))

_cuadros = {}


def _mata(variante, inclinacion, abierta):
    """Dibuja una mata de 16x16: cuatro manojos de hojas de distinta altura. inclinacion -1/0/1 es hacia
    dónde las empuja el viento; abierta = alguien está adentro (se abren hacia los lados y se agachan)."""
    rng = random.Random(variante * 97 + 13)
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    for mx in (2, 6, 10, 13):
        mx += rng.randint(-1, 1)
        for k in range(3):
            bx = mx + k - 1
            alto = rng.randint(8, 12)
            if abierta:
                alto = int(alto * 0.6)
                lado = -2 if mx < 8 else 2
            else:
                lado = inclinacion * (1 if k != 1 else 0.6)
            for j in range(alto):
                f = (j / max(1, alto - 1)) ** 2
                x = bx + round(lado * f * 1.5)
                y = TILE - 1 - j
                if 0 <= x < TILE:
                    color = OSCURO if j < 3 else MEDIO if j < alto - 3 else CLARO
                    if j == alto - 1:
                        color = PUNTA
                    s.set_at((x, y), color)
    return s


def cuadro(variante, inclinacion, abierta=False):
    """La mata ya con borde y escalada (crece 1 pixel por lado: dibujarla en x-1, y-1)."""
    clave = (variante, inclinacion, abierta)
    if clave not in _cuadros:
        _cuadros[clave] = escalar(borde(_mata(variante, inclinacion, abierta)))
    return _cuadros[clave]


class HierbaAlta:
    def __init__(self, mapa, semilla=5):
        self.mapa = mapa
        self.rng = random.Random(semilla)
        self.t = 0.0
        self.matas = self._sembrar()           # (tx, ty) -> {"var", "agitada", "dentro"}
        self.donde = {}                        # quién está en qué mata (para saber cuándo entra)
        self.hojitas = []                      # [x, y, vx, vy, vida, color]

    def _sembrar(self):
        """Manchas de hierba en el pasto que no toca caminos ni objetos (más en el parque)."""
        m = self.mapa
        H, W = len(m.suelo), len(m.suelo[0])
        parque = m.zonas.get("Parque", pygame.Rect(0, 0, 0, 0))
        # manchas suaves: un ruido de valores en una grilla gruesa
        g = [[self.rng.random() for _ in range(W // 3 + 2)] for _ in range(H // 3 + 2)]

        def mancha(tx, ty):
            fx, fy = tx / 3, ty / 3
            x0, y0 = int(fx), int(fy)
            ax, ay = fx - x0, fy - y0
            arriba = g[y0][x0] * (1 - ax) + g[y0][x0 + 1] * ax
            abajo = g[y0 + 1][x0] * (1 - ax) + g[y0 + 1][x0 + 1] * ax
            return arriba * (1 - ay) + abajo * ay

        res = {}
        for ty in range(1, H - 1):
            for tx in range(1, W - 1):
                if any(m.suelo[ty + dy][tx + dx] != "g" for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    continue
                if m.solido[ty][tx] or m.capa[ty][tx] is not None:
                    continue
                if not m.libre(pygame.Rect(tx * TILE + 1, ty * TILE + 1, TILE - 2, TILE - 2)):
                    continue
                if any(abs(x - tx * TILE) < 14 and -4 < yb - ty * TILE < 30 for _, x, yb, _ in m.props):
                    continue                     # no tapar troncos ni postes
                umbral = 0.56 if parque.collidepoint(tx, ty) else 0.7
                if mancha(tx, ty) > umbral:
                    res[(tx, ty)] = {"var": self.rng.randrange(3), "agitada": 0.0, "dentro": False}
        return res

    # ------------------------------------------------------------- tiempo
    def actualizar(self, dt, caminantes):
        """caminantes: [(clave, x, y)] de quienes pueden pisar la hierba (en pixeles nativos)."""
        self.t += dt
        for mata in self.matas.values():
            mata["dentro"] = False
            mata["agitada"] = max(0.0, mata["agitada"] - dt * 1.6)
        ahora = {}
        for clave, x, y in caminantes:
            tile = (int(x // TILE), int(y // TILE))
            mata = self.matas.get(tile)
            if mata is None:
                continue
            ahora[clave] = tile
            mata["dentro"] = True
            mata["agitada"] = 1.0
            if self.donde.get(clave) != tile:      # acaba de entrar: suelta hojitas
                for _ in range(self.rng.randint(4, 7)):
                    self.hojitas.append([x + self.rng.uniform(-6, 6), y - self.rng.uniform(2, 8),
                                         self.rng.uniform(-22, 22), self.rng.uniform(-48, -24), 0.0,
                                         self.rng.choice(HOJITAS)])
        self.donde = ahora
        for h in self.hojitas:
            h[0] += h[2] * dt
            h[1] += h[3] * dt
            h[3] += 110 * dt
            h[2] *= 0.97
            h[4] += dt
        self.hojitas = [h for h in self.hojitas if h[4] < 0.8]

    # ------------------------------------------------------------- dibujo
    def _imagen(self, tx, ty, mata):
        if mata["dentro"]:
            return cuadro(mata["var"], 0, True)
        if mata["agitada"] > 0:                    # recién la soltaron: tiembla
            return cuadro(mata["var"], 1 if int(self.t * 18) % 2 else -1)
        ola = math.sin(self.t * 1.9 - tx * 0.42 - ty * 0.17)
        return cuadro(mata["var"], -1 if ola < -0.45 else 1 if ola > 0.45 else 0)

    def dibujar(self, pant, render):
        x0 = int(render.cam[0] / ESC / TILE) - 1
        y0 = int(render.cam[1] / ESC / TILE) - 1
        x1 = x0 + int(pant.get_width() / ESC / TILE) + 3
        y1 = y0 + int(pant.get_height() / ESC / TILE) + 3
        for ty in range(y0, y1):
            for tx in range(x0, x1):
                mata = self.matas.get((tx, ty))
                if mata is not None:
                    pant.blit(self._imagen(tx, ty, mata), render.a_pantalla(tx * TILE - 1, ty * TILE - 1))

    def encima(self, pant, render, x, y):
        """La parte de adelante de la mata, encima de los pies de quien camina adentro."""
        ty = int(y // TILE)
        for tx in {int((x - 5) // TILE), int((x + 5) // TILE)}:
            mata = self.matas.get((tx, ty))
            if mata is None:
                continue
            img = self._imagen(tx, ty, mata)
            arriba = int(max(0.0, (y - 7) - (ty * TILE - 1)) * ESC)
            if arriba >= img.get_height():
                continue
            sx, sy = render.a_pantalla(tx * TILE - 1, ty * TILE - 1)
            pant.blit(img, (sx, sy + arriba), (0, arriba, img.get_width(), img.get_height() - arriba))

    def dibujar_hojitas(self, pant, render):
        for x, y, _, _, vida, color in self.hojitas:
            sx, sy = render.a_pantalla(x, y)
            ancho = ESC * (2 if int(vida * 12) % 2 else 1)
            pant.fill((34, 26, 44), (int(sx) - 1, int(sy) - 1, ancho + 2, ESC + 2))
            pant.fill(color, (int(sx), int(sy), ancho, ESC))
