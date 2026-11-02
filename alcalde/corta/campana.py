"""La campaña por Ciudad Nova: el mapa, el contagio entre barrios, estrellas, monedas, mejoras y el álbum.

Estructuras:
  * Mapa de la ciudad (grafo no dirigido): solo se puede jugar en barrios vecinos de uno ya liberado,
    y cada noche el rumor salta de un barrio enfermo a uno vecino (un paso de BFS desde los focos).
    Los barrios liberados hacen de muro: el rumor no pasa por ellos.
  * Red social (grafo dirigido): de ella salen los autores de las publicaciones y quiénes reenvían.
  * Archivo de hechos (árbol AVL): cada noticia verdadera que dejas llegar se guarda; el álbum la
    muestra en orden alfabético (recorrido en inorden).
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..estructuras.archivo_avl import ArchivoHechosAVL
from ..modelo.mapa import ZONAS, crear_mapa, nombre_zona
from ..modelo.red_social import generar_red
from .contenido import MEJORAS, SENALES

INICIO = "PLAZA"
FINAL = "ALCALDIA"
DIAS = 12
ARCHIVO = Path.home() / ".alcalde_digital_campana.json"


@dataclass
class Campana:
    semilla: int
    personaje: dict
    dia: int = 1
    monedas: int = 0
    puntos: int = 0
    mejoras: dict = field(default_factory=lambda: {k: 0 for k in MEJORAS})
    estrellas: dict = field(default_factory=dict)
    liberadas: list = field(default_factory=list)
    infeccion: dict = field(default_factory=dict)
    senales: list = field(default_factory=list)
    terminada: bool = False
    eleccion: Optional[dict] = None
    archivo: ArchivoHechosAVL = field(default_factory=ArchivoHechosAVL)

    def __post_init__(self):
        self.mapa = crear_mapa()
        self.red = generar_red(random.Random(self.semilla), self.mapa, set())
        self.rng = random.Random(self.semilla * 7 + self.dia)
        if not self.infeccion:
            self.infeccion = {z: 0 for z in ZONAS}
            focos = [z for z in ZONAS if z not in (INICIO, FINAL) and z not in self.mapa.vecinos(INICIO)]
            for z in self.rng.sample(sorted(focos), 2):
                self.infeccion[z] = 2

    @classmethod
    def nueva(cls, personaje: dict, semilla: Optional[int] = None) -> "Campana":
        return cls(semilla if semilla is not None else random.randrange(1 << 30), dict(personaje))

    # -------------------------------------------------------------- mapa
    def disponibles(self) -> list[str]:
        """Barrios que se pueden jugar hoy: el inicio, o los vecinos de un barrio liberado."""
        if not self.liberadas:
            return [INICIO]
        vecinos = set()
        for z in self.liberadas:
            vecinos |= set(self.mapa.vecinos(z))
        return sorted(z for z in vecinos if z not in self.liberadas)

    def estado_zona(self, z) -> str:
        if z in self.liberadas:
            return "liberada"
        if z in self.disponibles():
            return "disponible"
        return "bloqueada"

    def ruta_desde_inicio(self, z) -> list[str]:
        """Camino de menos minutos desde la Plaza hasta un barrio (Dijkstra), para dibujarlo en el mapa."""
        return self.mapa.camino_mas_corto(INICIO, z)[1]

    # -------------------------------------------------------------- después de jugar un nivel
    def registrar(self, res: dict) -> dict:
        """Guarda lo que pasó en un nivel y hace pasar la noche. Devuelve lo que cambió en el mapa."""
        z = res["zona"]
        nuevo = {"estrellas_antes": self.estrellas.get(z, 0), "contagios": [], "focos": [], "hechos_nuevos": [],
                 "senales_nuevas": []}
        self.monedas += res["monedas"]
        self.puntos += res["puntos"]
        if res["estrellas"] > self.estrellas.get(z, 0):
            self.estrellas[z] = res["estrellas"]
        if res["estrellas"] >= 1 and z not in self.liberadas:
            self.liberadas.append(z)
            self.infeccion[z] = 0
            nuevo["liberada"] = z
        for s in res.get("senales", []):
            if s in SENALES and s not in self.senales:
                self.senales.append(s)
                nuevo["senales_nuevas"].append(s)
        for h in res.get("hechos", []):
            if h not in self.archivo:
                self.archivo.insertar(h, h)
                nuevo["hechos_nuevos"].append(h)
        if z == FINAL and res["estado"] == "ganado":
            self.terminar()
            return nuevo
        nuevo.update(self.noche())
        if self.dia > DIAS:
            self.terminar()
        return nuevo

    def noche(self) -> dict:
        """El rumor avanza un paso por el mapa: cada barrio muy enfermo contagia a un vecino no liberado."""
        self.dia += 1
        contagios, focos = [], []
        enfermos = sorted(z for z, n in self.infeccion.items() if n >= 2 and z not in self.liberadas)
        for z in enfermos:
            vecinos = sorted(v for v in self.mapa.vecinos(z) if v not in self.liberadas and self.infeccion[v] < 3)
            if vecinos:
                v = self.rng.choice(vecinos)
                self.infeccion[v] += 1
                contagios.append((z, v))
            self.infeccion[z] = min(3, self.infeccion[z] + (1 if self.rng.random() < 0.3 else 0))
        libres = sorted(z for z in ZONAS if z not in self.liberadas and self.infeccion[z] == 0 and z != FINAL)
        if libres and self.rng.random() < 0.35:
            z = self.rng.choice(libres)
            self.infeccion[z] = 1
            focos.append(z)
        return {"contagios": contagios, "focos": focos}

    # -------------------------------------------------------------- tienda
    def precio(self, mejora) -> Optional[int]:
        nivel = self.mejoras.get(mejora, 0)
        precios = MEJORAS[mejora][3]
        return precios[nivel] if nivel < len(precios) else None

    def comprar(self, mejora) -> bool:
        p = self.precio(mejora)
        if p is None or self.monedas < p:
            return False
        self.monedas -= p
        self.mejoras[mejora] += 1
        return True

    # -------------------------------------------------------------- elección
    def terminar(self):
        self.terminada = True
        self.eleccion = self.votar()

    def votar(self) -> dict:
        """Cada barrio vota. Los liberados votan informados; en los enfermos pesa la desinformación."""
        zonas = {}
        total = informados = 0
        for z, info in ZONAS.items():
            pob = info["poblacion"]
            if z in self.liberadas:
                frac = 0.62 + 0.12 * self.estrellas.get(z, 1)
            else:
                frac = max(0.1, 0.5 - 0.13 * self.infeccion.get(z, 0))
            zonas[z] = round(frac * 100)
            total += pob
            informados += pob * frac
        pct = round(100 * informados / total)
        final = "oro" if pct >= 80 else "plata" if pct >= 60 else "bronce" if pct >= 45 else "derrota"
        return dict(zonas=zonas, porcentaje=pct, final=final, estrellas=sum(self.estrellas.values()),
                    liberadas=len(self.liberadas), hechos=len(self.archivo), senales=len(self.senales))

    # -------------------------------------------------------------- guardar
    def a_dict(self) -> dict:
        return dict(semilla=self.semilla, personaje=self.personaje, dia=self.dia, monedas=self.monedas,
                    puntos=self.puntos, mejoras=self.mejoras, estrellas=self.estrellas, liberadas=self.liberadas,
                    infeccion=self.infeccion, senales=self.senales, terminada=self.terminada, eleccion=self.eleccion,
                    archivo=list(self.archivo.preorden()))

    @classmethod
    def desde_dict(cls, d: dict) -> "Campana":
        archivo = ArchivoHechosAVL.desde_preorden(d.get("archivo", []), lambda k: k)
        c = cls(d["semilla"], d["personaje"], d["dia"], d["monedas"], d.get("puntos", 0), d["mejoras"],
                d["estrellas"], d["liberadas"], d["infeccion"], d["senales"], d["terminada"], d["eleccion"], archivo)
        return c

    def guardar(self, ruta: Path = ARCHIVO):
        try:
            ruta.write_text(json.dumps(self.a_dict(), ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    @classmethod
    def cargar(cls, ruta: Path = ARCHIVO) -> Optional["Campana"]:
        try:
            return cls.desde_dict(json.loads(ruta.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def borrar(ruta: Path = ARCHIVO):
        try:
            ruta.unlink()
        except OSError:
            pass

    def resumen_zona(self, z) -> str:
        n = self.infeccion.get(z, 0)
        if z in self.liberadas:
            return f"{nombre_zona(z)}: liberado"
        return f"{nombre_zona(z)}: " + ("tranquilo" if n == 0 else "con rumores" if n == 1 else
                                         "muy enfermo" if n == 2 else "lleno de mentiras")
