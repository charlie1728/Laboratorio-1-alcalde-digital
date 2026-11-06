"""Sprites propios en el mismo estilo pixel de Kenney (se dibujan a 16 px y se escalan x3)."""
import colorsys
import math

import pygame

from .recursos import U

_cache = {}


def _guardar(clave, fn):
    if clave not in _cache:
        _cache[clave] = fn()
    return _cache[clave]


# ----------------------------------------------------------------- Bulo
def bulo(cuadro=0, corona=False, congelado=False, mirada=(0, 0), enojado=True, color=None):
    """El Bulo: una gota morada con antenitas. cuadro 0/1 = estirado/aplastado."""
    clave = ("bulo", cuadro, corona, congelado, mirada, enojado, color)

    def hacer():
        s = pygame.Surface((16, 18), pygame.SRCALPHA)
        oy = 2
        cuerpo = color or ((150, 190, 255) if congelado else (128, 66, 232))
        borde = (40, 14, 84) if not congelado else (40, 70, 140)
        brillo = tuple(min(255, c + 70) for c in cuerpo)
        alto = 11 if cuadro == 0 else 10
        ancho = 12 if cuadro == 0 else 13
        x0 = 8 - ancho // 2
        y0 = oy + 3 + (11 - alto)
        pygame.draw.ellipse(s, borde, (x0, y0, ancho, alto + 1))
        pygame.draw.ellipse(s, cuerpo, (x0 + 1, y0 + 1, ancho - 2, alto - 1))
        pygame.draw.ellipse(s, brillo, (x0 + 2, y0 + 2, 4, 3))
        for ax in (5, 10):
            s.fill(borde, (ax, oy + 0 + (11 - alto), 1, 4))
            s.fill(brillo, (ax, oy + 0 + (11 - alto), 1, 1))
        mx, my = mirada
        ey = y0 + 4
        for ex in (5, 9):
            s.fill((255, 255, 255), (ex, ey, 2, 3))
            s.fill((26, 16, 51), (ex + (1 if mx > 0 else 0), ey + 1 + (1 if my > 0 else 0), 1, 1))
        if enojado:
            s.fill(borde, (4, ey - 1, 3, 1))
            s.fill(borde, (9, ey - 1, 3, 1))
        s.fill((255, 95, 122), (6, y0 + alto - 3, 4, 1))
        s.fill((255, 255, 255), (7, y0 + alto - 3, 1, 1))
        if corona:
            c = (255, 206, 50)
            s.fill(c, (5, y0 - 3, 6, 2))
            for cx in (5, 7, 10):
                s.fill(c, (cx, y0 - 5, 1, 2))
            s.fill((230, 60, 60), (7, y0 - 2, 2, 1))
        if congelado:
            s.fill((235, 250, 255), (3, y0 + 1, 1, 2))
            s.fill((235, 250, 255), (12, y0 + 6, 1, 2))
        return s
    return _guardar(clave, hacer)


def bulo_gigante(t):
    base = bulo(int(t * 4) % 2, corona=True, color=(200, 60, 200))
    return pygame.transform.scale(base, (32, 36))


def sombra(ancho=10):
    def hacer():
        s = pygame.Surface((ancho, 4), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, 70), (0, 0, ancho, 4))
        return s
    return _guardar(("sombra", ancho), hacer)


# ----------------------------------------------------------------- estrellas (noticias verdaderas)
def estrella(brillo=0):
    clave = ("estrella", brillo)

    def hacer():
        s = pygame.Surface((16, 16), pygame.SRCALPHA)
        pts = []
        for i in range(10):
            r = 7 if i % 2 == 0 else 3.2
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((7.5 + math.cos(a) * r, 8 + math.sin(a) * r))
        pygame.draw.polygon(s, (176, 108, 0), [(x, y + 1) for x, y in pts])
        pygame.draw.polygon(s, (255, 212, 60), pts)
        s.fill((255, 252, 220), (6, 5, 2, 2))
        if brillo:
            s.fill((255, 255, 255), (7, 0, 1, 2))
        return s
    return _guardar(clave, hacer)


