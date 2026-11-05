"""Pruebas de la simulación de Cazabulos: grafos e árboles funcionando dentro del juego."""
import os
import time
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((1, 1))

from cazabulos.ciudad import linea_libre, ruta  # noqa: E402
from cazabulos.mapa import H, NODOS, W  # noqa: E402
from cazabulos.mundo import Estrella, Mundo, mapa_compartido  # noqa: E402
from cazabulos.partida import Partida, calcular_eleccion  # noqa: E402
from cazabulos.trafico import Trafico  # noqa: E402


def nuevo(clave="caro", semilla=3):
    m = Mundo(semilla, clave, duracion=90, pistas=False)
    m.antenas.clear()
    m.t_antena = 1e9
    m.guion.clear()
    m.t_kiosco = 1e9
    for v in m.vecinos.values():
        v.espera = 1e9          # quietos para que la prueba sea exacta
    return m


class TestJusticia(unittest.TestCase):
    def test_misma_semilla_mismo_barrio(self):
        a, b = Mundo(77, "ana"), Mundo(77, "dani")
        self.assertEqual([g[:2] for g in a.guion], [g[:2] for g in b.guion])
        self.assertEqual(a.kiosco, b.kiosco)
        self.assertEqual(a.orden_antenas, b.orden_antenas)
        self.assertNotEqual([g[:2] for g in a.guion], [g[:2] for g in Mundo(78, "ana").guion])


class TestContagio(unittest.TestCase):
    def test_bulo_sube_a_la_cabeza_y_se_reenvia_por_el_grafo(self):
        m = nuevo()
        rosa = m.vecinos["Rosa"]
        b = m.nuevo_bulo(rosa.x + 3, rosa.y - 19)
        b.objetivo = "Rosa"
        m.actualizar(1 / 60, {})
        self.assertEqual(rosa.bulo, b.id)
        rosa.t_prop = 0
        m.actualizar(1 / 60, {})
        self.assertEqual(len(m.pulsos), 1)
        destino = m.pulsos[0].hasta
        self.assertIn(destino, m.social.vecinos("Rosa"))
        for _ in range(60 * 4):
            m.actualizar(1 / 60, {})
        hijo = m.vecinos[destino].bulo
        self.assertIsNotNone(hijo)
        self.assertEqual(m.arbol.raiz_de(hijo), b.id)

    def test_protegido_no_recibe_el_bulo(self):
        m = nuevo()
        luis = m.vecinos["Luis"]
        luis.escudo = 30
        b = m.nuevo_bulo(luis.x, luis.y - 20)
        b.objetivo = "Luis"
        m._bulos(1 / 60)
        self.assertIsNone(luis.bulo)


class TestCadena(unittest.TestCase):
    def test_atrapar_la_raiz_cura_a_toda_la_cadena(self):
        m = nuevo()
        r = m._infectar(m.vecinos["Rosa"], None)
        h = m._infectar(m.vecinos["Luis"], r)
        m._infectar(m.vecinos["Carlos"], h)
        m._infectar(m.vecinos["Pedro"], r)
        self.assertEqual(m.arbol.tamano(r), 4)
        n = m._atrapar(r)
        self.assertEqual(n, 4)
        self.assertEqual(len(m.infectados()), 0)
        self.assertEqual(m.jugador.stats["cadena"], 4)
        self.assertGreater(m.jugador.puntos, 40)

    def test_atrapar_una_rama_deja_lo_demas(self):
        m = nuevo()
        r = m._infectar(m.vecinos["Rosa"], None)
        h = m._infectar(m.vecinos["Luis"], r)
        m._infectar(m.vecinos["Carlos"], h)
        m._atrapar(h)
        self.assertEqual(m.vecinos["Rosa"].bulo, r)
        self.assertIsNone(m.vecinos["Carlos"].bulo)


class TestNoticias(unittest.TestCase):
    def _con_estrella(self, m, falsa):
        j = m.jugador
        j.estrella = Estrella(999, j.x, j.y, falsa)
        v = m.vecinos["Rosa"]
        j.x, j.y = v.x + 6, v.y
        return v

    def test_compartir_sin_mirar_un_bulo_disfrazado(self):
        m = nuevo()
        v = self._con_estrella(m, True)
        m.actualizar(1 / 60, {"accion": True})
        self.assertIsNotNone(v.bulo)
        self.assertEqual(m.decisiones.buscar("bulo").veces, 1)
        self.assertEqual(m.jugador.stats["compartidas_falsas"], 1)

    def test_mirar_antes_descubre_el_bulo(self):
        m = nuevo()
        self._con_estrella(m, True)
        for _ in range(int(60 * 1.4)):
            m.actualizar(1 / 60, {})
        self.assertIsNone(m.jugador.estrella)
        self.assertEqual(m.decisiones.buscar("reporte").veces, 1)

    def test_verdad_protege_y_beto_llega_a_los_amigos(self):
        m = nuevo("beto")
        v = self._con_estrella(m, False)
        m.jugador.estrella.revelada = True
        m.actualizar(1 / 60, {"accion": True})
        self.assertGreater(v.escudo, 0)
        for amigo in m.social.vecinos("Rosa"):
            self.assertGreater(m.vecinos[amigo].escudo, 0)
        self.assertEqual(m.decisiones.buscar("verdad").veces, 1)


