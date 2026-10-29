from __future__ import annotations

from ..estructuras.grafo import Grafo

MINUTOS_POR_TURNO = 15

# pos: coordenadas normalizadas (0-1) para dibujar el mapa; poblacion: votantes de la zona.
ZONAS = {
    "NORTE":    dict(nombre="Barrio Norte",       tipo="barrio",   pos=(0.14, 0.17), poblacion=14000),
    "TERMINAL": dict(nombre="Terminal de buses",  tipo="terminal", pos=(0.47, 0.15), poblacion=8000),
    "ESTADIO":  dict(nombre="Estadio Municipal",  tipo="estadio",  pos=(0.85, 0.16), poblacion=5000),
    "COLEGIO":  dict(nombre="Colegio San José",   tipo="colegio",  pos=(0.13, 0.52), poblacion=6000),
    "PARQUE":   dict(nombre="Parque Central",     tipo="parque",   pos=(0.38, 0.47), poblacion=5000),
    "HOSPITAL": dict(nombre="Hospital Nova",      tipo="hospital", pos=(0.86, 0.50), poblacion=6000),
    "PLAZA":    dict(nombre="Plaza de Mercado",   tipo="plaza",    pos=(0.62, 0.60), poblacion=9000),
    "PRADO":    dict(nombre="Barrio El Prado",    tipo="barrio2",  pos=(0.17, 0.86), poblacion=12000),
    "ALCALDIA": dict(nombre="Alcaldía",           tipo="alcaldia", pos=(0.50, 0.86), poblacion=7000),
}

CALLES = [
    ("NORTE", "COLEGIO", 7), ("NORTE", "TERMINAL", 9), ("COLEGIO", "PARQUE", 5),
    ("COLEGIO", "PRADO", 8), ("TERMINAL", "PARQUE", 6), ("TERMINAL", "ESTADIO", 8),
    ("TERMINAL", "HOSPITAL", 10), ("ESTADIO", "HOSPITAL", 7), ("PARQUE", "PLAZA", 4),
    ("PLAZA", "HOSPITAL", 6), ("PLAZA", "ALCALDIA", 5), ("PRADO", "ALCALDIA", 7),
    ("PARQUE", "ALCALDIA", 8),
]


def crear_mapa() -> Grafo:
    g = Grafo(dirigido=False)
    for zid, z in ZONAS.items():
        g.agregar_vertice(zid, z)
    for a, b, minutos in CALLES:
        g.agregar_arista(a, b, minutos)
    return g


def nombre_zona(zid: str) -> str:
    return ZONAS[zid]["nombre"] if zid in ZONAS else str(zid)
