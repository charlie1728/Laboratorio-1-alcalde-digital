"""Personajes ilustrados de Ciudad Nova, generados como SVG.

Cada personaje sale de su "look" (piel, peinado, color de pelo, ropa, accesorio), de su
rol (que define el vestuario) y de una expresión. Todo se dibuja en un lienzo de
200 x 300 (cuerpo completo); el busto es un recorte de la parte de arriba.
"""
from __future__ import annotations

import math

import pygame

from ..modelo.apariencia import normalizar
from . import recursos

TINTA = "#23214A"
PIEL = ["#FDE3CD", "#F6CBA6", "#E4A87C", "#C98757", "#9E633A", "#6B4127"]
PIEL_SOMBRA = ["#F2C6A8", "#E7B088", "#CF9064", "#B07043", "#87522D", "#583420"]
PELO = ["#2B1D16", "#5A3825", "#93602F", "#E0AE4A", "#B8462C", "#A7ADB8", "#5B44A8"]
ROPA = ["#FFC23D", "#FF6F61", "#2EC4B6", "#7B5CFF", "#6BCB77", "#3A86FF", "#FF5FA2", "#F2994A"]
PANTALON = ["#3E5BA9", "#2E2B45", "#6B5B4B", "#4F6D5A"]

EXPRESIONES = ["neutral", "feliz", "preocupado", "enojado", "sorprendido", "confundido"]

_S = dict(stroke=TINTA, stroke_width=4, stroke_linejoin="round", stroke_linecap="round")


def _el(tag, sil=False, **attrs):
    return (tag, attrs, sil)


def _txt(elems, respaldo=False):
    out = []
    for tag, attrs, sil in elems:
        if respaldo:
            if not sil:
                continue
            attrs = {k: v for k, v in attrs.items() if k not in ("opacity", "fill_opacity")}
            attrs.update(fill="#FFFFFF", stroke="#FFFFFF", stroke_width=18,
                         stroke_linejoin="round", stroke_linecap="round")
        partes = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
        out.append(f"<{tag} {partes}/>")
    return "".join(out)


def _oscurecer(hex_color: str, f: float = 0.82) -> str:
    r, g, b = recursos.hex_a_rgb(hex_color)
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def _hex(color) -> str:
    if isinstance(color, str):
        return color
    return "#%02x%02x%02x" % tuple(int(c) for c in color[:3])


def _pelo_atras(e, estilo, H):
    if estilo == "afro":
        cx, cy, R = 100, 84, 56
        bultos = [(cx + R * math.cos(a), cy + R * 0.92 * math.sin(a)) for a in
                  [i * 2 * math.pi / 11 - math.pi / 2 for i in range(11)]]
        for x, y in bultos:
            e.append(_el("circle", True, cx=f"{x:.1f}", cy=f"{y:.1f}", r=26, fill=H, stroke=TINTA, stroke_width=8))
        for x, y in bultos:
            e.append(_el("circle", cx=f"{x:.1f}", cy=f"{y:.1f}", r=26, fill=H))
        e.append(_el("circle", cx=cx, cy=cy, r=56, fill=H))
    elif estilo == "largo":
        e.append(_el("path", True, d="M36 96 Q30 26 100 26 Q170 26 164 96 L168 192 Q150 204 132 194 "
                                    "L128 150 L72 150 L68 194 Q50 204 32 192 Z", fill=H, **_S))
    elif estilo == "ondulado":
        e.append(_el("path", True, d="M36 96 Q30 26 100 26 Q170 26 164 96 Q176 118 164 136 Q172 154 154 162 "
                                    "L46 162 Q28 154 36 136 Q24 118 36 96 Z", fill=H, **_S))
    elif estilo == "cola":
        e.append(_el("path", True, d="M150 58 Q196 64 186 120 Q180 156 160 164 Q172 124 150 92 Z", fill=H, **_S))
    elif estilo == "mono":
        e.append(_el("circle", True, cx=100, cy=30, r=25, fill=H, **_S))
    elif estilo == "trenzas":
        for x in (46, 154):
            for i in range(5):
                e.append(_el("ellipse", True, cx=x, cy=128 + i * 17, rx=12, ry=10, fill=H, **_S))
            e.append(_el("circle", cx=x, cy=214, r=6, fill="#FF6F61", **_S))


