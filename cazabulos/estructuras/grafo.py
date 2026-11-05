"""Grafo no dirigido y ponderado con lista de adyacencia.

Se usa dos veces en el juego:
- Grafo social: los vecinos son vértices y los hilos de amistad son aristas (peso = confianza).
  Por ahí viajan los Bulos (BFS) y las noticias del Influencer.
- Grafo de la ciudad: las zonas y esquinas son vértices y las calles son aristas (peso = distancia).
  Dijkstra da la ruta más corta para la flecha guía y para que los vecinos caminen entre zonas.
"""
import heapq
from collections import deque


class Grafo:
    def __init__(self):
        self.ady = {}      # vértice -> {vecino: peso}
        self.datos = {}    # vértice -> información extra (posición, nombre...)

    # ------------------------------------------------------------- operaciones básicas
    def agregar_vertice(self, v, **datos):
        self.ady.setdefault(v, {})
        self.datos.setdefault(v, {}).update(datos)

    def eliminar_vertice(self, v):
        for u in list(self.ady.get(v, {})):
            del self.ady[u][v]
        self.ady.pop(v, None)
        self.datos.pop(v, None)

    def agregar_arista(self, a, b, peso=1):
        if a == b:
            return
        self.agregar_vertice(a)
        self.agregar_vertice(b)
        self.ady[a][b] = peso
        self.ady[b][a] = peso

    def eliminar_arista(self, a, b):
        existia = b in self.ady.get(a, {})
        self.ady.get(a, {}).pop(b, None)
        self.ady.get(b, {}).pop(a, None)
        return existia

    def tiene_arista(self, a, b):
        return b in self.ady.get(a, {})

    def peso(self, a, b):
        return self.ady[a][b]

    def vecinos(self, v):
        return self.ady.get(v, {})

    def grado(self, v):
        return len(self.ady.get(v, {}))

    def vertices(self):
        return list(self.ady)

    def aristas(self):
        vistas, res = set(), []
        for a, vs in self.ady.items():
            for b, p in vs.items():
                if (b, a) not in vistas:
                    vistas.add((a, b))
                    res.append((a, b, p))
        return res

    def __len__(self):
        return len(self.ady)

    def __contains__(self, v):
        return v in self.ady

    # ------------------------------------------------------------- recorridos
    def bfs(self, origen, filtro=None, max_nivel=None):
        """Recorrido por anchura. Devuelve [(vértice, nivel, padre)] en el orden en que se visitan.
        filtro(v) decide si se puede pasar por v (el origen siempre entra)."""
        if origen not in self.ady:
            return []
        orden = [(origen, 0, None)]
        visto = {origen}
        cola = deque([(origen, 0)])
        while cola:
            v, nivel = cola.popleft()
            if max_nivel is not None and nivel >= max_nivel:
                continue
            for u in sorted(self.ady[v], key=str):
                if u in visto or (filtro and not filtro(u)):
                    continue
                visto.add(u)
                orden.append((u, nivel + 1, v))
                cola.append((u, nivel + 1))
        return orden

    def dfs(self, origen, filtro=None):
        """Recorrido en profundidad (iterativo). Devuelve la lista de vértices visitados."""
        if origen not in self.ady:
            return []
        orden, visto, pila = [], set(), [origen]
        while pila:
            v = pila.pop()
            if v in visto:
                continue
            visto.add(v)
            orden.append(v)
            for u in sorted(self.ady[v], key=str, reverse=True):
                if u not in visto and (not filtro or filtro(u)):
                    pila.append(u)
        return orden

    def componentes(self, filtro=None):
        """Grupos de vértices conectados entre sí (comunidades del barrio)."""
        visto, res = set(), []
        for v in sorted(self.ady, key=str):
            if v in visto or (filtro and not filtro(v)):
                continue
            grupo = self.dfs(v, filtro)
            visto.update(grupo)
            res.append(grupo)
        return res

    def dijkstra(self, origen):
        """Distancias mínimas desde el origen y el padre de cada vértice en la ruta."""
        dist = {v: float("inf") for v in self.ady}
        previo = {v: None for v in self.ady}
        if origen not in self.ady:
            return dist, previo
        dist[origen] = 0
        cola = [(0, 0, origen)]
        contador = 1
        while cola:
            d, _, v = heapq.heappop(cola)
            if d > dist[v]:
                continue
            for u, p in self.ady[v].items():
                nd = d + p
                if nd < dist[u]:
                    dist[u] = nd
                    previo[u] = v
                    heapq.heappush(cola, (nd, contador, u))
                    contador += 1
        return dist, previo

    def camino(self, origen, destino):
        """Ruta más corta (lista de vértices) o [] si no hay camino."""
        if origen not in self.ady or destino not in self.ady:
            return []
        dist, previo = self.dijkstra(origen)
        if dist[destino] == float("inf"):
            return []
        ruta, v = [], destino
        while v is not None:
            ruta.append(v)
            v = previo[v]
        return ruta[::-1]

    def mas_conectado(self, candidatos=None):
        cand = list(self.ady) if candidatos is None else [c for c in candidatos if c in self.ady]
        if not cand:
            return None
        return max(cand, key=lambda v: (self.grado(v), str(v)))
