"""Partículas, confeti, números flotantes y curvas de animación."""
import math
import random

import pygame

from .tema import TEMA
from .widgets import texto

CONFETI = [(255, 194, 61), (108, 77, 245), (255, 111, 97), (46, 196, 182), (107, 203, 119), (255, 95, 162)]


def suave(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def rebote(t: float) -> float:
    t = max(0.0, min(1.0, t))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def acercar(actual: float, objetivo: float, k: float = 0.18) -> float:
    return actual + (objetivo - actual) * k


class Efectos:
    def __init__(self):
        self.particulas = []
        self.flotantes = []
        self.rng = random.Random()
        self.sacudida_t0 = -10_000

    def confeti(self, x, y, n=60, fuerza=7.0, colores=CONFETI):
        if TEMA.op["menos_movimiento"]:
            n //= 4
        for _ in range(n):
            a = self.rng.uniform(-math.pi, 0)
            v = self.rng.uniform(fuerza * 0.4, fuerza)
            self.particulas.append(dict(x=x, y=y, vx=math.cos(a) * v, vy=math.sin(a) * v - 2,
                                        g=0.22, vida=self.rng.randint(60, 110), edad=0,
                                        color=self.rng.choice(colores), tam=self.rng.randint(5, 9),
                                        rot=self.rng.uniform(0, 6), vr=self.rng.uniform(-0.3, 0.3), tipo="papel"))

    def chispas(self, x, y, color, n=14):
        if TEMA.op["menos_movimiento"]:
            n //= 3
        for _ in range(n):
            a = self.rng.uniform(0, 2 * math.pi)
            v = self.rng.uniform(1.5, 4)
            self.particulas.append(dict(x=x, y=y, vx=math.cos(a) * v, vy=math.sin(a) * v, g=0.05,
                                        vida=self.rng.randint(22, 40), edad=0, color=color,
                                        tam=self.rng.randint(3, 5), rot=0, vr=0, tipo="punto"))

    def flotante(self, x, y, s, color, tam=22):
        self.flotantes.append(dict(x=x, y=y, s=s, color=color, tam=tam, t0=pygame.time.get_ticks()))

    def sacudir(self):
        if not TEMA.op["menos_movimiento"]:
            self.sacudida_t0 = pygame.time.get_ticks()

    def desfase(self):
        e = (pygame.time.get_ticks() - self.sacudida_t0) / 1000
        if e > 0.35:
            return 0, 0
        f = (1 - e / 0.35) * 6
        return round(math.sin(e * 90) * f), round(math.cos(e * 70) * f * 0.5)

    def dibujar(self, sup):
        vivas = []
        for p in self.particulas:
            p["edad"] += 1
            if p["edad"] > p["vida"]:
                continue
            p["vy"] += p["g"]
            p["vx"] *= 0.985
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["rot"] += p["vr"]
            alpha = 255 if p["edad"] < p["vida"] * 0.7 else int(255 * (p["vida"] - p["edad"]) / (p["vida"] * 0.3))
            if p["tipo"] == "papel":
                w = abs(math.cos(p["rot"])) * p["tam"] + 2
                r = pygame.Rect(0, 0, w, p["tam"] * 0.6 + 2)
                r.center = (p["x"], p["y"])
                s = pygame.Surface(r.size, pygame.SRCALPHA)
                s.fill((*p["color"], alpha))
                sup.blit(s, r)
            else:
                s = pygame.Surface((p["tam"] * 2, p["tam"] * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*p["color"], alpha), (p["tam"], p["tam"]), p["tam"])
                sup.blit(s, (p["x"] - p["tam"], p["y"] - p["tam"]))
            vivas.append(p)
        self.particulas = vivas
        ahora = pygame.time.get_ticks()
        quedan = []
        for f in self.flotantes:
            e = (ahora - f["t0"]) / 1300
            if e >= 1:
                continue
            alpha = 255 if e < 0.6 else int(255 * (1 - e) / 0.4)
            dy = -46 * suave(e)
            c = TEMA.c
            for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
                texto(sup, f["s"], (f["x"] + ox, f["y"] + dy + oy), f["tam"], c["papel"], peso=700,
                      fam="titulo", ancla="c", alpha=alpha)
            texto(sup, f["s"], (f["x"], f["y"] + dy), f["tam"], f["color"], peso=700, fam="titulo",
                  ancla="c", alpha=alpha)
            quedan.append(f)
        self.flotantes = quedan


EFECTOS = Efectos()
