"""Dibujo de la isla de Ciudad Nova en vista isométrica (tipo diorama).

El suelo (mar, isla, pasto, calles) se dibuja una sola vez. Los edificios y los árboles se
dibujan cada uno en su propia imagen, para poder ordenarlos con los personajes según la
profundidad: así alguien puede pasar por detrás de un edificio.

Todo se dibuja al doble de tamaño y se reduce (supermuestreo) para que los bordes salgan suaves.
"""
from __future__ import annotations

import math
import random

import pygame
import pygame.gfxdraw

from ..modelo.mapa import ZONAS
from . import geometria as geo

N = geo.N
SS = 2          # supermuestreo


class Proyeccion:
    """Pasa del mundo (baldosas) a la pantalla. tw = ancho de una baldosa en píxeles."""

    def __init__(self, tw: float, ox: float, oy: float):
        self.tw, self.th = tw, tw / 2
        self.ox, self.oy = ox, oy
        self.k = tw / 108          # tamaño de un "píxel de diseño" (todo se pensó con baldosas de 108)

    def p(self, x, y, z=0.0):
        return (self.ox + (x - y) * self.tw / 2, self.oy + (x + y) * self.th / 2 - z * self.k)

    def escalada(self, f, dx=0.0, dy=0.0):
        return Proyeccion(self.tw * f, self.ox * f + dx, self.oy * f + dy)


def ajustar(ancho: int, alto: int, arriba: int, abajo: int) -> Proyeccion:
    """La proyección más grande con la que la isla cabe entre la barra de arriba y la de abajo."""
    disponible = alto - arriba - abajo
    tw = min(ancho * 0.96 / N, disponible / (N * 0.5 + 0.55))
    oy = arriba + (disponible - tw * (N * 0.5 + 0.45)) / 2 + tw * 0.2
    return Proyeccion(tw, ancho / 2, oy)


