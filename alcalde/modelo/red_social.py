from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..estructuras.grafo import Grafo
from .apariencia import look_aleatorio

# (nombre, femenino)
CIUDADANOS = [
    ("Ana", True), ("Luis", False), ("Pedro", False), ("María", True), ("Carlos", False),
    ("Sofía", True), ("Andrés", False), ("Camila", True), ("Jorge", False), ("Daniela", True),
    ("Mateo", False), ("Paula", True), ("Iván", False), ("Rosa", True), ("Kevin", False),
    ("Laura", True), ("Nicolás", False), ("Valeria", True), ("Samuel", False), ("Juliana", True),
]
RESERVA = [
    ("Diana", True), ("Óscar", False), ("Lucía", True), ("Felipe", False), ("Mónica", True),
    ("Hernán", False), ("Yuli", True), ("Brayan", False), ("Natalia", True), ("Esteban", False),
    ("Gloria", True), ("Wilson", False),
]
BOTS = ["@NoticiasYa24", "@LaVerdadOculta", "@AlertaNova", "@InfoUrgente_", "@NovaSinCensura"]

# Cuántos ciudadanos viven en cada zona (suman 20).
REPARTO = {"NORTE": 4, "PRADO": 4, "COLEGIO": 2, "PARQUE": 2, "PLAZA": 2,
           "ALCALDIA": 2, "HOSPITAL": 2, "TERMINAL": 1, "ESTADIO": 1}

SEGUIDORES_POR_ROL = {"ciudadano": 4, "periodista": 6, "influencer": 12, "candidato": 8}
SIGUE_POR_ROL = {"ciudadano": 5, "periodista": 6, "influencer": 4, "candidato": 5}
ZONA_INICIAL = {"ciudadano": ["NORTE", "PRADO"], "periodista": ["PLAZA", "TERMINAL"],
                "influencer": ["PARQUE", "ESTADIO"], "candidato": ["ALCALDIA"]}
MAX_CIUDADANOS = 26


@dataclass
class Ciudadano:
    nombre: str
    zona: str
    credulidad: float = 0.5
    actividad: float = 0.6
    look: dict = field(default_factory=dict)
    jugador: Optional[int] = None
    bot: bool = False

    @property
    def es_npc(self) -> bool:
        return self.jugador is None


def _amistad(g: Grafo, a: str, b: str, peso: float) -> None:
    g.agregar_arista(a, b, peso, tipo="amistad")
    g.agregar_arista(b, a, peso, tipo="amistad")


def generar_red(rng, mapa: Grafo, nombres_ocupados: set[str]) -> Grafo:
    """Red social de los 20 ciudadanos de Civitas (dirigida y ponderada).

    Las amistades son más probables entre vecinos de la misma zona o de zonas
    conectadas por una calle, así que el grafo social se apoya en el de la ciudad.
    """
    g = Grafo(dirigido=True)
    reserva = [r for r in RESERVA if r[0] not in nombres_ocupados]
    zonas = [z for z, n in REPARTO.items() for _ in range(n)]
    rng.shuffle(zonas)
    for (nombre, fem), zona in zip(CIUDADANOS, zonas):
        if nombre in nombres_ocupados:
            nombre, fem = reserva.pop(0)
        g.agregar_vertice(nombre, Ciudadano(
            nombre, zona, credulidad=round(rng.uniform(0.25, 0.8), 2),
            actividad=round(rng.uniform(0.35, 0.9), 2), look=look_aleatorio(rng, fem)))

    gente = g.vertices()
    for i, a in enumerate(gente):
        for b in gente[i + 1:]:
            za, zb = g.dato(a).zona, g.dato(b).zona
            if za == zb:
                p, rango = 0.65, (0.55, 0.9)
            elif mapa.tiene_arista(za, zb):
                p, rango = 0.22, (0.4, 0.75)
            else:
                p, rango = 0.05, (0.3, 0.6)
            if rng.random() < p:
                _amistad(g, a, b, round(rng.uniform(*rango), 2))

    # Dos superpropagadores: mucha gente los sigue aunque no sean sus amigos.
    activos = sorted(gente, key=lambda v: -g.dato(v).actividad)[:4]
    for sp in rng.sample(activos, 2):
        candidatos = [v for v in gente if v != sp and not g.tiene_arista(sp, v)]
        for v in rng.sample(candidatos, min(6, len(candidatos))):
            g.agregar_arista(sp, v, round(rng.uniform(0.35, 0.6), 2), tipo="seguimiento")

    for v in gente:
        cerca = [w for w in gente if w != v and (g.dato(w).zona == g.dato(v).zona or
                                                 mapa.tiene_arista(g.dato(w).zona, g.dato(v).zona))]
        while (g.grado_salida(v) < 2 or g.grado_entrada(v) < 2) and cerca:
            w = rng.choice(cerca)
            cerca.remove(w)
            if not g.tiene_arista(v, w):
                _amistad(g, v, w, round(rng.uniform(0.45, 0.8), 2))

    comps = g.componentes_conexas()
    for comp in comps[1:]:
        _amistad(g, rng.choice(comp), rng.choice(comps[0]), round(rng.uniform(0.4, 0.7), 2))
    return g


def conectar_jugador(g: Grafo, mapa: Grafo, rng, nombre: str, idx: int, rol: str,
                     look: dict, zona: Optional[str] = None) -> Ciudadano:
    zona = zona or rng.choice(ZONA_INICIAL[rol])
    c = Ciudadano(nombre, zona, credulidad=0.0, actividad=0.0, look=look, jugador=idx)
    g.agregar_vertice(nombre, c)
    npcs = [v for v in g.vertices() if g.dato(v).es_npc and not g.dato(v).bot]

    def cercania(v):
        zv = g.dato(v).zona
        return 0 if zv == zona else 1 if mapa.tiene_arista(zv, zona) else 2

    orden = sorted(npcs, key=lambda v: (cercania(v), rng.random()))
    for v in orden[:SEGUIDORES_POR_ROL[rol]]:
        g.agregar_arista(nombre, v, round(rng.uniform(0.5, 0.8), 2), tipo="seguimiento")
    sigue = sorted(npcs, key=lambda v: (cercania(v), -g.grado_salida(v), rng.random()))
    for v in sigue[:SIGUE_POR_ROL[rol]]:
        g.agregar_arista(v, nombre, round(rng.uniform(0.5, 0.8), 2), tipo="seguimiento")
    return c


def residentes(g: Grafo, zona: str, solo_npc: bool = True) -> list[str]:
    return [v for v in g.vertices() if g.dato(v).zona == zona and (g.dato(v).es_npc or not solo_npc)]
