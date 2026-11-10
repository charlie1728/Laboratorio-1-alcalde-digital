"""El barrio: suelo, edificios, objetos con colisión y carriles para los carros.

Medidas en tiles de 16 px. El mapa mide 64 x 46 tiles (unas 2,5 x 3 pantallas).
Zonas: Colegio, Alcaldía y plaza (noroeste), Mercado (noreste), Parque con laguna (suroeste)
y Terminal de buses (sureste), separadas por una avenida y una carrera con semáforo.
"""
import random

import pygame

from .config import TILE
from .recursos import CONTORNO, C, U

W, H = 64, 46

# Avenida (horizontal) y carrera (vertical)
AV_Y0, AV_Y1 = 20, 23      # filas de la calzada
CR_X0, CR_X1 = 44, 47      # columnas de la calzada

# Grafo de la ciudad: lugares y esquinas (en tiles) y las calles que los unen.
NODOS = {
    "Colegio": (8, 12), "Salida colegio": (8, 17.5), "Anden colegio": (8, 19.5),
    "Plaza": (24.5, 14.5), "Alcaldia": (25.5, 9.5), "Fuente": (28, 15.5), "Casas": (40.5, 8),
    "Cebra plaza": (23, 19.5), "Esquina NO": (42.5, 19.5), "Esquina NE": (49, 19.5),
    "Puestos": (58.5, 16), "Pasillo mercado": (58.5, 11.5), "Mercado": (54.5, 11.5),
    "Esquina SO": (42.5, 24.5), "Esquina SE": (49, 24.5), "Cebra parque": (23, 24.5),
    "Entrada parque": (23, 28.5), "Laguna": (13, 29.5), "Camino este": (33, 28.5),
    "Picnic": (33, 34.5), "Sur parque": (33, 40), "Kiosco": (27.5, 37), "Laguna sur": (18, 36),
    "Sur laguna": (18, 40), "Oeste parque": (4, 40), "Entrada terminal": (50, 30.5), "Terminal": (56, 31), "Paradero": (56, 34.6),
}
ARISTAS = [
    ("Colegio", "Salida colegio"), ("Salida colegio", "Anden colegio"), ("Anden colegio", "Cebra plaza"),
    ("Plaza", "Cebra plaza"), ("Plaza", "Alcaldia"), ("Plaza", "Fuente"),
    ("Alcaldia", "Casas"), ("Casas", "Esquina NO"), ("Cebra plaza", "Esquina NO"),
    ("Esquina NO", "Esquina NE"), ("Esquina NE", "Puestos"), ("Puestos", "Pasillo mercado"),
    ("Pasillo mercado", "Mercado"), ("Esquina NO", "Esquina SO"), ("Esquina NE", "Esquina SE"),
    ("Esquina SO", "Esquina SE"), ("Cebra plaza", "Cebra parque"), ("Cebra parque", "Esquina SO"),
    ("Cebra parque", "Entrada parque"), ("Entrada parque", "Laguna"), ("Entrada parque", "Camino este"),
    ("Camino este", "Picnic"), ("Picnic", "Sur parque"), ("Kiosco", "Laguna sur"),
    ("Laguna sur", "Sur laguna"), ("Sur laguna", "Oeste parque"), ("Sur laguna", "Sur parque"),
    ("Esquina SE", "Entrada terminal"), ("Entrada terminal", "Terminal"), ("Terminal", "Paradero"),
]
# Lugares donde el Bot puede plantar su antena (en tiles)
ANTENAS = [(12, 10), (36, 11), (61, 8), (37, 31), (3, 35), (61, 31), (8, 27), (24, 9)]

TECHO = {"rojo": 0, "gris": 8, "claro": 16, "beige": 24}
FACHADA = {"rojo": (148, 185, 407), "gris": (152, 189, 411), "beige": (156, 193, 415), "vitrina": (160, 197, 419)}

