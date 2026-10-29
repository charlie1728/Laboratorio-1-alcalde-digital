"""Edificios y decoración del mapa de Ciudad Nova (SVG en un lienzo de 160 x 130)."""
from __future__ import annotations

import pygame

from . import recursos

T = "#23214A"
S = f'stroke="{T}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"'
BASE = f'<ellipse cx="80" cy="121" rx="70" ry="8" fill="{T}" opacity="0.18"/>'


def _alcaldia():
    col = "".join(f'<rect x="{x}" y="62" width="9" height="40" fill="#FFFFFF" {S}/>' for x in (34, 54, 97, 117))
    return (BASE +
            f'<rect x="18" y="102" width="124" height="14" rx="3" fill="#E7DFCB" {S}/>'
            f'<rect x="26" y="58" width="108" height="46" fill="#FFF4DE" {S}/>' + col +
            f'<path d="M72 102 L72 82 Q80 70 88 82 L88 102 Z" fill="#6C4DF5" {S}/>'
            f'<path d="M18 60 L80 28 L142 60 Z" fill="#FFE3A6" {S}/>'
            f'<circle cx="80" cy="47" r="8" fill="#FFFFFF" {S}/>'
            f'<path d="M80 47 L80 42 M80 47 L84 49" stroke="{T}" stroke-width="2" stroke-linecap="round"/>'
            f'<path d="M80 28 L80 4" stroke="{T}" stroke-width="3" stroke-linecap="round"/>'
            f'<rect x="80" y="4" width="26" height="8" fill="#FCD116"/>'
            f'<rect x="80" y="12" width="26" height="4" fill="#003893"/>'
            f'<rect x="80" y="16" width="26" height="4" fill="#CE1126"/>'
            f'<rect x="80" y="4" width="26" height="16" fill="none" {S}/>')


def _colegio():
    ventanas = "".join(f'<rect x="{x}" y="64" width="15" height="16" rx="3" fill="#BDE7FF" {S}/>'
                       for x in (30, 50, 95, 115))
    return (BASE +
            f'<rect x="20" y="52" width="120" height="62" rx="4" fill="#FF8C6B" {S}/>'
            f'<path d="M12 56 L80 24 L148 56 Z" fill="#C2493F" {S}/>'
            f'<rect x="68" y="6" width="24" height="26" fill="#FFB199" {S}/>'
            f'<path d="M64 8 L80 -2 L96 8 Z" fill="#C2493F" {S}/>'
            f'<circle cx="80" cy="19" r="5" fill="#FFC23D" {S}/>'
            f'<circle cx="80" cy="42" r="7" fill="#FFFFFF" {S}/>' + ventanas +
            f'<rect x="68" y="80" width="24" height="34" rx="3" fill="#7A4B35" {S}/>'
            f'<path d="M80 80 L80 114" stroke="{T}" stroke-width="2.5"/>'
            f'<rect x="20" y="96" width="40" height="6" fill="#FFFFFF" opacity="0.5"/>')


def _arbol(x, y, r, c="#4FB04A"):
    return (f'<rect x="{x - 4}" y="{y}" width="8" height="{r + 6}" rx="3" fill="#8A5A3B" {S}/>'
            f'<circle cx="{x}" cy="{y - r * 0.2:.0f}" r="{r}" fill="{c}" {S}/>'
            f'<circle cx="{x - r * 0.35:.0f}" cy="{y - r * 0.45:.0f}" r="{r * 0.3:.0f}" fill="#FFFFFF" opacity="0.25"/>')


def _parque():
    return (BASE +
            f'<ellipse cx="80" cy="102" rx="72" ry="20" fill="#7CCB5E" {S}/>' +
            _arbol(36, 66, 24) + _arbol(126, 60, 28, "#3E9E4A") +
            f'<ellipse cx="80" cy="100" rx="26" ry="9" fill="#9AD9F5" {S}/>'
            f'<rect x="76" y="76" width="8" height="22" rx="3" fill="#E9E3D3" {S}/>'
            f'<path d="M80 74 Q70 64 64 80 M80 74 Q90 64 96 80" fill="none" stroke="#5CC8F0" stroke-width="4" stroke-linecap="round"/>'
            f'<rect x="100" y="104" width="30" height="6" rx="2" fill="#C9874E" {S}/>')


