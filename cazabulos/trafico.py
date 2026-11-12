"""Carros que andan por su carril, paran en el semáforo y frenan ante los peatones.

Cada carril mide 2 tiles (32 px) y el carro va siempre alineado al carril, así nunca se
monta en el andén. Los carros de lado usan bloques de 3x2 tiles y los de arriba de 2x2.
"""
import random

import pygame

from .config import TILE
from .mapa import AV_Y0, AV_Y1, CR_X0, CR_X1, H, W
from .recursos import bloque

# (color) -> bloques por dirección
_SPRITES = {
    "verde": {"izq": [[623, 624, 625], [660, 661, 662]], "der": [[626, 627, 628], [663, 664, 665]],
              "arriba": [[697, 698], [734, 735]], "abajo": [[699, 700], [736, 737]]},
    "gris": {"izq": [[771, 772, 773], [808, 809, 810]], "der": [[774, 775, 776], [811, 812, 813]],
             "arriba": [[845, 846], [882, 883]], "abajo": [[847, 848], [884, 885]]},
    "naranja": {"izq": [[919, 920, 921], [956, 957, 958]], "der": [[922, 923, 924], [959, 960, 961]],
                "arriba": [[993, 994], [1030, 1031]], "abajo": [[995, 996], [1032, 1033]]},
}
_cache = {}


def sprite(color, direccion):
    clave = (color, direccion)
    if clave not in _cache:
        _cache[clave] = bloque(_SPRITES[color][direccion])
    return _cache[clave]


class Carril:
    def __init__(self, direccion, fija, eje):
        self.dir = direccion          # izq, der, arriba, abajo
        self.fija = fija              # coordenada fija del carril (borde superior o izquierdo, px)
        self.eje = eje                # "h" o "v"
        self.signo = 1 if direccion in ("der", "abajo") else -1
        if eje == "h":
            self.pare = (CR_X0 - 2) * TILE if self.signo > 0 else (CR_X1 + 3) * TILE
        else:
            self.pare = (AV_Y0 - 2) * TILE if self.signo > 0 else (AV_Y1 + 3) * TILE


CARRILES = [
    Carril("izq", AV_Y0 * TILE, "h"), Carril("der", (AV_Y0 + 2) * TILE, "h"),
    Carril("abajo", CR_X0 * TILE, "v"), Carril("arriba", (CR_X0 + 2) * TILE, "v"),
]


class Carro:
    def __init__(self, carril, color, pos, velocidad):
        self.carril = carril
        self.color = color
        self.pos = pos                # coordenada a lo largo del carril (borde trasero/izquierdo del bloque)
        self.vel_max = velocidad
        self.vel = velocidad
        self.pito = 0.0               # > 0 mientras pita (para el subtítulo del sonido)
        img = sprite(color, carril.dir)
        self.largo = img.get_width() if carril.eje == "h" else img.get_height()

    @property
    def img(self):
        return sprite(self.color, self.carril.dir)

    def rect(self):
        c = self.carril
        if c.eje == "h":
            return pygame.Rect(int(self.pos) + 6, c.fija + 8, self.largo - 12, 22)
        return pygame.Rect(c.fija + 5, int(self.pos) + 2, 22, self.largo - 4)

    def topleft(self):
        c = self.carril
        return (self.pos, c.fija) if c.eje == "h" else (c.fija, self.pos)

    def frente(self):
        return self.pos + self.largo if self.carril.signo > 0 else self.pos

    def zona_delante(self, dist=18):
        r = self.rect()
        c = self.carril
        if c.eje == "h":
            return pygame.Rect(r.right, r.top, dist, r.height) if c.signo > 0 else pygame.Rect(r.left - dist, r.top, dist, r.height)
        return pygame.Rect(r.left, r.bottom, r.width, dist) if c.signo > 0 else pygame.Rect(r.left, r.top - dist, r.width, dist)


