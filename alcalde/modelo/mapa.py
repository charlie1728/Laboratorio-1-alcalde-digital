from __future__ import annotations

from ..estructuras.grafo import Grafo

# Minutos que tiene cada jugador por turno. Con 12 alcanza para 2 publicaciones (verificar y decidir
# cuestan 4 cada una) y una calle corta, pero no para todo: ir hasta el rumor cuesta una publicación.
MINUTOS_POR_TURNO = 12

# pos: coordenadas normalizadas (0-1) para dibujar el mapa; poblacion: votantes de la zona.
ZONAS = {
    "NORTE":    dict(nombre="Barrio Norte",       tipo="barrio",   pos=(0.12, 0.10), poblacion=14000),
    "TERMINAL": dict(nombre="Terminal de buses",  tipo="terminal", pos=(0.48, 0.09), poblacion=8000),
    "ESTADIO":  dict(nombre="Estadio Municipal",  tipo="estadio",  pos=(0.87, 0.11), poblacion=5000),
    "COLEGIO":  dict(nombre="Colegio San José",   tipo="colegio",  pos=(0.10, 0.50), poblacion=6000),
    "PARQUE":   dict(nombre="Parque Central",     tipo="parque",   pos=(0.40, 0.45), poblacion=5000),
    "HOSPITAL": dict(nombre="Hospital Nova",      tipo="hospital", pos=(0.89, 0.50), poblacion=6000),
    "PLAZA":    dict(nombre="Plaza de Mercado",   tipo="plaza",    pos=(0.72, 0.72), poblacion=9000),
    "PRADO":    dict(nombre="Barrio El Prado",    tipo="barrio2",  pos=(0.16, 0.92), poblacion=12000),
    "ALCALDIA": dict(nombre="Alcaldía",           tipo="alcaldia", pos=(0.50, 0.92), poblacion=7000),
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
