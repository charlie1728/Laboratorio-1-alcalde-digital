from __future__ import annotations

import heapq
import math
from collections import deque
from typing import Any, Callable, Hashable, Iterator, Optional

Vertice = Hashable


class Grafo:
    """Grafo ponderado con lista de adyacencia: ``_ady[u][v] = datos de la arista``.

    Sirve para los dos grafos del juego:
      * la red social de Civitas (dirigido: u -> v significa "v sigue a u",
        así que lo que u publica le llega a v; el peso es la confianza de v en u);
      * el mapa de Ciudad Nova (no dirigido: el peso son los minutos de la calle).
    """

    def __init__(self, dirigido: bool = False):
        self.dirigido = dirigido
        self._ady: dict[Vertice, dict[Vertice, dict]] = {}
        self._inv: dict[Vertice, dict[Vertice, dict]] = {}
        self._datos: dict[Vertice, Any] = {}

    def __len__(self) -> int:
        return len(self._ady)

    def __contains__(self, v: Vertice) -> bool:
        return v in self._ady

    def __iter__(self) -> Iterator[Vertice]:
        return iter(self._ady)

    def vertices(self) -> list[Vertice]:
        return list(self._ady)

    def dato(self, v: Vertice) -> Any:
        return self._datos.get(v)

    def num_aristas(self) -> int:
        total = sum(len(vs) for vs in self._ady.values())
        return total if self.dirigido else total // 2

    def aristas(self) -> list[tuple[Vertice, Vertice, dict]]:
        vistas, res = set(), []
        for u, vs in self._ady.items():
            for v, a in vs.items():
                if not self.dirigido:
                    clave = frozenset((u, v))
                    if clave in vistas:
                        continue
                    vistas.add(clave)
                res.append((u, v, a))
        return res

    def agregar_vertice(self, v: Vertice, dato: Any = None) -> bool:
        if v in self._ady:
            if dato is not None:
                self._datos[v] = dato
            return False
        self._ady[v] = {}
        self._inv[v] = {}
        self._datos[v] = dato
        return True

    def eliminar_vertice(self, v: Vertice) -> list[tuple[Vertice, Vertice]]:
        """Quita el vértice y todas sus aristas. Devuelve las aristas eliminadas."""
        if v not in self._ady:
            raise KeyError(f"No existe el vértice {v!r}")
        quitadas = [(v, w) for w in self._ady[v]]
        if self.dirigido:
            quitadas += [(w, v) for w in self._inv[v]]
        for w in list(self._ady[v]):
            self._inv[w].pop(v, None)
            if not self.dirigido:
                self._ady[w].pop(v, None)
        for w in list(self._inv[v]):
            self._ady[w].pop(v, None)
        del self._ady[v], self._inv[v], self._datos[v]
        return quitadas

    def agregar_arista(self, u: Vertice, v: Vertice, peso: float = 1.0, **extra) -> dict:
        if u == v:
            raise ValueError("No se permiten lazos")
        for x in (u, v):
            if x not in self._ady:
                self.agregar_vertice(x)
        datos = dict(peso=peso, **extra)
        self._ady[u][v] = datos
        self._inv[v][u] = datos
        if not self.dirigido:
            self._ady[v][u] = datos
            self._inv[u][v] = datos
        return datos

    def eliminar_arista(self, u: Vertice, v: Vertice) -> bool:
        if u not in self._ady or v not in self._ady[u]:
            return False
        del self._ady[u][v]
        del self._inv[v][u]
        if not self.dirigido:
            del self._ady[v][u]
            del self._inv[u][v]
        return True

    def tiene_arista(self, u: Vertice, v: Vertice) -> bool:
        return u in self._ady and v in self._ady[u]

    def arista(self, u: Vertice, v: Vertice) -> Optional[dict]:
        return self._ady.get(u, {}).get(v)

    def peso(self, u: Vertice, v: Vertice) -> float:
        return self._ady[u][v]["peso"]

    def ajustar_peso(self, u: Vertice, v: Vertice, delta: float,
                     minimo: float = 0.05, maximo: float = 1.0) -> Optional[float]:
        a = self.arista(u, v)
        if a is None:
            return None
        a["peso"] = round(max(minimo, min(maximo, a["peso"] + delta)), 3)
        return a["peso"]

    def vecinos(self, u: Vertice) -> dict[Vertice, dict]:
        """Sucesores de u (en la red social: sus seguidores)."""
        return self._ady[u]

    def predecesores(self, v: Vertice) -> dict[Vertice, dict]:
        """Vértices con arista hacia v (en la red social: a quién sigue v)."""
        return self._inv[v]

    def contactos(self, u: Vertice) -> set[Vertice]:
        """Vecindario sin dirección: sucesores y predecesores."""
        return set(self._ady[u]) | set(self._inv[u])

    def grado_salida(self, u: Vertice) -> int:
        return len(self._ady[u])

    def grado_entrada(self, u: Vertice) -> int:
        return len(self._inv[u])

    def grado(self, u: Vertice) -> int:
        return len(self.contactos(u)) if self.dirigido else len(self._ady[u])

    def centralidad_grado(self, n: Optional[int] = None) -> list[tuple[Vertice, int]]:
        """Vértices ordenados por grado de salida (los superpropagadores primero)."""
        orden = sorted(self._ady, key=lambda v: (-len(self._ady[v]), str(v)))
        res = [(v, len(self._ady[v])) for v in orden]
        return res[:n] if n is not None else res

    def bfs(self, origen: Vertice, max_nivel: Optional[int] = None,
            filtro: Optional[Callable[[Vertice, Vertice, dict], bool]] = None
            ) -> tuple[list[Vertice], dict[Vertice, int], dict[Vertice, Optional[Vertice]]]:
        """Recorrido en anchura con cola. Devuelve (orden, nivel, padre).

        ``nivel[v]`` es el número de saltos desde el origen; ``padre`` forma el árbol BFS.
        """
        if origen not in self._ady:
            raise KeyError(f"No existe el vértice {origen!r}")
        orden, nivel, padre = [origen], {origen: 0}, {origen: None}
        cola = deque([origen])
        while cola:
            u = cola.popleft()
            if max_nivel is not None and nivel[u] >= max_nivel:
                continue
            for v, a in self._ady[u].items():
                if v in nivel or (filtro and not filtro(u, v, a)):
                    continue
                nivel[v] = nivel[u] + 1
                padre[v] = u
                orden.append(v)
                cola.append(v)
        return orden, nivel, padre

    def bfs_niveles(self, origen: Vertice, max_nivel: Optional[int] = None) -> list[list[Vertice]]:
        orden, nivel, _ = self.bfs(origen, max_nivel)
        niveles: list[list[Vertice]] = []
        for v in orden:
            while len(niveles) <= nivel[v]:
                niveles.append([])
            niveles[nivel[v]].append(v)
        return niveles

    def dfs(self, origen: Vertice, dirigido: Optional[bool] = None) -> list[Vertice]:
        """Recorrido en profundidad iterativo (con pila).

        Con ``dirigido=False`` ignora el sentido de las aristas (útil para componentes).
        """
        if origen not in self._ady:
            raise KeyError(f"No existe el vértice {origen!r}")
        usar_sentido = self.dirigido if dirigido is None else dirigido
        visitados, orden = set(), []
        pila = [origen]
        while pila:
            u = pila.pop()
            if u in visitados:
                continue
            visitados.add(u)
            orden.append(u)
            vecinos = list(self._ady[u]) if usar_sentido else list(self.contactos(u))
            for v in sorted(vecinos, key=str, reverse=True):
                if v not in visitados:
                    pila.append(v)
        return orden

    def componentes_conexas(self) -> list[list[Vertice]]:
        """Componentes (débilmente) conexas, de la más grande a la más pequeña."""
        vistos: set = set()
        comps = []
        for v in sorted(self._ady, key=str):
            if v in vistos:
                continue
            comp = self.dfs(v, dirigido=False)
            vistos.update(comp)
            comps.append(comp)
        comps.sort(key=len, reverse=True)
        return comps

    def es_conexo(self) -> bool:
        return len(self.componentes_conexas()) <= 1

    def dijkstra(self, origen: Vertice, costo: Optional[Callable[[dict], float]] = None,
                 limite: Optional[float] = None
                 ) -> tuple[dict[Vertice, float], dict[Vertice, Optional[Vertice]]]:
        """Caminos de costo mínimo desde ``origen`` con montículo (heapq).

        ``costo`` convierte los datos de la arista en un costo no negativo (por defecto el peso).
        Con ``limite`` no se expanden vértices más lejanos que ese costo.
        """
        if origen not in self._ady:
            raise KeyError(f"No existe el vértice {origen!r}")
        costo = costo or (lambda a: a["peso"])
        dist: dict[Vertice, float] = {origen: 0.0}
        prev: dict[Vertice, Optional[Vertice]] = {origen: None}
        heap = [(0.0, 0, origen)]
        contador = 1
        cerrados = set()
        while heap:
            d, _, u = heapq.heappop(heap)
            if u in cerrados:
                continue
            cerrados.add(u)
            for v, a in self._ady[u].items():
                c = costo(a)
                if c < 0:
                    raise ValueError("Dijkstra no admite costos negativos")
                nd = d + c
                if limite is not None and nd > limite + 1e-9:
                    continue
                if nd < dist.get(v, math.inf) - 1e-12:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, contador, v))
                    contador += 1
        return dist, prev

    @staticmethod
    def reconstruir(prev: dict, destino: Vertice) -> list[Vertice]:
        if destino not in prev:
            return []
        camino = []
        while destino is not None:
            camino.append(destino)
            destino = prev[destino]
        return camino[::-1]

    def camino_mas_corto(self, u: Vertice, v: Vertice) -> tuple[float, list[Vertice]]:
        dist, prev = self.dijkstra(u)
        if v not in dist:
            return math.inf, []
        return dist[v], self.reconstruir(prev, v)

    def alcanzables(self, origen: Vertice, limite: float) -> dict[Vertice, float]:
        """Vértices a los que se llega con costo total <= limite (Dijkstra acotado)."""
        return self.dijkstra(origen, limite=limite)[0]

    def confianza_maxima(self, origen: Vertice) -> tuple[dict[Vertice, float], dict]:
        """Camino de máxima confianza: maximiza el producto de pesos en (0, 1].

        Equivale a Dijkstra con costo -log(peso): sumar logaritmos es multiplicar
        probabilidades, y como 0 < peso <= 1 los costos nunca son negativos.
        """
        dist, prev = self.dijkstra(origen, costo=lambda a: -math.log(max(1e-6, a["peso"])))
        return {v: math.exp(-d) for v, d in dist.items()}, prev

    def a_dict(self) -> dict:
        return dict(dirigido=self.dirigido,
                    vertices=list(self._ady),
                    aristas=[[u, v, dict(a)] for u, v, a in self.aristas()])

    @classmethod
    def desde_dict(cls, d: dict, datos: Optional[dict] = None) -> "Grafo":
        g = cls(dirigido=d["dirigido"])
        for v in d["vertices"]:
            g.agregar_vertice(v, (datos or {}).get(v))
        for u, v, a in d["aristas"]:
            a = dict(a)
            peso = a.pop("peso", 1.0)
            g.agregar_arista(u, v, peso, **a)
        return g
