"""Árbol n-ario de mutaciones de los Bulos.

Problema que resuelve: un rumor cambia cada vez que alguien lo reenvía. Cada Bulo que salta
de un vecino a otro es HIJO del Bulo que lo originó, así el juego sabe de dónde salió cada
mentira. La raíz (el Bulo con corona) es el rumor original: si lo atrapas, se elimina todo
su subárbol y caen todas sus copias de una vez.

Variante: árbol general (n-ario), cada nodo con lista de hijos y referencia al padre.
Insertar: se agrega un hijo a un nodo existente (o una raíz nueva).
Eliminar: se quita un nodo con todo su subárbol (recorrido en preorden).
Recorridos: preorden (la cadena al atrapar la raíz), postorden y por niveles.
"""
from collections import deque


class NodoBulo:
    __slots__ = ("id", "padre", "hijos", "datos")

    def __init__(self, ident, padre=None, **datos):
        self.id = ident
        self.padre = padre
        self.hijos = []
        self.datos = datos

    def __repr__(self):
        return f"NodoBulo({self.id})"


class ArbolMutaciones:
    def __init__(self):
        self.nodos = {}
        self.raices = []
        self.eliminados = 0
        self.mayor_cadena = 0      # el subárbol más grande que se ha cortado de una vez

    def __contains__(self, ident):
        return ident in self.nodos

    def __len__(self):
        return len(self.nodos)

    def crear_raiz(self, ident, **datos):
        nodo = NodoBulo(ident, None, **datos)
        self.nodos[ident] = nodo
        self.raices.append(nodo)
        return nodo

    def insertar(self, ident, padre_id, **datos):
        """El Bulo 'ident' es una mutación de 'padre_id'. Si el padre ya no existe, queda como raíz."""
        padre = self.nodos.get(padre_id)
        if padre is None:
            return self.crear_raiz(ident, **datos)
        nodo = NodoBulo(ident, padre, **datos)
        padre.hijos.append(nodo)
        self.nodos[ident] = nodo
        return nodo

    def preorden(self, ident):
        nodo = self.nodos.get(ident)
        if nodo is None:
            return []
        res, pila = [], [nodo]
        while pila:
            n = pila.pop()
            res.append(n.id)
            pila.extend(reversed(n.hijos))
        return res

    def postorden(self, ident):
        nodo = self.nodos.get(ident)
        if nodo is None:
            return []
        res = []

        def visitar(n):
            for h in n.hijos:
                visitar(h)
            res.append(n.id)
        visitar(nodo)
        return res

    def por_niveles(self, ident):
        nodo = self.nodos.get(ident)
        if nodo is None:
            return []
        res, cola = [], deque([(nodo, 0)])
        while cola:
            n, nivel = cola.popleft()
            res.append((n.id, nivel))
            cola.extend((h, nivel + 1) for h in n.hijos)
        return res

    def eliminar_subarbol(self, ident):
        """Quita el nodo y toda su descendencia. Devuelve los ids eliminados en preorden."""
        nodo = self.nodos.get(ident)
        if nodo is None:
            return []
        ids = self.preorden(ident)
        if nodo.padre is not None:
            nodo.padre.hijos.remove(nodo)
        else:
            self.raices.remove(nodo)
        for i in ids:
            del self.nodos[i]
        self.eliminados += len(ids)
        self.mayor_cadena = max(self.mayor_cadena, len(ids))
        return ids

    def tamano(self, ident):
        return len(self.preorden(ident))

    def altura(self, ident):
        nodo = self.nodos.get(ident)
        if nodo is None:
            return -1
        return max((nivel for _, nivel in self.por_niveles(ident)), default=0)

    def raiz_de(self, ident):
        nodo = self.nodos.get(ident)
        while nodo is not None and nodo.padre is not None:
            nodo = nodo.padre
        return nodo.id if nodo else None

    def camino_a_raiz(self, ident):
        res, nodo = [], self.nodos.get(ident)
        while nodo is not None:
            res.append(nodo.id)
            nodo = nodo.padre
        return res

    def es_raiz(self, ident):
        nodo = self.nodos.get(ident)
        return nodo is not None and nodo.padre is None

    def tiene_hijos(self, ident):
        nodo = self.nodos.get(ident)
        return bool(nodo and nodo.hijos)

    def mayor_arbol(self):
        """La raíz con más descendientes vivos (la cadena más peligrosa del barrio)."""
        if not self.raices:
            return None
        return max(self.raices, key=lambda r: self.tamano(r.id)).id
