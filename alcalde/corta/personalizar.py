"""Personalizar a un personaje: piel, peinado, color de pelo, ropa y accesorio.

El look de cada personaje se guarda en la carpeta del usuario y se usa en todos los modos
(campaña, juego rápido, fiesta y duelo).
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import pygame

from ..modelo.apariencia import COLORES_PELO, COLORES_ROPA, EXTRAS, PEINADOS, TONOS_PIEL, normalizar
from ..ui import personajes
from ..ui.dibujo import BLANCO, LILA, MANGO, TINTA, TINTA2, circulo, icono, rebote, texto
from ..ui.recursos import hex_a_rgb
from .comunes import Boton, Escala, panel, velo
from .logros import REGISTRO

ARCHIVO = Path.home() / ".alcalde_digital_personajes.json"
NOMBRE_EXTRA = {"": "Nada", "gafas": "Gafas", "barba": "Barba", "bigote": "Bigote", "aretes": "Aretes",
                "gorra": "Gorra"}
NOMBRE_PELO = {"corto": "Corto", "rapado": "Rapado", "afro": "Afro", "largo": "Largo", "cola": "Cola de caballo",
               "mono": "Moño", "ondulado": "Ondulado", "trenzas": "Trenzas", "calvo": "Calvo"}
# (clave del look, nombre, cuántas opciones, cómo se llama cada opción, color de muestra)
FILAS = [
    ("piel", "Piel", TONOS_PIEL, lambda v: f"Tono {v + 1}", lambda v: hex_a_rgb(personajes.PIEL[v])),
    ("pelo", "Peinado", len(PEINADOS), lambda v: NOMBRE_PELO.get(PEINADOS[v], PEINADOS[v]), None),
    ("color_pelo", "Color de pelo", COLORES_PELO, lambda v: f"Color {v + 1}", lambda v: hex_a_rgb(personajes.PELO[v])),
    ("ropa", "Ropa", COLORES_ROPA, lambda v: f"Color {v + 1}", lambda v: hex_a_rgb(personajes.ROPA[v])),
    ("extra", "Accesorio", len(EXTRAS), lambda v: NOMBRE_EXTRA.get(EXTRAS[v], EXTRAS[v]), None),
]


def cargar_looks(ruta: Path = ARCHIVO) -> dict:
    try:
        d = json.loads(ruta.read_text(encoding="utf-8"))
        return {rol: normalizar(look) for rol, look in d.items() if isinstance(look, dict)}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def guardar_look(rol: str, look: dict, ruta: Path = ARCHIVO):
    d = cargar_looks(ruta)
    d[rol] = normalizar(look)
    try:
        ruta.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


def aplicar_looks(lista: list[dict]):
    """Pone en la lista de personajes los looks que el jugador ya personalizó."""
    guardados = cargar_looks()
    for p in lista:
        if p["rol"] in guardados:
            p["look"] = guardados[p["rol"]]


def _indice(look, clave):
    v = look[clave]
    if clave == "pelo":
        return PEINADOS.index(v)
    if clave == "extra":
        return EXTRAS.index(v)
    return v


def _poner(look, clave, i):
    if clave == "pelo":
        look[clave] = PEINADOS[i]
    elif clave == "extra":
        look[clave] = EXTRAS[i]
    else:
        look[clave] = i


class Editor:
    """Panel encima del menú: el personaje en grande a la izquierda y las flechas para cambiarlo."""

    def __init__(self, app, personaje: dict):
        self.app = app
        self.p = personaje
        self.look = normalizar(personaje.get("look") or {})
        self.t = 0.0
        self.t_cambio = -1.0
        self._flechas = []
        self.btn_listo = Boton("¡Listo!", "listo", MANGO, "check", tecla=[pygame.K_RETURN, pygame.K_ESCAPE])
        self.btn_azar = Boton("Al azar", "azar", (226, 220, 255), "refresh-cw")

    def actualizar(self, dt):
        self.t += dt

    def evento(self, e):
        if self.btn_listo.toca(e):
            self.p["look"] = dict(self.look)
            guardar_look(self.p["rol"], self.look)
            REGISTRO.ganar("estilo")
            self.app.sonar("logro")
            return "cerrar"
        if self.btn_azar.toca(e):
            for clave, _, n, _, _ in FILAS:
                _poner(self.look, clave, random.randrange(n))
            self._cambio()
            return None
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, clave, paso in self._flechas:
                if r.collidepoint(e.pos):
                    n = next(f[2] for f in FILAS if f[0] == clave)
                    _poner(self.look, clave, (_indice(self.look, clave) + paso) % n)
                    self._cambio()
                    return None
        return None

    def _cambio(self):
        self.t_cambio = self.t
        self.app.sonar("pop")

    def dibujar(self, sup):
        E = Escala(sup)
        U = E.U
        velo(sup, 170)
        k = rebote(min(1, self.t / 0.3))
        r = panel(sup, E.r(110, 60 + (1 - k) * 30, 1060, 600), BLANCO, round(34 * U))
        texto(sup, f"Personaliza a {self.p['nombre']}", (r.x + 40 * U, r.y + 48 * U), 34 * U, TINTA, 700, "titulo",
              "midleft")
        texto(sup, self.p["titulo"], (r.x + 40 * U, r.y + 84 * U), 17 * U, LILA, 900, ancla="midleft")
        # el personaje
        salto = rebote(min(1, (self.t - self.t_cambio) / 0.4)) if self.t_cambio >= 0 else 1
        img = personajes.cuerpo(self.look, self.p["rol"], "feliz", round(380 * U * (0.92 + 0.08 * salto)),
                                parpadeo=int(self.t * 2) % 7 == 0)
        cx = r.x + 230 * U
        circulo(sup, (cx, r.y + 340 * U), 170 * U, tuple(c // 2 + 128 for c in self.p["color"]))
        sup.blit(img, (cx - img.get_width() / 2, r.y + 120 * U + math.sin(self.t * 2) * 4 * U))
        # las filas
        self._flechas = []
        y = r.y + 130 * U
        for clave, nombre, n, nombre_op, muestra in FILAS:
            i = _indice(self.look, clave)
            texto(sup, nombre, (r.x + 470 * U, y + 26 * U), 21 * U, TINTA, 700, "titulo", "midleft")
            for paso, x in ((-1, r.x + 680 * U), (1, r.x + 980 * U)):
                b = pygame.Rect(0, 0, 54 * U, 54 * U)
                b.center = (x, y + 26 * U)
                hover = b.collidepoint(pygame.mouse.get_pos())
                pygame.draw.rect(sup, LILA if hover else (236, 231, 255), b, border_radius=round(16 * U))
                icono(sup, "chevron-left" if paso < 0 else "chevron-right", b.center, 30 * U, BLANCO if hover else LILA, 3)
                self._flechas.append((b, clave, paso))
            if muestra:
                circulo(sup, (r.x + 760 * U, y + 26 * U), 16 * U, TINTA)
                circulo(sup, (r.x + 760 * U, y + 26 * U), 14 * U, muestra(i))
            texto(sup, nombre_op(i), (r.x + 850 * U, y + 26 * U), 18 * U, TINTA2, 900)
            y += 78 * U
        self.btn_azar.dibujar(sup, pygame.Rect(r.x + 470 * U, r.bottom - 90 * U, 220 * U, 62 * U), self.t)
        self.btn_listo.latir = True
        self.btn_listo.dibujar(sup, pygame.Rect(r.right - 330 * U, r.bottom - 96 * U, 290 * U, 70 * U), self.t)
