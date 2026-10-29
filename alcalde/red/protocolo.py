"""Protocolo cliente-servidor: un objeto JSON por línea (UTF-8) sobre TCP.

Cliente -> servidor
  {"t": "hola", "nombre", "rol", "look", "mas_tiempo"}   unirse al lobby
  {"t": "perfil", "nombre", "rol", "look", "mas_tiempo"} cambiar el personaje en el lobby
  {"t": "iniciar", "rondas"}                             solo el anfitrión
  {"t": "accion", "caso", "nodo", "clave"}               verificar, compartir, reportar...
  {"t": "mover", "zona"} / {"t": "conversar"} / {"t": "fin_turno"}
  {"t": "viral", "clave"}                                respuesta a la publicación viral
  {"t": "reaccion", "emoji"}                             reacción rápida visible para todos

Servidor -> cliente
  {"t": "bienvenida", "id"}            identificador de la conexión
  {"t": "lobby", "jugadores", "anfitrion"}
  {"t": "estado", "tu", "viral", "partida"}   estado completo tras cada jugada
  {"t": "aviso", "texto", "tipo"}      mensajes del servidor (errores, desconexiones)
  {"t": "reaccion", "de", "emoji"}
"""
from __future__ import annotations

import json
import socket

PUERTO = 5050
MAX_LINEA = 4 * 1024 * 1024


def codificar(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def enviar(sock: socket.socket, obj) -> None:
    sock.sendall(obj if isinstance(obj, bytes) else codificar(obj))


class Lector:
    """Acumula bytes del socket y entrega mensajes completos (una línea = un mensaje)."""

    def __init__(self):
        self.buffer = b""

    def alimentar(self, datos: bytes) -> list:
        self.buffer += datos
        if len(self.buffer) > MAX_LINEA:
            raise ValueError("Mensaje demasiado grande")
        mensajes = []
        while b"\n" in self.buffer:
            linea, self.buffer = self.buffer.split(b"\n", 1)
            if linea.strip():
                mensajes.append(json.loads(linea.decode("utf-8")))
        return mensajes


def ips_locales() -> list[str]:
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    ips.discard("127.0.0.1")
    return sorted(ips) or ["127.0.0.1"]
