"""Menú principal: de fondo un nivel que se juega solo; encima, los modos de juego y la elección de personaje."""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.apariencia import look_aleatorio
from ..ui import personajes
from ..ui.dibujo import BLANCO, LILA, MANGO, TINTA, TINTA2, ancho_texto, circulo, icono, pildora, rebote, texto
from .campana import Campana
from .comunes import Boton, Escala, partir, titulo_grande
from .contenido import PODERES
from .nivel import Nivel
from .pantalla_nivel import PantallaNivel
from .personalizar import Editor, aplicar_looks

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
        nivel = Nivel("ESTADIO", dict(nombre="", rol="periodista"), semilla=21, duracion=10_000, alertas=False)
        self.fondo = PantallaNivel(app, nivel, demo=True)
        self.t = 0.0
        self.t_paso = 0.0
        self.paso = "inicio"             # inicio | cuantos | personajes
        self.modo = "campana"
        self.cuantos = 1
        self.elegidos = []
        self.overlay = None
        aplicar_looks(PERSONAJES)
        self.guardada = Campana.cargar()
        if self.guardada and self.guardada.terminada:
            self.guardada = None
        self._rects = {}
        self.botones = []
        self._armar()

    def _armar(self):
        # Fila 1: el juego rápido (lo primero que ve un niño en la feria). Fila 2: la campaña.
        # Fila 3: los modos de varios jugadores. Fila 4: álbum, ayuda y opciones.
        jugar = Boton("¡Jugar ya!", "rapido", MANGO, "play")
        jugar.latir = True
        if self.guardada:
            campana = [Boton(f"Seguir campaña · día {self.guardada.dia}", "continuar", (255, 236, 180), "map"),
                       Boton("Nueva", "nueva", (255, 246, 214), "rotate-ccw")]
        else:
            campana = [Boton("Campaña por la ciudad", "campana", (255, 236, 180), "map")]
        varios = [Boton("Fiesta (2 a 4)", "fiesta", (255, 214, 226), "party-popper"),
                  Boton("Duelo en red", "duelo", (214, 240, 255), "network")]
        otros = [Boton("Récords", "records", (226, 220, 255), "trophy"),
                 Boton("Álbum", "album", (226, 220, 255), "book-open"),
                 Boton("Ayuda", "ayuda", (226, 220, 255), "circle-help"),
                 Boton("Opciones", "opciones", (226, 220, 255), "settings")]
        self.filas = [[jugar], campana, varios, otros]
        self.botones = [b for fila in self.filas for b in fila]

    # -------------------------------------------------------------- entrada
    def evento(self, e):
        if self.overlay is not None:
            r = self.overlay.evento(e)
            if r == "si":
                accion, self.overlay = self.overlay.al_aceptar, None
                accion()
            elif r == "cerrar":
                self.overlay = None
            return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            if self.paso == "inicio":
                # En la feria un niño puede pulsar Esc sin querer: se pregunta antes de cerrar.
                from .paneles import Confirmar
                self.overlay = Confirmar(self.app, "¿Salir del juego?", "Se cierra la ventana de Corta la mentira.",
                                         "Sí, salir", self._salir)
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
                    elif tipo == "estilo":
                        self.app.sonar("click")
                        self.overlay = Editor(self.app, PERSONAJES[valor])
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

    def _salir(self):
        self.app.corriendo = False

    def _accion(self, a):
        from .paneles import Album, Ayuda, Confirmar, Opciones, Records
        self.app.sonar("click")
        if a == "rapido":
            self.modo, self.cuantos, self.elegidos = "rapido", 1, []
            self._ir("personajes")
        elif a == "continuar":
            self.app.abrir_mapa(self.guardada)
        elif a == "nueva":
            self.overlay = Confirmar(self.app, "¿Empezar una campaña nueva?",
                                     f"Se borra la campaña guardada (día {self.guardada.dia}).", "Sí, empezar de cero",
                                     lambda: self._accion("campana"))
        elif a == "records":
            self.overlay = Records(self.app)
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
            elif self.modo == "rapido":
                self.app.rapido(elegidos[0])
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
        titulo_grande(sup, "Corta la mentira", (E.W / 2, 128 * U), 90 * U * k)
        sub = "Alcalde Digital · salva Ciudad Nova de los rumores"
        w = ancho_texto(sub, 21 * U, 900) + 50 * U
        pildora(sup, (E.W / 2 - w / 2, 190 * U, w, 44 * U), MANGO)
        texto(sup, sub, (E.W / 2, 212 * U), 21 * U, TINTA, 900)
        sup.blit(personajes.civi("feliz", round(150 * U), parpadeo=int(self.t * 3) % 9 == 0,
                                 ala=math.sin(self.t * 4) * 0.4), (E.x(70), E.y(470)))
        # Cada fila ocupa 500 de ancho; los botones se reparten el espacio (el de "Nueva" es más angosto).
        y = 260
        for i, fila in enumerate(self.filas):
            alto = 84 if i == 0 else 52 if i == 3 else 60
            pesos = [0.34 if b.accion == "nueva" else 1.0 for b in fila]
            sep = 12
            libre = 500 - sep * (len(fila) - 1)
            x = 640 - 250
            for b, peso in zip(fila, pesos):
                w = libre * peso / sum(pesos)
                b.dibujar(sup, E.r(x, y, w, alto), self.t)
                x += w + sep
            y += alto + (26 if i == 0 else 14)
        if self.t > 1.2:
            texto(sup, "Arrastra el mouse para cortar las mentiras", (E.W / 2, 357 * U), 14 * U, BLANCO, 900)
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
                b = pygame.Rect(r.centerx - 92 * U, r.bottom - 50 * U, 184 * U, 38 * U)
                sobre = b.collidepoint(pygame.mouse.get_pos())
                pildora(sup, b, LILA if sobre else (236, 231, 255), con_sombra=False)
                icono(sup, "wand-sparkles", (b.x + 26 * U, b.centery), 18 * U, BLANCO if sobre else LILA, 2.6)
                texto(sup, "Personalizar", (b.x + 44 * U, b.centery), 15 * U, BLANCO if sobre else LILA, 900,
                      ancla="midleft")
                self._rects[("estilo", i)] = b
            circulo(sup, (r.right - 24 * U, cab.centery), 14 * U, BLANCO)
            texto(sup, str(i + 1), (r.right - 24 * U, cab.centery), 15 * U, TINTA, 900)
            self._rects[("personaje", i)] = r
        texto(sup, "Esc: volver", (E.W / 2, E.H - 24 * U), 15 * U, BLANCO, 800)
