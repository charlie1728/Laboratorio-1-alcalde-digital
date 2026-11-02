"""Duelo en red: un servidor TCP que reparte la partida y unos clientes que juegan.

Arquitectura cliente-servidor (un objeto JSON por línea, ver protocolo.py):
  * El SERVIDOR mantiene la sala: quién está conectado, con qué personaje, qué barrio se juega y con
    qué semilla (así todos ven exactamente las mismas publicaciones), el marcador y los ataques.
  * Cada CLIENTE juega su nivel en su computador y le cuenta al servidor sus puntos. Cuando hace un
    combo de 5, le pide al servidor que le mande un rumor extra a los demás.
El anfitrión corre el servidor en un hilo y además se conecta a él como un cliente más.

Cliente -> servidor
  {"t": "hola", "nombre", "rol", "look", "color"}
  {"t": "empezar", "zona"}                      solo el anfitrión
  {"t": "puntos", "puntos", "salud", "estado"}  cada medio segundo durante el nivel
  {"t": "ataque"}                               combo de 5: un rumor para cada rival
Servidor -> cliente
  {"t": "bienvenida", "id"}
  {"t": "sala", "jugadores": [...], "anfitrion": id}
  {"t": "empezar", "zona", "semilla"}
  {"t": "marcador", "jugadores": [...]}
  {"t": "ataque", "de"}
  {"t": "aviso", "texto"}
"""
from __future__ import annotations

import queue
import random
import socket
import threading

from .protocolo import Lector, codificar

PUERTO_DUELO = 5051


class Servidor:
    def __init__(self, puerto: int = PUERTO_DUELO):
        self.puerto = puerto
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", puerto))
        self.sock.listen(8)
        self.jugadores = {}      # id -> dict(nombre, rol, look, color, puntos, salud, estado)
        self.conexiones = {}     # id -> socket
        self.anfitrion = None
        self.jugando = False
        self._sig = 1
        self._candado = threading.Lock()
        self.vivo = True
        threading.Thread(target=self._aceptar, daemon=True).start()

    def _aceptar(self):
        while self.vivo:
            try:
                c, _ = self.sock.accept()
            except OSError:
                break
            with self._candado:
                cid = self._sig
                self._sig += 1
                self.conexiones[cid] = c
                if self.anfitrion is None:
                    self.anfitrion = cid
            self._enviar(cid, {"t": "bienvenida", "id": cid})
            threading.Thread(target=self._atender, args=(cid, c), daemon=True).start()

    def _enviar(self, cid, msg):
        c = self.conexiones.get(cid)
        if c is None:
            return
        try:
            c.sendall(codificar(msg))
        except OSError:
            self._sacar(cid)

    def _todos(self, msg, excepto=None):
        for cid in list(self.conexiones):
            if cid != excepto:
                self._enviar(cid, msg)

    def _sala(self):
        lista = [dict(id=i, **j) for i, j in self.jugadores.items()]
        self._todos({"t": "sala", "jugadores": lista, "anfitrion": self.anfitrion, "jugando": self.jugando})

    def _sacar(self, cid):
        with self._candado:
            c = self.conexiones.pop(cid, None)
            j = self.jugadores.pop(cid, None)
            if cid == self.anfitrion:
                self.anfitrion = min(self.conexiones) if self.conexiones else None
        if c is not None:
            try:
                c.close()
            except OSError:
                pass
            if j:
                self._todos({"t": "aviso", "texto": f"{j['nombre']} se desconectó"})
            self._sala()

    def _atender(self, cid, c):
        lector = Lector()
        while self.vivo:
            try:
                datos = c.recv(65536)
                if not datos:
                    break
                mensajes = lector.alimentar(datos)
            except (OSError, ValueError):
                break
            for m in mensajes:
                self._procesar(cid, m)
        self._sacar(cid)

    def _procesar(self, cid, m):
        t = m.get("t")
        if t == "hola":
            with self._candado:
                self.jugadores[cid] = dict(nombre=str(m.get("nombre", "Jugador"))[:14], rol=m.get("rol", "periodista"),
                                           look=m.get("look") or {}, color=m.get("color") or [255, 194, 61],
                                           puntos=0, salud=100, estado="sala")
            self._sala()
        elif t == "empezar" and cid == self.anfitrion and not self.jugando:
            self.jugando = True
            for j in self.jugadores.values():
                j.update(puntos=0, salud=100, estado="jugando")
            self._todos({"t": "empezar", "zona": m.get("zona", "ESTADIO"), "semilla": random.randrange(1 << 30)})
            self._marcador()
        elif t == "puntos" and cid in self.jugadores:
            j = self.jugadores[cid]
            j.update(puntos=int(m.get("puntos", 0)), salud=int(m.get("salud", 0)), estado=m.get("estado", "jugando"))
            self._marcador()
            if all(x["estado"] != "jugando" for x in self.jugadores.values()):
                self.jugando = False
        elif t == "ataque" and cid in self.jugadores:
            self._todos({"t": "ataque", "de": self.jugadores[cid]["nombre"]}, excepto=cid)
        elif t == "volver" and cid == self.anfitrion:
            self.jugando = False
            for j in self.jugadores.values():
                j["estado"] = "sala"
            self._sala()

    def _marcador(self):
        lista = sorted((dict(id=i, **j) for i, j in self.jugadores.items()), key=lambda x: -x["puntos"])
        self._todos({"t": "marcador", "jugadores": lista})

    def cerrar(self):
        self.vivo = False
        try:
            self.sock.close()
        except OSError:
            pass
        for c in list(self.conexiones.values()):
            try:
                c.close()
            except OSError:
                pass


class Cliente:
    """Se conecta al servidor; un hilo lee los mensajes y los deja en una cola para la pantalla."""

    def __init__(self, ip: str, puerto: int = PUERTO_DUELO, timeout: float = 4.0):
        self.sock = socket.create_connection((ip, puerto), timeout=timeout)
        self.sock.settimeout(None)
        self.cola: queue.Queue = queue.Queue()
        self.id = None
        self.vivo = True
        threading.Thread(target=self._leer, daemon=True).start()

    def _leer(self):
        lector = Lector()
        while self.vivo:
            try:
                datos = self.sock.recv(65536)
                if not datos:
                    break
                for m in lector.alimentar(datos):
                    if m.get("t") == "bienvenida":
                        self.id = m.get("id")
                    self.cola.put(m)
            except (OSError, ValueError):
                break
        self.vivo = False
        self.cola.put({"t": "desconectado"})

    def enviar(self, msg):
        try:
            self.sock.sendall(codificar(msg))
        except OSError:
            self.vivo = False

    def mensajes(self):
        res = []
        while True:
            try:
                res.append(self.cola.get_nowait())
            except queue.Empty:
                return res

    def cerrar(self):
        self.vivo = False
        try:
            self.sock.close()
        except OSError:
            pass
