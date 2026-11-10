"""La historia de Ciudad Nova en 3 escenas cortas (se puede saltar con ESPACIO)."""
import math

import pygame

from .. import personajes, sprites
from ..config import ALTO, ANCHO
from ..partida import CANDIDATOS
from ..personajes import ORDEN, PERSONAJES
from ..recursos import borde, escalar
from ..ui import panel, texto
from .base import Escena, FondoCiudad, con_mando, es_aceptar


ESCENAS = [
    ("Ciudad Nova va a elegir alcalde", "Los candidatos hablan con la gente por la red social Civitas."),
    ("Pero el Bot de Emilio llena Civitas de BULOS", "Rumores falsos que se suben a la cabeza y vuelven morada a la gente."),
    ("¡Los Cazabulos al rescate!", "Atrapa los Bulos, cura a los vecinos morados y comparte la verdad."),
]


class Historia(Escena):
    def __init__(self, app, siguiente):
        super().__init__(app)
        self.siguiente = siguiente
        self.fondo = FondoCiudad(app, 150)
        self.k = 0
        self.t_esc = 0.0

    def evento(self, e):
        if es_aceptar(e) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            self.app.son.tocar("click")
            self._avanzar()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self._terminar()

    def _avanzar(self):
        self.k += 1
        self.t_esc = 0.0
        if self.k >= len(ESCENAS):
            self._terminar()

    def _terminar(self):
        self.app.op["historia_vista"] = True
        self.app.guardar_opciones()
        self.app.cambiar(self.siguiente)

    def actualizar(self, dt):
        super().actualizar(dt)
        self.t_esc += dt
        if self.t_esc > 5.5:
            self._avanzar()

    def dibujar(self, pant):
        self.fondo.dibujar(pant, 1 / 60)
        if self.k >= len(ESCENAS):
            return
        titulo, sub = ESCENAS[self.k]
        entra = min(1.0, self.t_esc / 0.4)
        y = int(70 - (1 - entra) * 30)
        texto(pant, titulo, (ANCHO // 2, y), 48, (255, 205, 50), "midtop", grosor=3, alfa=int(255 * entra))
        texto(pant, sub, (ANCHO // 2, y + 70), 24, (255, 255, 255), "midtop", 600, alfa=int(255 * entra))
        getattr(self, f"_e{self.k}")(pant)
        for i in range(len(ESCENAS)):
            pygame.draw.circle(pant, (255, 205, 50) if i == self.k else (90, 80, 140), (ANCHO // 2 - 30 + i * 30, ALTO - 70), 8)
        texto(pant, con_mando(self.app, "ESPACIO para seguir  ·  ESC para saltar"), (ANCHO // 2, ALTO - 34), 18, (220, 214, 240), "center", 600)

    def _e0(self, pant):
        cands = ["Lucia", "Marcos", "Elena", "Emilio"]
        from .final import _figura_candidato
        for i, c in enumerate(cands):
            x = 230 + i * 270
            aparece = self.t_esc > 0.3 + i * 0.35
            if not aparece:
                continue
            nombre, lema, color = CANDIDATOS[c]
            fig = _figura_candidato(c)
            dy = math.sin(self.t * 3 + i) * 5
            panel(pant, (x - 115, 230, 230, 300), borde=color)
            pant.blit(fig, fig.get_rect(midbottom=(x, 420 + dy)))
            texto(pant, nombre, (x, 438), 26, color, "midtop")
            texto(pant, lema, (x, 474), 15, (230, 226, 245), "midtop", 600)

    def _e1(self, pant):
        cx, cy = ANCHO // 2, 430
        img = pygame.transform.scale(sprites.antena(int(self.t * 3) % 2 == 0), (16 * 6, 40 * 6))
        pant.blit(img, img.get_rect(midbottom=(cx, cy + 120)))
        for k in range(3):
            r = ((self.t * 120 + k * 60) % 180) + 30
            s = pygame.Surface((int(r * 2), int(r * 2)), pygame.SRCALPHA)
            pygame.draw.arc(s, (190, 120, 255, int(255 * (1 - r / 210))), s.get_rect(), math.radians(30), math.radians(150), 6)
            pant.blit(s, (cx - r, cy - 110 - r))
        for i in range(7):
            a = self.t * 0.8 + i * math.tau / 7
            x = cx + math.cos(a) * (260 + 30 * math.sin(self.t * 2 + i))
            y = cy - 40 + math.sin(a) * 120
            b = escalar(borde(sprites.bulo(int(self.t * 4 + i) % 2, i == 0, False, (1 if math.cos(a) < 0 else -1, 0))), 4)
            pant.blit(b, b.get_rect(center=(x, y)))
        for i, (tipo, var) in enumerate(((1, 0), (4, 1), (2, 2), (0, 1))):
            x = 180 + i * 300 if i < 2 else 180 + i * 300
            v = sprites.morado(sprites.vecino(tipo, var, "abajo", 0))
            img = escalar(borde(v), 5)
            pant.blit(img, img.get_rect(midbottom=(x, 640)))
            b = escalar(borde(sprites.bulo(int(self.t * 3 + i) % 2)), 3)
            pant.blit(b, b.get_rect(midbottom=(x, 640 - 80 + math.sin(self.t * 4 + i) * 3)))

    def _e2(self, pant):
        for i, clave in enumerate(ORDEN):
            aparece = self.t_esc > 0.2 + i * 0.3
            if not aparece:
                continue
            cs = personajes.cuadros(clave)
            cuadro = int(self.t * 7 + i) % 4
            img = pygame.transform.scale(cs["abajo"][cuadro], (16 * 9, 24 * 9))
            x = 220 + i * 280
            salto = abs(math.sin(self.t * 4 + i)) * 20
            pygame.draw.ellipse(pant, (0, 0, 0), (x - 60, 610, 120, 24))
            pygame.draw.ellipse(pant, PERSONAJES[clave]["color"], (x - 72, 604, 144, 36), 5)
            pant.blit(img, img.get_rect(midbottom=(x, 624 - salto)))
            texto(pant, PERSONAJES[clave]["nombre"], (x, 360 - salto), 28, PERSONAJES[clave]["color"], "midbottom")
