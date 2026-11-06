"""Árbol de decisiones de cada publicación de Civitas (los Bulos y las estrellas del juego).

Problema que resuelve: toda publicación que aparece en el barrio termina de una forma, y cada
final tiene consecuencias distintas en los indicadores de la ciudad. Es exactamente el ejemplo
del enunciado: una publicación puede ser falsa o verdadera, y con ella se puede REPORTAR
(atrapar el Bulo en el aire), VERIFICAR (curar a quien se lo creyó), COMPARTIR (llevar la
estrella a la gente) o IGNORAR (dejar pasar una estrella que se tuvo en frente). El árbol guarda
esas reglas en un solo lugar: el juego baja por el árbol según lo que pasó y la hoja dice qué
consecuencias tiene. Al final del turno se dibuja con cuántas veces se pasó por cada rama.

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


def arbol_publicacion():
    """El árbol que usa el juego. Las hojas traen los puntos y los cambios en los indicadores.

    Publicación
    ├── falsa (un Bulo)
    │   ├── atrapar  -> Reportar: lo atrapas antes de que llegue a alguien
    │   └── llega    -> Alguien se la cree
    │       ├── curar -> Verificar: le muestras la verdad y se cura
    │       └── pasar -> Se la pasa a un amigo por la red social
    └── verdadera (una estrella)
        ├── compartir -> Compartir: la llevas y protege a la gente
        └── ignorar   -> Ignorar: la tuviste en frente y la dejaste pasar
    """
    N = NodoDecision
    a = ArbolDecision(N("publicacion", "Aparece una publicación"))
    a.insertar("publicacion", "falsa", N("falsa", "Es falsa (un Bulo)"))
    a.insertar("publicacion", "verdadera", N("verdadera", "Es verdadera (una estrella)"))
    a.insertar("falsa", "atrapar", N("reportada", "La atrapas: la reportas",
                                      {"desinformacion": -0.6, "informacion": 0.3}))
    a.insertar("falsa", "llega", N("creida", "Alguien se la cree"))
    a.insertar("creida", "curar", N("verificada", "Lo curas: verificas",
                                     {"confianza": 1.5, "bienestar": 1, "desinformacion": -0.4}))
    a.insertar("creida", "pasar", N("regada", "Se la pasa a un amigo",
                                     {"desinformacion": 1.5, "confianza": -1}))
    a.insertar("verdadera", "compartir", N("compartida", "La compartes",
                                            {"puntos": 20, "informacion": 5, "confianza": 2, "bienestar": 1}))
    a.insertar("verdadera", "ignorar", N("perdida", "Se pierde: la ignoras", {"informacion": -1}))
    return a