def _pelo_frente(e, estilo, H):
    if estilo in ("corto", "afro"):
        e.append(_el("path", d="M38 100 Q32 34 100 30 Q168 34 162 100 Q156 74 140 64 Q124 80 102 68 "
                               "Q82 82 62 66 Q46 76 38 100 Z", fill=H, **_S))
    elif estilo == "rapado":
        e.append(_el("path", d="M40 90 Q42 36 100 33 Q158 36 160 90 Q150 58 100 54 Q50 58 40 90 Z",
                     fill=H, opacity="0.92", **_S))
    elif estilo in ("largo", "ondulado"):
        e.append(_el("path", d="M38 100 Q34 32 100 30 Q166 32 162 100 Q158 66 126 56 Q104 80 66 66 "
                               "Q46 76 38 100 Z", fill=H, **_S))
    elif estilo in ("cola", "mono", "trenzas"):
        e.append(_el("path", d="M40 96 Q36 32 100 31 Q164 32 160 96 Q152 62 100 58 Q48 62 40 96 Z", fill=H, **_S))
        if estilo == "cola":
            e.append(_el("path", d="M150 60 Q160 52 166 62", fill="none", stroke="#FF6F61", stroke_width=6,
                         stroke_linecap="round"))
    elif estilo == "calvo":
        e.append(_el("path", d="M38 108 Q34 84 44 72 Q50 92 52 108 Z", fill=H, **_S))
        e.append(_el("path", d="M162 108 Q166 84 156 72 Q150 92 148 108 Z", fill=H, **_S))
        e.append(_el("ellipse", cx=116, cy=54, rx=16, ry=8, fill="#FFFFFF", opacity="0.45"))


