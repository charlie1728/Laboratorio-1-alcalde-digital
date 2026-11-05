"""Árbol de decisiones de una noticia (las estrellas del juego).

Problema que resuelve: cada estrella que recoges pasa por decisiones (mirarla antes de
compartirla, entregarla sin mirar o dejarla) y cada camino tiene consecuencias distintas en
los puntos y en los indicadores de la ciudad. El árbol guarda esas reglas en un solo lugar:
la partida baja por el árbol según lo que hace el jugador y la hoja dice qué pasa.
Al final del turno se dibuja el árbol con cuántas veces pasaste por cada rama.

Variante: árbol general con aristas etiquetadas (cada hijo se llega por una etiqueta).
Insertar: agregar un hijo con su etiqueta. Eliminar: quitar un nodo con su subárbol.
Recorridos: preorden (para dibujarlo) y por niveles; buscar un camino de la raíz a una hoja.
"""
from collections import deque


class NodoDecision:
    def __init__(self, clave, texto, efecto=None):
        self.clave = clave
        self.texto = texto
        self.hijos = {}          # etiqueta -> NodoDecision
        self.padre = None
        self.efecto = efecto or {}
        self.veces = 0

    @property
    def es_hoja(self):
        return not self.hijos


class ArbolDecision:
    def __init__(self, raiz):
        self.raiz = raiz
        self._indice = {raiz.clave: raiz}

    def buscar(self, clave):
        return self._indice.get(clave)

    def insertar(self, clave_padre, etiqueta, nodo):
        padre = self._indice[clave_padre]
        padre.hijos[etiqueta] = nodo
        nodo.padre = padre
        self._indice[nodo.clave] = nodo
        return nodo

    def eliminar(self, clave):
        nodo = self._indice.get(clave)
        if nodo is None or nodo is self.raiz:
            return False
        for c in [n.clave for n in self.preorden(nodo)]:
            self._indice.pop(c, None)
        padre = nodo.padre
        for et, h in list(padre.hijos.items()):
            if h is nodo:
                del padre.hijos[et]
        return True

    def preorden(self, desde=None):
        res, pila = [], [desde or self.raiz]
        while pila:
            n = pila.pop()
            res.append(n)
            pila.extend(reversed(list(n.hijos.values())))
        return res

    def por_niveles(self):
        res, cola = [], deque([(self.raiz, 0)])
        while cola:
            n, nivel = cola.popleft()
            res.append((n, nivel))
            cola.extend((h, nivel + 1) for h in n.hijos.values())
        return res

    def hojas(self):
        return [n for n in self.preorden() if n.es_hoja]

    def recorrer(self, etiquetas):
        """Baja por el árbol siguiendo las etiquetas, cuenta la visita en cada nodo y devuelve la hoja."""
        nodo = self.raiz
        nodo.veces += 1
        for et in etiquetas:
            nodo = nodo.hijos[et]
            nodo.veces += 1
        return nodo

    def camino_a(self, clave):
        nodo, res = self._indice.get(clave), []
        while nodo is not None:
            res.append(nodo.clave)
            nodo = nodo.padre
        return res[::-1]

    def reiniciar(self):
        for n in self.preorden():
            n.veces = 0


def arbol_noticia():
    """El árbol que usa el juego. Las hojas traen puntos y cambios en los indicadores."""
    N = NodoDecision
    a = ArbolDecision(N("noticia", "Encuentras una noticia"))
    a.insertar("noticia", "mirar", N("mirar", "Te detienes a mirarla"))
    a.insertar("noticia", "entregar", N("sin_mirar", "La compartes sin mirar"))
    a.insertar("noticia", "ignorar", N("ignorar", "La dejas pasar",
                                         {"puntos": 0}))
    a.insertar("mirar", "real", N("real", "Es real"))
    a.insertar("mirar", "falsa", N("reporte", "Era un Bulo: lo reportas",
                                     {"puntos": 15, "informacion": 4, "desinformacion": -4}))
    a.insertar("real", "entregar", N("verdad", "Compartes una verdad",
                                       {"puntos": 25, "informacion": 6, "confianza": 4, "bienestar": 2}))
    a.insertar("real", "ignorar", N("perdida", "Se te pasó entregarla", {"puntos": 0, "confianza": -1}))
    a.insertar("sin_mirar", "real", N("suerte", "Era real: tuviste suerte",
                                        {"puntos": 10, "informacion": 2}))
    a.insertar("sin_mirar", "falsa", N("bulo", "Compartiste un Bulo",
                                         {"puntos": -20, "informacion": -6, "confianza": -6,
                                          "desinformacion": 8, "bienestar": -3}))
    return a
