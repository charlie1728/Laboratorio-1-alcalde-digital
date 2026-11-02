"""Menú: de fondo la partida se juega sola; encima, el título, cuántos juegan y la elección de personaje."""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.apariencia import look_aleatorio
from ..ui import personajes
from ..vivo.dibujo import BLANCO, LILA, MANGO, TINTA, TINTA2, ancho_texto, pildora, rebote, sombra, texto
from .pantalla import PantallaCorta, _partir_lineas

_rng = random.Random(8)
PERSONAJES = [
    dict(nombre="Ana", rol="periodista", titulo="Periodista", ventaja="La lupa le dura más",
         color=(255, 194, 61), look=look_aleatorio(_rng, True)),
    dict(nombre="Beto", rol="influencer", titulo="Influencer", ventaja="Doble premio por cortes múltiples",
         color=(96, 190, 255), look=look_aleatorio(_rng, False)),
    dict(nombre="Caro", rol="ciudadano", titulo="Ciudadana", ventaja="La verdad sana más a su barrio",
         color=(255, 120, 170), look=look_aleatorio(_rng, True)),
    dict(nombre="Dani", rol="candidato", titulo="Candidato", ventaja="Su escudo protege más tiempo",
         color=(120, 220, 140), look=look_aleatorio(_rng, False)),
]