def _cara(e, expresion, H, piel_i, parpadeo):
    cejas = _oscurecer(H, 0.7) if H not in ("#2B1D16",) else H
    ojo_y = 100
    if expresion == "sorprendido":
        ojo_y = 98
    # cejas
    cj = dict(fill="none", stroke=cejas, stroke_width=5, stroke_linecap="round")
    if expresion == "enojado":
        e += [_el("path", d="M66 80 L88 88", **cj), _el("path", d="M134 80 L112 88", **cj)]
    elif expresion == "preocupado":
        e += [_el("path", d="M66 88 L88 80", **cj), _el("path", d="M134 88 L112 80", **cj)]
    elif expresion == "sorprendido":
        e += [_el("path", d="M66 76 Q77 68 88 76", **cj), _el("path", d="M112 76 Q123 68 134 76", **cj)]
    elif expresion == "confundido":
        e += [_el("path", d="M66 78 Q77 72 88 80", **cj), _el("path", d="M112 84 L134 84", **cj)]
    else:
        e += [_el("path", d="M67 83 Q77 78 88 82", **cj), _el("path", d="M112 82 Q123 78 133 83", **cj)]
    # ojos
    if parpadeo:
        for x in (78, 122):
            e.append(_el("path", d=f"M{x - 9} {ojo_y + 1} Q{x} {ojo_y + 7} {x + 9} {ojo_y + 1}",
                         fill="none", stroke=TINTA, stroke_width=4, stroke_linecap="round"))
    elif expresion == "feliz":
        for x in (78, 122):
            e.append(_el("path", d=f"M{x - 9} {ojo_y + 4} Q{x} {ojo_y - 8} {x + 9} {ojo_y + 4}",
                         fill="none", stroke=TINTA, stroke_width=5, stroke_linecap="round"))
    else:
        ry = 11 if expresion == "sorprendido" else 9
        for x in (78, 122):
            e.append(_el("ellipse", cx=x, cy=ojo_y, rx=7, ry=ry, fill=TINTA))
            e.append(_el("circle", cx=x + 2.5, cy=ojo_y - 3.5, r=2.8, fill="#FFFFFF"))
    # mejillas y nariz
    e.append(_el("ellipse", cx=64, cy=118, rx=10, ry=6, fill="#FF7E9D", opacity="0.38"))
    e.append(_el("ellipse", cx=136, cy=118, rx=10, ry=6, fill="#FF7E9D", opacity="0.38"))
    e.append(_el("path", d="M97 108 Q100 113 104 108", fill="none", stroke=PIEL_SOMBRA[piel_i] if piel_i < 4 else "#3E2416",
                 stroke_width=4, stroke_linecap="round"))
    # boca
    bk = dict(fill="none", stroke=TINTA, stroke_width=4.5, stroke_linecap="round")
    if expresion == "feliz":
        e.append(_el("path", d="M84 120 Q100 144 116 120 Z", fill=TINTA, stroke=TINTA, stroke_width=3,
                     stroke_linejoin="round"))
        e.append(_el("path", d="M92 132 Q100 126 108 132 Q100 140 92 132 Z", fill="#FF7E9D"))
    elif expresion == "preocupado":
        e.append(_el("path", d="M88 131 Q100 122 112 131", **bk))
        e.append(_el("path", d="M150 70 Q156 80 150 86 Q144 80 150 70 Z", fill="#8FD8FF", stroke=TINTA, stroke_width=2.5))
    elif expresion == "enojado":
        e.append(_el("path", d="M87 130 Q100 123 113 130", **bk))
    elif expresion == "sorprendido":
        e.append(_el("ellipse", cx=100, cy=128, rx=7, ry=9, fill=TINTA))
    elif expresion == "confundido":
        e.append(_el("path", d="M86 128 Q93 122 100 128 Q107 134 114 128", **bk))
    else:
        e.append(_el("path", d="M87 123 Q100 134 113 123", **bk))