# Los árboles y arbustos verde oscuro de Kenney usan justo el verde del pasto: encima del pasto se veían
# huecos (solo el borde). Se pintan de verde pino para que se distingan.
PINO = {(64, 156, 98): (36, 122, 98), (48, 126, 77): (26, 94, 76), (75, 168, 109): (62, 154, 124),
        (61, 144, 91): (32, 112, 90)}
VERDE_PASTO = (403, 406, 440, 443, 514, 517)
_tiles_pino = {}
_arboles = {}


def repintar(img, cambios):
    img = img.copy()
    for y in range(img.get_height()):
        for x in range(img.get_width()):
            c = img.get_at((x, y))
            nuevo = cambios.get(tuple(c[:3]))
            if nuevo and c[3]:
                img.set_at((x, y), (*nuevo, c[3]))
    return img


def tile_cosa(i):
    """Tile de un objeto del barrio (árbol, arbusto...), en verde pino si era del color del pasto."""
    if i not in VERDE_PASTO:
        return C(i)
    if i not in _tiles_pino:
        _tiles_pino[i] = repintar(C(i), PINO)
    return _tiles_pino[i]


def imagen_arbol(tipo):
    """Árbol de 2 tiles. Todos los árboles del mismo tipo comparten la imagen."""
    if tipo not in _arboles:
        img = pygame.Surface((TILE, TILE * 2), pygame.SRCALPHA)
        img.blit(tile_cosa(401 + tipo), (0, 0))
        img.blit(tile_cosa(438 + tipo), (0, TILE))
        _arboles[tipo] = img
    return _arboles[tipo]


