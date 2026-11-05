"""Una partida: jugadores, rondas y turnos. Mismo PC = por turnos; en línea = todos a la vez.

Cada ronda usa una semilla distinta, pero dentro de la ronda todos juegan con la MISMA
semilla (mismo barrio, mismos eventos). El orden de los turnos rota cada ronda.
"""
import random

from .personajes import PERSONAJES

MOMENTOS = {1: "Mañana", 2: "Tarde", 3: "Noche"}
CANDIDATOS = {
    "Lucia": ("Lucía Ríos", "Más libros y wifi para el colegio", (90, 200, 255)),
    "Marcos": ("Marcos Paz", "Un mercado limpio y seguro", (255, 170, 70)),
    "Elena": ("Elena Sol", "Parques y ciclovías para todos", (120, 220, 140)),
    "Emilio": ("Emilio Bot", "Promete todo... por cadenas", (170, 100, 255)),
    "Dani": ("Dani", "Escuchar al barrio y decir la verdad", (70, 140, 255)),
}


class Partida:
    def __init__(self, jugadores, rondas=2, duracion=90, tranquilo=False, semilla=None):
        self.jugadores = jugadores          # [{"clave", "piel", "pelo", "nombre"}]
        self.rondas = rondas
        self.duracion = duracion
        self.tranquilo = tranquilo
        base = semilla if semilla is not None else random.randrange(1, 10 ** 6)
        self.semillas = [base + 1013 * r for r in range(rondas)]
        self.ronda = 1
        self.paso = 0
        self.resultados = {}                # (ronda, índice jugador) -> resumen

    def orden(self, ronda=None):
        r = (ronda or self.ronda) - 1
        n = len(self.jugadores)
        return [(i + r) % n for i in range(n)]

    @property
    def actual(self):
        return self.orden()[self.paso]

    @property
    def semilla(self):
        return self.semillas[self.ronda - 1]

    def guardar(self, indice, resumen):
        self.resultados[(self.ronda, indice)] = resumen

    def avanzar(self):
        """Pasa al siguiente turno. Devuelve 'turno', 'ronda' (empieza otra) o 'fin'."""
        self.paso += 1
        if self.paso < len(self.jugadores):
            return "turno"
        if self.ronda < self.rondas:
            return "ronda"
        return "fin"

    def siguiente_ronda(self):
        self.ronda += 1
        self.paso = 0

    def total(self, i):
        return sum(r["total"] for (ronda, j), r in self.resultados.items() if j == i)

    def salvados(self, i):
        return sum(r["salvados"] for (ronda, j), r in self.resultados.items() if j == i)

    def ranking(self):
        idx = list(range(len(self.jugadores)))
        return sorted(idx, key=lambda i: (-self.total(i), -self.salvados(i)))

    def total_ronda(self, ronda, i):
        r = self.resultados.get((ronda, i))
        return r["total"] if r else 0


def calcular_eleccion(resultados, jugadores, votantes=1000):
    """La elección depende de cómo quedó el barrio en todos los turnos."""
    res = list(resultados.values())
    if not res:
        return [], {}
    prom = {k: sum(r["indicadores"][k] for r in res) / len(res) for k in res[0]["indicadores"]}
    rumores = {c: sum(r["rumores"].get(c, 0) for r in res) for c in ("Lucia", "Marcos", "Elena")}
    defendidos = {c: sum(r["defendidos"].get(c, 0) for r in res) for c in ("Lucia", "Marcos", "Elena")}
    bot = 0.06 + prom["desinformacion"] / 100 * 0.6 + prom["conflictos"] / 100 * 0.15 - prom["informacion"] / 100 * 0.12
    bot = max(0.04, min(0.8, bot))
    pesos = {
        "Lucia": 1 + prom["confianza"] / 120 + 0.35 * defendidos["Lucia"] - 0.4 * rumores["Lucia"],
        "Marcos": 1 + prom["convivencia"] / 120 + 0.35 * defendidos["Marcos"] - 0.4 * rumores["Marcos"],
        "Elena": 1 + prom["bienestar"] / 120 + 0.35 * defendidos["Elena"] - 0.4 * rumores["Elena"],
    }
    dani = [i for i, j in enumerate(jugadores) if j["clave"] == "dani"]
    if dani:
        mios = [r for (ronda, i), r in resultados.items() if i == dani[0]]
        if mios:
            pesos["Dani"] = 0.8 + 2.2 * sum(r["salvados"] / r["vecinos"] for r in mios) / len(mios)
    for c in pesos:
        pesos[c] = max(0.2, pesos[c])
    suma = sum(pesos.values())
    votos = {c: int(votantes * (1 - bot) * p / suma) for c, p in pesos.items()}
    votos["Emilio"] = votantes - sum(votos.values())
    orden = sorted(votos, key=lambda c: -votos[c])
    return orden, {"votos": votos, "promedio": prom, "rumores": rumores, "defendidos": defendidos}


def nombre_jugador(j):
    return j.get("nombre") or PERSONAJES[j["clave"]]["nombre"]
