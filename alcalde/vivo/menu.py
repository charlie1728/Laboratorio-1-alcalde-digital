"""Menú de inicio: la ciudad viva de fondo y cada jugador se une con su propia tecla."""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.apariencia import look_aleatorio
from ..modelo.roles import ORDEN_ROLES, ROLES
from ..ui import personajes
from .dibujo import (BLANCO, LILA, LILA2, MANGO, TINTA, TINTA2, ancho_texto, icono, pildora, rebote, sombra,
                     suave, tecla, texto)
from .juego import COLORES_JUGADOR, MANDO, PERFILES, PantallaJuego
from .mundo import PODERES

NOMBRES = ["Ana", "Beto", "Caro", "Dani"]
ICONO_ROL = {"periodista": "git-branch", "influencer": "megaphone", "ciudadano": "bell-ring", "candidato": "mic"}


class PantallaMenu:
    def __init__(self, app):
        self.app = app
        self.fondo = PantallaJuego(app, [], semilla=11, demo=True)
        self.t = 0.0
        rng = random.Random(5)
        self.looks = [look_aleatorio(rng, i % 2 == 0) for i in range(4)]
        self.slots = [None] * 4          # None = libre; si no, dict(rol=..., t0=...)
        self.mandos = {}
        self._joy()

    def _joy(self):
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                js = pygame.joystick.Joystick(i)
                js.init()
                self.mandos[js.get_instance_id()] = js
        except pygame.error:
            pass

    def _rol_libre(self, desde=0, paso=1, excepto=None):
        usados = {s["rol"] for i, s in enumerate(self.slots) if s and i != excepto}
        n = len(ORDEN_ROLES)
        for k in range(n):
            rol = ORDEN_ROLES[(desde + paso * k) % n]
            if rol not in usados:
                return rol
        return ORDEN_ROLES[desde % n]

    def _unir(self, i):
        if self.slots[i] is None:
            orden = ["periodista", "influencer", "ciudadano", "candidato"]
            self.slots[i] = dict(rol=self._rol_libre(ORDEN_ROLES.index(orden[i])), t0=self.t)
            self.app.sonar("pop")

    def _cambiar(self, i, paso):
        s = self.slots[i]
        if s is None:
            return
        actual = ORDEN_ROLES.index(s["rol"])
        s["rol"] = self._rol_libre(actual + paso, paso, excepto=i)
        s["t0"] = self.t
        self.app.sonar("click")

    def _jugar(self):
        config = []
        for i, s in enumerate(self.slots):
            if s:
                config.append(dict(nombre=NOMBRES[i], rol=s["rol"], look=self.looks[i], color=COLORES_JUGADOR[i]))
        if config:
            self.app.sonar("turno")
            self.app.jugar(config)

    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                if not any(self.slots):
                    self._unir(0)
                self._jugar()
                return
            if e.key == pygame.K_ESCAPE:
                self.app.corriendo = False
                return
            for i, p in enumerate(PERFILES):
                if e.key in p["escanear"] + p["reportar"] + p["compartir"] + p["poder"]:
                    self._unir(i)
                elif e.key in p["izq"]:
                    self._cambiar(i, -1)
                elif e.key in p["der"]:
                    self._cambiar(i, 1)
        elif e.type == pygame.JOYDEVICEADDED:
            js = pygame.joystick.Joystick(e.device_index)
            js.init()
            self.mandos[js.get_instance_id()] = js
        elif e.type == pygame.JOYBUTTONDOWN:
            lista = list(self.mandos)
            if e.instance_id in lista:
                i = len(PERFILES) + lista.index(e.instance_id)
                if i < 4:
                    if e.button == 7:
                        self._jugar()
                    elif self.slots[i] is None:
                        self._unir(i)
                    elif e.button in (4, 1):
                        self._cambiar(i, -1)
                    elif e.button in (5, 2):
                        self._cambiar(i, 1)
        elif e.type == pygame.JOYHATMOTION:
            lista = list(self.mandos)
            if e.instance_id in lista and e.value[0]:
                self._cambiar(len(PERFILES) + lista.index(e.instance_id), e.value[0])
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, r in enumerate(getattr(self, "_rects", [])):
                if r.collidepoint(e.pos):
                    if self.slots[i] is None:
                        self._unir(i)
                    else:
                        self._cambiar(i, 1)
            if getattr(self, "_btn", None) and self._btn.collidepoint(e.pos):
                self._jugar()

    def actualizar(self, dt):
        self.t += dt
        self.fondo.actualizar(dt)

    def dibujar(self, sup):
        self.fondo.dibujar(sup)
        U = self.fondo.U
        W, H = sup.get_size()
        velo = pygame.Surface((W, H), pygame.SRCALPHA)
        velo.fill((30, 22, 90, 105))
        sup.blit(velo, (0, 0))
        # título
        k = rebote(min(1, self.t / 0.7))
        cx = W / 2
        ty = 92 * U
        sup.blit(personajes.civi("feliz", round(120 * U), parpadeo=int(self.t * 3) % 9 == 0,
                                 ala=math.sin(self.t * 4) * 0.4),
                 (cx - ancho_texto("Alcalde Digital", 70 * U, 700, "titulo") / 2 - 100 * U, ty - 70 * U))
        texto(sup, "Alcalde Digital", (cx + 3 * U, ty + 4 * U), 70 * U * k, (40, 20, 110), 700, "titulo")
        texto(sup, "Alcalde Digital", (cx, ty), 70 * U * k, BLANCO, 700, "titulo")
        sub = "Los rumores se riegan solos por Ciudad Nova. ¡Corre, descúbrelos y frénalos!"
        w = ancho_texto(sub, 20 * U, 900) + 50 * U
        pildora(sup, (cx - w / 2, ty + 48 * U, w, 42 * U), MANGO)
        texto(sup, sub, (cx, ty + 69 * U), 20 * U, TINTA, 900)
        # cuatro puestos de jugador
        ancho, alto = 270 * U, 340 * U
        sep = 22 * U
        x0 = cx - (4 * ancho + 3 * sep) / 2
        y0 = 220 * U
        self._rects = []
        for i in range(4):
            r = pygame.Rect(x0 + i * (ancho + sep), y0, ancho, alto)
            self._rects.append(r)
            self._puesto(sup, r, i)
        # botón de jugar
        hay = any(self.slots)
        w = 420 * U
        br = pygame.Rect(cx - w / 2, y0 + alto + 34 * U, w, 76 * U)
        self._btn = br
        lat = 1 + (math.sin(self.t * 5) * 0.03 if hay else 0)
        bb = br.inflate(br.w * (lat - 1), br.h * (lat - 1))
        sombra(sup, bb, round(26 * U))
        pygame.draw.rect(sup, (200, 140, 0) if hay else (150, 150, 180), bb.move(0, 7 * U), border_radius=round(26 * U))
        pygame.draw.rect(sup, MANGO if hay else (226, 229, 240), bb, border_radius=round(26 * U))
        tecla(sup, "Enter", (bb.x + 70 * U, bb.centery), 40 * U)
        texto(sup, "¡A jugar!" if hay else "Únete primero", (bb.centerx + 40 * U, bb.centery), 34 * U, TINTA, 700, "titulo")
        pie = "M: sonido     F11: pantalla completa     Esc: salir"
        texto(sup, pie, (cx, H - 26 * U), 15 * U, BLANCO, 800)

    def _puesto(self, sup, r, i):
        U = self.fondo.U
        s = self.slots[i]
        col = COLORES_JUGADOR[i]
        etiquetas = PERFILES[i]["etiquetas"] if i < len(PERFILES) else MANDO["etiquetas"]
        if s is None:
            sup_v = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(sup_v, (40, 30, 110, 170), (0, 0, r.w, r.h), border_radius=round(26 * U))
            sup.blit(sup_v, r)
            pygame.draw.rect(sup, (255, 255, 255), r, max(2, round(3 * U)), border_radius=round(26 * U))
            texto(sup, f"Jugador {i + 1}", (r.centerx, r.y + 40 * U), 24 * U, BLANCO, 700, "titulo")
            lat = 1 + 0.08 * math.sin(self.t * 4 + i)
            if i < len(PERFILES):
                tecla(sup, etiquetas["escanear"], (r.centerx, r.centery - 10 * U), 64 * U * lat, col)
                texto(sup, "Pulsa para unirte", (r.centerx, r.centery + 50 * U), 17 * U, BLANCO, 900)
                texto(sup, f"Se mueve con {etiquetas['mover']}", (r.centerx, r.bottom - 30 * U), 14 * U, BLANCO, 800)
            else:
                icono(sup, "gamepad-2", (r.centerx, r.centery - 10 * U), 70 * U * lat, BLANCO, 2.2)
                texto(sup, "Conecta un mando", (r.centerx, r.centery + 50 * U), 17 * U, BLANCO, 900)
                texto(sup, "y pulsa A", (r.centerx, r.centery + 74 * U), 17 * U, BLANCO, 900)
            return
        k = rebote(min(1, (self.t - s["t0"]) / 0.4))
        pildora(sup, r, BLANCO, round(26 * U))
        pygame.draw.rect(sup, col, r, max(4, round(5 * U)), border_radius=round(26 * U))
        head = pygame.Rect(r.x, r.y, r.w, 44 * U)
        pygame.draw.rect(sup, col, head, border_top_left_radius=round(26 * U), border_top_right_radius=round(26 * U))
        texto(sup, NOMBRES[i], (r.centerx, head.centery), 22 * U, TINTA, 700, "titulo")
        alto = 150 * U * (0.85 + 0.15 * k)
        img = personajes.cuerpo(self.looks[i], s["rol"], "feliz", round(alto), parpadeo=int(self.t * 2 + i) % 7 == 0)
        bote = math.sin(self.t * 3 + i) * 3 * U
        sup.blit(img, (r.centerx - img.get_width() / 2, r.y + 56 * U + bote))
        y = r.y + 56 * U + 150 * U + 14 * U
        texto(sup, ROLES[s["rol"]]["nombre"], (r.centerx, y), 24 * U, TINTA, 700, "titulo")
        icono(sup, ICONO_ROL[s["rol"]], (r.x + 30 * U, y + 34 * U), 22 * U, LILA, 2.6)
        texto(sup, PODERES[s["rol"]]["nombre"], (r.x + 48 * U, y + 34 * U), 15 * U, LILA, 900, ancla="midleft")
        # flechas para cambiar
        if i < len(PERFILES):
            iz, de = PERFILES[i]["etiquetas"]["mover"], ""
            teclas = ("A", "D") if i == 0 else ("◀", "▶")
        else:
            teclas = ("LB", "RB")
        for lado, t in ((-1, teclas[0]), (1, teclas[1])):
            if t in ("◀", "▶"):
                cxx = r.centerx + lado * (r.w / 2 - 26 * U)
                icono(sup, "chevron-left" if lado < 0 else "chevron-right", (cxx, r.y + 130 * U), 30 * U, TINTA2, 3)
            else:
                tecla(sup, t, (r.centerx + lado * (r.w / 2 - 28 * U), r.y + 130 * U), 30 * U, LILA2)
        texto(sup, "cambiar personaje", (r.centerx, r.bottom - 22 * U), 12 * U, TINTA2, 800)
