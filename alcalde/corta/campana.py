"""La campaña por Ciudad Nova: el mapa, el contagio entre barrios, estrellas, monedas, mejoras y el álbum.

Estructuras:
  * Mapa de la ciudad (grafo no dirigido): solo se puede jugar en barrios vecinos de uno ya liberado,
    y cada noche el rumor salta de un barrio enfermo a uno vecino (un paso de BFS desde los focos).
    Los barrios liberados hacen de muro: el rumor no pasa por ellos.
  * Red social (grafo dirigido): de ella salen los autores de las publicaciones y quiénes reenvían.
  * Archivo de hechos (árbol AVL): cada noticia verdadera que dejas llegar se guarda; el álbum la
    muestra en orden alfabético (recorrido en inorden).
Además la ciudad tiene seis indicadores (información verificada, confianza, convivencia, bienestar digital,
desinformación y conflictos) que suben o bajan con lo que pasa en cada nivel y en cada noche. Al final
votan los barrios y el resultado sale de esos indicadores y de qué barrios se liberaron.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..estructuras.archivo_avl import ArchivoHechosAVL
from ..modelo.mapa import ZONAS, crear_mapa, nombre_zona
from ..modelo.red_social import conectar_jugador, generar_red
from .contenido import CANDIDATOS, INDICADORES, INDICADORES_INICIO, MEJORAS, SENALES

INICIO = "PLAZA"
FINAL = "ALCALDIA"
DIAS = 12
PARA_EL_JEFE = 4          # barrios liberados (sin contar la Alcaldía) para poder enfrentar al jefe
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
    indicadores: dict = field(default_factory=lambda: dict(INDICADORES_INICIO))
    stats: dict = field(default_factory=dict)     # lo que hizo el jugador en toda la campaña (para el periódico)
    diario: list = field(default_factory=list)    # titulares de cada día

    def __post_init__(self):
        self.mapa = crear_mapa()
        nombre = self.personaje.get("nombre") or "Tú"
        self.red = generar_red(random.Random(self.semilla), self.mapa, {nombre})
        # El jugador también es un vértice de la red social: lo que comparte les llega a sus seguidores.
        conectar_jugador(self.red, self.mapa, random.Random(self.semilla + 1), nombre, 0,
                         self.personaje.get("rol", "periodista"), self.personaje.get("look") or {}, INICIO)
        for k, v in INDICADORES_INICIO.items():
            self.indicadores.setdefault(k, v)
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
        """Barrios que se pueden jugar hoy: el inicio, o los vecinos de un barrio liberado.
        La Alcaldía (el jefe) además pide haber liberado PARA_EL_JEFE barrios."""
        if not self.liberadas:
            return [INICIO]
        vecinos = set()
        for z in self.liberadas:
            vecinos |= set(self.mapa.vecinos(z))
        return sorted(z for z in vecinos if z not in self.liberadas and (z != FINAL or self.jefe_abierto()))

    def liberados_sin_jefe(self) -> int:
        return len([z for z in self.liberadas if z != FINAL])

    def jefe_abierto(self) -> bool:
        return self.liberados_sin_jefe() >= PARA_EL_JEFE

    def estado_zona(self, z) -> str:
        if z in self.liberadas:
            return "liberada"
        if z in self.disponibles():
            return "disponible"
        return "bloqueada"

    def mision(self, z) -> str:
        """La misión del día en un barrio: cambia cada día, pero es la misma en el mapa y en el nivel."""
        from .nivel import elegir_mision
        return elegir_mision(z, random.Random(self.semilla * 17 + self.dia * 31 + sum(map(ord, z))))

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
        nuevo["indicadores_antes"] = dict(self.indicadores)
        self.mover_indicadores(res.get("efectos", {}))
        self._contar(res)
        nuevo["titular"] = self.titular(res, nuevo)
        self.diario.append(dict(dia=self.dia, titulo=nuevo["titular"][0], bajada=nuevo["titular"][1]))
        if nuevo.get("liberada"):
            self.mover_indicadores(dict(confianza=3, desinformacion=-3))
        if z == FINAL and res["estado"] == "ganado":
            self.terminar()
            return nuevo
        nuevo.update(self.noche())
        if self.dia > DIAS:
            self.terminar()
        return nuevo

    def _contar(self, res: dict):
        s = self.stats
        decis = res.get("decisiones", [])
        for k, v in (("niveles", 1), ("ganados", res["estado"] == "ganado"), ("cortadas", res.get("cortadas", 0)),
                     ("salvadas", res.get("salvadas", 0)), ("calmadas", res.get("calmadas", 0)),
                     ("misiones", bool((res.get("mision") or {}).get("cumplida"))),
                     ("verificadas", sum(d["clave"].startswith("v_") for d in decis)),
                     ("frenadas", sum(d["clave"] in ("v_no_reportar", "r_no") for d in decis)),
                     ("mentiras_compartidas", sum(d["clave"] in ("c_no", "v_no_compartir") for d in decis)),
                     ("verdades_compartidas", sum(d["clave"] in ("c_si", "v_si_compartir") for d in decis))):
            s[k] = s.get(k, 0) + int(v)

    def titular(self, res: dict, nuevo: dict) -> tuple[str, str]:
        """El titular del Diario Nova al día siguiente: cuenta lo más importante que pasó en el nivel."""
        barrio = nombre_zona(res["zona"])
        quien = self.personaje.get("nombre", "Alguien")
        for d in res.get("decisiones", []):
            if d["clave"] in ("c_no", "v_no_compartir"):
                return (f"Rumor viral llegó a {d['alcance']} vecinos",
                        f"«{d.get('texto', '')}» era falso y se compartió en Civitas.")
            if d["clave"] in ("v_no_reportar", "r_no"):
                return (f"{quien} frenó un rumor viral", f"«{d.get('texto', '')}» era falso: lo reportaron a tiempo.")
            if d["clave"] in ("c_si", "v_si_compartir"):
                return (f"Noticia real llegó a {d['alcance']} vecinos", f"«{d.get('texto', '')}», confirmado.")
        if res["estado"] != "ganado":
            return f"Los rumores ganan en {barrio}", "Mañana habrá otra oportunidad para recuperar el barrio."
        if nuevo.get("liberada"):
            return f"{barrio} vuelve a confiar", f"Cortaron {res.get('cortadas', 0)} mentiras en un solo día."
        return f"Otro día tranquilo en {barrio}", f"{res.get('salvadas', 0)} noticias reales llegaron a la gente."

    def mover_indicadores(self, cambios: dict):
        for k, v in cambios.items():
            if k in self.indicadores:
                self.indicadores[k] = max(0, min(100, round(self.indicadores[k] + v)))

    def indicadores_lista(self) -> list[tuple]:
        """(id, nombre corto, ícono, valor, ¿es mejor que suba?) en el orden en que se muestran."""
        return [(k, INDICADORES[k][1], INDICADORES[k][2], self.indicadores[k], INDICADORES[k][3]) for k in INDICADORES]

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
        # De noche los rumores que saltan suben la desinformación y los conflictos de la ciudad.
        self.mover_indicadores(dict(desinformacion=2 * len(contagios) + len(focos), conflictos=len(contagios)))
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

    def candidatos(self) -> list[dict]:
        """Los cuatro candidatos. Si juegas con el Candidato, tú reemplazas a uno de los tres honestos."""
        lista = [dict(c) for c in CANDIDATOS]
        if self.personaje.get("rol") == "candidato":
            lista[1].update(id="jugador", nombre=self.personaje.get("nombre", "Tú") + " (tú)", lema="Tu campaña",
                            color=tuple(self.personaje.get("color", (120, 220, 140))), jugador=True)
        return lista

    def votar(self) -> dict:
        """Cada barrio vota. Los informados votan por propuestas; los desinformados, por la campaña de bots.

        Qué tan informado vota un barrio depende de si lo liberaste (y con cuántas estrellas), de cuánto
        rumor le quedó y de los indicadores de la ciudad (verificada, confianza, convivencia y bienestar
        ayudan; desinformación y conflictos estorban).
        """
        ind = self.indicadores
        clima = ((ind["verificada"] + ind["confianza"] + ind["convivencia"] + ind["bienestar"]) / 4
                 - (ind["desinformacion"] + ind["conflictos"]) / 2) / 250
        candidatos = self.candidatos()
        honestos = [c for c in candidatos if not c.get("bot")]
        votos = {c["id"]: 0.0 for c in candidatos}
        zonas = {}
        total = informados = 0
        for z, info in ZONAS.items():
            pob = info["poblacion"]
            if z in self.liberadas:
                frac = 0.62 + 0.12 * self.estrellas.get(z, 1)
            else:
                frac = 0.5 - 0.13 * self.infeccion.get(z, 0)
            frac = max(0.1, min(0.97, frac + clima))
            zonas[z] = round(frac * 100)
            total += pob
            informados += pob * frac
            # Los informados votan sobre todo por el candidato que más conocen en su barrio. De los
            # desinformados, la mitad le cree a la campaña de bots y la otra mitad vota al azar.
            local = next((c for c in honestos if z in c["barrios"]), honestos[0])
            for c in honestos:
                votos[c["id"]] += pob * frac * (0.6 if c is local else 0.2) + pob * (1 - frac) * 0.5 / len(honestos)
            votos["emilio"] += pob * (1 - frac) * 0.5
        pct = round(100 * informados / total)
        final = "oro" if pct >= 80 else "plata" if pct >= 60 else "bronce" if pct >= 45 else "derrota"
        reparto = {k: round(100 * v / total, 1) for k, v in votos.items()}
        ganador = max(reparto, key=reparto.get)
        if ganador == "emilio":
            final = "derrota"
        return dict(zonas=zonas, porcentaje=pct, final=final, estrellas=sum(self.estrellas.values()),
                    liberadas=len(self.liberadas), hechos=len(self.archivo), senales=len(self.senales),
                    votos=reparto, ganador=ganador, indicadores=dict(ind))

    # -------------------------------------------------------------- guardar
    def a_dict(self) -> dict:
        return dict(semilla=self.semilla, personaje=self.personaje, dia=self.dia, monedas=self.monedas,
                    puntos=self.puntos, mejoras=self.mejoras, estrellas=self.estrellas, liberadas=self.liberadas,
                    infeccion=self.infeccion, senales=self.senales, terminada=self.terminada, eleccion=self.eleccion,
                    archivo=list(self.archivo.preorden()), indicadores=self.indicadores, stats=self.stats,
                    diario=self.diario[-30:])

    @classmethod
    def desde_dict(cls, d: dict) -> "Campana":
        archivo = ArchivoHechosAVL.desde_preorden(d.get("archivo", []), lambda k: k)
        return cls(d["semilla"], d["personaje"], d["dia"], d["monedas"], d.get("puntos", 0), d["mejoras"],
                   d["estrellas"], d["liberadas"], d["infeccion"], d["senales"], d["terminada"], d["eleccion"], archivo,
                   dict(d.get("indicadores") or INDICADORES_INICIO), dict(d.get("stats") or {}),
                   list(d.get("diario") or []))

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
