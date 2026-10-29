"""Utilidades compartidas por las vistas del juego (colores de caso, caras, estados)."""
from __future__ import annotations

from ..modelo.hechos import CANDIDATOS
from . import personajes
from .tema import TEMA

CASO_COLORES = [(108, 77, 245), (46, 176, 168), (255, 111, 97), (242, 153, 74), (58, 134, 255),
                (230, 70, 140), (120, 170, 40)]

EXPRESION = {"falso": "confundido", "corregido": "feliz", "veraz": "neutral", "duda": "neutral",
             "nada": "neutral"}


def color_caso(cid: int):
    return CASO_COLORES[(cid - 1) % len(CASO_COLORES)]


def estado_nodo(n) -> str:
    if n.es_correccion:
        return "correccion"
    if not n.verificado:
        return "nada"
    return "veraz" if n.es_veraz else "falso"


def color_estado(estado: str):
    c = TEMA.c
    return {"falso": c["n_falso"], "veraz": c["n_veraz"], "corregido": c["n_correccion"],
            "correccion": c["n_correccion"], "duda": c["n_duda"]}.get(estado, c["n_desconocido"])


def forma_creencia(estado: str) -> str:
    return {"falso": "falso", "veraz": "veraz", "corregido": "correccion", "duda": "duda"}.get(estado, "nada")


def info_persona(p, nombre):
    """(look, rol, bot, color del jugador o None)."""
    j = p.jugador_de(nombre)
    if j is not None:
        return j.look, j.rol, False, j.color
    c = p.ciudadano(nombre)
    if c is None:
        return {}, "npc", nombre.startswith("@"), None
    return c.look, "npc", c.bot, None


def cara(p, nombre, tam, fondo=None, expresion="neutral", borde=None, grosor=3, parpadeo=False):
    look, rol, bot, color = info_persona(p, nombre)
    c = TEMA.c
    fondo = fondo or (color if color else c["papel2"])
    j = p.jugador_de(nombre)
    extra = dict(CANDIDATOS).get(j.candidato, (58, 110, 230)) if j is not None and j.candidato else (58, 110, 230)
    return personajes.avatar(look, tam, fondo, rol, expresion, parpadeo, borde or c["borde"], grosor,
                             color_extra=extra, bot=bot)
