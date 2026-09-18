"""
Árbol de Mutaciones (árbol n-ario general con raíz).

Problema que resuelve
---------------------
En Civitas una publicación no se comparte "igual": cada vez que alguien la
reenvía puede cambiarle algo (exagera una cifra, quita el contexto, cambia la
fuente...). El árbol guarda la GENEALOGÍA de un rumor:

    - la raíz es la publicación original (paciente cero),
    - cada hijo es un reenvío hecho a partir de su padre,
    - cada nodo recuerda qué distorsión nueva introdujo (si introdujo alguna).

Con esa forma podemos responder preguntas que el juego necesita:

    * ¿De dónde salió esta versión?          -> camino_a_raiz()
    * ¿En qué reenvío exacto se torció?      -> punto_de_mutacion()
    * ¿Qué tan lejos/rápido llegó?           -> por_niveles(), altura()
    * ¿Cuánta gente vio la versión falsa?    -> postorden() (agregación)
    * Si reporto este nodo, ¿qué cae con él? -> podar()  (subárbol completo)
    * ¿Dos versiones vienen del mismo tronco?-> ancestro_comun()

Variante: árbol general (n-ario) con referencia al padre, sin orden entre
hermanos, más un índice hash id -> nodo para acceder en O(1) al nodo que el
jugador selecciona con el mouse.
"""
from __future__ import annotations

import itertools
from collections import deque
from typing import Callable, Iterator, Optional


