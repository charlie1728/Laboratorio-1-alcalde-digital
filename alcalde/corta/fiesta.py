"""Modo fiesta: 2 a 4 jugadores se turnan el mouse. Cada uno juega un barrio por ronda y gana quien sume más."""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.mapa import ZONAS, crear_mapa, nombre_zona
from ..modelo.red_social import conectar_jugador, generar_red
from ..ui import personajes
from ..ui.dibujo import BLANCO, LILA, MANGO, ROJO, TINTA, TINTA2, VERDE, icono, mezclar, rebote, texto
from ..ui.tema import TEMA
from .comunes import Boton, Escala, panel, parrafo, titulo_grande
from .contenido import BARRIOS_JUEGO
from .nivel import Nivel
from .pantalla_nivel import PantallaNivel

RONDAS = 2
DORADO = (255, 200, 40)


class PantallaFiesta:
    def __init__(self, app, jugadores):
        self.app = app
        self.jugadores = [dict(j, puntos=0, estrellas=0) for j in jugadores]
        self.semilla = app.semilla if app.semilla is not None else random.randrange(1 << 30)
        rng = random.Random(self.semilla)
        mapa = crear_mapa()
        nombres = {j["nombre"] for j in self.jugadores}
        self.red = generar_red(random.Random(self.semilla), mapa, nombres)
        # Cada jugador es un vértice de la red: en la alerta viral, lo que comparte les llega a sus seguidores.
        for i, j in enumerate(self.jugadores):
            conectar_jugador(self.red, mapa, random.Random(self.semilla + 1 + i), j["nombre"], i, j["rol"],
                             j.get("look") or {})
        barrios = [z for z in ZONAS if z not in ("PLAZA", "ALCALDIA")]
        # La misma ronda tiene el mismo barrio para todos: así la competencia es justa.
        self.zonas = [rng.choice(barrios) for _ in range(RONDAS - 1)] + ["ALCALDIA"]
        self.turno = 0
        self.t = 0.0
        self.t_estado = 0.0
        self.estado = "turno"
        self.ultimo = None
        self.btn = Boton("¡Listo, a jugar!", "jugar", MANGO, "play", tecla=[pygame.K_RETURN, pygame.K_SPACE])
        self.btn_otra = Boton("Otra fiesta", "otra", MANGO, "party-popper", tecla=pygame.K_RETURN)
        self.btn_menu = Boton("Menú", "menu", (236, 238, 248), "log-out", tecla=pygame.K_ESCAPE)
        self.confeti = []

    @property
    def ronda(self):
        return self.turno // len(self.jugadores)

    @property
    def jugador(self):
        return self.jugadores[self.turno % len(self.jugadores)]

    def evento(self, e):
        if self.estado == "turno":
            if self.btn.toca(e):
                self._jugar()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.app.ir_menu()
        elif self.estado == "podio" and self.t_estado > 1.5:
            if self.btn_otra.toca(e):
                self.app.fiesta([{k: v for k, v in j.items() if k not in ("puntos", "estrellas")} for j in self.jugadores])
            elif self.btn_menu.toca(e):
                self.app.ir_menu()

    def _jugar(self):
        zona = self.zonas[self.ronda]
        j = self.jugador
        kw = {} if self.app.duracion is None else dict(duracion=self.app.duracion)
        n = Nivel(zona, j, semilla=self.semilla + self.ronda * 101, red=self.red, infeccion=self.ronda,
                  tranquilo=TEMA.op["tranquilo"], **kw)
        titulo = f"{nombre_zona(zona)} · turno de {j['nombre']}"
        self.app.sonar("turno")
        self.app.cambiar(PantallaNivel(self.app, n, self._volver, titulo=titulo))

    def _volver(self, res):
        if res is not None:
            j = self.jugador
            j["puntos"] += res["puntos"]
            j["estrellas"] += res["estrellas"]
            self.ultimo = (j["nombre"], res)
            self.turno += 1
        self.estado = "podio" if self.turno >= RONDAS * len(self.jugadores) else "turno"
        self.t_estado = 0.0
        if self.estado == "podio":
            self.app.sonar("victoria")
        self.app.cambiar(self)

    def actualizar(self, dt):
        self.t += dt
        self.t_estado += dt
        if self.estado == "podio" and not self.app.menos_movimiento and random.random() < 0.5:
            self.confeti.append(dict(x=random.random(), y=-0.05, v=random.uniform(0.15, 0.35), c=random.choice(
                [MANGO, ROJO, LILA, VERDE, (96, 190, 255)]), r=random.uniform(0, math.tau)))
        for c in self.confeti:
            c["y"] += c["v"] * dt
            c["r"] += dt * 5
        self.confeti = [c for c in self.confeti if c["y"] < 1.1][-200:]

    def dibujar(self, sup):
        E = Escala(sup)
        U = E.U
        for y in range(0, E.H, 4):
            pygame.draw.rect(sup, mezclar((108, 77, 245), (255, 150, 190), y / E.H), (0, y, E.W, 4))
        if self.estado == "turno":
            self._turno(sup, E, U)
        else:
            self._podio(sup, E, U)
        for c in self.confeti:
            x, y = c["x"] * E.W, c["y"] * E.H
            pygame.draw.polygon(sup, c["c"], [(x + math.cos(c["r"] + a) * 7 * U, y + math.sin(c["r"] + a) * 4 * U)
                                              for a in (0, 2, 3.5, 5)])

    def _marcador(self, sup, E, U, y0):
        orden = sorted(self.jugadores, key=lambda j: -j["puntos"])
        w = 240
        x0 = 640 - (len(orden) * w + (len(orden) - 1) * 16) / 2
        for i, j in enumerate(orden):
            r = E.r(x0 + i * (w + 16), y0, w, 86)
            panel(sup, r, BLANCO, round(22 * U), borde=j["color"])
            av = personajes.avatar(j["look"], round(60 * U), j["color"], j["rol"], "feliz")
            sup.blit(av, (r.x + 12 * U, r.y + 13 * U))
            texto(sup, j["nombre"], (r.x + 84 * U, r.y + 28 * U), 20 * U, TINTA, 700, "titulo", "midleft")
            texto(sup, f"{j['puntos']:,} pts".replace(",", "."), (r.x + 84 * U, r.y + 58 * U), 18 * U, TINTA2, 900,
                  ancla="midleft")

    def _turno(self, sup, E, U):
        j = self.jugador
        zona = self.zonas[self.ronda]
        info = BARRIOS_JUEGO[zona]
        titulo_grande(sup, f"Ronda {self.ronda + 1} de {RONDAS}", (E.W / 2, 80 * U), 50 * U)
        self._marcador(sup, E, U, 120)
        r = panel(sup, E.r(240, 240, 800, 380), BLANCO, round(32 * U))
        k = rebote(min(1, self.t_estado / 0.5))
        img = personajes.cuerpo(j["look"], j["rol"], "feliz", round(250 * U * k))
        sup.blit(img, (r.x + 50 * U, r.y + 60 * U + math.sin(self.t * 3) * 5 * U))
        texto(sup, f"¡Turno de {j['nombre']}!", (r.x + 470 * U, r.y + 60 * U), 40 * U, TINTA, 700, "titulo")
        texto(sup, "Pásale el mouse", (r.x + 470 * U, r.y + 102 * U), 18 * U, TINTA2, 900)
        icono(sup, info["icono"], (r.x + 300 * U, r.y + 166 * U), 40 * U, LILA, 2.6)
        texto(sup, nombre_zona(zona), (r.x + 330 * U, r.y + 156 * U), 26 * U, TINTA, 700, "titulo", "midleft")
        texto(sup, info["titulo"], (r.x + 330 * U, r.y + 186 * U), 18 * U, LILA, 900, ancla="midleft")
        parrafo(sup, info["texto"], r.x + 300 * U, r.y + 210 * U, 460 * U, 16 * U, TINTA2, max_lineas=3)
        self.btn.latir = True
        self.btn.dibujar(sup, pygame.Rect(r.x + 330 * U, r.bottom - 100 * U, 380 * U, 76 * U), self.t)
        if self.ultimo:
            nombre, res = self.ultimo
            texto(sup, f"{nombre} hizo {res['puntos']} puntos en el turno anterior", (E.W / 2, E.H - 50 * U), 17 * U,
                  BLANCO, 900)

    def _podio(self, sup, E, U):
        orden = sorted(self.jugadores, key=lambda j: -j["puntos"])
        titulo_grande(sup, f"¡{orden[0]['nombre']} es el Alcalde Digital!", (E.W / 2, 90 * U), 52 * U)
        alturas = [260, 190, 140, 100]
        pos = [1, 0, 2, 3]
        w = 220
        visibles = [p for p in pos if p < len(orden)]
        x0 = 640 - (len(visibles) * w + (len(visibles) - 1) * 20) / 2
        for k, lugar in enumerate(visibles):
            j = orden[lugar]
            e = rebote(min(1, max(0, self.t_estado - 0.3 * (3 - lugar)) / 0.5))
            alto = alturas[lugar] * e
            r = E.r(x0 + k * (w + 20), 640 - alto, w, alto)
            pygame.draw.rect(sup, j["color"], r, border_top_left_radius=round(20 * U), border_top_right_radius=round(20 * U))
            texto(sup, f"{lugar + 1}°", (r.centerx, r.y + 40 * U), 44 * U, BLANCO, 700, "titulo")
            texto(sup, f"{j['puntos']:,}".replace(",", "."), (r.centerx, r.y + 84 * U), 22 * U, TINTA, 700, "titulo")
            img = personajes.cuerpo(j["look"], j["rol"], "feliz" if lugar == 0 else "neutral", round(150 * U))
            sup.blit(img, (r.centerx - img.get_width() / 2, r.y - img.get_height() + 8 * U))
            if lugar == 0:
                icono(sup, "crown", (r.centerx, r.y - img.get_height() - 14 * U), 44 * U, DORADO, 3)
        if self.t_estado > 1.5:
            self.btn_otra.dibujar(sup, E.r(640 - 330, 650, 320, 58), self.t)
            self.btn_menu.dibujar(sup, E.r(650, 650, 240, 58), self.t)
