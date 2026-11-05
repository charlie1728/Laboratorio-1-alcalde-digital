"""Protocolo del modo en línea: mensajes JSON, uno por línea, sobre TCP.

Cliente -> servidor: hola, elegir, empezar (solo anfitrión), estado, resultado, aviso, listo.
Servidor -> clientes: bienvenida, sala, error, ronda, marcador, aviso, fin_ronda, fin.
"""
import json
import socket

PUERTO = 5070


def codificar(msg):
    return (json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


class Lector:
    """Junta los pedazos que llegan por el socket y devuelve mensajes completos."""

    def __init__(self):
        self.buffer = b""

    def agregar(self, datos):
        self.buffer += datos
        mensajes = []
        while b"\n" in self.buffer:
            linea, self.buffer = self.buffer.split(b"\n", 1)
            if linea.strip():
                try:
                    mensajes.append(json.loads(linea.decode("utf-8")))
                except ValueError:
                    pass
        return mensajes


def ips_locales():
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
