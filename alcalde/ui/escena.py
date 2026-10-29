"""Fondos ilustrados: cielo, sol, nubes y el horizonte de Ciudad Nova con gente caminando."""
import math
import random

import pygame

from ..modelo.apariencia import look_aleatorio
from . import edificios, personajes
from .tema import TEMA
from .widgets import texto

_cache = {}


def _degradado(w, h, arriba, abajo):
    clave = (w, h, arriba, abajo)
    if clave not in _cache:
        s = pygame.Surface((w, h))
        for y in range(h):
            t = y / max(1, h - 1)
            s.fill([round(a + (b - a) * t) for a, b in zip(arriba, abajo)], (0, y, w, 1))
        _cache[clave] = s
    return _cache[clave]


def mezclar(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def cielo(sup, noche: float = 0.0, rect=None):
    c = TEMA.c
    rect = pygame.Rect(rect or sup.get_rect())
    if TEMA.alto_contraste:
        sup.fill(c["papel"], rect)
        return
    arriba = mezclar(c["cielo1"], (34, 36, 92), noche)
    abajo = mezclar(c["cielo2"], (110, 88, 170), noche)
    sup.blit(_degradado(rect.w, rect.h, arriba, abajo), rect)


def texto_contorno(sup, s, pos, tam, color, contorno, grosor=4, fam="titulo", peso=700, ancla="c"):
    for dx in range(-grosor, grosor + 1, 2):
        for dy in range(-grosor, grosor + 1, 2):
            if dx or dy:
                texto(sup, s, (pos[0] + dx, pos[1] + dy), tam, contorno, peso=peso, fam=fam, ancla=ancla)
    texto(sup, s, (pos[0], pos[1] + grosor + 1), tam, contorno, peso=peso, fam=fam, ancla=ancla)
    return texto(sup, s, pos, tam, color, peso=peso, fam=fam, ancla=ancla)


class Escena:
    """Sol, nubes y horizonte con ciudadanos que pasean (para menú y pantallas de configuración)."""

    def __init__(self, semilla=5, gente=7, y_suelo=600):
        rng = random.Random(semilla)
        self.y_suelo = y_suelo
        self.nubes = [[rng.uniform(0, 1280), rng.uniform(40, 260), rng.uniform(0.12, 0.35), rng.randint(110, 190)]
                      for _ in range(6)]
        self.gente = []
        for i in range(gente):
            self.gente.append(dict(look=look_aleatorio(rng, i % 2 == 0), x=rng.uniform(0, 1280),
                                   v=rng.choice([-1, 1]) * rng.uniform(0.5, 1.1), fase=rng.uniform(0, 6),
                                   alto=rng.randint(64, 78)))
        self.edificios = [("barrio", 30, 200), ("colegio", 220, 190), ("alcaldia", 520, 240),
                          ("plaza", 760, 190), ("hospital", 940, 180), ("barrio2", 1100, 190)]
        self.arboles = [(185, False), (470, True), (735, False), (905, True), (1250, False), (12, True)]

    def dibujar(self, sup, noche=0.0, sol=True):
        c = TEMA.c
        t = pygame.time.get_ticks() / 1000
        mov = not TEMA.op["menos_movimiento"]
        cielo(sup, noche)
        if sol and not TEMA.alto_contraste:
            cx, cy = 1196, 70
            capa = pygame.Surface((300, 300), pygame.SRCALPHA)
            for k in range(12):
                a = k * math.pi / 6 + (t * 0.15 if mov else 0)
                p1 = (150 + math.cos(a) * 70, 150 + math.sin(a) * 70)
                p2 = (150 + math.cos(a) * 120, 150 + math.sin(a) * 120)
                pygame.draw.line(capa, (255, 236, 160, 150), p1, p2, 10)
            sup.blit(capa, (cx - 150, cy - 150))
            pygame.draw.circle(sup, (255, 214, 90), (cx, cy), 58)
            pygame.draw.circle(sup, c["tinta"], (cx, cy), 58, 4)
        for n in self.nubes:
            if mov:
                n[0] = (n[0] + n[2]) % 1480
            sup.blit(edificios.nube(n[3]), (n[0] - 200, n[1]))
        suelo = self.y_suelo
        for tipo, x, w in self.edificios:
            img = edificios.edificio(tipo, w)
            sup.blit(img, (x, suelo - img.get_height() + 18))
        for x, palma in self.arboles:
            img = edificios.arbolito(70 if palma else 64, palma)
            sup.blit(img, (x - 30, suelo - img.get_height() + 16))
        pygame.draw.rect(sup, c["pasto"], (0, suelo + 10, 1280, 720 - suelo))
        pygame.draw.line(sup, c["tinta"], (0, suelo + 10), (1280, suelo + 10), 3)
        pygame.draw.rect(sup, c["calle"], (0, suelo + 44, 1280, 46))
        pygame.draw.line(sup, c["tinta"], (0, suelo + 44), (1280, suelo + 44), 3)
        pygame.draw.line(sup, c["tinta"], (0, suelo + 90), (1280, suelo + 90), 3)
        for x in range(-40, 1320, 80):
            pygame.draw.rect(sup, c["papel"], (x, suelo + 64, 40, 6), border_radius=3)
        for g in sorted(self.gente, key=lambda g: g["alto"]):
            if mov:
                g["x"] += g["v"]
                if g["x"] > 1330:
                    g["x"] = -50
                elif g["x"] < -50:
                    g["x"] = 1330
            paso = abs(math.sin(t * 6 + g["fase"])) * 4 if mov else 0
            img = personajes.cuerpo(g["look"], "npc", "neutral", alto=g["alto"],
                                    parpadeo=(int(t * 2 + g["fase"]) % 9 == 0))
            if g["v"] < 0:
                img = pygame.transform.flip(img, True, False)
            pies = suelo + 40 + (g["alto"] - 64) * 0.5
            sup.blit(img, (g["x"] - img.get_width() / 2, pies - img.get_height() - paso))