def _ropa(e, rol, R, look, color_extra):
    torso = "M52 240 L52 192 Q52 160 82 156 L118 156 Q148 160 148 192 L148 240 Z"
    brazo_i = dict(x=33, y=164, width=22, height=62, rx=11, transform="rotate(9 44 164)")
    brazo_d = dict(x=145, y=164, width=22, height=62, rx=11, transform="rotate(-9 156 164)")
    if rol == "periodista":
        e.append(_el("path", True, d=torso, fill="#FFFFFF", **_S))
        e.append(_el("path", d="M52 240 L52 192 Q52 162 82 156 L94 240 Z", fill=R, **_S))
        e.append(_el("path", d="M148 240 L148 192 Q148 162 118 156 L106 240 Z", fill=R, **_S))
        e.append(_el("path", d="M88 158 L112 200 L124 158", fill="none", stroke="#6C4DF5", stroke_width=4))
        e.append(_el("rect", x=110, y=196, width=26, height=32, rx=5, fill="#FFFFFF", **_S))
        e.append(_el("rect", x=114, y=201, width=18, height=7, rx=2, fill="#6C4DF5"))
        e.append(_el("path", d="M115 216 L131 216 M115 222 L126 222", stroke=TINTA, stroke_width=2.5, stroke_linecap="round"))
        e.append(_el("rect", x=58, y=198, width=30, height=21, rx=5, fill=TINTA))
        e.append(_el("circle", cx=73, cy=208.5, r=6.5, fill="#A8C8F0", stroke="#FFFFFF", stroke_width=2))
        manga = R
    elif rol == "influencer":
        e.append(_el("path", True, d=torso, fill="#FFFFFF", **_S))
        e.append(_el("path", d="M100 188 L105 200 L118 200 L108 208 L112 221 L100 213 L88 221 L92 208 "
                               "L82 200 L95 200 Z", fill="#FF5FA2", stroke=TINTA, stroke_width=2.5, stroke_linejoin="round"))
        e.append(_el("path", d="M52 240 L52 192 Q52 160 82 156 L86 240 Z", fill=R, **_S))
        e.append(_el("path", d="M148 240 L148 192 Q148 160 118 156 L114 240 Z", fill=R, **_S))
        manga = R
    elif rol == "candidato":
        traje = "#33406E"
        e.append(_el("path", True, d=torso, fill=traje, **_S))
        e.append(_el("path", d="M84 157 L100 196 L116 157 Z", fill="#FFFFFF", stroke=TINTA, stroke_width=3,
                     stroke_linejoin="round"))
        corb = _hex(color_extra) if color_extra else R
        e.append(_el("path", d="M96 162 L104 162 L107 192 L100 202 L93 192 Z", fill=corb, stroke=TINTA,
                     stroke_width=2.5, stroke_linejoin="round"))
        e.append(_el("path", d="M84 157 L74 176 L88 182 L100 200", fill="none", stroke=TINTA, stroke_width=3))
        e.append(_el("path", d="M116 157 L126 176 L112 182 L100 200", fill="none", stroke=TINTA, stroke_width=3))
        if color_extra:
            e.append(_el("path", d="M60 168 L74 160 L146 226 L134 236 Z", fill=corb, opacity="0.95",
                         stroke=TINTA, stroke_width=3, stroke_linejoin="round"))
            e.append(_el("circle", cx=104, cy=200, r=8, fill="#FFC23D", stroke=TINTA, stroke_width=2.5))
        manga = traje
    else:
        e.append(_el("path", True, d=torso, fill=R, **_S))
        if rol == "ciudadano":
            e.append(_el("path", d="M74 158 Q100 182 126 158", fill="none", stroke=TINTA, stroke_width=3.5))
            e.append(_el("path", d="M92 170 L90 190 M108 170 L110 190", stroke=TINTA, stroke_width=3, stroke_linecap="round"))
            e.append(_el("rect", x=74, y=208, width=52, height=20, rx=9, fill=_oscurecer(R, 0.9), stroke=TINTA, stroke_width=3))
        else:
            i = look["ropa"] % 3
            if i == 0:
                e.append(_el("path", d="M54 200 L146 200 M54 218 L146 218", stroke="#FFFFFF", stroke_width=6, opacity="0.75"))
            elif i == 1:
                e.append(_el("path", d="M84 157 Q100 176 116 157", fill="none", stroke=TINTA, stroke_width=3))
            else:
                e.append(_el("circle", cx=100, cy=196, r=9, fill="#FFFFFF", opacity="0.8", stroke=TINTA, stroke_width=2.5))
        manga = R
    e.append(_el("rect", True, fill=manga, **brazo_i, **_S))
    e.append(_el("rect", True, fill=manga, **brazo_d, **_S))