# ------------------------------------------------------------------ utilidades de dibujo
def mezclar(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def oscuro(c, f):
    return tuple(max(0, min(255, round(v * f))) for v in c[:3])


def poli(sup, pts, color):
    pts = [(round(x), round(y)) for x, y in pts]
    pygame.gfxdraw.filled_polygon(sup, pts, color)
    pygame.gfxdraw.aapolygon(sup, pts, color)


def sombra_blanda(sup, cx, cy, rx, ry, alfa=70):
    cx, cy, rx, ry = round(cx), round(cy), max(2, round(rx)), max(2, round(ry))
    pad = max(6, rx // 3)
    s = pygame.Surface((rx * 2 + pad * 2, ry * 2 + pad * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (20, 30, 40, alfa), (pad, pad, rx * 2, ry * 2))
    w, h = s.get_size()
    s = pygame.transform.smoothscale(pygame.transform.smoothscale(s, (max(1, w // 6), max(1, h // 6))), (w, h))
    sup.blit(s, (cx - w // 2, cy - h // 2))


def caja(sup, pr, x, y, z, w, d, h, color, techo=None, ventanas=None):
    P = pr.p
    a, b, c = P(x, y + d, z), P(x + w, y + d, z), P(x + w, y, z)
    A, B, C, E = P(x, y + d, z + h), P(x + w, y + d, z + h), P(x + w, y, z + h), P(x, y, z + h)
    poli(sup, [a, b, B, A], oscuro(color, 0.86))
    poli(sup, [b, c, C, B], oscuro(color, 0.70))
    poli(sup, [A, B, C, E], techo or mezclar(color, (255, 255, 255), 0.18))
    linea = oscuro(color, 0.55)
    for p1, p2 in ((A, B), (B, C), (B, b)):
        pygame.draw.aaline(sup, linea, p1, p2)
    if ventanas:
        filas, cols, colv = ventanas
        for f in range(filas):
            for kk in range(cols):
                t0, t1 = (kk + 0.28) / cols, (kk + 0.72) / cols
                z0 = z + h * (f + 0.3) / (filas + 0.2)
                z1 = z + h * (f + 0.78) / (filas + 0.2)
                poli(sup, [P(x + w * t0, y + d, z0), P(x + w * t1, y + d, z0), P(x + w * t1, y + d, z1),
                           P(x + w * t0, y + d, z1)], colv)
                poli(sup, [P(x + w, y + d * (1 - t0), z0), P(x + w, y + d * (1 - t1), z0),
                           P(x + w, y + d * (1 - t1), z1), P(x + w, y + d * (1 - t0), z1)], oscuro(colv, 0.82))


def tejado(sup, pr, x, y, z, w, d, alto, color):
    P = pr.p
    m = y + d / 2
    a, b, c, e = P(x, y + d, z), P(x + w, y + d, z), P(x + w, y, z), P(x, y, z)
    r1, r2 = P(x, m, z + alto), P(x + w, m, z + alto)
    poli(sup, [a, b, r2, r1], oscuro(color, 0.95))
    poli(sup, [b, c, r2], oscuro(color, 0.72))
    poli(sup, [e, c, r2, r1], oscuro(color, 1.08))
    pygame.draw.aaline(sup, oscuro(color, 0.6), r1, r2)


def arbol(sup, pr, x, y, tam=1.0, color=(108, 187, 82)):
    k = pr.k * tam
    cx, cy = map(round, pr.p(x, y))
    sombra_blanda(sup, cx + 6 * k, cy + 2 * k, 22 * k, 10 * k, 80)
    pygame.draw.rect(sup, (126, 86, 58), (cx - 3 * k, cy - 18 * k, 6 * k, 18 * k), border_radius=max(1, round(3 * k)))
    for dy, r, f in ((30, 20, 0.86), (42, 17, 1.0), (52, 12, 1.12)):
        col = oscuro(color, f)
        pygame.gfxdraw.filled_circle(sup, cx, round(cy - dy * k), round(r * k), col)
        pygame.gfxdraw.aacircle(sup, cx, round(cy - dy * k), round(r * k), col)
    pygame.gfxdraw.filled_circle(sup, cx - round(6 * k), round(cy - 50 * k), max(1, round(5 * k)), (255, 255, 255, 60))


# ------------------------------------------------------------------ edificios
def casa(sup, pr, x, y, color, techo):
    sombra_blanda(sup, *pr.p(x + 0.45, y + 0.55), 46 * pr.k, 22 * pr.k, 80)
    caja(sup, pr, x, y, 0, 0.8, 0.8, 40, color, ventanas=(1, 2, (90, 150, 210)))
    tejado(sup, pr, x - 0.05, y - 0.05, 40, 0.9, 0.9, 26, techo)


def puesto(sup, pr, x, y, toldo):
    sombra_blanda(sup, *pr.p(x + 0.4, y + 0.45), 36 * pr.k, 16 * pr.k, 70)
    caja(sup, pr, x, y, 0, 0.7, 0.7, 22, (240, 226, 200))
    tejado(sup, pr, x - 0.05, y - 0.05, 22, 0.8, 0.8, 18, toldo)


def ed_terminal(sup, pr, cx, cy):
    k = pr.k
    sombra_blanda(sup, *pr.p(cx, cy + 0.2), 110 * k, 44 * k, 80)
    caja(sup, pr, cx - 1.2, cy - 0.7, 0, 2.2, 1.0, 34, (233, 236, 245), ventanas=(1, 5, (110, 180, 230)))
    caja(sup, pr, cx - 1.35, cy - 0.85, 34, 2.5, 1.3, 8, (108, 77, 245))
    caja(sup, pr, cx - 0.9, cy + 0.55, 4, 1.3, 0.45, 26, (255, 194, 61), ventanas=(1, 4, (60, 70, 110)))
    for t in (0.2, 1.1):
        x, y = pr.p(cx - 0.9 + t, cy + 1.0, 4)
        pygame.gfxdraw.filled_circle(sup, round(x), round(y), round(7 * k), (40, 40, 60))


def ed_estadio(sup, pr, cx, cy):
    k, P = pr.k, pr.p
    sombra_blanda(sup, *P(cx, cy + 0.2), 120 * k, 56 * k, 90)
    lados, rx, ry, alto = 18, 1.4, 1.1, 34
    base = [(cx + rx * math.cos(2 * math.pi * i / lados), cy + ry * math.sin(2 * math.pi * i / lados)) for i in range(lados)]
    for i in sorted(range(lados), key=lambda i: base[i][0] + base[i][1]):
        a, b = base[i], base[(i + 1) % lados]
        poli(sup, [P(*a), P(*b), P(*b, alto), P(*a, alto)], oscuro((226, 230, 244), 0.9 if b[0] > a[0] else 0.78))
    poli(sup, [P(*q, alto) for q in base], (236, 240, 252))
    interior = [(cx + rx * 0.72 * math.cos(2 * math.pi * i / lados), cy + ry * 0.68 * math.sin(2 * math.pi * i / lados))
                for i in range(lados)]
    poli(sup, [P(*q, alto) for q in interior], (92, 180, 90))
    poli(sup, [P(cx - 0.5, cy - 0.3, alto), P(cx + 0.5, cy - 0.3, alto), P(cx + 0.5, cy + 0.3, alto),
               P(cx - 0.5, cy + 0.3, alto)], (112, 196, 104))
    pygame.draw.aaline(sup, (230, 250, 230), P(cx, cy - 0.3, alto), P(cx, cy + 0.3, alto))
    for i in range(0, lados, 5):
        x, y = P(*base[i], alto)
        pygame.draw.line(sup, (90, 96, 130), (x, y), (x, y - 34 * k), max(1, round(3 * k)))
        pygame.draw.rect(sup, (255, 240, 170), (x - 7 * k, y - 40 * k, 14 * k, 7 * k), border_radius=max(1, round(3 * k)))


def ed_colegio(sup, pr, cx, cy):
    k = pr.k
    sombra_blanda(sup, *pr.p(cx, cy + 0.2), 100 * k, 44 * k, 85)
    caja(sup, pr, cx - 1.1, cy - 0.6, 0, 2.0, 1.0, 58, (236, 120, 96), ventanas=(2, 5, (250, 244, 225)))
    tejado(sup, pr, cx - 1.2, cy - 0.7, 58, 2.2, 1.2, 22, (126, 78, 160))
    caja(sup, pr, cx - 0.25, cy - 0.15, 58, 0.4, 0.4, 44, (236, 120, 96))
    tejado(sup, pr, cx - 0.3, cy - 0.2, 102, 0.5, 0.5, 20, (126, 78, 160))
    x, y = pr.p(cx - 0.05, cy + 0.05, 128)
    pygame.draw.line(sup, (80, 80, 100), (x, y), (x, y - 30 * k), max(1, round(2 * k)))
    poli(sup, [(x, y - 30 * k), (x + 20 * k, y - 25 * k), (x, y - 19 * k)], (255, 194, 61))


def ed_fuente(sup, pr, cx, cy):
    k, P = pr.k, pr.p
    pts = [(cx + 0.7 * math.cos(2 * math.pi * i / 22), cy + 0.7 * math.sin(2 * math.pi * i / 22)) for i in range(22)]
    poli(sup, [P(*q, 1) for q in pts], (214, 204, 186))
    pts = [(cx + 0.58 * math.cos(2 * math.pi * i / 22), cy + 0.58 * math.sin(2 * math.pi * i / 22)) for i in range(22)]
    poli(sup, [P(*q, 3) for q in pts], (100, 196, 236))
    x, y = P(cx, cy, 3)
    pygame.draw.rect(sup, (226, 220, 206), (x - 6 * k, y - 26 * k, 12 * k, 26 * k), border_radius=max(1, round(4 * k)))
    pygame.gfxdraw.filled_circle(sup, round(x), round(y - 28 * k), round(9 * k), (190, 236, 255))


def ed_hospital(sup, pr, cx, cy):
    k = pr.k
    sombra_blanda(sup, *pr.p(cx, cy + 0.2), 96 * k, 44 * k, 90)
    caja(sup, pr, cx - 0.9, cy - 0.7, 0, 1.8, 1.3, 92, (244, 246, 252), ventanas=(4, 4, (120, 186, 236)))
    caja(sup, pr, cx - 0.4, cy - 0.3, 92, 0.8, 0.6, 16, (226, 230, 244))
    x, y = pr.p(cx, cy + 0.6, 70)
    pygame.draw.rect(sup, (232, 72, 72), (x - 5 * k, y - 16 * k, 10 * k, 32 * k), border_radius=max(1, round(3 * k)))
    pygame.draw.rect(sup, (232, 72, 72), (x - 16 * k, y - 5 * k, 32 * k, 10 * k), border_radius=max(1, round(3 * k)))


def ed_alcaldia(sup, pr, cx, cy):
    k = pr.k
    sombra_blanda(sup, *pr.p(cx, cy + 0.2), 120 * k, 50 * k, 90)
    caja(sup, pr, cx - 1.3, cy - 0.7, 0, 2.4, 1.2, 12, (226, 220, 206))
    caja(sup, pr, cx - 1.15, cy - 0.55, 12, 2.1, 0.95, 52, (250, 246, 236), ventanas=(2, 4, (150, 190, 230)))
    for i in range(6):
        caja(sup, pr, cx - 1.05 + i * 0.38, cy + 0.42, 12, 0.1, 0.1, 50, (255, 255, 255))
    tejado(sup, pr, cx - 1.2, cy - 0.6, 64, 2.2, 1.1, 22, (200, 190, 170))
    x, y = pr.p(cx - 0.1, cy - 0.05, 86)
    pygame.draw.rect(sup, (240, 234, 220), (x - 22 * k, y - 14 * k, 44 * k, 16 * k))
    cup = [(x + math.cos(math.pi * i / 24) * 24 * k, y - 14 * k - math.sin(math.pi * i / 24) * 26 * k) for i in range(25)]
    poli(sup, cup, (108, 77, 245))
    poli(sup, [(x, y - 14 * k)] + cup[:12], (84, 58, 210))
    pygame.draw.line(sup, (80, 80, 100), (x, y - 40 * k), (x, y - 70 * k), max(1, round(2 * k)))
    poli(sup, [(x, y - 70 * k), (x + 24 * k, y - 64 * k), (x, y - 58 * k)], (255, 194, 61))


PALETA_CASAS = {
    "barrio": [((255, 214, 150), (232, 96, 72)), ((180, 220, 250), (90, 110, 200)), ((250, 190, 210), (200, 80, 120))],
    "barrio2": [((210, 236, 200), (60, 150, 110)), ((255, 230, 160), (220, 130, 50)), ((220, 210, 250), (120, 90, 200))],
}
TOLDOS = [(232, 72, 72), (255, 194, 61), (0, 158, 115), (108, 77, 245)]
UNICO = {"terminal": ed_terminal, "estadio": ed_estadio, "colegio": ed_colegio, "parque": ed_fuente,
         "hospital": ed_hospital, "alcaldia": ed_alcaldia}


class Pieza:
    """Una cosa con altura (edificio o árbol) ya dibujada, con su caja en el mundo para ordenarla."""

    def __init__(self, img, pos, caja_mundo, clave):
        self.img, self.pos, self.caja, self.clave = img, pos, caja_mundo, clave


class Escenario:
    def __init__(self, ancho, alto, arriba, abajo, semilla=7):
        self.ancho, self.alto = ancho, alto
        self.pr = ajustar(ancho, alto, arriba, abajo)
        self.rng = random.Random(semilla)
        self.suelo = self._suelo()
        self.piezas = self._piezas()

    # -------------------------------------------------------------- suelo
    def _suelo(self):
        W, H = self.ancho * SS, self.alto * SS
        pr = self.pr.escalada(SS)
        P = pr.p
        sup = pygame.Surface((W, H))
        a, b = (120, 214, 236), (64, 160, 208)
        for yy in range(0, H, 4):
            pygame.draw.rect(sup, mezclar(a, b, yy / H), (0, yy, W, 4))
        r = random.Random(3)
        for _ in range(90):
            x, y = r.randrange(W), r.randrange(H)
            pygame.draw.arc(sup, (168, 230, 246), (x, y, 40 * pr.k, 14 * pr.k), 0.3, 2.8, max(1, round(2 * pr.k)))
        prof = 46
        sombra_blanda(sup, *P(N * 0.6, N * 0.6, -prof - 10), N * pr.tw * 0.42, N * pr.th * 0.36, 22)
        poli(sup, [P(0, N), P(N, N), P(N, N, -prof), P(0, N, -prof)], (196, 140, 92))
        poli(sup, [P(N, N), P(N, 0), P(N, 0, -prof), P(N, N, -prof)], (160, 108, 70))
        for i in range(1, 4):
            z = -prof * i / 4
            pygame.draw.aaline(sup, (150, 100, 64), P(0, N, z), P(N, N, z))
            pygame.draw.aaline(sup, (130, 86, 54), P(N, N, z), P(N, 0, z))
        poli(sup, [P(0, N, 0), P(N, N, 0), P(N, N, -8), P(0, N, -8)], (96, 170, 72))
        poli(sup, [P(N, N, 0), P(N, 0, 0), P(N, 0, -8), P(N, N, -8)], (80, 150, 60))
        for gx in range(N):
            for gy in range(N):
                col = mezclar((139, 211, 107), (126, 202, 96), self.rng.random() * 0.5 + ((gx + gy) % 2) * 0.35)
                poli(sup, [P(gx, gy), P(gx + 1, gy), P(gx + 1, gy + 1), P(gx, gy + 1)], col)
        calle = geo.CALLE
        for gx, gy in calle:
            poli(sup, [P(gx, gy), P(gx + 1, gy), P(gx + 1, gy + 1), P(gx, gy + 1)], (250, 238, 210))
        ancho = max(1, round(3 * pr.k))
        for gx, gy in calle:
            for (ax, ay), (bx, by), vecina in (((gx, gy), (gx + 1, gy), (gx, gy - 1)),
                                               ((gx + 1, gy), (gx + 1, gy + 1), (gx + 1, gy)),
                                               ((gx, gy + 1), (gx + 1, gy + 1), (gx, gy + 1)),
                                               ((gx, gy), (gx, gy + 1), (gx - 1, gy))):
                if vecina not in calle:
                    pygame.draw.line(sup, (222, 205, 170), P(ax, ay), P(bx, by), ancho)
        for gx, gy in calle:
            hor = (gx + 1, gy) in calle or (gx - 1, gy) in calle
            ver = (gx, gy + 1) in calle or (gx, gy - 1) in calle
            if hor and not ver:
                pygame.draw.line(sup, (236, 214, 170), P(gx + 0.3, gy + 0.5), P(gx + 0.7, gy + 0.5), ancho)
            elif ver and not hor:
                pygame.draw.line(sup, (236, 214, 170), P(gx + 0.5, gy + 0.3), P(gx + 0.5, gy + 0.7), ancho)
        return pygame.transform.smoothscale(sup, (self.ancho, self.alto)).convert()

    # -------------------------------------------------------------- piezas con altura
    def _pieza(self, dibujar, cx, cy, caja_mundo, clave, radio=2.4):
        """Dibuja una pieza al doble en una imagen pequeña centrada en (cx, cy) del mundo y la recorta."""
        x0, y0 = self.pr.p(cx, cy)
        lado = round(self.pr.tw * radio * 2) * SS
        pr = self.pr.escalada(SS, lado / 2 - x0 * SS, lado * 0.7 - y0 * SS)
        tmp = pygame.Surface((lado, lado), pygame.SRCALPHA)
        dibujar(tmp, pr)
        r = tmp.get_bounding_rect()
        if r.w == 0:
            return None
        recorte = tmp.subsurface(r).copy()
        img = pygame.transform.smoothscale(recorte, (max(1, r.w // SS), max(1, r.h // SS)))
        pos = (x0 - lado / 2 / SS + r.x / SS, y0 - lado * 0.7 / SS + r.y / SS)
        return Pieza(img.convert_alpha(), (round(pos[0]), round(pos[1])), caja_mundo, clave)

    def _piezas(self):
        piezas = []
        huellas = geo._HUELLAS
        for z, (cx, cy) in geo.CENTRO.items():
            tipo = ZONAS[z]["tipo"]
            if tipo in PALETA_CASAS:
                for (dx, dy, w, d), (col, tec) in zip(huellas[tipo], PALETA_CASAS[tipo]):
                    x, y = cx + dx, cy + dy
                    piezas.append(self._pieza(lambda s, pr, x=x, y=y, col=col, tec=tec: casa(s, pr, x, y, col, tec),
                                              x + 0.4, y + 0.4, (x, y, w, d), x + y + 0.8, 1.2))
            elif tipo == "plaza":
                for i, (dx, dy, w, d) in enumerate(huellas[tipo]):
                    x, y = cx + dx, cy + dy
                    piezas.append(self._pieza(lambda s, pr, x=x, y=y, i=i: puesto(s, pr, x, y, TOLDOS[i]),
                                              x + 0.35, y + 0.35, (x, y, w, d), x + y + 0.7, 1.0))
            else:
                hx = [cx + dx for dx, dy, w, d in huellas[tipo]]
                hy = [cy + dy for dx, dy, w, d in huellas[tipo]]
                x1 = max(cx + dx + w for dx, dy, w, d in huellas[tipo])
                y1 = max(cy + dy + d for dx, dy, w, d in huellas[tipo])
                caja_m = (min(hx), min(hy), x1 - min(hx), y1 - min(hy))
                piezas.append(self._pieza(lambda s, pr, f=UNICO[tipo], cx=cx, cy=cy: f(s, pr, cx, cy),
                                          cx, cy, caja_m, cx + cy, 2.6))
            if tipo == "parque":
                for dx, dy, t in ((-1.2, -0.9, 1.1), (1.0, -1.1, 0.95), (-1.3, 0.8, 1.0), (1.1, 0.9, 1.15)):
                    x, y = cx + dx, cy + dy
                    piezas.append(self._pieza(lambda s, pr, x=x, y=y, t=t: arbol(s, pr, x, y, t, (96, 182, 84)),
                                              x, y, (x - 0.1, y - 0.1, 0.2, 0.2), x + y, 0.9))
        ocupadas = {(round(x) + dx, round(y) + dy) for x, y in geo.CENTRO.values() for dx in (-1, 0, 1, 2)
                    for dy in (-1, 0, 1, 2)}
        for gx in range(N):
            for gy in range(N):
                if (gx, gy) in geo.CALLE or (gx, gy) in ocupadas or self.rng.random() > 0.36:
                    continue
                x, y = gx + 0.3 + self.rng.random() * 0.4, gy + 0.3 + self.rng.random() * 0.4
                t = 0.7 + self.rng.random() * 0.5
                col = self.rng.choice([(108, 187, 82), (90, 170, 80), (130, 196, 90)])
                piezas.append(self._pieza(lambda s, pr, x=x, y=y, t=t, col=col: arbol(s, pr, x, y, t, col),
                                          x, y, (x - 0.1, y - 0.1, 0.2, 0.2), x + y, 0.9))
        return [p for p in piezas if p is not None]

    def clave_personaje(self, x, y) -> float:
        """Profundidad de un personaje, corregida para no quedar mal parado frente a un edificio."""
        clave = x + y
        for p in self.piezas:
            bx, by, w, d = p.caja
            if w < 0.5:
                continue
            if abs(x - (bx + w / 2)) > w / 2 + 1.6 or abs(y - (by + d / 2)) > d / 2 + 1.6:
                continue
            if x >= bx + w - 0.05 or y >= by + d - 0.05:
                clave = max(clave, p.clave + 0.01)
            elif x <= bx + 0.05 or y <= by + 0.05:
                clave = min(clave, p.clave - 0.01)
        return clave
