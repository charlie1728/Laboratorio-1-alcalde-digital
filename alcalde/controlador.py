"""La interfaz no toca la Partida directamente: le pide las jugadas a un controlador.

* ControladorLocal: todos juegan en el mismo computador y la jugada se aplica al instante.
* ControladorRed: la jugada se envía al servidor y el estado vuelve en el siguiente mensaje.
"""
from __future__ import annotations

import time
from typing import Optional

from .modelo.partida import Mensaje
from .modelo.serializacion import partida_desde_dict


class ControladorLocal:
    en_red = False

    def __init__(self, partida):
        self.partida = partida
        self.indice: Optional[int] = None
        self.desconectados: list[int] = []

    def es_mi_turno(self) -> bool:
        return not self.partida.terminada

    def decido_viral(self) -> bool:
        return self.partida.evento_viral is not None

    def accion(self, caso_id: int, nodo_id: int, clave: str) -> list[Mensaje]:
        caso = self.partida.caso_por_id(caso_id)
        nodo = caso.arbol.buscar(nodo_id) if caso else None
        if nodo is None:
            return []
        return self.partida.ejecutar(clave, caso, nodo)

    def mover(self, zona: str) -> list[Mensaje]:
        return self.partida.mover(zona)

    def conversar(self) -> list[Mensaje]:
        return self.partida.conversar()

    def siguiente(self) -> list[Mensaje]:
        return self.partida.siguiente_publicacion()

    def terminar_turno(self) -> None:
        self.partida.terminar_turno()

    def resolver_viral(self, clave: Optional[str]) -> list[Mensaje]:
        return self.partida.resolver_viral(clave)

    def reaccion(self, emoji: str) -> None:
        pass

    def actualizar(self) -> tuple[bool, list]:
        return False, []

    def viral_restante(self) -> Optional[float]:
        return None

    def cerrar(self) -> None:
        pass


class ControladorRed:
    en_red = True

    def __init__(self, cliente, estado_inicial: dict, servidor=None):
        self.cliente = cliente
        self.servidor = servidor
        self.partida = partida_desde_dict(estado_inicial["partida"])
        self.indice: Optional[int] = estado_inicial.get("tu")
        self.desconectados: list[int] = estado_inicial.get("desconectados", [])
        self.esperando = False
        self.conectado = True
        self._viral_fin = None
        self._fijar_viral(estado_inicial.get("viral"))

    def _fijar_viral(self, restante) -> None:
        self._viral_fin = time.monotonic() + restante if restante is not None else None

    def es_mi_turno(self) -> bool:
        p = self.partida
        return (not p.terminada and not self.esperando and p.evento_viral is None
                and p.turno_idx == self.indice)

    def decido_viral(self) -> bool:
        ev = self.partida.evento_viral
        return ev is not None and self.partida.jugadores.index(ev.jugador) == self.indice and not self.esperando

    def _enviar(self, obj) -> list[Mensaje]:
        if self.cliente.enviar(obj):
            self.esperando = True
        return []

    def accion(self, caso_id, nodo_id, clave):
        return self._enviar(dict(t="accion", caso=caso_id, nodo=nodo_id, clave=clave))

    def mover(self, zona):
        return self._enviar(dict(t="mover", zona=zona))

    def conversar(self):
        return self._enviar(dict(t="conversar"))

    def siguiente(self):
        return self._enviar(dict(t="siguiente"))

    def terminar_turno(self):
        self._enviar(dict(t="fin_turno"))

    def resolver_viral(self, clave):
        return self._enviar(dict(t="viral", clave=clave))

    def reaccion(self, emoji: str) -> None:
        self.cliente.enviar(dict(t="reaccion", emoji=emoji))

    def actualizar(self) -> tuple[bool, list]:
        """Procesa lo que llegó del servidor. Devuelve (hubo estado nuevo, otros mensajes)."""
        nuevo, otros = False, []
        for m in self.cliente.recibir():
            t = m.get("t")
            if t == "estado":
                self.partida = partida_desde_dict(m["partida"])
                self.indice = m.get("tu", self.indice)
                self.desconectados = m.get("desconectados", [])
                self._fijar_viral(m.get("viral"))
                self.esperando = False
                nuevo = True
            elif t == "_cerrado":
                self.conectado = False
                otros.append(dict(t="aviso", tipo="malo", texto="Se perdió la conexión con el servidor."))
            elif t == "aviso":
                self.esperando = False
                otros.append(m)
            else:
                otros.append(m)
        return nuevo, otros

    def viral_restante(self) -> Optional[float]:
        if self._viral_fin is None:
            return None
        return max(0.0, self._viral_fin - time.monotonic())

    def cerrar(self) -> None:
        self.cliente.cerrar()
        if self.servidor:
            self.servidor.detener()
