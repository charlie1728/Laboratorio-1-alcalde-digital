"""Protocolo cliente-servidor: un objeto JSON por línea (UTF-8) sobre TCP. Los mensajes del duelo están en sala.py."""
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