class Trafico:
    """Semáforo de 4 fases y carros en los 4 carriles."""
    CICLO = (("h", 7.0), ("rojo", 3.5), ("v", 6.0), ("rojo", 3.5))
    # caja del cruce (con las cebras): nadie entra si hay un carro del otro sentido adentro
    CRUCE = pygame.Rect((CR_X0 - 2) * TILE, (AV_Y0 - 2) * TILE, (CR_X1 - CR_X0 + 5) * TILE, (AV_Y1 - AV_Y0 + 5) * TILE)

    def __init__(self, semilla=1, cantidad=3):
        self.rng = random.Random(semilla)
        self.carros = []
        self.t_fase = 0.0
        self.fase = 0
        self.espera = {id(c): self.rng.uniform(0.5, 4.0) for c in CARRILES}
        self.cantidad = cantidad
        largo_h, largo_v = W * TILE, H * TILE
        for c in CARRILES:
            total = largo_h if c.eje == "h" else largo_v
            for k in range(cantidad - 1):
                pos = self.rng.uniform(0.05, 0.3) * total if self.rng.random() < 0.5 else self.rng.uniform(0.75, 0.95) * total
                self._agregar(c, pos=pos)

    @property
    def verde(self):
        return self.CICLO[self.fase][0]

    def _agregar(self, carril, pos=None):
        color = self.rng.choice(list(_SPRITES))
        carro = Carro(carril, color, 0, self.rng.uniform(46, 62))
        total = (W if carril.eje == "h" else H) * TILE
        if pos is None:
            pos = -carro.largo - 4 if carril.signo > 0 else total + 4
        carro.pos = pos
        if any(o.carril is carril and abs(o.pos - pos) < carro.largo + 12 for o in self.carros):
            return False
        self.carros.append(carro)
        return True

    def actualizar(self, dt, peatones=()):
        self.t_fase += dt
        if self.t_fase >= self.CICLO[self.fase][1]:
            self.t_fase = 0.0
            self.fase = (self.fase + 1) % len(self.CICLO)
        for c in CARRILES:
            self.espera[id(c)] -= dt
            if self.espera[id(c)] <= 0 and sum(1 for k in self.carros if k.carril is c) < self.cantidad:
                if self._agregar(c):
                    self.espera[id(c)] = self.rng.uniform(2.5, 6.0)
        for carro in self.carros:
            self._mover(carro, dt, peatones)
        total = {"h": W * TILE, "v": H * TILE}
        self.carros = [k for k in self.carros if -80 <= k.pos <= total[k.carril.eje] + 80]

    def _mover(self, carro, dt, peatones):
        c = carro.carril
        frenar = False
        # semáforo: si está en rojo para su eje y aún no pasa la línea de pare, se detiene en ella
        if self.verde != c.eje:
            antes = carro.frente() <= c.pare if c.signo > 0 else carro.frente() >= c.pare
            if antes and abs(carro.frente() - c.pare) < 26:
                frenar = True
        # el cruce ocupado por un carro del otro eje
        antes = carro.frente() <= c.pare if c.signo > 0 else carro.frente() >= c.pare
        if antes and abs(carro.frente() - c.pare) < 26:
            if any(o.carril.eje != c.eje and o.rect().colliderect(self.CRUCE) for o in self.carros):
                frenar = True
        # el carro de adelante
        for otro in self.carros:
            if otro is carro or otro.carril is not c:
                continue
            delta = (otro.pos - carro.pos) * c.signo
            if 0 < delta < carro.largo + 10:
                frenar = True
        # peatones adelante: frena y pita
        delante = carro.zona_delante()
        if any(delante.colliderect(p) for p in peatones):
            frenar = True
            carro.pito = 0.6
        carro.pito = max(0.0, carro.pito - dt)
        objetivo = 0.0 if frenar else carro.vel_max
        carro.vel += (objetivo - carro.vel) * min(1.0, dt * (8 if frenar else 2))
        carro.pos += carro.vel * c.signo * dt

    def rects(self):
        return [k.rect() for k in self.carros]
