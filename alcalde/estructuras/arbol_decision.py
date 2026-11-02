"""Árbol de decisiones de la alerta viral (árbol n-ario con raíz).

Es el árbol del enunciado: ante una publicación viral el jugador escoge qué hacer y cada camino
termina en una consecuencia distinta.

                         PUBLICACIÓN VIRAL
              /         |            |           \\
        Verificar    Compartir     Reportar     Ignorar
            |            |            |            |
     ¿Es verdadera?  ¿Es verdadera? ¿Es verdadera? ¿Es verdadera?
        /      \\        /   \\        /   \\        /   \\
      Sí        No     Sí    No     Sí    No     Sí    No
     /  \\      /  \\
Compartir Reportar ...

Hay tres clases de nodo:
  * ACCIÓN: lo escoge el jugador (un botón por hijo).
  * PREGUNTA: la responde el juego mirando la publicación. Si ``revela`` es verdadero el jugador ve la
    respuesta (eso es verificar); si no, el juego la usa en silencio para saber qué pasó.
  * HOJA: la consecuencia. Guarda los puntos, los cambios en los indicadores de la ciudad y si la
    publicación se propaga por el grafo social (y desde quién).
"""
from __future__ import annotations

from collections import deque
from typing import Iterator, Optional

ACCION, PREGUNTA, HOJA = "accion", "pregunta", "hoja"


class NodoDecision:
    def __init__(self, clave: str, texto: str, tipo: str, icono: str = "", revela: bool = False,
                 respuesta: Optional[bool] = None, puntos: int = 0, efectos: Optional[dict] = None,
                 propaga: Optional[str] = None, mensaje: str = "", bien: Optional[bool] = None):
        self.clave = clave
        self.texto = texto
        self.tipo = tipo
        self.icono = icono
        self.revela = revela            # PREGUNTA: el jugador ve la respuesta
        self.respuesta = respuesta      # hijo de una PREGUNTA: a qué respuesta corresponde (True = sí)
        self.puntos = puntos
        self.efectos = dict(efectos or {})
        self.propaga = propaga          # HOJA: None | "jugador" (la compartió él) | "autor" (la compartieron otros)
        self.mensaje = mensaje
        self.bien = bien                # HOJA: ¿fue una buena decisión?
        self.padre: Optional[NodoDecision] = None
        self.hijos: list[NodoDecision] = []

    @property
    def es_hoja(self) -> bool:
        return not self.hijos

    @property
    def profundidad(self) -> int:
        d, n = 0, self
        while n.padre is not None:
            d, n = d + 1, n.padre
        return d

    def __repr__(self) -> str:
        return f"NodoDecision({self.clave})"


