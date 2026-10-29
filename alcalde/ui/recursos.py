"""Carga de fuentes, iconos e ilustraciones SVG (con caché).

Pygame trae nanosvg: dibuja trazos, curvas y degradados, pero ignora el viewBox, así
que cada SVG se escala con una transformación ``scale(k)`` dentro de un grupo.
"""
from __future__ import annotations

import io
import re
from collections import OrderedDict
from pathlib import Path

import pygame

RAIZ = Path(__file__).resolve().parents[2]
ASSETS = RAIZ / "assets"
FUENTES = ASSETS / "fuentes"
ICONOS = ASSETS / "iconos"
SONIDOS = ASSETS / "sonidos"


class _LRU(OrderedDict):
    def __init__(self, maximo: int):
        super().__init__()
        self.maximo = maximo

    def obtener(self, clave, crear):
        if clave in self:
            self.move_to_end(clave)
            return self[clave]
        valor = crear()
        self[clave] = valor
        if len(self) > self.maximo:
            self.popitem(last=False)
        return valor


_fuentes: dict = {}
_textos = _LRU(1600)
_svgs = _LRU(900)
_iconos_src: dict[str, str] = {}

_ARCHIVOS = {
    ("titulo", 500): "Fredoka-500.ttf", ("titulo", 600): "Fredoka-600.ttf",
    ("titulo", 700): "Fredoka-700.ttf",
    ("texto", 400): "Nunito-400.ttf", ("texto", 600): "Nunito-600.ttf",
    ("texto", 700): "Nunito-700.ttf", ("texto", 800): "Nunito-800.ttf",
    ("texto", 900): "Nunito-900.ttf",
}


def fuente(tam: int, peso: int = 600, familia: str = "texto") -> pygame.font.Font:
    pesos = sorted(p for f, p in _ARCHIVOS if f == familia)
    peso = min(pesos, key=lambda p: abs(p - peso))
    clave = (familia, peso, tam)
    if clave not in _fuentes:
        ruta = FUENTES / _ARCHIVOS[(familia, peso)]
        try:
            _fuentes[clave] = pygame.font.Font(str(ruta), tam)
        except (FileNotFoundError, OSError):
            nombre = pygame.font.match_font("segoeui,arial,dejavusans", bold=peso >= 700)
            _fuentes[clave] = pygame.font.Font(nombre, tam)
    return _fuentes[clave]


def render_texto(s: str, tam: int, color, peso: int = 600, familia: str = "texto") -> pygame.Surface:
    clave = (s, tam, tuple(color[:3]), peso, familia)
    return _textos.obtener(clave, lambda: fuente(tam, peso, familia).render(s, True, color[:3]))


def svg(texto: str, ancho: int, alto: int, base: float = None) -> pygame.Surface:
    """Rasteriza un SVG. Si se da ``base``, el dibujo está en un lienzo de ese ancho y se escala."""
    clave = (texto, ancho, alto)

    def crear():
        k = 1.0 if base is None else ancho / base
        doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}">'
               f'<g transform="scale({k:.5f})">{texto}</g></svg>')
        try:
            sup = pygame.image.load(io.BytesIO(doc.encode("utf-8")), "x.svg")
        except pygame.error:
            sup = pygame.Surface((ancho, alto), pygame.SRCALPHA)
        return sup.convert_alpha() if pygame.display.get_surface() else sup
    return _svgs.obtener(clave, crear)


def _hex(color) -> str:
    if isinstance(color, str):
        return color
    return "#%02x%02x%02x" % tuple(int(c) for c in color[:3])


def icono(nombre: str, tam: int, color, grosor: float = 2.0) -> pygame.Surface:
    if nombre not in _iconos_src:
        ruta = ICONOS / f"{nombre}.svg"
        try:
            crudo = ruta.read_text(encoding="utf-8")
            cuerpo = crudo[crudo.index(">", crudo.index("<svg")) + 1:crudo.rindex("</svg>")]
        except (FileNotFoundError, ValueError):
            cuerpo = '<circle cx="12" cy="12" r="9"/>'
        _iconos_src[nombre] = re.sub(r"\s+", " ", cuerpo)
    c = _hex(color)
    cuerpo = (f'<g fill="none" stroke="{c}" stroke-width="{grosor}" stroke-linecap="round" '
              f'stroke-linejoin="round">{_iconos_src[nombre]}</g>')
    return svg(cuerpo, tam, tam, base=24)


def hex_a_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