def _hospital():
    ventanas = "".join(f'<rect x="{x}" y="{y}" width="14" height="12" rx="2" fill="#BDE7FF" {S}/>'
                       for y in (52, 72) for x in (32, 52, 94, 114))
    return (BASE +
            f'<rect x="24" y="40" width="112" height="76" rx="5" fill="#FFFFFF" {S}/>'
            f'<rect x="24" y="40" width="112" height="9" fill="#2EC4B6" {S}/>' + ventanas +
            f'<rect x="64" y="90" width="32" height="26" rx="3" fill="#9AD9F5" {S}/>'
            f'<rect x="58" y="86" width="44" height="6" rx="2" fill="#2EC4B6" {S}/>'
            f'<circle cx="80" cy="24" r="17" fill="#FFFFFF" {S}/>'
            f'<path d="M75 13 L85 13 L85 19 L91 19 L91 29 L85 29 L85 35 L75 35 L75 29 L69 29 L69 19 L75 19 Z" '
            f'fill="#00A884" {S}/>')


def _puesto(x, c):
    rayas = "".join(f'<path d="M{x + i * 10} 54 L{x + i * 10 + 10} 54 L{x + i * 10 + 10} 66 Q{x + i * 10 + 5} 72 '
                    f'{x + i * 10} 66 Z" fill="{c if i % 2 == 0 else "#FFFFFF"}"/>' for i in range(4))
    return (f'<rect x="{x + 2}" y="66" width="36" height="40" fill="#FFF4DE" {S}/>' + rayas +
            f'<path d="M{x} 54 L{x + 40} 54 L{x + 40} 66 L{x} 66 Z" fill="none" {S}/>'
            f'<rect x="{x}" y="86" width="40" height="10" rx="2" fill="#C9874E" {S}/>'
            f'<circle cx="{x + 10}" cy="83" r="5" fill="#FF6F61" {S}/>'
            f'<circle cx="{x + 21}" cy="83" r="5" fill="#FFC23D" {S}/>'
            f'<circle cx="{x + 31}" cy="83" r="5" fill="#6BCB77" {S}/>')


def _plaza():
    return (BASE + f'<rect x="8" y="104" width="144" height="12" rx="4" fill="#F2D49B" {S}/>' +
            _puesto(12, "#FF6F61") + _puesto(60, "#2EC4B6") + _puesto(108, "#FFC23D") +
            f'<path d="M8 104 L8 96 M152 104 L152 96" stroke="{T}" stroke-width="3"/>')


def _estadio():
    return (BASE +
            f'<path d="M24 34 L24 6 M136 34 L136 6" stroke="{T}" stroke-width="4" stroke-linecap="round"/>'
            f'<rect x="16" y="2" width="16" height="9" rx="2" fill="#FFF3B0" {S}/>'
            f'<rect x="128" y="2" width="16" height="9" rx="2" fill="#FFF3B0" {S}/>'
            f'<ellipse cx="80" cy="74" rx="72" ry="44" fill="#D9DFF2" {S}/>'
            f'<ellipse cx="80" cy="70" rx="72" ry="40" fill="#EEF1FB" {S}/>'
            f'<ellipse cx="80" cy="72" rx="50" ry="25" fill="#6BCB77" {S}/>'
            f'<path d="M80 47 L80 97" stroke="#FFFFFF" stroke-width="2.5"/>'
            f'<ellipse cx="80" cy="72" rx="10" ry="6" fill="none" stroke="#FFFFFF" stroke-width="2.5"/>'
            f'<path d="M14 80 Q80 132 146 80" fill="none" stroke="#B4BDDB" stroke-width="3"/>')


def _casa(x, y, w, h, pared, techo):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{pared}" {S}/>'
            f'<path d="M{x - 5} {y + 2} L{x + w / 2} {y - h * 0.55:.0f} L{x + w + 5} {y + 2} Z" fill="{techo}" {S}/>'
            f'<rect x="{x + w / 2 - 6}" y="{y + h - 20}" width="12" height="20" rx="2" fill="#7A4B35" {S}/>'
            f'<rect x="{x + 5}" y="{y + 8}" width="10" height="10" rx="2" fill="#BDE7FF" {S}/>'
            f'<rect x="{x + w - 15}" y="{y + 8}" width="10" height="10" rx="2" fill="#BDE7FF" {S}/>')