def antena(luz=True, golpe=False):
    clave = ("antena", luz, golpe)

    def hacer():
        s = pygame.Surface((16, 40), pygame.SRCALPHA)
        metal = (255, 200, 200) if golpe else (96, 98, 118)
        claro = (255, 230, 230) if golpe else (136, 138, 160)
        pygame.draw.rect(s, (52, 52, 64), (2, 33, 12, 6))
        pygame.draw.rect(s, (80, 80, 96), (3, 34, 10, 3))
        pygame.draw.line(s, metal, (4, 33), (8, 7))
        pygame.draw.line(s, metal, (12, 33), (8, 7))
        for y in (14, 21, 28):
            w = (y - 6) // 5
            pygame.draw.line(s, claro, (8 - w, y), (8 + w, y))
        s.fill((40, 40, 50), (6, 9, 5, 4))
        s.fill((255, 255, 255), (7, 10, 1, 1))
        s.fill((255, 255, 255), (9, 10, 1, 1))
        pygame.draw.circle(s, (232, 62, 70) if luz else (110, 40, 46), (8, 4), 3)
        if luz:
            s.fill((255, 210, 210), (7, 3, 1, 1))
        return s
    return _guardar(clave, hacer)


HERRAMIENTAS = {
    # Ana: periódico enrollado · Beto: corazón (un "me gusta") · Caro: su red · Dani: un volante
    "ana": [".kkkkkkkkkk.", "kwwwwrwwwwwk", "kgggwrgggwwk", "kwwwwrwwwwwk", "kgggwrggwwwk", ".kkkkkkkkkk."],
    "beto": [".kk...kk.", "kppk.kppk", "kpwpkpppk", "kpppppppk", ".kpppppk.", "..kpppk..", "...kpk...", "....k...."],
    "caro": ["..kkkkk..", ".kgwgwgk.", "kgwgwgwgk", "kwgwgwgwk", "kgwgwgwgk", ".kgwgwgk.", "..kkkkk..", "....b....", "....b...."],
    "dani": ["kkkkkkkk", "kwwwwwwk", "kbbbbbbk", "kwwwwwwk", "kwbbbbwk", "kwwwwwwk", "kwwwbbwk", "kkkkkkkk"],
}
_COLORES_H = {"k": (40, 26, 38), "w": (250, 250, 255), "g": (120, 200, 120), "p": (255, 96, 170),
              "b": (70, 120, 240), "r": (226, 58, 64)}


def herramienta(clave):
    def hacer():
        filas = HERRAMIENTAS[clave]
        colores = dict(_COLORES_H)
        if clave == "ana":
            colores["g"] = (150, 150, 165)
        if clave == "caro":
            colores["b"] = (140, 90, 50)
        s = pygame.Surface((max(len(f) for f in filas), len(filas)), pygame.SRCALPHA)
        for y, f in enumerate(filas):
            for x, ch in enumerate(f):
                if ch in colores:
                    s.set_at((x, y), colores[ch])
        return s
    return _guardar(("herr", clave), hacer)


def corazon(color=(255, 90, 130)):
    def hacer():
        s = pygame.Surface((7, 6), pygame.SRCALPHA)
        for y, fila in enumerate((".xx.xx.", "xxxxxxx", "xxxxxxx", ".xxxxx.", "..xxx..", "...x...")):
            for x, ch in enumerate(fila):
                if ch == "x":
                    s.set_at((x, y), color)
        s.set_at((1, 1), (255, 220, 230))
        return s
    return _guardar(("corazon", color), hacer)