def svg_personaje(look: dict, rol: str = "npc", expresion: str = "neutral", parpadeo: bool = False,
                  color_extra=None) -> str:
    look = normalizar(look)
    pi = look["piel"]
    piel, H, R = PIEL[pi], PELO[look["color_pelo"]], ROPA[look["ropa"]]
    P = PANTALON[(look["ropa"] + look["color_pelo"]) % len(PANTALON)]
    if rol == "ciudadano":
        P = "#3E5BA9"
    elif rol == "periodista":
        P = "#7A6A55"
    elif rol == "influencer":
        P = "#2E2B45"
    elif rol == "candidato":
        P = "#33406E"
    estilo = look["pelo"]
    e = []
    e.append(_el("ellipse", cx=100, cy=288, rx=58, ry=9, fill=TINTA, opacity="0.16"))
    e.append(_el("rect", True, x=68, y=230, width=28, height=50, rx=9, fill=P, **_S))
    e.append(_el("rect", True, x=104, y=230, width=28, height=50, rx=9, fill=P, **_S))
    e.append(_el("ellipse", True, cx=80, cy=281, rx=20, ry=10, fill="#3B2F4A", **_S))
    e.append(_el("ellipse", True, cx=120, cy=281, rx=20, ry=10, fill="#3B2F4A", **_S))
    _ropa(e, rol, R, look, color_extra)
    e.append(_el("circle", True, cx=47, cy=228, r=11, fill=piel, **_S))
    e.append(_el("circle", True, cx=153, cy=228, r=11, fill=piel, **_S))
    if rol == "influencer":
        e.append(_el("rect", x=146, y=200, width=20, height=34, rx=5, fill=TINTA, transform="rotate(-12 156 217)"))
        e.append(_el("rect", x=149, y=204, width=14, height=24, rx=3, fill="#9AE7FF", transform="rotate(-12 156 217)"))
    if estilo in ("largo", "ondulado", "trenzas"):
        e.append(_el("rect", x=88, y=136, width=24, height=26, rx=7, fill=PIEL_SOMBRA[pi], **_S))
    _pelo_atras(e, estilo, H)
    if estilo not in ("largo", "ondulado", "trenzas"):
        e.append(_el("rect", x=88, y=136, width=24, height=26, rx=7, fill=PIEL_SOMBRA[pi], **_S))
    e.append(_el("ellipse", True, cx=40, cy=102, rx=10, ry=13, fill=piel, **_S))
    e.append(_el("ellipse", True, cx=160, cy=102, rx=10, ry=13, fill=piel, **_S))
    e.append(_el("ellipse", True, cx=100, cy=94, rx=61, ry=58, fill=piel, **_S))
    if look["extra"] == "barba":
        e.append(_el("path", d="M42 104 Q46 162 100 166 Q154 162 158 104 Q150 140 124 140 Q100 150 76 140 "
                               "Q50 140 42 104 Z", fill=H, **_S))
    _cara(e, expresion, H, pi, parpadeo)
    if look["extra"] == "bigote":
        e.append(_el("path", d="M82 121 Q91 111 100 118 Q109 111 118 121 Q109 126 100 122 Q91 126 82 121 Z",
                     fill=H, stroke=TINTA, stroke_width=2.5, stroke_linejoin="round"))
    if look["extra"] == "gorra":
        e.append(_el("path", d="M36 84 Q38 26 100 25 Q162 26 164 84 Q140 66 100 66 Q60 66 36 84 Z",
                     fill=R, **_S))
        e.append(_el("path", d="M96 70 Q150 62 180 80 Q156 92 100 86 Z", fill=_oscurecer(R, 0.85), **_S))
        e.append(_el("circle", cx=100, cy=27, r=6, fill=_oscurecer(R, 0.8), stroke=TINTA, stroke_width=3))
    else:
        _pelo_frente(e, estilo, H)
    if look["extra"] == "gafas":
        for x in (78, 122):
            e.append(_el("circle", cx=x, cy=100, r=15, fill="#FFFFFF", fill_opacity="0.22", stroke=TINTA, stroke_width=4))
        e.append(_el("path", d="M93 99 Q100 94 107 99", fill="none", stroke=TINTA, stroke_width=4))
    if look["extra"] == "aretes":
        e.append(_el("circle", cx=40, cy=118, r=5, fill="#FFC23D", stroke=TINTA, stroke_width=2.5))
        e.append(_el("circle", cx=160, cy=118, r=5, fill="#FFC23D", stroke=TINTA, stroke_width=2.5))
    if rol == "influencer" and look["extra"] != "gorra":
        e.append(_el("rect", x=58, y=40, width=34, height=18, rx=8, fill=TINTA, transform="rotate(-6 75 49)"))
        e.append(_el("rect", x=108, y=36, width=34, height=18, rx=8, fill=TINTA, transform="rotate(6 125 45)"))
        e.append(_el("path", d="M92 48 Q100 42 108 46", fill="none", stroke=TINTA, stroke_width=4))
    if rol == "periodista" and look["extra"] not in ("gorra",) and estilo not in ("afro", "mono"):
        e.append(_el("path", d="M44 60 Q60 22 108 22 Q150 24 160 52 Q120 40 44 60 Z", fill="#8A5A44", **_S))
        e.append(_el("circle", cx=104, cy=24, r=5, fill="#8A5A44", stroke=TINTA, stroke_width=3))
    return _txt(e, respaldo=True) + _txt(e)