def _palma(x, y):
    hojas = "".join(f'<path d="M{x} {y} Q{x + dx * 0.6} {y + dy - 12} {x + dx} {y + dy}" fill="none" '
                    f'stroke="#3E9E4A" stroke-width="7" stroke-linecap="round"/>'
                    for dx, dy in ((-24, 6), (24, 6), (-16, -14), (16, -14), (0, -22)))
    return (f'<path d="M{x - 3} {y + 62} Q{x - 8} {y + 30} {x} {y}" fill="none" stroke="{T}" stroke-width="10" stroke-linecap="round"/>'
            f'<path d="M{x - 3} {y + 62} Q{x - 8} {y + 30} {x} {y}" fill="none" stroke="#B9824F" stroke-width="5" stroke-linecap="round"/>'
            + hojas + f'<circle cx="{x}" cy="{y + 3}" r="5" fill="#8A5A3B" {S}/>')


def _barrio():
    return (BASE + _casa(14, 66, 40, 48, "#FFD166", "#EF476F") + _casa(62, 52, 38, 62, "#4CC9F0", "#7B5CFF")
            + _casa(108, 70, 40, 44, "#FF9FB2", "#2EC4B6"))


def _barrio2():
    return (BASE + _palma(26, 40) + _casa(46, 62, 44, 52, "#B8F2C9", "#F2994A")
            + _casa(98, 58, 46, 56, "#FFC23D", "#C2493F"))


def _terminal():
    return (BASE +
            f'<path d="M10 40 L150 40 L140 28 L20 28 Z" fill="#7B5CFF" {S}/>'
            f'<path d="M24 40 L24 112 M136 40 L136 112" stroke="{T}" stroke-width="4"/>'
            f'<rect x="30" y="66" width="104" height="42" rx="10" fill="#FFC23D" {S}/>'
            f'<rect x="30" y="86" width="104" height="8" fill="#3A86FF"/>'
            f'<rect x="30" y="66" width="104" height="42" rx="10" fill="none" {S}/>'
            + "".join(f'<rect x="{x}" y="72" width="16" height="12" rx="3" fill="#BDE7FF" {S}/>' for x in (40, 62, 84, 106))
            + f'<circle cx="52" cy="110" r="8" fill="#3B2F4A" {S}/><circle cx="112" cy="110" r="8" fill="#3B2F4A" {S}/>')


DIBUJOS = dict(alcaldia=_alcaldia, colegio=_colegio, parque=_parque, hospital=_hospital, plaza=_plaza,
               estadio=_estadio, barrio=_barrio, barrio2=_barrio2, terminal=_terminal)


def edificio(tipo: str, ancho: int) -> pygame.Surface:
    alto = round(ancho * 130 / 160)
    dibujo = DIBUJOS.get(tipo, _barrio)()
    return recursos.svg(f'<g transform="translate(0 4)">{dibujo}</g>', ancho, alto, base=160)


def arbolito(tam: int, palma: bool = False, tono: int = 0) -> pygame.Surface:
    color = ("#4FB04A", "#3E9E4A", "#6BCB77")[tono % 3]
    d = _palma(40, 18) if palma else _arbol(40, 54, 22, color)
    return recursos.svg(f'<ellipse cx="40" cy="84" rx="20" ry="5" fill="{T}" opacity="0.18"/>' + d,
                        tam, round(tam * 90 / 80), base=80)


def nube(ancho: int, gris: bool = False) -> pygame.Surface:
    c = "#AEB4C8" if gris else "#FFFFFF"
    d = (f'<path d="M20 50 Q4 50 6 36 Q8 22 24 26 Q28 8 50 10 Q68 2 80 20 Q100 14 104 34 Q118 38 112 50 Z" '
         f'fill="{c}" stroke="{T}" stroke-width="3" stroke-linejoin="round" opacity="0.95"/>')
    if gris:
        d += f'<path d="M40 56 L34 70 M62 56 L56 72 M84 56 L78 68" stroke="#5CC8F0" stroke-width="4" stroke-linecap="round"/>'
    return recursos.svg(d, ancho, round(ancho * 76 / 120), base=120)
