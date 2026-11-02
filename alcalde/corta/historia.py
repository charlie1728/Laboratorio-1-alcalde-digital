"""La historia de Ciudad Nova, contada en cinco escenas antes de la primera campaña.

Cada escena se dibuja con las mismas piezas del juego (el barrio de fondo, los personajes, las tarjetas)
y el texto aparece letra por letra. Clic, Espacio o Enter pasan a la siguiente; Esc la salta.
"""
from __future__ import annotations

import math
import random

import pygame

from ..ui import personajes
from ..ui.dibujo import BLANCO, LILA, MANGO, ROJO, TINTA, TINTA2, circulo, icono, mezclar, pildora, rebote, texto
from .ciudad import Fondo
from .comunes import Boton, Escala, partir, titulo_grande
from .contenido import CANDIDATOS
from .pantalla_mapa import LOOK_CANDIDATO
from .pantalla_nivel import CARAS

AZUL_OK = (29, 155, 240)
ESCENAS = [
    ("Ciudad Nova va a elegir alcalde. Cuatro candidatos quieren ganar y faltan pocos días para votar.", "ciudad"),
    ("Todos se informan en Civitas, la red social de la ciudad. Lo que alguien comparte les llega a sus seguidores.",
     "civitas"),
    ("Pero apareció el Bot Supremo: llena Civitas de mentiras para que gane su candidato, Emilio.", "bot"),
    ("Los rumores enferman los barrios. La gente se asusta, pelea y deja de confiar en los demás.", "enfermo"),
    ("Tú y Civi pueden salvar la ciudad: corta lo falso, deja pasar lo verdadero y verifica antes de compartir.",
     "heroe"),
]
VEL_LETRAS = 38          # letras por segundo