def svg_bot(expresion: str = "neutral") -> str:
    e = []
    e.append(_el("ellipse", cx=100, cy=288, rx=56, ry=9, fill=TINTA, opacity="0.16"))
    e.append(_el("rect", True, x=70, y=226, width=26, height=52, rx=8, fill="#8A93B5", **_S))
    e.append(_el("rect", True, x=104, y=226, width=26, height=52, rx=8, fill="#8A93B5", **_S))
    e.append(_el("rect", True, x=50, y=156, width=100, height=82, rx=20, fill="#B8C0DA", **_S))
    e.append(_el("circle", cx=100, cy=196, r=14, fill="#FF5F6D", stroke=TINTA, stroke_width=3))
    e.append(_el("rect", True, x=32, y=166, width=20, height=56, rx=10, fill="#9AA3C4", **_S))
    e.append(_el("rect", True, x=148, y=166, width=20, height=56, rx=10, fill="#9AA3C4", **_S))
    e.append(_el("path", d="M100 36 L100 14", stroke=TINTA, stroke_width=5, stroke_linecap="round"))
    e.append(_el("circle", True, cx=100, cy=12, r=9, fill="#FF5F6D", **_S))
    e.append(_el("rect", True, x=38, y=36, width=124, height=112, rx=30, fill="#C9D0E6", **_S))
    e.append(_el("rect", x=52, y=56, width=96, height=66, rx=18, fill="#2B2A4C", stroke=TINTA, stroke_width=3))
    ojo = "#FF5F6D" if expresion in ("enojado", "feliz") else "#7CFFCB"
    e.append(_el("rect", x=68, y=76, width=20, height=14, rx=5, fill=ojo))
    e.append(_el("rect", x=112, y=76, width=20, height=14, rx=5, fill=ojo))
    e.append(_el("path", d="M80 106 L88 102 L96 108 L104 102 L112 108 L120 104", fill="none", stroke=ojo,
                 stroke_width=3.5, stroke_linecap="round", stroke_linejoin="round"))
    return _txt(e, respaldo=True) + _txt(e)


def svg_civi(expresion: str = "feliz", parpadeo: bool = False, ala: float = 0.0) -> str:
    """Civi, la lechuza de Civitas: la mascota que da las indicaciones."""
    V, V2, B = "#6C4DF5", "#5638D9", "#EDE7FF"
    e = []
    e.append(_el("ellipse", cx=100, cy=288, rx=56, ry=9, fill=TINTA, opacity="0.16"))
    e.append(_el("path", True, d="M44 92 L36 40 L74 70 Z", fill=V2, **_S))
    e.append(_el("path", True, d="M156 92 L164 40 L126 70 Z", fill=V2, **_S))
    rot = -18 - 40 * ala
    e.append(_el("ellipse", True, cx=46, cy=190, rx=22, ry=46, fill=V2, transform=f"rotate({-rot:.1f} 56 160)", **_S))
    e.append(_el("ellipse", True, cx=154, cy=190, rx=22, ry=46, fill=V2, transform=f"rotate({rot:.1f} 144 160)", **_S))
    e.append(_el("ellipse", True, cx=100, cy=168, rx=74, ry=106, fill=V, **_S))
    e.append(_el("ellipse", cx=100, cy=200, rx=46, ry=62, fill=B))
    for i, y in enumerate((178, 198, 218)):
        for x in ((86, 114) if i % 2 == 0 else (100,)):
            e.append(_el("path", d=f"M{x - 8} {y} Q{x} {y + 9} {x + 8} {y}", fill="none", stroke="#C9BCFF",
                         stroke_width=3.5, stroke_linecap="round"))
    for x in (72, 128):
        e.append(_el("circle", cx=x, cy=112, r=27, fill="#FFFFFF", **_S))
    if parpadeo:
        for x in (72, 128):
            e.append(_el("path", d=f"M{x - 13} 113 Q{x} 121 {x + 13} 113", fill="none", stroke=TINTA,
                         stroke_width=5, stroke_linecap="round"))
    elif expresion == "feliz":
        for x in (72, 128):
            e.append(_el("path", d=f"M{x - 13} 118 Q{x} 100 {x + 13} 118", fill="none", stroke=TINTA,
                         stroke_width=6, stroke_linecap="round"))
    else:
        for x in (72, 128):
            e.append(_el("circle", cx=x + 2, cy=113, r=12, fill=TINTA))
            e.append(_el("circle", cx=x + 6, cy=108, r=4, fill="#FFFFFF"))
    e.append(_el("path", d="M90 134 L110 134 L100 152 Z", fill="#FFC23D", stroke=TINTA, stroke_width=3.5,
                 stroke_linejoin="round"))
    e.append(_el("path", d="M80 272 L80 282 M92 272 L92 284 M108 272 L108 284 M120 272 L120 282",
                 stroke="#FFC23D", stroke_width=6, stroke_linecap="round"))
    return _txt(e, respaldo=True) + _txt(e)


