"""Cliente del modo en línea: se conecta al servidor y guarda los mensajes en una cola."""
import queue
import socket
import threading

from .protocolo import PUERTO, Lector, codificar


class Cliente:
    def __init__(self, ip, puerto=PUERTO, servidor=None):
        self.sock = socket.create_connection((ip, puerto), timeout=4)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock.settimeout(1.0)
        self.cola = queue.Queue()
        self.vivo = True
        self.servidor = servidor        # si este computador creó la sala
        self.id = None
        self.anfitrion = False
        self._marcador = []
        self._avisos = []
        self.lock = threading.Lock()
        threading.Thread(target=self._leer, daemon=True).start()

    def _leer(self):
        lector = Lector()
        while self.vivo:
            try:
                datos = self.sock.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                break
            if not datos:
                break
            for msg in lector.agregar(datos):
                if msg.get("t") == "marcador":
                    with self.lock:
                        self._marcador = msg["jugadores"]
                elif msg.get("t") == "aviso":
                    with self.lock:
                        self._avisos.append(msg.get("texto", ""))
                    self.cola.put(msg)
                else:
                    if msg.get("t") == "bienvenida":
                        self.id = msg["id"]
                        self.anfitrion = msg.get("anfitrion", False)
                    self.cola.put(msg)
        self.vivo = False
        self.cola.put({"t": "desconectado"})

    def enviar(self, msg):
        try:
            self.sock.sendall(codificar(msg))
        except OSError:
            self.vivo = False

    def recibir(self):
        res = []
        while True:
            try:
                res.append(self.cola.get_nowait())
            except queue.Empty:
                return res

    # ------------------------------------------------------------- lo que usa la pantalla del juego
    def enviar_estado(self, estado):
        msg = {"t": "estado"}
        msg.update(estado)
        self.enviar(msg)

    def fantasmas(self):
        with self.lock:
            return [{"x": j["x"], "y": j["y"], "dir": j.get("dir") or "abajo", "paso": j.get("paso") or 0,
                     "clave": j["clave"], "nombre": j["nombre"]}
                    for j in self._marcador if j.get("id") != self.id and j.get("x") is not None and j.get("clave")]

    def marcador(self):
        with self.lock:
            return [(j["nombre"], j["clave"], j.get("puntos") or 0) for j in self._marcador if j.get("clave")]

    def avisos(self):
        with self.lock:
            a, self._avisos = self._avisos, []
        return a

    def terminar(self, res):
        ligero = {k: v for k, v in res.items() if k != "logros"}
        self.enviar({"t": "resultado", "res": ligero})

    def cerrar(self):
        self.vivo = False
        try:
            self.sock.close()
        except OSError:
            pass
        if self.servidor:
            self.servidor.cerrar()
            self.servidor = None
