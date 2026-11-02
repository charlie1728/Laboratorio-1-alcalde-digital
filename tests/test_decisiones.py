"""Pruebas de la alerta viral (árbol de decisiones), la propagación por la red social, la calle (discusiones),
los indicadores de la ciudad, la elección, los récords y lo compartido en el duelo.
    python -m unittest discover -s tests -v
"""
import random
import tempfile
import time
import unittest
from pathlib import Path

from alcalde.corta import records
from alcalde.corta.campana import Campana
from alcalde.corta.contenido import INDICADORES
from alcalde.corta.nivel import DISCUSION_SEG, DISCUSION_Y, Nivel
from alcalde.estructuras.arbol_decision import ACCION, HOJA, PREGUNTA, NodoDecision, arbol_viral
from alcalde.modelo.mapa import crear_mapa
from alcalde.modelo.red_social import conectar_jugador, generar_red


def _red_con(nombre, rol):
    mapa = crear_mapa()
    red = generar_red(random.Random(1), mapa, {nombre})
    conectar_jugador(red, mapa, random.Random(2), nombre, 0, rol, {}, "PLAZA")
    return red


def _con_alerta(rol="periodista", semilla=3, verdad=None):
    """Un nivel con la alerta viral abierta (si se pide, de una publicación verdadera o falsa)."""
    red = _red_con("Ana", rol)
    for s in range(semilla, semilla + 60):
        n = Nivel("NORTE", dict(nombre="Ana", rol=rol), semilla=s, red=red)
        n.prox_alerta = 0.05
        for _ in range(10):
            n.actualizar(1 / 60)
        if n.alerta and (verdad is None or (n.alerta["pub"].tipo == "verdad") == verdad):
            return n
    raise AssertionError("no salió la alerta pedida")


class TestArbolDecision(unittest.TestCase):
    def test_forma_del_arbol(self):
        a = arbol_viral()
        self.assertEqual([h.clave for h in a.raiz.hijos], ["verificar", "compartir", "reportar", "ignorar"])
        self.assertEqual(len(a.hojas()), 10)
        self.assertEqual(a.altura(), 4)                      # raíz > verificar > ¿es verdad? > sí/no > hoja
        self.assertTrue(all(h.tipo == HOJA for h in a.hojas()))
        self.assertEqual([n.clave for n in a.camino("v_no_reportar")],
                         ["raiz", "verificar", "v_es", "v_no", "v_no_reportar"])
        self.assertEqual(len(a.preorden()), len(a))
        self.assertEqual(sum(len(nivel) for nivel in a.por_niveles()), len(a))

    def test_recorrer_jugando(self):
        a = arbol_viral()
        nodo = a.avanzar(a.elegir(a.raiz, "verificar"), False)
        self.assertEqual(nodo.tipo, PREGUNTA)                 # verificar revela la respuesta
        self.assertTrue(nodo.revela)
        nodo = a.responder(nodo, False)
        self.assertEqual(nodo.tipo, ACCION)
        self.assertEqual([h.clave for h in a.opciones(nodo)], ["v_no_reportar", "v_no_compartir"])
        # compartir sin verificar baja solo hasta la hoja: el juego contesta en silencio
        self.assertEqual(a.avanzar(a.elegir(a.raiz, "compartir"), True).clave, "c_si")
        self.assertEqual(a.avanzar(a.elegir(a.raiz, "compartir"), False).clave, "c_no")
        with self.assertRaises(KeyError):
            a.elegir(a.raiz, "borrar")

    def test_insertar_y_eliminar(self):
        a = arbol_viral()
        antes = len(a)
        a.insertar("raiz", NodoDecision("preguntar", "Preguntar a un adulto", HOJA, puntos=20, bien=True))
        self.assertIn("preguntar", a)
        self.assertEqual(len(a), antes + 1)
        with self.assertRaises(ValueError):
            a.insertar("preguntar", NodoDecision("x", "x", HOJA))          # una hoja no tiene hijos
        quitados = a.eliminar("verificar")                                  # se va con todo su subárbol
        self.assertEqual(len(quitados), 8)       # verificar, la pregunta, sí, no y sus 4 hojas
        self.assertNotIn("v_no_reportar", a)
        self.assertEqual(len(a), antes + 1 - 8)
        with self.assertRaises(ValueError):
            a.eliminar("raiz")


