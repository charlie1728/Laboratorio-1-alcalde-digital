"""Menú principal: de fondo un nivel que se juega solo; encima, los modos de juego y la elección de personaje."""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.apariencia import look_aleatorio
from ..ui import personajes
from ..ui.dibujo import BLANCO, LILA, MANGO, TINTA, TINTA2, ancho_texto, pildora, rebote, texto
from .campana import Campana
from .comunes import Boton, Escala, partir, titulo_grande
from .contenido import PODERES
from .nivel import Nivel
from .pantalla_nivel import PantallaNivel

_rng = random.Random(8)
PERSONAJES = [
    dict(nombre="Ana", rol="periodista", titulo="Periodista", color=(255, 194, 61), look=look_aleatorio(_rng, True)),
    dict(nombre="Beto", rol="influencer", titulo="Influencer", color=(96, 190, 255), look=look_aleatorio(_rng, False)),
    dict(nombre="Caro", rol="ciudadano", titulo="Ciudadana", color=(255, 120, 170), look=look_aleatorio(_rng, True)),
    dict(nombre="Dani", rol="candidato", titulo="Candidato", color=(120, 220, 140), look=look_aleatorio(_rng, False)),
]


class MenuPrincipal:
    def __init__(self, app):
        self.app = app
        nivel = Nivel("ESTADIO", dict(nombre="", rol="periodista"), semilla=21, duracion=10_000)
        self.fondo = PantallaNivel(app, nivel, demo=True)
        self.t = 0.0
        self.t_paso = 0.0
        self.paso = "inicio"             # inicio | cuantos | personajes
        self.modo = "campana"
        self.cuantos = 1
        self.elegidos = []
        self.overlay = None
        self.guardada = Campana.cargar()
        if self.guardada and self.guardada.terminada:
            self.guardada = None
        self._rects = {}
        self.botones = []
        self._armar()

    def _armar(self):
        b = []
        if self.guardada:
            b.append(Boton(f"Continuar campaña · día {self.guardada.dia}", "continuar", MANGO, "play"))
            b.append(Boton("Nueva campaña", "campana", (255, 236, 180), "map"))
        else:
            b.append(Boton("Campaña", "campana", MANGO, "map"))
        b += [Boton("Fiesta (2 a 4 jugadores)", "fiesta", (255, 214, 226), "party-popper"),
              Boton("Duelo en red", "duelo", (214, 240, 255), "network"),
              Boton("Álbum", "album", (226, 220, 255), "book-open"),
              Boton("Ayuda", "ayuda", (226, 220, 255), "circle-help"),
              Boton("Opciones", "opciones", (226, 220, 255), "settings")]
        b[0].latir = True
        self.botones = b

    # -------------------------------------------------------------- entrada
    def evento(self, e):
        if self.overlay is not None:
            if self.overlay.evento(e) == "cerrar":
                self.overlay = None
            return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            if self.paso == "inicio":
                self.app.corriendo = False
            else:
                self._ir("inicio")
            return
        if self.paso == "inicio":
            for b in self.botones:
                if b.toca(e):
                    self._accion(b.accion)
                    return
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._accion(self.botones[0].accion)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for (tipo, valor), r in self._rects.items():
                if r.collidepoint(e.pos):
                    if tipo == "cuantos":
                        self.cuantos = valor
                        self._ir("personajes")
                    elif tipo == "personaje":
                        self._elegir(valor)
                    return
        elif e.type == pygame.KEYDOWN and pygame.K_1 <= e.key <= pygame.K_4:
            k = e.key - pygame.K_1
            if self.paso == "cuantos" and k >= 1:
                self.cuantos = k + 1
                self._ir("personajes")
            elif self.paso == "personajes":
                self._elegir(k)

    def _accion(self, a):
        from .paneles import Album, Ayuda, Opciones
        self.app.sonar("click")
        if a == "continuar":
            self.app.abrir_mapa(self.guardada)
        elif a == "campana":
            self.modo, self.cuantos, self.elegidos = "campana", 1, []
            self._ir("personajes")
        elif a == "fiesta":
            self.modo, self.elegidos = "fiesta", []
            self._ir("cuantos")
        elif a == "duelo":
            from .duelo import PantallaDuelo
            self.app.cambiar(PantallaDuelo(self.app))
        elif a == "album":
            self.overlay = Album(self.app, self.guardada or Campana.cargar())
        elif a == "ayuda":
            self.overlay = Ayuda(self.app)
        elif a == "opciones":
            self.overlay = Opciones(self.app)

    def _ir(self, paso):
        self.paso = paso
        self.t_paso = self.t
        self.elegidos = [] if paso != "personajes" else self.elegidos

    def _elegir(self, i):
        if i in self.elegidos:
            return
        self.elegidos.append(i)
        self.app.sonar("pop")
        if len(self.elegidos) == self.cuantos:
            elegidos = [dict(PERSONAJES[k]) for k in self.elegidos]
            if self.modo == "campana":
                Campana.borrar()
                self.app.nueva_campana(elegidos[0])
            else:
                self.app.fiesta(elegidos)

    def actualizar(self, dt):
        self.t += dt
        self.fondo.actualizar(dt)
        if self.overlay is not None:
            self.overlay.actualizar(dt)

    # -------------------------------------------------------------- dibujo
    def dibujar(self, sup):
        self.fondo.dibujar(sup)
        E = Escala(sup)
        U = E.U
        v = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
        v.fill((30, 20, 90, 120 if self.paso == "inicio" else 175))
        sup.blit(v, (0, 0))
        self._rects = {}
        getattr(self, "_pantalla_" + self.paso)(sup, E, U)
        if self.overlay is not None:
            self.overlay.dibujar(sup)

    def _pantalla_inicio(self, sup, E, U):
        k = rebote(min(1, self.t / 0.7))
        titulo_grande(sup, "Corta la mentira", (E.W / 2, 150 * U), 96 * U * k)
        sub = "Alcalde Digital · salva Ciudad Nova de los rumores"
        w = ancho_texto(sub, 21 * U, 900) + 50 * U
        pildora(sup, (E.W / 2 - w / 2, 214 * U, w, 44 * U), MANGO)
        texto(sup, sub, (E.W / 2, 236 * U), 21 * U, TINTA, 900)
        sup.blit(personajes.civi("feliz", round(150 * U), parpadeo=int(self.t * 3) % 9 == 0,
                                 ala=math.sin(self.t * 4) * 0.4), (E.x(70), E.y(470)))
        principales = [b for b in self.botones if b.accion not in ("album", "ayuda", "opciones")]
        secundarios = [b for b in self.botones if b.accion in ("album", "ayuda", "opciones")]
        y = 290
        for i, b in enumerate(principales):
            alto = 72 if i == 0 else 58
            b.dibujar(sup, E.r(640 - 240, y, 480, alto), self.t)
            y += alto + 14
        x = 640 - (3 * 150 + 2 * 15) / 2
        for b in secundarios:
            b.dibujar(sup, E.r(x, y + 10, 150, 50), self.t)
            x += 165
        texto(sup, "M: sonido   ·   F11: pantalla completa   ·   Esc: salir", (E.W / 2, E.H - 24 * U), 15 * U, BLANCO, 800)

    def _pantalla_cuantos(self, sup, E, U):
        titulo_grande(sup, "Fiesta", (E.W / 2, 110 * U), 60 * U)
        texto(sup, "¿Cuántos van a jugar? Se turnan el mouse y gana quien haga más puntos.", (E.W / 2, 180 * U), 19 * U,
              BLANCO, 800)
        w, h, sep = 230, 220, 30
        x0 = 640 - (3 * w + 2 * sep) / 2
        for i, n in enumerate((2, 3, 4)):
            r = E.r(x0 + i * (w + sep), 240, w, h)
            hover = r.collidepoint(pygame.mouse.get_pos())
            pildora(sup, r, (255, 248, 222) if hover else BLANCO, round(30 * U))
            if hover:
                pygame.draw.rect(sup, MANGO, r, max(3, round(5 * U)), border_radius=round(30 * U))
            texto(sup, str(n), (r.centerx, r.y + 90 * U), 90 * U, LILA, 700, "titulo")
            texto(sup, "jugadores", (r.centerx, r.y + 170 * U), 22 * U, TINTA2, 900)
            self._rects[("cuantos", n)] = r
        texto(sup, "Esc: volver", (E.W / 2, E.H - 24 * U), 15 * U, BLANCO, 800)

    def _pantalla_personajes(self, sup, E, U):
        turno = len(self.elegidos) + 1
        titulo = "Escoge tu personaje" if self.cuantos == 1 else f"Jugador {turno}: escoge tu personaje"
        titulo_grande(sup, titulo, (E.W / 2, 100 * U), 46 * U)
        w, h, sep = 270, 430, 24
        x0 = 640 - (4 * w + 3 * sep) / 2
        for i, p in enumerate(PERSONAJES):
            k = rebote(min(1, max(0, self.t - self.t_paso - i * 0.08) / 0.4))
            r = E.r(x0 + i * (w + sep), 160 + (1 - k) * 40, w, h)
            tomado = i in self.elegidos
            hover = r.collidepoint(pygame.mouse.get_pos()) and not tomado
            pildora(sup, r, (210, 212, 228) if tomado else BLANCO, round(28 * U))
            pygame.draw.rect(sup, p["color"], r, max(4, round((7 if hover else 5) * U)), border_radius=round(28 * U))
            cab = pygame.Rect(r.x, r.y, r.w, 50 * U)
            pygame.draw.rect(sup, p["color"], cab, border_top_left_radius=round(28 * U), border_top_right_radius=round(28 * U))
            texto(sup, p["nombre"], cab.center, 26 * U, TINTA, 700, "titulo")
            img = personajes.cuerpo(p["look"], p["rol"], "feliz" if hover else "neutral", round(180 * U),
                                    parpadeo=int(self.t * 2 + i) % 8 == 0)
            bote = math.sin(self.t * (6 if hover else 2) + i) * (6 if hover else 2) * U
            sup.blit(img, (r.centerx - img.get_width() / 2, r.y + 58 * U + bote))
            texto(sup, p["titulo"], (r.centerx, r.y + 266 * U), 22 * U, TINTA, 700, "titulo")
            poder = PODERES[p["rol"]]
            texto(sup, f"Poder: {poder['nombre']}", (r.centerx, r.y + 298 * U), 16 * U, LILA, 900)
            for j, l in enumerate(partir(poder["texto"], 14 * U, r.w - 40 * U)[:3]):
                texto(sup, l, (r.centerx, r.y + 326 * U + j * 20 * U), 14 * U, TINTA2, 800)
            if tomado:
                n = self.elegidos.index(i) + 1
                pildora(sup, (r.centerx - 70 * U, r.bottom - 46 * U, 140 * U, 32 * U), TINTA)
                texto(sup, f"Jugador {n}", (r.centerx, r.bottom - 30 * U), 15 * U, BLANCO, 900)
            else:
                texto(sup, f"Tecla {i + 1}", (r.centerx, r.bottom - 22 * U), 13 * U, TINTA2, 800)
            self._rects[("personaje", i)] = r
        texto(sup, "Esc: volver", (E.W / 2, E.H - 24 * U), 15 * U, BLANCO, 800)