# ------------------------------------------------------------------ superficies

def cuerpo(look, rol="npc", expresion="neutral", alto=240, parpadeo=False, color_extra=None,
           bot=False) -> pygame.Surface:
    ancho = round(alto * 200 / 300)
    texto = svg_bot(expresion) if bot else svg_personaje(look, rol, expresion, parpadeo, color_extra)
    return recursos.svg(texto, ancho, alto, base=200)


def busto(look, rol="npc", expresion="neutral", tam=64, parpadeo=False, color_extra=None,
          bot=False) -> pygame.Surface:
    """Cabeza y hombros (recorte 14..186 x 0..172 del lienzo)."""
    texto = svg_bot(expresion) if bot else svg_personaje(look, rol, expresion, parpadeo, color_extra)
    k = 200 / 172
    recorte = f'<g transform="scale({k:.4f}) translate(-14 -2)">{texto}</g>'
    return recursos.svg(recorte, tam, tam, base=200)


def civi(expresion="feliz", alto=140, parpadeo=False, ala=0.0) -> pygame.Surface:
    ancho = round(alto * 200 / 300)
    return recursos.svg(svg_civi(expresion, parpadeo, round(ala, 1)), ancho, alto, base=200)


_avatares = recursos._LRU(700)


def avatar(look, tam, fondo, rol="npc", expresion="neutral", parpadeo=False, borde=None,
           grosor=3, color_extra=None, bot=False) -> pygame.Surface:
    """Busto recortado en un círculo con fondo de color (para la red, el feed y el árbol)."""
    clave = (repr(sorted(normalizar(look).items())) if not bot else "bot", tam, tuple(fondo[:3]), rol,
             expresion, parpadeo, tuple(borde[:3]) if borde else None, grosor,
             tuple(color_extra[:3]) if color_extra else None)

    def crear():
        s = pygame.Surface((tam, tam), pygame.SRCALPHA)
        pygame.draw.circle(s, fondo, (tam // 2, tam // 2), tam // 2)
        b = busto(look, rol, expresion, round(tam * 1.05), parpadeo, color_extra, bot)
        s.blit(b, ((tam - b.get_width()) // 2, round(tam * 0.06)))
        mascara = pygame.Surface((tam, tam), pygame.SRCALPHA)
        pygame.draw.circle(mascara, (255, 255, 255, 255), (tam // 2, tam // 2), tam // 2 - 1)
        s.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        if borde:
            pygame.draw.circle(s, borde, (tam // 2, tam // 2), tam // 2, grosor)
        return s
    return _avatares.obtener(clave, crear)