class PantallaHistoria:
    def __init__(self, app, personaje: dict, al_terminar):
        self.app = app
        self.p = personaje
        self.al_terminar = al_terminar
        self.i = 0
        self.t = 0.0
        self.t_escena = 0.0
        self.tam = None
        self.btn_saltar = Boton("Saltar", "saltar", (236, 238, 248), "skip-forward", tecla=pygame.K_ESCAPE)
        self.btn_seguir = Boton("Siguiente", "seguir", MANGO, "chevron-right",
                                tecla=[pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT])
        app.sonar("turno")

    def _terminar(self):
        cb, self.al_terminar = self.al_terminar, None
        if cb:
            cb()

    def _siguiente(self):
        largo = len(ESCENAS[self.i][0])
        if self.t_escena * VEL_LETRAS < largo:
            self.t_escena = largo / VEL_LETRAS + 0.01          # primero termina de escribir el texto
            return
        self.app.sonar("click")
        if self.i + 1 >= len(ESCENAS):
            self._terminar()
        else:
            self.i += 1
            self.t_escena = 0.0

    def evento(self, e):
        if self.btn_saltar.toca(e):
            self._terminar()
        elif self.btn_seguir.toca(e) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1):
            self._siguiente()

    def actualizar(self, dt):
        self.t += dt
        self.t_escena += dt

    # -------------------------------------------------------------- dibujo
    def _preparar(self, sup):
        if sup.get_size() != self.tam:
            self.tam = sup.get_size()
            W, H = self.tam
            U = H / 720
            self.U = U
            self.sano = Fondo("PLAZA", W, H, U, semilla=5)
            self.enfermo = Fondo("NORTE", W, H, U, semilla=6)

    def dibujar(self, sup):
        self._preparar(sup)
        E = Escala(sup)
        U = E.U
        texto_escena, tipo = ESCENAS[self.i]
        noche = tipo in ("bot", "enfermo")
        arriba, abajo = ((50, 36, 110), (150, 90, 160)) if noche else ((110, 200, 245), (220, 240, 255))
        for y in range(0, E.H, 4):
            pygame.draw.rect(sup, mezclar(arriba, abajo, y / E.H), (0, y, E.W, 4))
        getattr(self, "_" + tipo)(sup, E, U)
        # el texto de abajo, letra por letra
        caja = pygame.Rect(E.x(140), E.y(560), 1000 * U, 130 * U)
        pildora(sup, caja, BLANCO, round(28 * U))
        civi = personajes.civi("feliz", round(120 * U), parpadeo=int(self.t * 3) % 11 == 0,
                               ala=math.sin(self.t * 3) * 0.3)
        sup.blit(civi, (caja.x - 70 * U, caja.y - 40 * U))
        n = int(self.t_escena * VEL_LETRAS)
        visible = texto_escena[:n]
        for j, linea in enumerate(partir(visible, 22 * U, caja.w - 260 * U, 900)[:3]):
            texto(sup, linea, (caja.x + 60 * U, caja.y + 34 * U + j * 30 * U), 22 * U, TINTA, 900, ancla="midleft")
        listo = n >= len(texto_escena)
        self.btn_seguir.etiqueta = "¡A jugar!" if self.i == len(ESCENAS) - 1 else "Siguiente"
        self.btn_seguir.latir = listo
        self.btn_seguir.dibujar(sup, pygame.Rect(caja.right - 200 * U, caja.bottom - 78 * U, 180 * U, 60 * U), self.t)
        for j in range(len(ESCENAS)):
            circulo(sup, (caja.centerx - (len(ESCENAS) - 1) * 12 * U + j * 24 * U, caja.bottom + 18 * U), 6 * U,
                    MANGO if j == self.i else (200, 196, 230))
        self.btn_saltar.dibujar(sup, E.r(1280 - 190, 20, 170, 54), self.t)

    def _entrada(self, demora=0.0):
        return rebote(min(1, max(0, self.t_escena - demora) / 0.5))

    def _ciudad(self, sup, E, U):
        self.sano.dibujar(sup, 0.0)
        titulo_grande(sup, "Ciudad Nova", (E.W / 2, 90 * U), 70 * U * self._entrada())
        for i, c in enumerate(CANDIDATOS):
            k = self._entrada(0.2 + i * 0.15)
            x = E.x(340 + i * 200)
            img = personajes.cuerpo(LOOK_CANDIDATO[c["id"]], "candidato", "feliz", round(190 * U * k))
            y = E.y(420) - img.get_height() + math.sin(self.t * 2 + i) * 4 * U
            sup.blit(img, (x - img.get_width() / 2, y))
            # el atril con el nombre
            pygame.draw.rect(sup, c["color"], (x - 80 * U, E.y(400), 160 * U, 70 * U), border_radius=round(12 * U))
            texto(sup, c["nombre"], (x, E.y(424)), 17 * U, BLANCO, 700, "titulo")
            texto(sup, c["lema"] if not c.get("bot") else "Cadenas y bots", (x, E.y(448)), 12 * U, BLANCO, 900)

    def _civitas(self, sup, E, U):
        self.sano.dibujar(sup, 0.0)
        k = self._entrada()
        tel = pygame.Rect(0, 0, 300 * U * k, 440 * U * k)
        tel.center = (E.W / 2, E.y(300))
        pygame.draw.rect(sup, TINTA, tel, border_radius=round(40 * U))
        pantalla = tel.inflate(-24 * U, -60 * U)
        pygame.draw.rect(sup, (244, 245, 255), pantalla, border_radius=round(24 * U))
        if k > 0.9:
            texto(sup, "Civitas", (pantalla.centerx, pantalla.y + 26 * U), 24 * U, LILA, 700, "titulo")
            for j in range(3):
                d = self._entrada(0.4 + j * 0.3)
                r = pygame.Rect(pantalla.x + 14 * U, pantalla.y + 56 * U + j * 106 * U, (pantalla.w - 28 * U) * d,
                                94 * U)
                pygame.draw.rect(sup, BLANCO, r, border_radius=round(16 * U))
                if d > 0.8:
                    av = personajes.avatar(CARAS[j * 5], round(40 * U), (236, 231, 255))
                    sup.blit(av, (r.x + 10 * U, r.y + 10 * U))
                    pygame.draw.rect(sup, (210, 212, 230), (r.x + 60 * U, r.y + 18 * U, 120 * U, 10 * U),
                                     border_radius=round(5 * U))
                    circulo(sup, (r.x + 194 * U, r.y + 23 * U), 8 * U, AZUL_OK)
                    for q in range(2):
                        pygame.draw.rect(sup, (226, 228, 240), (r.x + 60 * U, r.y + 42 * U + q * 18 * U,
                                                                 (r.w - 76 * U) * (1 - q * 0.3), 10 * U),
                                         border_radius=round(5 * U))
        # vecinos alrededor, felices, con flechas que muestran que la publicación les llega
        for i in range(6):
            lado = -1 if i < 3 else 1
            x = E.W / 2 + lado * (260 + (i % 3) * 110) * U
            y = E.y(300 + (i % 3 - 1) * 110)
            img = personajes.avatar(CARAS[i + 3], round(64 * U), (236, 231, 255), "npc", "feliz")
            sup.blit(img, img.get_rect(center=(x, y)))
            f = (self.t_escena * 0.8 + i * 0.17) % 1
            ax = tel.centerx + lado * tel.w / 2
            px = ax + (x - ax) * f
            py = tel.centery + (y - tel.centery) * f
            circulo(sup, (px, py), 6 * U, MANGO)

    def _bot(self, sup, E, U):
        self.enfermo.dibujar(sup, 0.6)
        k = self._entrada()
        aura = pygame.Surface((round(420 * U), round(420 * U)), pygame.SRCALPHA)
        pygame.draw.circle(aura, (255, 60, 90, 90), (aura.get_width() // 2, aura.get_height() // 2),
                           round(200 * U * (0.9 + 0.1 * math.sin(self.t * 4))))
        sup.blit(aura, aura.get_rect(center=(E.W / 2, E.y(250))))
        img = personajes.cuerpo({}, "npc", "enojado", round(300 * U * k), bot=True)
        sup.blit(img, img.get_rect(center=(E.W / 2, E.y(250) + math.sin(self.t * 2) * 8 * U)))
        rng = random.Random(4)
        for i in range(8):
            f = (self.t_escena * 0.5 + i / 8) % 1
            ang = rng.uniform(-2.6, -0.5) if i % 2 else rng.uniform(-2.6, -0.5) + math.pi
            dist = 140 * U + f * 520 * U
            x = E.W / 2 + math.cos(ang) * dist
            y = E.y(250) + math.sin(ang) * dist * 0.5 + f * f * 200 * U
            r = pygame.Rect(0, 0, 120 * U, 44 * U)
            r.center = (x, y)
            pygame.draw.rect(sup, BLANCO, r, border_radius=round(10 * U))
            pygame.draw.rect(sup, ROJO, r, max(2, round(3 * U)), border_radius=round(10 * U))
            texto(sup, ("¡PÁSENLO!", "¡URGENTE!", "¡CORRAN!", "¡¡YA!!")[i % 4], r.center, 14 * U, ROJO, 900)

    def _enfermo(self, sup, E, U):
        k = min(1, self.t_escena / 1.5)
        self.enfermo.dibujar(sup, k)
        for i in range(8):
            look = CARAS[(i * 3) % len(CARAS)]
            img = personajes.cuerpo(look, "npc", "enojado" if i % 2 else "preocupado", round(120 * U))
            if i % 2:
                img = pygame.transform.flip(img, True, False)
            x = E.W * (i + 0.5) / 8
            salto = abs(math.sin(self.t * 7 + i)) * 6 * U
            sup.blit(img, (x - img.get_width() / 2, self.enfermo.base + 20 * U - img.get_height() - salto))
            if i % 2:
                icono(sup, "angry", (x - 20 * U, self.enfermo.base - 130 * U), 34 * U, ROJO, 2.8)

    def _heroe(self, sup, E, U):
        self.sano.dibujar(sup, 0.0)
        k = self._entrada()
        img = personajes.cuerpo(self.p.get("look") or {}, self.p.get("rol", "periodista"), "feliz", round(300 * U * k))
        sup.blit(img, (E.x(300) - img.get_width() / 2, E.y(470) - img.get_height()))
        # una mentira que se parte en dos, una y otra vez
        f = (self.t_escena * 0.7) % 1
        cx, cy = E.x(820), E.y(260)
        if f < 0.45:
            r = pygame.Rect(0, 0, 300 * U, 100 * U)
            r.center = (cx, cy)
            pygame.draw.rect(sup, BLANCO, r, border_radius=round(18 * U))
            pygame.draw.rect(sup, ROJO, r, max(2, round(4 * U)), border_radius=round(18 * U))
            texto(sup, "¡¡Mañana no hay clases!!", (cx, cy - 10 * U), 20 * U, TINTA, 900)
            texto(sup, "Cadena del colegio", (cx, cy + 22 * U), 14 * U, TINTA2, 900)
            avance = f / 0.45
            pts = [(cx - 220 * U + 440 * U * q / 10 * avance, cy + 60 * U - 120 * U * q / 10 * avance) for q in range(11)]
            pygame.draw.lines(sup, tuple(self.p.get("color", MANGO)), False, pts, max(4, round(12 * U)))
            pygame.draw.lines(sup, BLANCO, False, pts, max(2, round(4 * U)))
        else:
            sep = (f - 0.45) * 300 * U
            for lado in (-1, 1):
                r = pygame.Rect(0, 0, 300 * U, 50 * U)
                r.center = (cx + lado * sep * 0.4, cy + lado * 25 * U - sep * 0.2 + (f - 0.45) ** 2 * 900 * U)
                pygame.draw.rect(sup, BLANCO, r, border_radius=round(12 * U))
                pygame.draw.rect(sup, ROJO, r, max(2, round(3 * U)), border_radius=round(12 * U))
            texto(sup, "+10", (cx, cy - 80 * U - sep * 0.3), 40 * U, MANGO, 700, "titulo")