def nube_pelea(t):
    s = pygame.Surface((26, 16), pygame.SRCALPHA)
    gris = (90, 86, 110)
    for cx, cy, r in ((7, 9, 5), (13, 7, 6), (19, 9, 5), (13, 11, 5)):
        pygame.draw.circle(s, gris, (cx, cy), r)
    for cx, cy, r in ((7, 8, 3), (13, 6, 4), (19, 8, 3)):
        pygame.draw.circle(s, (120, 116, 140), (cx, cy), r)
    if int(t * 6) % 3 == 0:
        pygame.draw.lines(s, (255, 230, 80), False, [(12, 12), (10, 15), (14, 14), (12, 16)], 1)
    return s


# ----------------------------------------------------------------- vecinos (Kenney con colores cambiados)
def _cambiar_tono(img, giro):
    if not giro:
        return img
    out = img.copy()
    w, h = out.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = out.get_at((x, y))
            if a == 0:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            piel = 0.02 <= hh <= 0.12 and ss < 0.6
            if ss > 0.35 and vv > 0.25 and not piel:
                hh = (hh + giro) % 1.0
                r2, g2, b2 = colorsys.hsv_to_rgb(hh, ss, vv)
                out.set_at((x, y), (int(r2 * 255), int(g2 * 255), int(b2 * 255), a))
    return out


_COL_DIR = {"izq": 23, "abajo": 24, "arriba": 25, "der": 26}


def vecino(tipo, variante, direccion, cuadro):
    """cuadro 0..3 -> filas quieto, paso, quieto, paso."""
    fila = (0, 1, 0, 2)[cuadro % 4]
    clave = ("vecino", tipo, variante, direccion, fila)

    def hacer():
        img = U((tipo * 3 + fila) * 27 + _COL_DIR[direccion]).copy()
        return _cambiar_tono(img, (0, 0.33, 0.62)[variante % 3])
    return _guardar(clave, hacer)


def desaturar(img):
    clave = ("gris", id(img))

    def hacer():
        g = img.copy()
        arr = pygame.surfarray.pixels3d(g)
        lum = arr[:, :, 0] * 0.3 + arr[:, :, 1] * 0.59 + arr[:, :, 2] * 0.11
        for c in range(3):
            arr[:, :, c] = (arr[:, :, c] * 0.35 + lum * 0.45 + 30).clip(0, 255)
        del arr
        return g
    return _guardar(clave, hacer)


def morado(img):
    """El vecino que se creyó un Bulo se pone morado (así se ve de lejos a quién hay que curar)."""
    clave = ("morado", id(img))

    def hacer():
        g = img.copy()
        arr = pygame.surfarray.pixels3d(g)
        lum = arr[:, :, 0] * 0.3 + arr[:, :, 1] * 0.59 + arr[:, :, 2] * 0.11
        for c, (k, base) in enumerate(((0.55, 70), (0.25, 20), (0.75, 110))):
            arr[:, :, c] = (lum * k + base).clip(0, 255)
        del arr
        return g
    return _guardar(clave, hacer)


def bandera(color):
    """Banderita del candidato sobre un Bulo que dice un rumor de él o de ella."""
    def hacer():
        s = pygame.Surface((6, 7), pygame.SRCALPHA)
        s.fill((60, 50, 70), (0, 0, 1, 7))
        s.fill(color, (1, 0, 5, 4))
        s.fill(tuple(min(255, c + 60) for c in color), (1, 0, 5, 1))
        return s
    return _guardar(("bandera", color), hacer)


def silueta(img, color):
    clave = ("sil", id(img), color)

    def hacer():
        return pygame.mask.from_surface(img).to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    return _guardar(clave, hacer)


def luz(radio):
    """Círculo de luz suave (para la noche)."""
    def hacer():
        s = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
        for r in range(radio, 0, -2):
            a = int(255 * (1 - r / radio) ** 0.7)
            pygame.draw.circle(s, (a, a, a, a), (radio, radio), r)
        return s
    return _guardar(("luz", radio), hacer)