class TestAlertaViral(unittest.TestCase):
    def test_la_ciudad_se_congela_mientras_decides(self):
        n = _con_alerta()
        pos = [(p.x, p.y) for p in n.pubs]
        reloj = n.reloj
        for _ in range(60):
            n.actualizar(1 / 60)
        self.assertEqual(pos, [(p.x, p.y) for p in n.pubs])
        self.assertEqual(n.reloj, reloj)
        self.assertLess(n.alerta["t"], n.alerta["limite"])
        self.assertEqual(n.cortar((0, 0), (1280, 720)), 0)                   # no se corta durante la alerta

    def test_verificar_y_reportar_una_mentira_la_frena(self):
        n = _con_alerta(verdad=False)
        self.assertTrue(n.decidir("verificar"))
        self.assertEqual(n.alerta["etapa"], "verificado")
        self.assertEqual([o.clave for o in n.opciones_alerta()], ["v_no_reportar", "v_no_compartir"])
        n.decidir("v_no_reportar")
        a = n.alerta
        self.assertEqual(a["etapa"], "resultado")
        self.assertEqual(a["puntos"], 70 + 15)                               # +15 de bono por ser periodista
        self.assertLess(n.efectos["desinformacion"], 0)
        if a["propagacion"]:
            self.assertTrue(a["propagacion"]["frenada"])
        self.assertEqual(a["camino"][-1], "Reportar")
        self.assertTrue(set(a["pub"].senales) <= set(n.senales_vistas))  # verificar enseña las pistas

    def test_compartir_se_propaga_por_los_seguidores(self):
        n = _con_alerta(rol="influencer")
        n.decidir("compartir")
        prop = n.alerta["propagacion"]
        self.assertEqual(prop["origen"], "Ana")                              # sale del jugador
        red = n.red
        for v, p in prop["padre"].items():
            if p is not None:
                self.assertTrue(red.tiene_arista(p, v))                       # solo viaja por aristas de la red
                self.assertEqual(prop["nivel"][v], prop["nivel"][p] + 1)      # cada salto es un nivel del BFS
                self.assertIsNone(red.dato(v).jugador)
        self.assertEqual(prop["n"], len(prop["orden"]) - 1)

    def test_si_se_acaba_el_tiempo_se_ignora(self):
        n = _con_alerta()
        for _ in range(60 * 12):
            n.actualizar(1 / 60)
            if n.alerta and n.alerta["etapa"] == "resultado":
                break
        self.assertTrue(n.alerta["por_tiempo"])
        self.assertIn(n.decisiones[-1]["clave"], ("i_si", "i_no"))
        for _ in range(60 * 8):
            n.actualizar(1 / 60)
        self.assertIsNone(n.alerta)                                          # el resultado se cierra solo

    def test_compartir_una_mentira_daña_la_ciudad(self):
        n = _con_alerta(verdad=False)
        salud = n.salud
        n.decidir("compartir")
        self.assertIs(n.alerta["hoja"].bien, False)
        self.assertGreater(n.efectos["desinformacion"], 0)
        self.assertLessEqual(n.salud, salud)


class TestCalle(unittest.TestCase):
    def test_cortar_la_discusion_la_calma(self):
        n = Nivel("PRADO", dict(nombre="", rol="ciudadano"), semilla=4)
        n._abrir_discusion()
        x = n.discusion["x"]
        n.cortar((x - 100, DISCUSION_Y - 30), (x + 100, DISCUSION_Y - 30))
        self.assertIsNone(n.discusion)
        self.assertEqual(n.calmadas, 1)
        self.assertGreater(n.efectos["convivencia"], 0)

    def test_discusion_sin_calmar_sube_los_conflictos(self):
        n = Nivel("PRADO", dict(nombre="", rol="ciudadano"), semilla=4)
        n.prox_alerta = n.prox_reporte = float("inf")
        n._abrir_discusion()
        for _ in range(int(60 * (DISCUSION_SEG + 0.5))):
            n.actualizar(1 / 60)
        self.assertEqual(n.peleas, 1)
        self.assertGreater(n.efectos["conflictos"], 0)

    def test_efectos_del_nivel_estan_acotados(self):
        n = Nivel("PRADO", dict(nombre="", rol="ciudadano"), semilla=4)
        n.caidas, n.efectos["desinformacion"] = 50, 99
        ef = n.efectos_finales()
        self.assertEqual(set(ef), set(INDICADORES))
        self.assertTrue(all(-15 <= v <= 15 for v in ef.values()))

    def test_lo_compartido_por_un_rival_llega_como_publicacion(self):
        n = Nivel("PRADO", dict(nombre="", rol="ciudadano"), semilla=4)
        n.recibir_compartida("Beto", "Hospital Nova", "Abre jornada de vacunación", True, "Hospital: vacunación")
        p = n.pubs[-1]
        self.assertEqual((p.tipo, p.enviado_por), ("verdad", "Beto"))


