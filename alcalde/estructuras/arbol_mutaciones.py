from __future__ import annotations

from collections import deque
from typing import Callable, Iterator, Optional

class NodoMutacion:

    _siguiente = 1

    def __init__(self, afirmacion, autor: str, turno: int = 0,
                 distorsion: Optional[str] = None, alcance: int = 10,
                 es_correccion: bool = False, id: Optional[int] = None):
        if id is None:
            id = NodoMutacion._siguiente
        NodoMutacion._siguiente = max(NodoMutacion._siguiente, id + 1)
        self.id: int = id
        self.afirmacion = afirmacion
        self.autor = autor
        self.turno = turno
        self.distorsion = distorsion
        self.alcance = alcance
        self.es_correccion = es_correccion
        self.padre: Optional[NodoMutacion] = None
        self.hijos: list[NodoMutacion] = []
        self.verificado = False
        self.inmune = False
        self.viral = False
        # True cuando el nodo ya entregó la publicación a sus seguidores (BFS: vértice procesado).
        self.entregado = False

    @property
    def es_raiz(self) -> bool:
        return self.padre is None

    @property
    def es_hoja(self) -> bool:
        return not self.hijos

    @property
    def profundidad(self) -> int:
        d, n = 0, self
        while n.padre is not None:
            d += 1
            n = n.padre
        return d

    @property
    def es_veraz(self) -> bool:
        return self.es_correccion or not self.afirmacion.distorsiones

    def __repr__(self) -> str:
        return f"Nodo#{self.id}({self.autor})"

class ArbolMutaciones:

    def __init__(self, titulo: str, raiz: NodoMutacion):
        self.titulo = titulo
        self.raiz: Optional[NodoMutacion] = raiz
        self._indice: dict[int, NodoMutacion] = {raiz.id: raiz}

    def __len__(self) -> int:
        return len(self._indice)

    def __contains__(self, nodo_id: int) -> bool:
        return nodo_id in self._indice

    def buscar(self, nodo_id: int) -> Optional[NodoMutacion]:
        return self._indice.get(nodo_id)

    def altura(self, nodo: Optional[NodoMutacion] = None) -> int:
        nodo = self.raiz if nodo is None else nodo
        if nodo is None:
            return -1
        if not nodo.hijos:
            return 0
        return 1 + max(self.altura(h) for h in nodo.hijos)

    def hojas(self) -> list[NodoMutacion]:
        return [n for n in self.preorden() if n.es_hoja]

    def insertar(self, padre_id: int, nodo: NodoMutacion) -> NodoMutacion:
        padre = self._indice.get(padre_id)
        if padre is None:
            raise KeyError(f"No existe el nodo {padre_id}")
        if nodo.id in self._indice:
            raise ValueError("El nodo ya está en el árbol")
        nodo.padre = padre
        padre.hijos.append(nodo)
        self._indice[nodo.id] = nodo
        return nodo

    def podar(self, nodo_id: int) -> list[NodoMutacion]:
        nodo = self._indice.get(nodo_id)
        if nodo is None:
            raise KeyError(f"No existe el nodo {nodo_id}")
        eliminados = list(self.postorden(nodo))
        for n in eliminados:
            del self._indice[n.id]
        if nodo.padre is None:
            self.raiz = None
        else:
            nodo.padre.hijos.remove(nodo)
            nodo.padre = None
        return eliminados

    def eliminar_nodo(self, nodo_id: int) -> NodoMutacion:
        nodo = self._indice.get(nodo_id)
        if nodo is None:
            raise KeyError(f"No existe el nodo {nodo_id}")
        hijos = list(nodo.hijos)
        if nodo.padre is not None:
            padre = nodo.padre
            pos = padre.hijos.index(nodo)
            padre.hijos[pos:pos + 1] = hijos                         
            for h in hijos:
                h.padre = padre
        else:
            if hijos:
                nueva = hijos[0]
                nueva.padre = None
                for h in hijos[1:]:
                    h.padre = nueva
                    nueva.hijos.append(h)
                self.raiz = nueva
            else:
                self.raiz = None
        nodo.hijos = []
        nodo.padre = None
        del self._indice[nodo.id]
        return nodo

    def preorden(self, nodo: Optional[NodoMutacion] = None) -> Iterator[NodoMutacion]:
        nodo = self.raiz if nodo is None else nodo
        if nodo is None:
            return
        yield nodo
        for h in nodo.hijos:
            yield from self.preorden(h)

    def postorden(self, nodo: Optional[NodoMutacion] = None) -> Iterator[NodoMutacion]:
        nodo = self.raiz if nodo is None else nodo
        if nodo is None:
            return
        for h in nodo.hijos:
            yield from self.postorden(h)
        yield nodo

    def por_niveles(self, nodo: Optional[NodoMutacion] = None) -> list[list[NodoMutacion]]:
        nodo = self.raiz if nodo is None else nodo
        if nodo is None:
            return []
        niveles: list[list[NodoMutacion]] = []
        cola = deque([(nodo, 0)])
        while cola:
            actual, d = cola.popleft()
            if d == len(niveles):
                niveles.append([])
            niveles[d].append(actual)
            for h in actual.hijos:
                cola.append((h, d + 1))
        return niveles

    def camino_a_raiz(self, nodo_id: int) -> list[NodoMutacion]:
        nodo = self._indice.get(nodo_id)
        if nodo is None:
            raise KeyError(f"No existe el nodo {nodo_id}")
        camino = []
        while nodo is not None:
            camino.append(nodo)
            nodo = nodo.padre
        return camino

    def punto_de_mutacion(self, nodo_id: int) -> dict[str, NodoMutacion]:
        resultado: dict[str, NodoMutacion] = {}
        for n in self.camino_a_raiz(nodo_id):                                 
            if n.distorsion:
                resultado[n.distorsion] = n                              
        return resultado

    def ancestro_comun(self, a_id: int, b_id: int) -> Optional[NodoMutacion]:
        vistos = {n.id for n in self.camino_a_raiz(a_id)}
        for n in self.camino_a_raiz(b_id):
            if n.id in vistos:
                return n
        return None

    def agregar(self, funcion: Callable[[NodoMutacion], int],
                nodo: Optional[NodoMutacion] = None) -> dict[int, int]:
        totales: dict[int, int] = {}
        for n in self.postorden(nodo):
            totales[n.id] = funcion(n) + sum(totales[h.id] for h in n.hijos)
        return totales

    def estadisticas(self) -> dict[str, int]:
        if self.raiz is None:
            return dict(nodos=0, alcance=0, alcance_falso=0, verificados=0,
                        altura=-1, olas=0, activos=0)
        alcance = self.agregar(lambda n: n.alcance)[self.raiz.id]
        falso = self.agregar(lambda n: 0 if n.es_veraz else n.alcance)[self.raiz.id]
        verif = sum(1 for n in self.preorden() if n.verificado)
        activos = len(self.frontera())
        return dict(nodos=len(self), alcance=alcance, alcance_falso=falso,
                    verificados=verif, altura=self.altura(),
                    olas=len(self.por_niveles()), activos=activos)

    def inmunizar(self, nodo_id: int) -> list[NodoMutacion]:
        nodo = self._indice.get(nodo_id)
        if nodo is None:
            raise KeyError(f"No existe el nodo {nodo_id}")
        marcados = []
        for n in self.preorden(nodo):
            if not n.inmune:
                n.inmune = True
                marcados.append(n)
        return marcados

    def frontera(self) -> list[NodoMutacion]:
        """Nodos que todavía pueden propagarse: ni contenidos ni entregados."""
        return [n for n in self.preorden() if not n.inmune and not n.entregado]