class ArbolDecision:
    def __init__(self, raiz: NodoDecision):
        self.raiz = raiz
        self._indice: dict[str, NodoDecision] = {}
        for n in self._preorden_desde(raiz):
            self._indice[n.clave] = n

    def __len__(self) -> int:
        return len(self._indice)

    def __contains__(self, clave: str) -> bool:
        return clave in self._indice

    def buscar(self, clave: str) -> Optional[NodoDecision]:
        return self._indice.get(clave)

    # -------------------------------------------------------------- inserción y eliminación
    def insertar(self, clave_padre: str, nodo: NodoDecision) -> NodoDecision:
        padre = self._indice.get(clave_padre)
        if padre is None:
            raise KeyError(f"No existe el nodo {clave_padre!r}")
        if nodo.clave in self._indice:
            raise ValueError(f"Ya existe un nodo {nodo.clave!r}")
        if padre.tipo == HOJA:
            raise ValueError("Una hoja no puede tener hijos: primero conviértela en acción o pregunta")
        nodo.padre = padre
        padre.hijos.append(nodo)
        for n in self._preorden_desde(nodo):
            self._indice[n.clave] = n
        return nodo

    def eliminar(self, clave: str) -> list[NodoDecision]:
        """Quita un nodo con todo su subárbol (una opción deja de existir con todo lo que venía después)."""
        nodo = self._indice.get(clave)
        if nodo is None:
            raise KeyError(f"No existe el nodo {clave!r}")
        if nodo is self.raiz:
            raise ValueError("No se puede quitar la raíz")
        quitados = list(self._postorden_desde(nodo))
        for n in quitados:
            del self._indice[n.clave]
        nodo.padre.hijos.remove(nodo)
        nodo.padre = None
        return quitados

    # -------------------------------------------------------------- recorridos
    def _preorden_desde(self, nodo: NodoDecision) -> Iterator[NodoDecision]:
        pila = [nodo]
        while pila:
            n = pila.pop()
            yield n
            pila.extend(reversed(n.hijos))

    def _postorden_desde(self, nodo: NodoDecision) -> Iterator[NodoDecision]:
        for h in nodo.hijos:
            yield from self._postorden_desde(h)
        yield nodo

    def preorden(self) -> list[NodoDecision]:
        return list(self._preorden_desde(self.raiz))

    def por_niveles(self) -> list[list[NodoDecision]]:
        niveles: list[list[NodoDecision]] = []
        cola = deque([(self.raiz, 0)])
        while cola:
            n, d = cola.popleft()
            if d == len(niveles):
                niveles.append([])
            niveles[d].append(n)
            cola.extend((h, d + 1) for h in n.hijos)
        return niveles

    def hojas(self) -> list[NodoDecision]:
        return [n for n in self.preorden() if n.es_hoja]

    def altura(self) -> int:
        return len(self.por_niveles()) - 1

    def camino(self, clave: str) -> list[NodoDecision]:
        """De la raíz hasta el nodo (para mostrarle al jugador el camino que tomó)."""
        n = self._indice.get(clave)
        if n is None:
            raise KeyError(f"No existe el nodo {clave!r}")
        res = []
        while n is not None:
            res.append(n)
            n = n.padre
        return res[::-1]

    # -------------------------------------------------------------- recorrer jugando
    def opciones(self, nodo: NodoDecision) -> list[NodoDecision]:
        """Los botones que ve el jugador en un nodo de acción."""
        return list(nodo.hijos) if nodo.tipo == ACCION else []

    def elegir(self, nodo: NodoDecision, clave: str) -> NodoDecision:
        if nodo.tipo != ACCION:
            raise ValueError("Solo se escoge en un nodo de acción")
        for h in nodo.hijos:
            if h.clave == clave:
                return h
        raise KeyError(f"{clave!r} no es una opción de {nodo.clave!r}")

    @staticmethod
    def responder(nodo: NodoDecision, es_verdad: bool) -> NodoDecision:
        """Una pregunta la contesta el juego: baja por el hijo que corresponde a la respuesta."""
        if nodo.tipo != PREGUNTA:
            raise ValueError("Solo se responde un nodo de pregunta")
        for h in nodo.hijos:
            if h.respuesta == es_verdad:
                return h
        raise KeyError("La pregunta no tiene hijo para esa respuesta")

    def avanzar(self, nodo: NodoDecision, es_verdad: bool) -> NodoDecision:
        """Baja sola hasta el próximo punto donde el jugador ve algo: una pregunta que se revela, un nodo
        con varias opciones o una hoja. Una acción con una sola pregunta debajo no tiene nada que escoger,
        y las preguntas silenciosas las contesta el juego."""
        while True:
            if nodo.tipo == ACCION and len(nodo.hijos) == 1 and nodo.hijos[0].tipo == PREGUNTA:
                nodo = nodo.hijos[0]
            elif nodo.tipo == PREGUNTA and not nodo.revela:
                nodo = self.responder(nodo, es_verdad)
            else:
                return nodo

def _hoja(clave, texto, puntos, efectos, mensaje, bien, propaga=None, icono=""):
    return NodoDecision(clave, texto, HOJA, icono=icono, puntos=puntos, efectos=efectos, propaga=propaga,
                        mensaje=mensaje, bien=bien)


