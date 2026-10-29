from __future__ import annotations

import queue
import socket
import threading

from .protocolo import PUERTO, Lector, codificar


class Cliente:
    """Conexión con el servidor. Un hilo lee los mensajes y los deja en una cola."""

    def __init__(self, host: str, puerto: int = PUERTO, timeout: float = 4.0):
        self.cola: queue.Queue = queue.Queue()
        self.conectado = False
        self.error = ""
        self.id = None
        self.sock = socket.create_connection((host, puerto), timeout=timeout)
        self.sock.settimeout(None)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.conectado = True
        self._bloqueo = threading.Lock()
        threading.Thread(target=self._leer, daemon=True, name="cliente-lector").start()

    def _leer(self) -> None:
        lector = Lector()
        try:
            while self.conectado:
                datos = self.sock.recv(262144)
                if not datos:
                    break
                for m in lector.alimentar(datos):
                    if m.get("t") == "bienvenida":
                        self.id = m.get("id")
                    self.cola.put(m)
        except (OSError, ValueError) as ex:
            self.error = str(ex)
        self.conectado = False
        self.cola.put(dict(t="_cerrado"))

    def enviar(self, obj) -> bool:
        if not self.conectado:
            return False
        try:
            with self._bloqueo:
                self.sock.sendall(codificar(obj))
            return True
        except OSError as ex:
            self.error = str(ex)
            self.conectado = False
            return False

    def recibir(self) -> list:
        out = []
        while True:
            try:
                out.append(self.cola.get_nowait())
            except queue.Empty:
                return out

    def cerrar(self) -> None:
        self.conectado = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass
