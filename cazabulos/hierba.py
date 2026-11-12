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
from .recursos import escalar

BORDE_HIERBA = (20, 68, 44)
OSCURO = (30, 98, 62)
MEDIO = (54, 146, 84)
CLARO = (98, 190, 102)
PUNTA = (158, 228, 120)
BRILLO_VIENTO = (188, 242, 144)
FLORES_MATA = ((255, 230, 96), (255, 182, 212), (245, 250, 255))
HOJITAS = ((98, 190, 102), (158, 228, 120), (204, 232, 118), (74, 166, 90))

_cuadros = {}


def _borde_verde(s):
    """Contorno verde bosque oscuro alrededor de la mata (1 px por lado, pasa de 16x16 a 18x18)
    para que la hierba alta se integre con el prado como en Pokémon sin verse como rejas negras."""
    w, h = s.get_size()
    out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
    mascara = pygame.mask.from_surface(s, 40)
    sil = mascara.to_surface(setcolor=(*BORDE_HIERBA, 235), unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (1 + dx, 1 + dy))
    out.blit(s, (1, 1))
    return out


def _mata(variante, inclinacion, abierta):
    """Dibuja una mata frondosa de 16x16 al estilo Pokémon: capa trasera de hojas oscuras, base unida
    y hojas delanteras en abanico con puntas iluminadas. inclinacion -1/0/1 es hacia dónde las empuja
    el viento; abierta = alguien está adentro (se abren hacia los lados y se agachan)."""
    rng = random.Random(variante * 131 + 19)
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    # 1) Base tupida abajo para unir los manojos y dar volumen
    if not abierta:
        for x in range(2, TILE - 2):
            alto_base = 3 + ((x + variante) % 2)
            for y in range(TILE - alto_base, TILE):
                s.set_at((x, y), OSCURO if y >= TILE - 2 else MEDIO)
    else:
        for x in (1, 2, 3, 4, 11, 12, 13, 14):
            s.set_at((x, TILE - 1), OSCURO)
            s.set_at((x, TILE - 2), MEDIO)

    # 2) Hojas traseras (más oscuras, llenan los huecos entre manojos)
    for mx in (3, 6, 9, 12):
        ox = mx + rng.randint(-1, 1)
        alto = rng.randint(9, 12)
        if abierta:
            alto = int(alto * 0.55)
            empuje = -2.2 if ox < 8 else 2.2
        else:
            empuje = inclinacion * 0.9
        for j in range(alto):
            f = (j / max(1, alto - 1)) ** 1.6
            x = int(round(ox + empuje * f))
            y = TILE - 1 - j
            if 0 <= x < TILE and 0 <= y < TILE:
                col = OSCURO if j < alto - 3 else MEDIO
                s.set_at((x, y), col)
                if 0 <= x + 1 < TILE and j < alto - 2:
                    s.set_at((x + 1, y), OSCURO if j < 4 else MEDIO)

    # 3) Manojos principales en forma de abanico ("V") con puntas brillantes
    puntas_luz =BRILLO_VIENTO if inclinacion > 0 and not abierta else PUNTA
    for mx in (2, 5, 8, 11, 14):
        cx = mx + (rng.randint(-1, 0) if mx > 8 else rng.randint(0, 1))
        for rama in (-1, 0, 1):
            alto = rng.randint(10, 14) - abs(rama)
            if abierta:
                alto = int(alto * 0.62)
                curva = (-2.6 if cx < 8 else 2.6) + rama * 0.7
            else:
                curva = rama * 1.15 + inclinacion * (1.35 if rama == 0 else 1.05)
            for j in range(alto):
                f = (j / max(1, alto - 1)) ** 1.45
                x = int(round(cx + rama * 0.5 + curva * f))
                y = TILE - 1 - j
                if 0 <= x < TILE and 0 <= y < TILE:
                    if j < 3:
                        col = OSCURO
                    elif j < alto - 4:
                        col = MEDIO
                    elif j < alto - 1:
                        col = CLARO
                    else:
                        col = puntas_luz
                    s.set_at((x, y), col)

    # 4) En algunas matas, un capullo de flor silvestre entre las hojas
    if variante == 3 and not abierta:
        fx = 5 + inclinacion
        fy = 5
        ColorFlor = FLORES_MATA[(variante + max(0, inclinacion)) % len(FLORES_MATA)]
        for dx, dy in ((0, 0), (1, 0), (0, 1)):
            if 0 <= fx + dx < TILE and 0 <= fy + dy < TILE:
                s.set_at((fx + dx, fy + dy), ColorFlor)
        if 0 <= fx + 9 < TILE:
            s.set_at((fx + 7, fy + 2), FLORES_MATA[0])
    return s


def cuadro(variante, inclinacion, abierta=False):
    """La mata ya con su contorno verde oscuro y escalada (crece 1 pixel por lado: dibujarla en x-1, y-1)."""
    clave = (variante, inclinacion, abierta)
    if clave not in _cuadros:
        _cuadros[clave] = escalar(_borde_verde(_mata(variante, inclinacion, abierta)))
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
                if m.suelo[ty][tx] != "g":
                    continue
                if any(m.suelo[ty + dy][tx + dx] != "g" for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                    continue
                if m.solido[ty][tx] or m.capa[ty][tx] is not None:
                    continue
                if not m.libre(pygame.Rect(tx * TILE + 1, ty * TILE + 1, TILE - 2, TILE - 2)):
                    continue
                if any(abs(x - tx * TILE) < 13 and -4 < yb - ty * TILE < 28 for _, x, yb, _ in m.props):
                    continue                     # no tapar troncos ni postes
                umbral = 0.48 if parque.collidepoint(tx, ty) else 0.62
                if mancha(tx, ty) > umbral:
                    var = 3 if self.rng.random() < 0.2 else self.rng.randrange(3)
                    res[(tx, ty)] = {"var": var, "agitada": 0.0, "dentro": False}
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