def _pregunta(clave, si: NodoDecision, no: NodoDecision, revela=False):
    p = NodoDecision(clave, "¿Es verdadera?", PREGUNTA, icono="circle-help", revela=revela)
    for h, r in ((si, True), (no, False)):
        h.respuesta = r
        h.padre = p
        p.hijos.append(h)
    return p


def _accion(clave, texto, icono, *hijos):
    n = NodoDecision(clave, texto, ACCION, icono=icono)
    for h in hijos:
        h.padre = n
        n.hijos.append(h)
    return n


def arbol_viral() -> ArbolDecision:
    """El árbol completo de la alerta viral, con la consecuencia de cada camino.

    Efectos sobre los indicadores de Ciudad Nova: verificada, confianza, convivencia, bienestar,
    desinformacion y conflictos (los dos últimos es mejor que bajen).
    """
    # Verificar y luego decidir con la respuesta en la mano.
    tras_si = _accion("v_si", "Es verdadera", "badge-check",
                      _hoja("v_si_compartir", "Compartir", 60,
                            dict(verificada=6, confianza=4, bienestar=2),
                            "¡Perfecto! Verificaste y compartiste una noticia real.", True, "jugador", "share-2"),
                      _hoja("v_si_reportar", "Reportar", 0, dict(confianza=-4, verificada=-3),
                            "Era verdad y la reportaste: así se castiga a quien dice la verdad.", False, None, "flag"))
    tras_no = _accion("v_no", "Es falsa", "circle-x",
                      _hoja("v_no_reportar", "Reportar", 70,
                            dict(desinformacion=-6, verificada=4, convivencia=2),
                            "¡Excelente! Verificaste, era falsa y la frenaste.", True, None, "flag"),
                      _hoja("v_no_compartir", "Compartir", -20,
                            dict(desinformacion=8, confianza=-5, conflictos=3),
                            "¡Sabías que era falsa y la compartiste! Ahora la cree mucha gente.", False, "jugador",
                            "share-2"))
    verificar = _accion("verificar", "Verificar", "search", _pregunta("v_es", tras_si, tras_no, revela=True))
    compartir = _accion("compartir", "Compartir", "share-2", _pregunta(
        "c_es",
        _hoja("c_si", "Era verdad", 30, dict(verificada=3, confianza=1),
              "Era verdad… ¡pero tuviste suerte! Verifica antes de compartir.", True, "jugador", "share-2"),
        _hoja("c_no", "Era falsa", 0, dict(desinformacion=10, confianza=-6, conflictos=4),
              "¡Era falsa! Al compartirla le llegó a todos tus seguidores.", False, "jugador", "share-2")))
    reportar = _accion("reportar", "Reportar", "flag", _pregunta(
        "r_es",
        _hoja("r_si", "Era verdad", 0, dict(confianza=-5, verificada=-4),
              "¡Era verdad! Reportar sin verificar le quita la voz a quien dice la verdad.", False, None, "flag"),
        _hoja("r_no", "Era falsa", 45, dict(desinformacion=-4, convivencia=1),
              "¡Bien! Era falsa y la reportaste. La próxima vez verifica primero: vale más.", True, None, "flag")))
    ignorar = _accion("ignorar", "Ignorar", "eye-off", _pregunta(
        "i_es",
        _hoja("i_si", "Era verdad", 5, dict(),
              "Era una noticia real: compartirla habría ayudado a tu barrio.", None, None, "eye-off"),
        _hoja("i_no", "Era falsa", 5, dict(desinformacion=3),
              "Tú no la compartiste, pero otros sí. Reportarla la habría frenado.", None, "autor", "eye-off")))
    raiz = NodoDecision("raiz", "Publicación viral", ACCION, icono="siren")
    for h in (verificar, compartir, reportar, ignorar):
        h.padre = raiz
        raiz.hijos.append(h)
    return ArbolDecision(raiz)

