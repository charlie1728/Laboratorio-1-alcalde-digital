from __future__ import annotations

import random

from .hechos import CANDIDATOS
from .mapa import ZONAS
from .red_social import residentes

# Cuánto pesa en una zona que todos sus residentes crean un rumor contra un candidato.
CASTIGO_RUMOR = 18


def _reparto(votantes: int, puntaje: dict) -> dict:
    pot = {c: max(0.5, s) ** 2 for c, s in puntaje.items()}
    total = sum(pot.values())
    votos = {c: int(votantes * v / total) for c, v in pot.items()}
    sobran = votantes - sum(votos.values())
    for c in sorted(pot, key=lambda c: -pot[c])[:sobran]:
        votos[c] += 1
    return votos


def calcular_eleccion(p) -> dict:
    """Votación por zonas del mapa.

    Cada zona vota según el apoyo de cada candidato, la gira de los candidatos
    jugadores y lo que creen sus residentes: si creen un rumor falso contra alguien,
    ese candidato pierde votos allí. Se calcula también el resultado "sin rumores"
    para mostrar cuánto cambió la desinformación la elección.
    """
    rng = random.Random(round(p.ciudad.salud() * 1000 + sum(p.apoyo.values()) * 7))
    cands = [c[0] for c in CANDIDATOS]
    base = dict(p.apoyo)
    for j in p.jugadores:
        if j.candidato:
            bono = (j.reputacion - 50) / 8 + j.stats["verificados"] * 0.25 + j.stats["corregidos"] * 0.1
            base[j.candidato] += max(-8.0, min(6.0, bono))
    v = p.ciudad.v
    part_base = 0.47 + 0.3 * (v["bienestar"] + v["convivencia"]) / 200 - 0.18 * v["conflictos"] / 100

    zonas, tot, tot_sin = {}, {c: 0 for c in cands}, {c: 0 for c in cands}
    for z, info in ZONAS.items():
        gente = residentes(p.red, z)
        n = max(1, len(gente))
        castigo = {c: 0 for c in cands}
        for r in gente:
            for caso in p.casos:
                if caso.creencia.get(r) == "falso":
                    sujeto = p._version_de(caso, r)
                    for c in cands:
                        if c in sujeto:
                            castigo[c] += 1
        ruido = {c: rng.uniform(-3, 3) for c in cands}
        puntaje = {c: base[c] + p.apoyo_zona[z][c] + ruido[c] - CASTIGO_RUMOR * castigo[c] / n for c in cands}
        puntaje_sin = {c: base[c] + p.apoyo_zona[z][c] + ruido[c] for c in cands}
        part = max(0.25, min(0.9, part_base - 0.25 * p.tension(z) / 100))
        votantes = round(info["poblacion"] * part)
        votos = _reparto(votantes, puntaje)
        votos_sin = _reparto(votantes, puntaje_sin)
        for c in cands:
            tot[c] += votos[c]
            tot_sin[c] += votos_sin[c]
        zonas[z] = dict(votos=votos, participacion=round(part, 3), votantes=votantes,
                        ganador=max(votos, key=votos.get), castigo=castigo)

    ganador = max(tot, key=tot.get)
    ganador_sin = max(tot_sin, key=tot_sin.get)
    votantes = sum(z["votantes"] for z in zonas.values())
    poblacion = sum(z["poblacion"] for z in ZONAS.values())
    return dict(zonas=zonas, totales=tot, totales_sin_rumores=tot_sin, ganador=ganador,
                ganador_sin_rumores=ganador_sin, cambio=ganador != ganador_sin,
                participacion=round(votantes / poblacion, 3), votantes=votantes,
                perdidos=dict((c, max(0, tot_sin[c] - tot[c])) for c in cands))