class TestRelaciones(unittest.TestCase):
    def test_pelea_sin_calmar_rompe_el_hilo(self):
        m = nuevo()
        m._empezar_pelea(0.0)
        p = m.peleas[0]
        a, b = p["a"], p["b"]
        p["activa"], p["t"] = True, 0.01
        m._peleas(0.1)
        self.assertFalse(m.social.tiene_arista(a, b))
        self.assertIn((a, b), m.rotos)

    def test_calmar_fortalece_el_hilo(self):
        m = nuevo()
        m._empezar_pelea(0.0)
        p = m.peleas[0]
        antes = m.social.peso(p["a"], p["b"])
        m._calmar(p)
        self.assertEqual(m.social.peso(p["a"], p["b"]), min(3, antes + 1))
        self.assertEqual(m.jugador.stats["peleas"], 1)

    def test_viral_se_riega_por_bfs_dos_niveles(self):
        m = nuevo()
        m._evento("viral", 0.5)
        self.assertIsNotNone(m.viral)
        origen = m.viral.objetivo
        m.vecinos[list(m.social.vecinos(origen))[0]].escudo = 99
        m.viral.t = 0
        m._viral(1 / 60)
        esperados = {v for v, nivel, _ in m.social.bfs(origen, filtro=lambda u: m.vecinos[u].escudo <= 0, max_nivel=2)}
        self.assertEqual({v.nombre for v in m.infectados()}, esperados)


class TestMapa(unittest.TestCase):
    def test_no_se_atraviesan_edificios(self):
        m = nuevo()
        j = m.jugador
        j.x, j.y = 26.5 * 16, 9.5 * 16      # frente a la alcaldía
        for _ in range(120):
            m.actualizar(1 / 60, {"arriba": True})
        self.assertGreaterEqual(j.y, 8 * 16)

    def test_grafo_de_la_ciudad_conectado_y_caminable(self):
        mapa, g = mapa_compartido()
        self.assertEqual(g.descartadas, [])
        self.assertEqual(len(g.componentes()), 1)
        for a, b, _ in g.aristas():
            self.assertTrue(linea_libre(mapa, g.datos[a]["pos"], g.datos[b]["pos"]))
        puntos = ruta(g, mapa, g.datos["Colegio"]["pos"], g.datos["Terminal"]["pos"])
        self.assertGreater(len(puntos), 2)

    def test_carros_en_su_carril_y_sin_chocar(self):
        mapa, _ = mapa_compartido()
        t = Trafico(5)
        for _ in range(60 * 40):
            t.actualizar(1 / 60)
            rs = [c.rect() for c in t.carros]
            for r in rs:
                for x, y in ((r.left, r.top), (r.right - 1, r.bottom - 1)):
                    if 0 <= x < W * 16 and 0 <= y < H * 16:
                        self.assertTrue(mapa.es_calzada(x, y))
            for i in range(len(rs)):
                for k in range(i + 1, len(rs)):
                    self.assertFalse(rs[i].colliderect(rs[k]))


class TestPartida(unittest.TestCase):
    def test_turnos_rotan_y_terminan(self):
        js = [{"clave": c, "piel": None, "pelo": None, "nombre": c} for c in ("ana", "beto", "caro")]
        pa = Partida(js, rondas=2, semilla=1)
        self.assertEqual(pa.orden(1), [0, 1, 2])
        self.assertEqual(pa.orden(2), [1, 2, 0])
        self.assertEqual([pa.avanzar() for _ in range(3)], ["turno", "turno", "ronda"])
        pa.siguiente_ronda()
        self.assertEqual(pa.actual, 1)
        self.assertEqual([pa.avanzar() for _ in range(3)], ["turno", "turno", "fin"])

    def test_la_eleccion_depende_del_barrio(self):
        js = [{"clave": "caro", "piel": None, "pelo": None, "nombre": "CARO"}]

        def res(desinfo, info):
            return {(1, 0): {"indicadores": {"informacion": info, "confianza": 60, "convivencia": 60, "bienestar": 60,
                                             "desinformacion": desinfo, "conflictos": 10},
                             "rumores": {}, "defendidos": {}, "salvados": 10, "vecinos": 18}}
        _, bueno = calcular_eleccion(res(5, 90), js)
        _, malo = calcular_eleccion(res(95, 10), js)
        self.assertLess(bueno["votos"]["Emilio"], malo["votos"]["Emilio"])
        orden, _ = calcular_eleccion(res(100, 0), js)
        self.assertEqual(orden[0], "Emilio")


class TestRed(unittest.TestCase):
    def test_sala_ronda_y_resultados(self):
        from cazabulos.red.cliente import Cliente
        from cazabulos.red.servidor import Servidor
        srv = Servidor(5099)
        try:
            a = Cliente("127.0.0.1", 5099)
            b = Cliente("127.0.0.1", 5099)
            a.enviar({"t": "hola", "nombre": "ANA", "clave": "ana"})
            time.sleep(0.2)
            b.enviar({"t": "hola", "nombre": "BETO", "clave": "ana"})   # ocupado: le dan otro
            time.sleep(0.3)
            a.enviar({"t": "empezar", "rondas": 1, "duracion": 60})
            time.sleep(0.4)
            msgs_a, msgs_b = a.recibir(), b.recibir()
            ronda = [m for m in msgs_b if m["t"] == "ronda"][0]
            claves = {j["clave"] for j in ronda["jugadores"]}
            self.assertEqual(len(claves), 2)
            a.enviar_estado({"x": 10, "y": 20, "dir": "abajo", "paso": 0, "puntos": 50, "salvados": 9})
            time.sleep(0.5)
            self.assertTrue(any(f["nombre"] == "ANA" for f in b.fantasmas()))
            for c, pts in ((a, 100), (b, 80)):
                c.terminar({"total": pts, "salvados": 5, "vecinos": 18, "indicadores": {}, "rumores": {}, "defendidos": {}})
            time.sleep(0.5)
            tipos = [m["t"] for m in b.recibir()]
            self.assertIn("fin_ronda", tipos)
            self.assertIn("fin", tipos)
        finally:
            for c in (a, b):
                c.cerrar()
            srv.cerrar()


if __name__ == "__main__":
    unittest.main()
