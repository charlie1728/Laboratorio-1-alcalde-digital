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
from cazabulos.mapa import H, W  # noqa: E402
from cazabulos.mundo import (AVISO_REENVIO, MAX_VIRAL, Estrella, Mundo, Proyectil, mapa_compartido,  # noqa: E402
                             umbrales_reputacion)
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


def lanzar_a(m, punto, clave=None):
    """Pone un proyectil quieto justo encima de 'punto' y lo hace chocar."""
    pr = Proyectil(punto[0], punto[1], 0, 0, (255, 255, 255), clave or m.jugador.clave)
    m.proyectiles.append(pr)
    m._proyectiles(1 / 60)


class TestEstrellas(unittest.TestCase):
    def _tocar_estrella_junto_a(self, m, nombre):
        j = m.jugador
        v = m.vecinos[nombre]
        j.x, j.y = v.x + 6, v.y
        m.estrellas.append(Estrella(999, j.x, j.y - 6))
        m.actualizar(1 / 60, {})
        return v

    def test_estrella_comparte_la_verdad_por_el_grafo(self):
        m = nuevo("caro")
        amigos = list(m.social.vecinos("Rosa"))
        m._infectar(m.vecinos[amigos[0]], None)
        v = self._tocar_estrella_junto_a(m, "Rosa")
        self.assertGreater(v.escudo, 0)
        for amigo in amigos:
            self.assertGreater(m.vecinos[amigo].escudo, 0)
        self.assertIsNone(m.vecinos[amigos[0]].bulo)               # la verdad lo curó
        self.assertEqual(m.decisiones.buscar("compartida").veces, 1)
        self.assertEqual(m.jugador.stats["compartidas"], 1)
        nivel2 = [u for u, n, _ in m.social.bfs("Rosa", max_nivel=2) if n == 2]
        self.assertTrue(any(m.vecinos[u].escudo == 0 for u in nivel2))   # a los amigos de los amigos no

    def test_beto_el_influencer_llega_a_dos_niveles(self):
        m = nuevo("beto")
        self._tocar_estrella_junto_a(m, "Rosa")
        for u, n, _ in m.social.bfs("Rosa", max_nivel=2):
            self.assertGreater(m.vecinos[u].escudo, 0)

    def test_estrella_que_se_deja_pasar_es_ignorar(self):
        m = nuevo()
        j = m.jugador
        m.estrellas.append(Estrella(5, j.x + 60, j.y))             # en la pantalla del jugador
        m.estrellas[0].vida = 0.001
        m._estrellas(1 / 60)
        self.assertEqual(m.decisiones.buscar("perdida").veces, 1)

    def test_estrella_que_nunca_se_vio_no_cuenta_como_ignorada(self):
        m = nuevo()
        j = m.jugador
        m.estrellas.append(Estrella(6, j.x + 600, j.y + 300))      # al otro lado del mapa
        m.estrellas[0].vida = 0.001
        m._estrellas(1 / 60)
        self.assertEqual(m.estrellas, [])
        self.assertEqual(m.decisiones.buscar("perdida").veces, 0)