class TestCiudad(unittest.TestCase):
    def test_indicadores_se_mueven_y_se_guardan(self):
        c = Campana.nueva(dict(nombre="Ana", rol="periodista"), 3)
        c.registrar(dict(zona="PLAZA", estado="ganado", estrellas=3, puntos=100, monedas=10, senales=[], hechos=[],
                         efectos=dict(verificada=10, desinformacion=-200)))
        self.assertTrue(all(0 <= v <= 100 for v in c.indicadores.values()))
        self.assertLess(c.indicadores["desinformacion"], 15)       # llegó a 0 y la noche la subió un poco
        ruta = Path(tempfile.gettempdir()) / "alcalde_prueba_indicadores.json"
        c.guardar(ruta)
        self.assertEqual(Campana.cargar(ruta).indicadores, c.indicadores)
        ruta.unlink()

    def test_el_jugador_es_parte_de_la_red_social(self):
        c = Campana.nueva(dict(nombre="Beto", rol="influencer"), 3)
        self.assertEqual(c.red.dato("Beto").jugador, 0)
        self.assertEqual(c.red.grado_salida("Beto"), 12)                     # el influencer llega lejos

    def test_la_eleccion_depende_de_lo_que_hiciste(self):
        c = Campana.nueva(dict(nombre="Dani", rol="candidato"), 3)
        nada = c.votar()
        self.assertEqual(nada["final"], "derrota")
        self.assertEqual(nada["ganador"], "emilio")                          # ganan los bots
        c.liberadas = ["PLAZA", "PARQUE", "HOSPITAL", "COLEGIO", "NORTE", "TERMINAL", "ESTADIO", "PRADO"]
        c.estrellas = {z: 3 for z in c.liberadas}
        todo = c.votar()
        self.assertGreater(todo["porcentaje"], nada["porcentaje"])
        self.assertNotEqual(todo["ganador"], "emilio")
        self.assertIn("jugador", todo["votos"])                              # el candidato eres tú
        self.assertAlmostEqual(sum(todo["votos"].values()), 100, delta=0.5)


class TestRecords(unittest.TestCase):
    def test_puesto_y_orden(self):
        ruta = Path(tempfile.gettempdir()) / "alcalde_prueba_records.json"
        ruta.unlink(missing_ok=True)
        self.assertEqual(records.agregar("Sofi", 300, "periodista", "PARQUE", 2, ruta), 1)
        self.assertEqual(records.agregar("Leo", 500, "influencer", "PRADO", 3, ruta), 1)
        self.assertEqual(records.agregar("Mía", 300, "ciudadano", "PLAZA", 1, ruta), 3)   # empate: llegó después
        self.assertEqual([d["nombre"] for d in records.mejores(8, ruta)], ["Leo", "Sofi", "Mía"])
        ruta.unlink()


class TestDueloCompartir(unittest.TestCase):
    def test_lo_compartido_le_llega_a_los_rivales(self):
        from alcalde.red.sala import Cliente, Servidor
        srv = Servidor(puerto=5098)
        try:
            a, b = Cliente("127.0.0.1", 5098), Cliente("127.0.0.1", 5098)
            a.enviar({"t": "hola", "nombre": "Ana", "rol": "periodista"})
            b.enviar({"t": "hola", "nombre": "Beto", "rol": "influencer"})
            time.sleep(0.3)
            a.enviar({"t": "compartir", "fuente": "Hospital Nova", "texto": "Abre jornada de vacunación", "verdad": True})
            fin, recibido = time.time() + 3, None
            while time.time() < fin and recibido is None:
                recibido = next((m for m in b.mensajes() if m.get("t") == "compartida"), None)
                time.sleep(0.02)
            self.assertIsNotNone(recibido)
            self.assertEqual((recibido["de"], recibido["verdad"]), ("Ana", True))
            self.assertTrue(any("compartió" in txt for _, txt in srv.historial))
            a.cerrar()
            b.cerrar()
        finally:
            srv.cerrar()


if __name__ == "__main__":
    unittest.main()