class NodoMutacion:
    """Un reenvío (o la publicación original si no tiene padre)."""

    _ids = itertools.count(1)

    def __init__(self, afirmacion, autor: str, turno: int = 0,
                 distorsion: Optional[str] = None, alcance: int = 10,
                 es_correccion: bool = False):
        self.id: int = next(NodoMutacion._ids)
        self.afirmacion = afirmacion          # modelo.afirmacion.Afirmacion
        self.autor = autor                    # quién lo publicó / reenvió
        self.turno = turno                    # ronda en que apareció
        self.distorsion = distorsion          # distorsión NUEVA en este nodo
        self.alcance = alcance                # personas que lo vieron
        self.es_correccion = es_correccion    # nodo de desmentido
        self.padre: Optional[NodoMutacion] = None
        self.hijos: list[NodoMutacion] = []
        # estado de juego
        self.verificado = False               # alguien ya revisó este nodo
        self.inmune = False                   # ya no muta ni se reenvía
        self.viral = False                    # marcado por evento viral
        self.creado_ms = 0                    # para animación (lo pone la UI)

    # --- propiedades de la estructura -----------------------------------
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
    """Árbol general de la genealogía de un rumor."""

    def __init__(self, titulo: str, raiz: NodoMutacion):
        self.titulo = titulo
        self.raiz: Optional[NodoMutacion] = raiz
        self._indice: dict[int, NodoMutacion] = {raiz.id: raiz}

    # =================================================================
    # Consultas básicas
    # =================================================================
    def __len__(self) -> int:
        return len(self._indice)

    def __contains__(self, nodo_id: int) -> bool:
        return nodo_id in self._indice

    def buscar(self, nodo_id: int) -> Optional[NodoMutacion]:
        """O(1) gracias al índice hash (el mouse selecciona por id)."""
        return self._indice.get(nodo_id)

    def altura(self, nodo: Optional[NodoMutacion] = None) -> int:
        """Altura en aristas. Árbol de un solo nodo -> 0. Vacío -> -1."""
        nodo = self.raiz if nodo is None else nodo
        if nodo is None:
            return -1
        if not nodo.hijos:
            return 0
        return 1 + max(self.altura(h) for h in nodo.hijos)

    def hojas(self) -> list[NodoMutacion]:
        return [n for n in self.preorden() if n.es_hoja]

    # =================================================================
    # Inserción
    # =================================================================
    def insertar(self, padre_id: int, nodo: NodoMutacion) -> NodoMutacion:
        """Agrega `nodo` como reenvío (hijo) de `padre_id`. O(1)."""
        padre = self._indice.get(padre_id)
        if padre is None:
            raise KeyError(f"No existe el nodo {padre_id}")
        if nodo.id in self._indice:
            raise ValueError("El nodo ya está en el árbol")
        nodo.padre = padre
        padre.hijos.append(nodo)
        self._indice[nodo.id] = nodo
        return nodo

    # =================================================================
    # Eliminación
    # =================================================================
    def podar(self, nodo_id: int) -> list[NodoMutacion]:
        """REPORTAR: elimina el nodo y TODO su subárbol.

        Recorre el subárbol en postorden (primero hijos, luego el padre)
        para sacarlos del índice. Devuelve los nodos eliminados.
        Si se poda la raíz el árbol queda vacío.
        """
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
        """BORRAR MI PUBLICACIÓN: quita solo ese nodo.

        Sus hijos NO desaparecen: se re-enganchan al abuelo (los reenvíos ya
        hechos siguen circulando). Es la lección de "borrar no deshace lo
        compartido". Si se elimina la raíz, su primer hijo pasa a ser raíz y
        adopta a sus hermanos.
        """
        nodo = self._indice.get(nodo_id)
        if nodo is None:
            raise KeyError(f"No existe el nodo {nodo_id}")
        hijos = list(nodo.hijos)
        if nodo.padre is not None:
            padre = nodo.padre
            pos = padre.hijos.index(nodo)
            padre.hijos[pos:pos + 1] = hijos      # conserva el orden
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

    # =================================================================
    # Recorridos
    # =================================================================
    def preorden(self, nodo: Optional[NodoMutacion] = None) -> Iterator[NodoMutacion]:
        """Raíz -> hijos (izq. a der.). Orden "cronológico" del hilo:
        así se lee una conversación y así se propaga un DESMENTIDO hacia
        abajo (se marca el padre antes que los hijos)."""
        nodo = self.raiz if nodo is None else nodo
        if nodo is None:
            return
        yield nodo
        for h in nodo.hijos:
            yield from self.preorden(h)

    def postorden(self, nodo: Optional[NodoMutacion] = None) -> Iterator[NodoMutacion]:
        """Hijos -> raíz. Sirve para AGREGAR de abajo hacia arriba
        (alcance total de un subárbol) y para podar sin dejar huérfanos."""
        nodo = self.raiz if nodo is None else nodo
        if nodo is None:
            return
        for h in nodo.hijos:
            yield from self.postorden(h)
        yield nodo

    def por_niveles(self, nodo: Optional[NodoMutacion] = None) -> list[list[NodoMutacion]]:
        """BFS. Cada nivel = una "ola" de reenvíos. El número de niveles
        mide qué tan rápido/lejos viajó el rumor."""
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
        """RASTREAR ORIGEN: [nodo, padre, abuelo, ..., raíz]. O(profundidad)."""
        nodo = self._indice.get(nodo_id)
        if nodo is None:
            raise KeyError(f"No existe el nodo {nodo_id}")
        camino = []
        while nodo is not None:
            camino.append(nodo)
            nodo = nodo.padre
        return camino

    # =================================================================
    # Operaciones propias del juego
    # =================================================================
    def punto_de_mutacion(self, nodo_id: int) -> dict[str, NodoMutacion]:
        """Para cada distorsión presente en `nodo_id`, devuelve el ancestro
        (o el mismo nodo) donde se introdujo por PRIMERA vez.
        Se obtiene subiendo por camino_a_raiz."""
        resultado: dict[str, NodoMutacion] = {}
        for n in self.camino_a_raiz(nodo_id):          # de abajo hacia arriba
            if n.distorsion:
                resultado[n.distorsion] = n            # el más alto gana
        return resultado

    def ancestro_comun(self, a_id: int, b_id: int) -> Optional[NodoMutacion]:
        """Ancestro común más bajo (LCA): ¿dónde se separaron dos versiones?"""
        vistos = {n.id for n in self.camino_a_raiz(a_id)}
        for n in self.camino_a_raiz(b_id):
            if n.id in vistos:
                return n
        return None

    def agregar(self, funcion: Callable[[NodoMutacion], int],
                nodo: Optional[NodoMutacion] = None) -> dict[int, int]:
        """Agregación en postorden: total[nodo] = f(nodo) + Σ total[hijos].
        Devuelve un dict id -> total del subárbol."""
        totales: dict[int, int] = {}
        for n in self.postorden(nodo):
            totales[n.id] = funcion(n) + sum(totales[h.id] for h in n.hijos)
        return totales

    def estadisticas(self) -> dict[str, int]:
        """Resumen usado por los indicadores de la ciudad."""
        if self.raiz is None:
            return dict(nodos=0, alcance=0, alcance_falso=0, verificados=0,
                        altura=-1, olas=0, activos=0)
        alcance = self.agregar(lambda n: n.alcance)[self.raiz.id]
        falso = self.agregar(lambda n: 0 if n.es_veraz else n.alcance)[self.raiz.id]
        verif = sum(1 for n in self.preorden() if n.verificado)
        activos = sum(1 for n in self.preorden() if not n.inmune and not n.es_correccion)
        return dict(nodos=len(self), alcance=alcance, alcance_falso=falso,
                    verificados=verif, altura=self.altura(),
                    olas=len(self.por_niveles()), activos=activos)

    def inmunizar(self, nodo_id: int) -> list[NodoMutacion]:
        """DESMENTIDO: marca el subárbol en preorden como inmune
        (ya no muta ni se sigue reenviando). Devuelve los marcados."""
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
        """Nodos que todavía pueden reenviarse en la próxima ola."""
        return [n for n in self.preorden() if not n.inmune and not n.es_correccion]
