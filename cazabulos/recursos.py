"""Carga de imágenes y fuentes. Todo se guarda en caché para no repetir trabajo."""
import pygame

from .config import ASSETS, ESC, TILE

_hojas = {}
_fuentes = {}
_escaladas = {}

COLUMNAS = {"ciudad": 37, "urbano": 27}


def hoja(nombre):
    if nombre not in _hojas:
        img = pygame.image.load(str(ASSETS / "kenney" / f"{nombre}.png"))
        _hojas[nombre] = img.convert_alpha() if pygame.display.get_surface() else img
    return _hojas[nombre]


def tile(i, nombre="ciudad"):
    """Tile número i de la hoja (16x16 nativo)."""
    cols = COLUMNAS[nombre]
    return hoja(nombre).subsurface(((i % cols) * TILE, (i // cols) * TILE, TILE, TILE))


def C(i):
    return tile(i, "ciudad")


def U(i):
    return tile(i, "urbano")


def bloque(ids, nombre="ciudad"):
    """Une varios tiles: ids es una lista de filas, por ejemplo [[623, 624], [660, 661]]."""
    alto, ancho = len(ids), len(ids[0])
    s = pygame.Surface((ancho * TILE, alto * TILE), pygame.SRCALPHA)
    for fy, fila in enumerate(ids):
        for fx, i in enumerate(fila):
            if i is not None:
                s.blit(tile(i, nombre), (fx * TILE, fy * TILE))
    return s


def escalar(img, factor=ESC):
    """Escala con vecino más cercano (el pixel art no se emborrona)."""
    clave = (id(img), factor)
    if clave not in _escaladas:
        _escaladas[clave] = (pygame.transform.scale(img, (img.get_width() * factor, img.get_height() * factor)), img)
    return _escaladas[clave][0]


def fuente(tam, peso=700):
    clave = (tam, peso)
    if clave not in _fuentes:
        nombre = {500: "Fredoka-500.ttf", 600: "Fredoka-600.ttf", 700: "Fredoka-700.ttf",
                  800: "Nunito-800.ttf", 750: "Nunito-700.ttf"}.get(peso, "Fredoka-700.ttf")
        try:
            _fuentes[clave] = pygame.font.Font(str(ASSETS / "fuentes" / nombre), tam)
        except (OSError, FileNotFoundError):
            _fuentes[clave] = pygame.font.SysFont("arial", tam, bold=True)
    return _fuentes[clave]


def gris(img, claro=40):
    g = img.copy()
    arr = pygame.surfarray.pixels3d(g)
    lum = arr[:, :, 0] * 0.3 + arr[:, :, 1] * 0.59 + arr[:, :, 2] * 0.11
    for c in range(3):
        arr[:, :, c] = (lum * 0.75 + claro).clip(0, 255)
    del arr
    return g


def tenir(img, color, fuerza=0.5):
    """Mezcla la imagen con un color (para efectos de golpe, noche, etc.)."""
    t = img.copy()
    capa = pygame.Surface(t.get_size(), pygame.SRCALPHA)
    capa.fill((*color, int(255 * fuerza)))
    t.blit(capa, (0, 0), special_flags=pygame.BLEND_RGBA_MULT if False else 0)
    return t


def silueta(img, color, alfa=255):
    """La misma forma de la imagen pintada de un solo color (bordes y destellos)."""
    m = pygame.mask.from_surface(img)
    return m.to_surface(setcolor=(*color, alfa), unsetcolor=(0, 0, 0, 0))


def contorno(img, color, grosor=1):
    """Imagen con un borde de color alrededor (agrega 'grosor' pixeles a cada lado)."""
    w, h = img.get_size()
    out = pygame.Surface((w + 2 * grosor, h + 2 * grosor), pygame.SRCALPHA)
    sil = silueta(img, color)
    for dx in range(-grosor, grosor + 1):
        for dy in range(-grosor, grosor + 1):
            if dx or dy:
                out.blit(sil, (grosor + dx, grosor + dy))
    out.blit(img, (grosor, grosor))
    return out