class TestLanzar(unittest.TestCase):
    def test_curar_lanzando_al_cuerpo_del_morado(self):
        m = nuevo()
        rosa = m.vecinos["Rosa"]
        m._infectar(rosa, None)
        lanzar_a(m, rosa.cuerpo)
        self.assertIsNone(rosa.bulo)
        self.assertEqual(m.jugador.stats["curados"], 1)
        self.assertEqual(m.decisiones.buscar("verificada").veces, 1)

    def test_atrapar_en_el_aire_es_reportar(self):
        m = nuevo()
        b = m.nuevo_bulo(300, 300)
        lanzar_a(m, b.pos)
        self.assertNotIn(b.id, m.bulos)
        self.assertEqual(m.decisiones.buscar("reportada").veces, 1)

    def test_beto_cura_tambien_a_los_amigos(self):
        m = nuevo("beto")
        amigo = list(m.social.vecinos("Rosa"))[0]
        m._infectar(m.vecinos["Rosa"], None)
        m._infectar(m.vecinos[amigo], None)          # otra cadena distinta
        lanzar_a(m, m.vecinos["Rosa"].cuerpo)
        self.assertIsNone(m.vecinos[amigo].bulo)

    def test_el_periodico_de_ana_atraviesa_varios(self):
        for clave, esperado in (("ana", 3), ("dani", 1)):
            m = nuevo(clave)
            for k in range(3):
                m.nuevo_bulo(300 + k * 14, 300)
            m.jugador.x, m.jugador.y, m.jugador.vec = 280, 312, (1.0, 0.0)
            m._lanzar()
            for _ in range(30):
                m._proyectiles(1 / 60)
            self.assertEqual(m.jugador.stats["bulos"], esperado, clave)

    def test_pelea_se_calma_lanzando(self):
        for clave, golpes in (("ana", 2), ("caro", 1)):
            m = nuevo(clave)
            m._empezar_pelea(0.0)
            p = m.peleas[0]
            p["activa"], p["t"] = True, 15
            for _ in range(golpes):
                lanzar_a(m, m.vecinos[p["a"]].cuerpo)
            self.assertEqual(p.get("fin"), "paz", clave)

    def test_el_morado_avisa_a_quien_se_lo_va_a_pasar(self):
        m = nuevo()
        rosa = m.vecinos["Rosa"]
        m._infectar(rosa, None)
        rosa.t_prop = AVISO_REENVIO - 0.5
        m._vecinos(1 / 60)
        u = rosa.siguiente
        self.assertIn(u, m.social.vecinos("Rosa"))
        self.assertEqual(m.social.peso("Rosa", u), max(m.social.vecinos("Rosa").values()))   # el de más confianza
        rosa.t_prop = 0
        m._vecinos(1 / 60)
        self.assertEqual(m.pulsos[0].hasta, u)          # se lo pasa justo a quien se marcó
        self.assertIsNone(rosa.siguiente)

    def test_si_el_amigo_queda_protegido_avisa_a_otro(self):
        m = nuevo()
        rosa = m.vecinos["Rosa"]
        m._infectar(rosa, None)
        rosa.t_prop = 1.0
        m._vecinos(1 / 60)
        primero = rosa.siguiente
        m.vecinos[primero].escudo = 20
        m._vecinos(1 / 60)
        self.assertNotEqual(rosa.siguiente, primero)
        self.assertEqual(m.vecinos[primero].bulo, None)

    def test_reenvio_que_llega_es_regar(self):
        m = nuevo()
        rosa = m.vecinos["Rosa"]
        m._infectar(rosa, None)
        rosa.t_prop = 0
        m._vecinos(1 / 60)
        self.assertEqual(len(m.pulsos), 1)
        m.pulsos[0].f = 0.999
        m._pulsos(1 / 60)
        self.assertEqual(m.decisiones.buscar("regada").veces, 1)
        self.assertEqual(m.jugador.stats["regados"], 1)


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
        orden = [v for v, nivel, _ in m.social.bfs(origen, filtro=lambda u: m.vecinos[u].escudo <= 0, max_nivel=2)]
        infectados = {v.nombre for v in m.infectados()}
        self.assertEqual(infectados, set(orden[:MAX_VIRAL]))     # le llega a los primeros del BFS
        self.assertIn(origen, infectados)
        self.assertNotIn(list(m.social.vecinos(origen))[0], infectados)   # el protegido no


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
    def test_estrellas_de_reputacion(self):
        self.assertEqual(umbrales_reputacion(18), (14, 9))
        m = nuevo()
        for nombre in sorted(m.vecinos)[:5]:      # 5 morados: quedan 13 a salvo
            m._infectar(m.vecinos[nombre], None)
        self.assertEqual(m.resumen()["reputacion"], 2)
        m._atrapar(m.vecinos[sorted(m.vecinos)[0]].bulo)       # 14 a salvo
        self.assertEqual(m.resumen()["reputacion"], 3)

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
        # la regla del umbral: con 50 o más de desinformación gana Emilio; con menos, no
        self.assertNotEqual(calcular_eleccion(res(49, 30), js)[0][0], "Emilio")
        self.assertEqual(calcular_eleccion(res(50, 80), js)[0][0], "Emilio")


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
            self.assertTrue(any(m["t"] == "ronda" for m in msgs_a))     # los dos reciben la ronda
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


class TestMensajeFinal(unittest.TestCase):
    def test_el_mensaje_va_con_las_estrellas(self):
        from cazabulos.pantallas.final import mensaje
        base = {"vecinos": 18, "stats": {"regados": 6}}
        self.assertIn("Increíble", mensaje(dict(base, salvados=18, reputacion=3)))      # nunca regaña si ganó 3
        self.assertIn("Muy bien", mensaje(dict(base, salvados=10, reputacion=2)))
        self.assertNotIn("bien", mensaje(dict(base, salvados=2, reputacion=1)).lower().split("!")[0])


if __name__ == "__main__":
    unittest.main()