class Mapa:
    def __init__(self):
        self.suelo = [["g"] * W for _ in range(H)]
        self.solido = [[False] * W for _ in range(H)]
        self.capa = [[None] * W for _ in range(H)]        # tile extra encima del suelo (plano)
        self.rects = []                                    # colisiones pequeñas (pixeles nativos)
        self.props = []                                    # (imagen nativa, x, y_base) que se ordenan por y
        self.edificios = []
        self.carteles = []                                 # (texto, x, y) en pixeles nativos
        self.zonas = {}
        self.cebras = []                                   # rects en tiles
        self.semaforos = []
        self.luces = []                                    # puntos que brillan de noche
        self.lineas = []                                   # líneas blancas pintadas (x0, y0, x1, y1) en px
        self.ventanas_luz = []                             # ventanas que se encienden de noche (px)
        self._construir()
        # para las animaciones del barrio (en pixeles nativos)
        self.agua = [pygame.Rect(7 * TILE, 32 * TILE, 8 * TILE, 5 * TILE)]      # la laguna, sin el borde
        self.fuente = (28 * TILE, 11 * TILE + 8)                                 # punta de la estatua (chorro)
        self.superficie = self._dibujar_suelo()

    # ------------------------------------------------------------- utilidades de construcción
    def rect(self, x0, y0, x1, y1, codigo):
        for y in range(max(0, y0), min(H, y1 + 1)):
            for x in range(max(0, x0), min(W, x1 + 1)):
                self.suelo[y][x] = codigo

    def bloquear(self, x0, y0, x1, y1):
        for y in range(max(0, y0), min(H, y1 + 1)):
            for x in range(max(0, x0), min(W, x1 + 1)):
                self.solido[y][x] = True

    def edificio(self, x, y, w, h, color, fachada=None, puerta=None, ventanas=True, letrero=None):
        """Techo arriba (h-3 filas) y fachada de 3 filas abajo. Todo el edificio es sólido."""
        self.edificios.append((x, y, w, h, color, fachada or color, puerta, ventanas))
        self.bloquear(x, y, x + w - 1, y + h - 1)
        if letrero:
            self.carteles.append((letrero, (x + w / 2) * TILE, (y + h - 3) * TILE + 2))

    def arbol(self, x, y, tipo=0):
        """Árbol de 2 tiles; (x, y) es el tile del tronco."""
        self.props.append((imagen_arbol(tipo % 6), x * TILE, (y + 1) * TILE, "arbol"))
        self.rects.append(pygame.Rect(x * TILE + 4, y * TILE + 9, 8, 6))

    def poste(self, x, y):
        """Poste de luz de 3 tiles; (x, y) es el tile de la base."""
        img = pygame.Surface((TILE, TILE * 3), pygame.SRCALPHA)
        for k, i in enumerate((597, 634, 671)):
            img.blit(C(i), (0, k * TILE))
        self.props.append((img, x * TILE, (y + 1) * TILE, "poste"))
        self.rects.append(pygame.Rect(x * TILE + 6, y * TILE + 11, 4, 3))
        self.luces.append((x * TILE + 8, y * TILE + 2))

    def arbusto(self, x, y, tipo=0):
        self.capa[y][x] = 512 + tipo % 6
        self.rects.append(pygame.Rect(x * TILE + 2, y * TILE + 4, TILE - 4, TILE - 6))

    def bus(self, x, y):
        img = pygame.Surface((TILE * 2, TILE * 2), pygame.SRCALPHA)
        for dy, fila in enumerate(((447, 448), (474, 475))):
            for dx, i in enumerate(fila):
                img.blit(U(i), (dx * TILE, dy * TILE))
        self.props.append((img, x * TILE, (y + 2) * TILE, "bus"))
        self.rects.append(pygame.Rect(x * TILE + 3, y * TILE + 4, 2 * TILE - 6, 2 * TILE - 6))

    def objeto(self, x, y, tile, solido=True, alto=1):
        if alto == 1:
            self.capa[y][x] = tile
        else:
            img = pygame.Surface((TILE, TILE * alto), pygame.SRCALPHA)
            for k in range(alto):
                img.blit(C(tile + 37 * k), (0, k * TILE))
            self.props.append((img, x * TILE, (y + 1) * TILE, "objeto"))
        if solido:
            self.rects.append(pygame.Rect(x * TILE + 2, y * TILE + 6, TILE - 4, TILE - 7))

    # ------------------------------------------------------------- el diseño del barrio
    def _construir(self):
        # calles y andenes
        self.rect(0, AV_Y0 - 2, W - 1, AV_Y0 - 1, "a")
        self.rect(0, AV_Y1 + 1, W - 1, AV_Y1 + 2, "a")
        self.rect(CR_X0 - 2, 0, CR_X0 - 1, H - 1, "a")
        self.rect(CR_X1 + 1, 0, CR_X1 + 2, H - 1, "a")
        self.rect(0, AV_Y0, W - 1, AV_Y1, "r")
        self.rect(CR_X0, 0, CR_X1, H - 1, "r")
        self.cebras = [(CR_X0 - 2, AV_Y0, CR_X0 - 1, AV_Y1), (CR_X1 + 1, AV_Y0, CR_X1 + 2, AV_Y1),
                       (CR_X0, AV_Y0 - 2, CR_X1, AV_Y0 - 1), (CR_X0, AV_Y1 + 1, CR_X1, AV_Y1 + 2),
                       (22, AV_Y0, 23, AV_Y1)]
        self.semaforos = [(CR_X0 - 1, AV_Y0 - 1), (CR_X1 + 1, AV_Y1 + 1)]

        # ---------------- noroeste: colegio, alcaldía, plaza y casas
        self.zonas["Colegio"] = pygame.Rect(1, 7, 14, 10)
        self.edificio(2, 0, 12, 7, "beige", puerta=7, letrero="COLEGIO")
        self.rect(1, 8, 14, 16, "s")                      # patio de arena
        self.zonas["Alcaldia"] = pygame.Rect(17, 7, 22, 11)
        self.edificio(19, 0, 16, 8, "claro", fachada="gris", puerta=7, letrero="ALCALDIA")
        self.rect(16, 8, 39, 17, "p")                     # plaza
        self.rect(16, 7, 18, 7, "p")
        self.rect(35, 7, 39, 7, "p")
        self.edificio(37, 0, 5, 6, "rojo", puerta=2)
        for x in (0, 15, 36):
            for y in range(0, 7, 2):
                if not self.solido[y][x]:
                    self.arbol(x, y + 1, (x + y) % 6)
        # fuente con estatua en el centro de la plaza
        for dy, fila in enumerate(((177, 178), (214, 215), (251, 252))):
            for dx, i in enumerate(fila):
                self.capa[11 + dy][27 + dx] = i
        self.rects.append(pygame.Rect(27 * TILE + 1, 11 * TILE + 6, 2 * TILE - 2, 3 * TILE - 7))
        for x in (19, 34):
            self.poste(x, 10)
            self.poste(x, 16)
        for x, y in ((22, 12), (31, 12)):
            self.objeto(x, y, 572)
            self.objeto(x + 1, y, 573)
        for x in (17, 38):
            self.arbol(x, 13, 2)

        # ---------------- noreste: mercado
        self.zonas["Mercado"] = pygame.Rect(50, 7, 13, 10)
        self.edificio(50, 0, 13, 6, "claro", fachada="vitrina", puerta=6, letrero="MERCADO")
        self.rect(50, 6, 63, 17, "p")
        for k, x in enumerate((51, 55, 59)):
            for y in (9, 13):
                base = 357 if (k + y) % 2 else 360
                for dx in range(3):
                    self.capa[y][x + dx] = base + dx
                    self.capa[y + 1][x + dx] = 675 + (dx + k) % 5
                self.bloquear(x, y, x + 2, y + 1)

        # ---------------- suroeste: parque
        self.zonas["Parque"] = pygame.Rect(1, 26, 40, 19)
        self.zonas["Laguna"] = pygame.Rect(5, 30, 12, 9)
        self.rect(6, 31, 15, 37, "w")
        self.bloquear(6, 31, 15, 37)
        # caminos que serpentean
        for x0, y0, x1, y1 in ((22, 26, 23, 29), (12, 28, 23, 29), (12, 28, 13, 30), (24, 28, 33, 29),
                               (32, 28, 33, 40), (17, 39, 33, 40), (17, 33, 18, 40), (3, 39, 18, 40)):
            self.rect(x0, y0, x1, y1, "b")
        self.zonas["Kiosco"] = pygame.Rect(25, 31, 6, 6)
        self.edificio(26, 32, 4, 4, "rojo", fachada="rojo", puerta=1, letrero="NOTICIAS")
        for x, y, t in ((2, 27, 0), (4, 42, 1), (20, 31, 2), (21, 36, 3), (36, 27, 4), (38, 33, 5),
                        (36, 42, 0), (27, 43, 2), (9, 42, 3), (1, 33, 4), (40, 38, 1), (14, 26, 5)):
            self.arbol(x, y, t)
        for x, y in ((35, 30), (35, 36)):
            self.objeto(x, y, 553, alto=2)

        # ---------------- sureste: terminal
        self.zonas["Terminal"] = pygame.Rect(50, 26, 13, 19)
        self.rect(50, 26, 63, 33, "e")
        self.rect(50, 34, 63, 35, "a")
        self.edificio(51, 38, 6, 6, "gris", puerta=2, letrero="TERMINAL")
        self.edificio(58, 37, 5, 7, "rojo", puerta=2)
        for x in (50, 63):
            self.arbol(x, 44, 1)

        # ---------------- detalles: postes en los andenes, arbustos, bancas, canecas
        for x in (4, 13, 31, 38, 52, 60):
            self.poste(x, AV_Y0 - 2)
            self.poste(x, AV_Y1 + 2)
        for x in range(1, 15):
            if x not in (7, 8):
                self.arbusto(x, 17, x)
        # cancha pintada en el patio del colegio
        x0, y0, x1, y1 = 3 * TILE, 9 * TILE + 4, 13 * TILE, 16 * TILE - 4
        self.lineas += [(x0, y0, x1, y0), (x0, y1, x1, y1), (x0, y0, x0, y1), (x1, y0, x1, y1),
                        ((x0 + x1) // 2, y0, (x0 + x1) // 2, y1)]
        for x, y in ((21, 9), (33, 9), (54, 7), (41, 17), (26, 17), (3, 25), (60, 25)):
            self.objeto(x, y, 496)
        self.objeto(43, 17, 533)
        self.objeto(48, 26, 533)
        for x, y in ((20, 16), (30, 16)):
            for k in range(3):
                self.capa[y][x + k] = 179 + k
            self.rects.append(pygame.Rect(x * TILE + 1, y * TILE + 5, 3 * TILE - 2, TILE - 6))
        # parque: arbustos, bancas y materas
        for k, (x, y) in enumerate(((19, 27), (11, 27), (25, 30), (30, 30), (34, 38), (16, 38), (20, 41), (4, 37),
                                    (2, 30), (38, 29), (39, 41), (30, 41), (11, 41), (24, 34))):
            self.arbusto(x, y, k)
        for x, y in ((14, 30), (20, 38), (29, 38), (8, 38)):
            self.objeto(x, y, 572)
            self.objeto(x + 1, y, 573)
        # mercado: canecas de fruta y una matera
        for x, y in ((50, 12), (63, 12), (63, 16)):
            self.objeto(x, y, 675 + x % 5)
        # terminal: buses en sus bahías y la línea de parqueo
        for x in (51, 54, 57, 60):
            self.bus(x, 27)
            self.lineas.append(((x - 1) * TILE + 8, 26 * TILE + 2, (x - 1) * TILE + 8, 29 * TILE + 8))
        self.lineas.append(((63) * TILE + 8, 26 * TILE + 2, 63 * TILE + 8, 29 * TILE + 8))
        self.objeto(53, 34, 572)
        self.objeto(54, 34, 573)
        self.objeto(59, 34, 572)
        self.objeto(60, 34, 573)

        # borde inferior del mapa: fila de árboles
        for x in range(0, W, 3):
            if self.suelo[H - 1][x] not in ("r", "a"):
                self.arbol(x, H - 2, x % 6)

    # ------------------------------------------------------------- dibujo del suelo
    def _tile_suelo(self, x, y, rng):
        c = self.suelo[y][x]
        if c == "g":
            return 888 if rng.random() < 0.7 else 889
        if c == "a":
            return 704 if (x + y) % 3 else 741
        if c == "p":
            return 710 if (x + y) % 2 else 711
        if c == "b":
            return 707 if (x + y) % 2 else 744
        if c == "s":
            return 895
        if c in ("r", "e"):
            return 714
        if c == "w":
            return 888
        return 888

    def _dibujar_suelo(self):
        rng = random.Random(7)
        s = pygame.Surface((W * TILE, H * TILE), pygame.SRCALPHA)
        for y in range(H):
            for x in range(W):
                s.blit(C(self._tile_suelo(x, y, rng)), (x * TILE, y * TILE))
        self._pasto(s, rng)
        # laguna con borde de piedra (9 partes) y un borde oscuro alrededor
        self._nueve(s, 6, 31, 15, 37, ((174, 175, 176), (211, 212, 213), (248, 249, 250)))
        pygame.draw.rect(s, CONTORNO, pygame.Rect(6 * TILE - 1, 31 * TILE - 1, 10 * TILE + 2, 7 * TILE - 1), 1)
        # marcas de la calle (pintadas en pixel)
        blanco, amarillo = (236, 236, 236), (255, 204, 60)
        for x in range(0, W * TILE, 12):
            if not (CR_X0 * TILE - 4 <= x <= (CR_X1 + 1) * TILE):
                s.fill(amarillo, (x, (AV_Y0 + 2) * TILE - 1, 6, 2))
        for y in range(0, H * TILE, 12):
            if not (AV_Y0 * TILE - 4 <= y <= (AV_Y1 + 1) * TILE):
                s.fill(amarillo, ((CR_X0 + 2) * TILE - 1, y, 2, 6))
        for x0, y0, x1, y1 in self.cebras:
            horizontal = (x1 - x0) > (y1 - y0)
            for y in range(y0 * TILE, (y1 + 1) * TILE):
                for x in range(x0 * TILE, (x1 + 1) * TILE):
                    if (horizontal and (x // 4) % 2 == 0 and 2 <= (y % 32) <= 29) or \
                       (not horizontal and (y // 4) % 2 == 0 and 2 <= (x % 32) <= 29):
                        s.set_at((x, y), blanco)
        for x0, y0, x1, y1 in self.lineas:
            pygame.draw.line(s, (245, 245, 240), (x0, y0), (x1, y1), 1)
        # bordillo entre andén y calzada
        for y in range(H):
            for x in range(W):
                if self.suelo[y][x] != "r":
                    continue
                for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and self.suelo[ny][nx] == "a":
                        px, py = x * TILE, y * TILE
                        if dy == -1:
                            s.fill((180, 184, 196), (px, py, TILE, 2))
                            s.fill((60, 62, 70), (px, py + 2, TILE, 1))
                        elif dy == 1:
                            s.fill((180, 184, 196), (px, py + TILE - 2, TILE, 2))
                        elif dx == -1:
                            s.fill((180, 184, 196), (px, py, 2, TILE))
                        else:
                            s.fill((180, 184, 196), (px + TILE - 2, py, 2, TILE))
        # sombras en el piso: edificios (hacia abajo a la derecha) y lo que sobresale (árboles, postes, buses)
        sombras = pygame.Surface((W * TILE, H * TILE), pygame.SRCALPHA)
        for x, y, w, h, *_ in self.edificios:
            sombras.fill((0, 0, 0, 70), ((x + w) * TILE, y * TILE + 4, 4, h * TILE))
            sombras.fill((0, 0, 0, 55), (x * TILE + 4, (y + h) * TILE, w * TILE, 3))
        for img, px, yb, tipo in self.props:
            ancho = {"arbol": 12, "poste": 8, "bus": 30, "objeto": 12}[tipo]
            alto = 6 if tipo == "bus" else 4
            pygame.draw.ellipse(sombras, (0, 0, 0, 75), (px + (img.get_width() - ancho) // 2 + 2, yb - alto + 1,
                                                         ancho, alto))
        s.blit(sombras, (0, 0))
        # edificios y objetos planos (bancas, canecas, materas, puestos, la fuente) en capas aparte para
        # ponerles a todos un borde oscuro y una sombrita
        edif = pygame.Surface((W * TILE, H * TILE), pygame.SRCALPHA)
        for x, y, w, h, color, fachada, puerta, ventanas in self.edificios:
            self._edificio(edif, x, y, w, h, color, fachada, puerta, ventanas)
        self._con_borde(s, edif, sombra=False)
        planos = pygame.Surface((W * TILE, H * TILE), pygame.SRCALPHA)
        for y in range(H):
            for x in range(W):
                if self.capa[y][x] is not None:
                    planos.blit(tile_cosa(self.capa[y][x]), (x * TILE, y * TILE))
        self._con_borde(s, planos, sombra=True)
        return s

    @staticmethod
    def _con_borde(destino, capa, sombra):
        """Pega una capa con un borde oscuro de 1 pixel alrededor de cada forma (y, si se pide, una
        sombrita corrida hacia abajo)."""
        mascara = pygame.mask.from_surface(capa, 40)
        if sombra:
            destino.blit(mascara.to_surface(setcolor=(0, 0, 0, 70), unsetcolor=(0, 0, 0, 0)), (1, 2))
        sil = mascara.to_surface(setcolor=(*CONTORNO, 255), unsetcolor=(0, 0, 0, 0))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            destino.blit(sil, (dx, dy))
        destino.blit(capa, (0, 0))

    def _pasto(self, s, rng):
        """Textura del pasto (hojitas más claras y más oscuras) y un borde donde el pasto se encuentra
        con un andén, la plaza, la arena o un camino: así cada zona se ve recortada."""
        oscuro, claro, borde = (52, 134, 84), (92, 182, 116), (40, 108, 66)
        for y in range(H):
            for x in range(W):
                if self.suelo[y][x] != "g":
                    continue
                px, py = x * TILE, y * TILE
                for _ in range(3):
                    hx, hy = rng.randrange(1, TILE - 1), rng.randrange(1, TILE - 2)
                    s.fill(oscuro if rng.random() < 0.6 else claro, (px + hx, py + hy, 1, 2))
                for dx, dy, r in ((0, -1, (px, py, TILE, 1)), (0, 1, (px, py + TILE - 1, TILE, 1)),
                                  (-1, 0, (px, py, 1, TILE)), (1, 0, (px + TILE - 1, py, 1, TILE))):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and self.suelo[ny][nx] in ("a", "p", "b", "s", "e"):
                        s.fill(borde, r)

    def _nueve(self, s, x0, y0, x1, y1, ids):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                fy = 0 if y == y0 else 2 if y == y1 else 1
                fx = 0 if x == x0 else 2 if x == x1 else 1
                if fy == 1 and fx == 1:
                    # centro del agua liso con ondas (el tile original repite unas piedras)
                    agua = C(ids[0][1]).get_at((8, 12))
                    s.fill(agua, (x * TILE, y * TILE, TILE, TILE))
                    continue
                s.blit(C(ids[fy][fx]), (x * TILE, y * TILE))

    def _edificio(self, s, x, y, w, h, color, fachada, puerta, ventanas):
        base = TECHO[color]
        filas_techo = h - 3
        for fy in range(filas_techo):
            fila_t = 0 if fy == 0 else 111 if fy == filas_techo - 1 else (37 if fy % 2 else 74)
            for fx in range(w):
                col = 0 if fx == 0 else 3 if fx == w - 1 else 1 + fx % 2
                s.blit(C(base + fila_t + col), ((x + fx) * TILE, (y + fy) * TILE))
        corn, muro, abajo = FACHADA[fachada]
        yf = y + filas_techo
        for fx in range(w):
            col = 0 if fx == 0 else 3 if fx == w - 1 else 1 + fx % 2
            s.blit(C(corn + col), ((x + fx) * TILE, yf * TILE))
            s.blit(C(muro + col), ((x + fx) * TILE, (yf + 1) * TILE))
            s.blit(C(abajo + col), ((x + fx) * TILE, (yf + 2) * TILE))
            if ventanas and fachada != "vitrina" and 0 < fx < w - 1 and fx != puerta and fx % 2 == 1:
                s.blit(C(617), ((x + fx) * TILE, (yf + 1) * TILE))
                self.ventanas_luz.append(((x + fx) * TILE + 8, (yf + 1) * TILE + 8))
        if puerta is not None:
            s.blit(C(800), ((x + puerta) * TILE, (yf + 1) * TILE))
            s.blit(C(837), ((x + puerta) * TILE, (yf + 2) * TILE))

    # ------------------------------------------------------------- colisión
    def libre(self, r):
        """True si el rectángulo (pixeles nativos) no choca con nada fijo."""
        if r.left < 0 or r.top < 0 or r.right > W * TILE or r.bottom > H * TILE:
            return False
        for ty in range(r.top // TILE, (r.bottom - 1) // TILE + 1):
            for tx in range(r.left // TILE, (r.right - 1) // TILE + 1):
                if self.solido[ty][tx]:
                    return False
        return r.collidelist(self.rects) == -1

    def es_calzada(self, px, py):
        tx, ty = int(px // TILE), int(py // TILE)
        return 0 <= tx < W and 0 <= ty < H and self.suelo[ty][tx] == "r"
