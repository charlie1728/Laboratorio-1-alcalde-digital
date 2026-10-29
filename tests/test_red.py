"""Prueba de la arquitectura cliente-servidor con sockets reales (sin interfaz)."""
import random
import socket
import time
import unittest

from alcalde.controlador import ControladorRed
from alcalde.red.cliente import Cliente
from alcalde.red.servidor import Servidor


def _puerto_libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _esperar(cond, t=5.0):
    fin = time.time() + t
    while time.time() < fin:
        if cond():
            return True
        time.sleep(0.02)
    return False


class TestClienteServidor(unittest.TestCase):
    def setUp(self):
        self.puerto = _puerto_libre()
        self.srv = Servidor("127.0.0.1", self.puerto, semilla=9, registro=lambda *_: None).iniciar()
        self.clientes = []

    def tearDown(self):
        for c in self.clientes:
            c.cerrar()
        self.srv.detener()

    def _lobby(self, roles):
        for i, rol in enumerate(roles):
            c = Cliente("127.0.0.1", self.puerto)
            c.enviar(dict(t="hola", nombre=f"J{i}", rol=rol, look=dict(piel=i, pelo="afro")))
            self.clientes.append(c)
        lobbies = {}

        def listo():
            for i, c in enumerate(self.clientes):
                for m in c.recibir():
                    if m["t"] == "lobby":
                        lobbies[i] = m
            return len(lobbies) == len(roles) and all(len(m["jugadores"]) == len(roles) for m in lobbies.values())
        self.assertTrue(_esperar(listo))
        return lobbies

    def _estado_inicial(self):
        estados = {}

        def listo():
            for i, c in enumerate(self.clientes):
                for m in c.recibir():
                    if m["t"] == "estado":
                        estados[i] = m
            return len(estados) == len(self.clientes)
        self.assertTrue(_esperar(listo))
        return [ControladorRed(c, estados[i]) for i, c in enumerate(self.clientes)]

    def test_lobby_y_solo_anfitrion_inicia(self):
        lobbies = self._lobby(["ciudadano", "periodista", "influencer"])
        self.assertEqual(lobbies[0]["anfitrion"], self.clientes[0].id)
        self.clientes[1].enviar(dict(t="iniciar"))
        self.assertTrue(_esperar(lambda: any(m["t"] == "aviso" for m in self.clientes[1].recibir())))
        self.assertEqual(self.srv.estado, "lobby")

    def test_partida_sincronizada(self):
        self._lobby(["ciudadano", "periodista", "influencer"])
        self.clientes[0].enviar(dict(t="iniciar", rondas=4))
        ctrls = self._estado_inicial()
        self.assertEqual(sorted(c.indice for c in ctrls), [0, 1, 2])
        rng = random.Random(1)
        jugadas = 0
        while not ctrls[0].partida.terminada and jugadas < 300:
            jugadas += 1
            for c in ctrls:
                c.actualizar()
            p = ctrls[0].partida
            if p.evento_viral:
                decide = next(c for c in ctrls if c.indice == p.jugadores.index(p.evento_viral.jugador))
                decide.resolver_viral(rng.choice([None, "verificar"]))
                actor = decide
            else:
                actor = next(c for c in ctrls if c.indice == p.turno_idx)
                otro = next(c for c in ctrls if c is not actor)
                otro.terminar_turno()          # fuera de turno: el servidor lo rechaza con un aviso
                q = actor.partida
                casos = q.casos_abiertos()
                if casos and q.jugador_actual.atencion > 0 and rng.random() < 0.7:
                    caso = rng.choice(casos)
                    nodo = rng.choice(list(caso.arbol.preorden()))
                    ok = [a["clave"] for a in q.acciones_para(nodo) if a["ok"]]
                    if ok:
                        actor.accion(caso.id, nodo.id, rng.choice(ok))
                    else:
                        actor.terminar_turno()
                else:
                    actor.terminar_turno()
            # cada jugada recibe respuesta: el estado nuevo (o un aviso) desbloquea al cliente
            self.assertTrue(_esperar(lambda: actor.actualizar()[0] or not actor.esperando, 5))
            objetivo = self.srv.partida.total_mensajes()
            self.assertTrue(_esperar(lambda: all(c.actualizar() is not None and
                                                 c.partida.total_mensajes() == objetivo for c in ctrls), 5))
        self.assertTrue(_esperar(lambda: [c.actualizar() for c in ctrls] and
                                 all(c.partida.terminada for c in ctrls), 5))
        p0 = ctrls[0].partida
        for c in ctrls[1:]:
            self.assertEqual(c.partida.ciudad.v, p0.ciudad.v)
            self.assertEqual(c.partida.eleccion["ganador"], p0.eleccion["ganador"])
            self.assertEqual(c.partida.red.num_aristas(), p0.red.num_aristas())
        self.assertEqual(p0.ciudad.v, self.srv.partida.ciudad.v)

    def test_desconexion_en_lobby(self):
        self._lobby(["ciudadano", "periodista"])
        self.clientes[1].cerrar()
        self.assertTrue(_esperar(lambda: len([c for c in self.srv.clientes if c.vivo]) == 1))


if __name__ == "__main__":
    unittest.main()