class MenuCorta:
    def __init__(self, app):
        self.app = app
        self.fondo = PantallaCorta(app, [dict(nombre="Demo", rol="periodista")], semilla=21, demo=True)
        self.t = 0.0
        self.t_paso = 0.0
        self.paso = "titulo"          # titulo -> cuantos -> personajes
        self.cuantos = 1
        self.elegidos = []
        self.zonas = {}

    # -------------------------------------------------------------- entrada
    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.paso == "titulo":
                    self.app.corriendo = False
                else:
                    self.elegidos = []
                    self._ir("titulo")
            elif self.paso == "titulo" and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._ir("cuantos")
            elif self.paso == "cuantos" and pygame.K_1 <= e.key <= pygame.K_4:
                self._cuantos(e.key - pygame.K_0)
            elif self.paso == "personajes" and pygame.K_1 <= e.key <= pygame.K_4:
                self._elegir(e.key - pygame.K_1)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for (tipo, valor), r in self.zonas.items():
                if r.collidepoint(e.pos):
                    if tipo == "jugar":
                        self._ir("cuantos")
                    elif tipo == "cuantos":
                        self._cuantos(valor)
                    elif tipo == "personaje":
                        self._elegir(valor)
                    return

    def _ir(self, paso):
        self.paso = paso
        self.t_paso = self.t
        self.app.sonar("click")

    def _cuantos(self, n):
        self.cuantos = n
        self.elegidos = []
        self._ir("personajes")

    def _elegir(self, i):
        if i in self.elegidos:
            return
        self.elegidos.append(i)
        self.app.sonar("pop")
        if len(self.elegidos) == self.cuantos:
            self.app.jugar([dict(nombre=PERSONAJES[k]["nombre"], rol=PERSONAJES[k]["rol"],
                                 look=PERSONAJES[k]["look"], color=PERSONAJES[k]["color"]) for k in self.elegidos])

    def actualizar(self, dt):
        self.t += dt
        self.fondo.actualizar(dt)

    # -------------------------------------------------------------- dibujo
    def dibujar(self, sup):
        self.fondo.dibujar(sup)
        U = self.fondo.U
        W, H = sup.get_size()
        velo = pygame.Surface((W, H), pygame.SRCALPHA)
        velo.fill((30, 20, 90, 110 if self.paso == "titulo" else 175))
        sup.blit(velo, (0, 0))
        self.zonas = {}
        self._encabezado(sup, U, W, chico=self.paso != "titulo")
        getattr(self, "_pantalla_" + self.paso)(sup, U, W, H)

    def _encabezado(self, sup, U, W, chico):
        k = rebote(min(1, self.t / 0.7))
        cy = (110 if chico else 220) * U
        tam = (60 if chico else 104) * U * k
        texto(sup, "Corta la mentira", (W / 2 + 5 * U, cy + 6 * U), tam, (40, 20, 110), 700, "titulo")
        texto(sup, "Corta la mentira", (W / 2, cy), tam, BLANCO, 700, "titulo")
        if not chico:
            sub = "Alcalde Digital · Ciudad Nova"
            w = ancho_texto(sub, 22 * U, 900) + 50 * U
            pildora(sup, (W / 2 - w / 2, cy + 64 * U, w, 44 * U), MANGO)
            texto(sup, sub, (W / 2, cy + 86 * U), 22 * U, TINTA, 900)

    def _boton(self, sup, r, color, etiqueta, clave, latir=False):
        r = pygame.Rect(r)
        if latir:
            k = 1 + 0.035 * math.sin(self.t * 5)
            r = r.inflate(r.w * (k - 1), r.h * (k - 1))
        hover = r.collidepoint(pygame.mouse.get_pos())
        radio = round(r.h / 3)
        sombra(sup, r, radio)
        pygame.draw.rect(sup, tuple(round(c * 0.78) for c in color), r.move(0, round(r.h * 0.09)), border_radius=radio)
        pygame.draw.rect(sup, tuple(min(255, c + 18) for c in color) if hover else color, r, border_radius=radio)
        texto(sup, etiqueta, r.center, r.h * 0.42, TINTA, 700, "titulo")
        self.zonas[clave] = r

    def _pantalla_titulo(self, sup, U, W, H):
        r = pygame.Rect(0, 0, 420 * U, 96 * U)
        r.center = (W / 2, 450 * U)
        self._boton(sup, r, MANGO, "¡Jugar!", ("jugar", None), latir=True)
        regla = "Corta lo falso · deja pasar lo verdadero · cuida la ciudad"
        w = ancho_texto(regla, 19 * U, 900) + 44 * U
        pildora(sup, (W / 2 - w / 2, 540 * U, w, 42 * U), BLANCO)
        texto(sup, regla, (W / 2, 561 * U), 19 * U, TINTA, 900)
        texto(sup, "Esc: salir     M: sonido     F11: pantalla completa", (W / 2, H - 28 * U), 15 * U, BLANCO, 800)

    def _pantalla_cuantos(self, sup, U, W, H):
        texto(sup, "¿Cuántos van a jugar?", (W / 2, 210 * U), 34 * U, BLANCO, 700, "titulo")
        texto(sup, "Se turnan el mouse: cada uno juega un día y gana quien haga más puntos.", (W / 2, 252 * U),
              18 * U, BLANCO, 800)
        w, h, sep = 200 * U, 200 * U, 30 * U
        x0 = W / 2 - (4 * w + 3 * sep) / 2
        for n in range(1, 5):
            r = pygame.Rect(x0 + (n - 1) * (w + sep), 300 * U, w, h)
            hover = r.collidepoint(pygame.mouse.get_pos())
            pildora(sup, r, (255, 248, 222) if hover else BLANCO, round(30 * U))
            if hover:
                pygame.draw.rect(sup, MANGO, r, max(3, round(5 * U)), border_radius=round(30 * U))
            texto(sup, str(n), (r.centerx, r.y + 80 * U), 80 * U, LILA, 700, "titulo")
            texto(sup, "jugador" if n == 1 else "jugadores", (r.centerx, r.y + 150 * U), 20 * U, TINTA2, 900)
            self.zonas[("cuantos", n)] = r
        texto(sup, "Esc: volver", (W / 2, H - 28 * U), 15 * U, BLANCO, 800)

    def _pantalla_personajes(self, sup, U, W, H):
        turno = len(self.elegidos) + 1
        titulo = "Escoge tu personaje" if self.cuantos == 1 else f"Jugador {turno}: escoge tu personaje"
        texto(sup, titulo, (W / 2, 200 * U), 32 * U, BLANCO, 700, "titulo")
        w, h, sep = 270 * U, 380 * U, 24 * U
        x0 = W / 2 - (4 * w + 3 * sep) / 2
        for i, p in enumerate(PERSONAJES):
            r = pygame.Rect(x0 + i * (w + sep), 240 * U, w, h)
            tomado = i in self.elegidos
            hover = r.collidepoint(pygame.mouse.get_pos()) and not tomado
            k = rebote(min(1, max(0, self.t - self.t_paso - i * 0.08) / 0.4))
            r = r.move(0, (1 - k) * 40 * U)
            pildora(sup, r, (210, 212, 228) if tomado else BLANCO, round(28 * U))
            pygame.draw.rect(sup, p["color"], r, max(4, round((7 if hover else 5) * U)), border_radius=round(28 * U))
            cab = pygame.Rect(r.x, r.y, r.w, 50 * U)
            pygame.draw.rect(sup, p["color"], cab, border_top_left_radius=round(28 * U),
                             border_top_right_radius=round(28 * U))
            texto(sup, p["nombre"], cab.center, 26 * U, TINTA, 700, "titulo")
            img = personajes.cuerpo(p["look"], p["rol"], "feliz" if hover else "neutral", round(180 * U),
                                    parpadeo=int(self.t * 2 + i) % 8 == 0)
            bote = math.sin(self.t * (6 if hover else 2) + i) * (6 if hover else 2) * U
            sup.blit(img, (r.centerx - img.get_width() / 2, r.y + 58 * U + bote))
            texto(sup, p["titulo"], (r.centerx, r.y + 270 * U), 22 * U, TINTA, 700, "titulo")
            for j, l in enumerate(_partir_lineas(p["ventaja"], 15 * U, w - 40 * U)):
                texto(sup, l, (r.centerx, r.y + 304 * U + j * 22 * U), 15 * U, LILA, 900)
            if tomado:
                n = self.elegidos.index(i) + 1
                pildora(sup, (r.centerx - 70 * U, r.bottom - 50 * U, 140 * U, 34 * U), TINTA)
                texto(sup, f"Jugador {n}", (r.centerx, r.bottom - 33 * U), 16 * U, BLANCO, 900)
            else:
                texto(sup, f"Tecla {i + 1}", (r.centerx, r.bottom - 26 * U), 13 * U, TINTA2, 800)
            self.zonas[("personaje", i)] = r
        texto(sup, "Esc: volver", (W / 2, H - 28 * U), 15 * U, BLANCO, 800)
