"""Pruebas de Corta la mentira: niveles, campaña, árbol del rumor, contagio, archivo AVL y duelo en red.
    python -m unittest discover -s tests -v
"""
import random
import tempfile
import time
import unittest
from pathlib import Path

from alcalde.corta.campana import FINAL, INICIO, PARA_EL_JEFE, Campana
from alcalde.corta.nivel import ALTO, Nivel
from alcalde.modelo.mapa import ZONAS, crear_mapa
from alcalde.modelo.red_social import generar_red

RED = generar_red(random.Random(1), crear_mapa(), set())
ANA = dict(nombre="Ana", rol="periodista")


def _avanzar_hasta(n, condicion, max_seg=60):
    for _ in range(int(max_seg * 60)):
        if condicion():
            return True
        n.actualizar(1 / 60)
    return condicion()


def _cortar(n, p):
    return n.cortar((p.x - 10, p.y), (p.x + 10, p.y))


class TestNivel(unittest.TestCase):
    def test_cortar_falsa_suma_y_carga_el_poder(self):
        n = Nivel("PLAZA", ANA, semilla=1, red=RED)
        _avanzar_hasta(n, lambda: any(p.tipo == "falsa" for p in n.pubs))
        p = next(p for p in n.pubs if p.tipo == "falsa")
        self.assertEqual(_cortar(n, p), 1)
        self.assertGreater(n.puntos, 0)
        self.assertGreater(n.energia, 0)
        self.assertEqual(n.cortadas, 1)
        self.assertTrue(set(p.senales) <= set(n.senales_vistas))

    def test_cortar_verdad_quita_confianza(self):
        n = Nivel("PLAZA", ANA, semilla=2, red=RED)
        _avanzar_hasta(n, lambda: any(p.tipo == "verdad" for p in n.pubs))
        p = next(p for p in n.pubs if p.tipo == "verdad")
        antes = n.salud
        _cortar(n, p)
        self.assertLess(n.salud, antes)
        self.assertEqual(n.errores, 1)

    def test_falsa_que_cae_quita_confianza_y_verdad_va_al_archivo(self):
        n = Nivel("NORTE", ANA, semilla=3, red=RED)
        _avanzar_hasta(n, lambda: n.caidas > 0 and n.salvadas > 0, 60)
        self.assertLess(n.salud, n.salud_max)
        self.assertTrue(n.hechos)

    def test_origen_se_reenvia_por_la_red_y_cortarlo_poda_las_copias(self):
        n = Nivel("NORTE", ANA, semilla=4, red=RED)
        _avanzar_hasta(n, lambda: any(p.copia_de for p in n.pubs), 90)
        copias = [p for p in n.pubs if p.copia_de]
        self.assertTrue(copias)
        c = copias[0]
        arbol = n.arboles[c.caso]
        hijo = arbol.buscar(c.nodo)
        padre = hijo.padre
        # cada copia la reenvió un seguidor del autor del origen (arista de salida del grafo social)
        if c.autor and padre.autor in RED:
            self.assertTrue(RED.tiene_arista(padre.autor, c.autor))
        # cortar el padre (si sigue en pantalla) o la copia poda su subárbol
        antes = len(arbol)
        _cortar(n, c)
        self.assertLess(len(arbol), antes)
        self.assertNotIn(c.nodo, arbol)

    def test_la_misma_semilla_da_el_mismo_nivel(self):
        a = Nivel("ESTADIO", ANA, semilla=9, red=RED)
        b = Nivel("ESTADIO", ANA, semilla=9, red=RED)
        for _ in range(600):
            a.actualizar(1 / 60)
            b.actualizar(1 / 60)
        self.assertEqual([(p.texto, round(p.x)) for p in a.pubs], [(p.texto, round(p.x)) for p in b.pubs])

    def test_todos_los_barrios_terminan(self):
        for z in ZONAS:
            n = Nivel(z, ANA, semilla=5, red=RED, duracion=20)
            rng = random.Random(5)
            for _ in range(60 * 200):
                if n.estado != "jugando":
                    break
                for p in list(n.pubs):
                    if p.tipo != "verdad" and 80 < p.y < ALTO - 100 and -50 < p.x < 1330 and rng.random() < 0.08:
                        _cortar(n, p)
                if n.energia >= 1:
                    n.usar_poder()
                n.actualizar(1 / 60)
            self.assertIn(n.estado, ("ganado", "perdido"), z)

    def test_el_jefe_se_puede_derrotar(self):
        n = Nivel("ALCALDIA", ANA, semilla=6, red=RED)
        for _ in range(60 * 240):
            if n.estado != "jugando":
                break
            for p in list(n.pubs):
                if p.tipo != "verdad" and p.y < ALTO - 100:
                    _cortar(n, p)
            n.actualizar(1 / 60)
        self.assertEqual(n.estado, "ganado")
        self.assertEqual(n.jefe["hp"], 0)

    def test_estrellas(self):
        n = Nivel("PLAZA", ANA, semilla=1, red=RED)
        n.estado = "ganado"
        n.salud = n.salud_max
        self.assertEqual(n.estrellas(), 3)
        n.errores = 1
        self.assertEqual(n.estrellas(), 2)
        n.salud = n.salud_max * 0.3
        self.assertEqual(n.estrellas(), 1)


class TestCampana(unittest.TestCase):
    def _res(self, zona, estrellas=2, estado="ganado"):
        return dict(zona=zona, estado=estado, estrellas=estrellas, puntos=100, monedas=30, senales=["cadena"],
                    hechos=["Zeta", "Alfa", "Mitad"])

    def test_solo_se_juega_en_vecinos_de_un_barrio_liberado(self):
        c = Campana.nueva(ANA, 3)
        self.assertEqual(c.disponibles(), [INICIO])
        c.registrar(self._res(INICIO))
        # La Alcaldía es vecina de la Plaza, pero el jefe pide liberar antes PARA_EL_JEFE barrios.
        self.assertEqual(set(c.disponibles()), set(c.mapa.vecinos(INICIO)) - {FINAL})
        c.liberadas += [z for z in ZONAS if z not in (INICIO, FINAL)][:PARA_EL_JEFE - 1]
        self.assertIn(FINAL, c.disponibles())

    def test_el_rumor_no_pasa_por_barrios_liberados(self):
        c = Campana.nueva(ANA, 4)
        c.registrar(self._res(INICIO))
        for _ in range(8):
            cambios = c.noche()
            for a, b in cambios["contagios"]:
                self.assertNotIn(b, c.liberadas)
                self.assertIn(b, c.mapa.vecinos(a))       # el contagio va por una calle del mapa
        self.assertEqual(c.infeccion[INICIO], 0)

    def test_archivo_avl_y_album(self):
        c = Campana.nueva(ANA, 5)
        c.registrar(self._res(INICIO))
        self.assertEqual([k for k, _ in c.archivo.inorden()], ["Alfa", "Mitad", "Zeta"])
        self.assertTrue(c.archivo.es_avl_valido())
        self.assertIn("cadena", c.senales)

    def test_tienda(self):
        c = Campana.nueva(ANA, 6)
        c.monedas = 100
        self.assertTrue(c.comprar("filo"))
        self.assertEqual(c.mejoras["filo"], 1)
        self.assertEqual(c.monedas, 60)
        c.monedas = 0
        self.assertFalse(c.comprar("filo"))

    def test_ganarle_al_jefe_termina_con_la_eleccion(self):
        c = Campana.nueva(ANA, 7)
        for z in ZONAS:
            if z != FINAL:
                c.liberadas.append(z)
                c.estrellas[z] = 3
        c.registrar(self._res(FINAL, 3))
        self.assertTrue(c.terminada)
        self.assertEqual(c.eleccion["final"], "oro")

    def test_guardar_y_cargar(self):
        c = Campana.nueva(ANA, 8)
        c.registrar(self._res(INICIO))
        ruta = Path(tempfile.gettempdir()) / "alcalde_prueba_campana.json"
        c.guardar(ruta)
        d = Campana.cargar(ruta)
        self.assertEqual(d.a_dict(), c.a_dict())
        self.assertTrue(d.archivo.es_avl_valido())
        Campana.borrar(ruta)


class TestDueloEnRed(unittest.TestCase):
    def test_sala_empieza_y_reparte_ataques(self):
        from alcalde.red.sala import Cliente, Servidor
        srv = Servidor(puerto=5099)
        try:
            a, b = Cliente("127.0.0.1", 5099), Cliente("127.0.0.1", 5099)
            a.enviar({"t": "hola", "nombre": "Ana", "rol": "periodista"})
            time.sleep(0.2)
            b.enviar({"t": "hola", "nombre": "Beto", "rol": "influencer"})

            def esperar(cli, tipo, seg=3.0):
                fin = time.time() + seg
                while time.time() < fin:
                    for m in cli.mensajes():
                        if m.get("t") == tipo:
                            return m
                    time.sleep(0.02)
                return None
            sala = None
            fin = time.time() + 3
            while time.time() < fin and (sala is None or len(sala["jugadores"]) < 2):
                sala = esperar(a, "sala", 0.5) or sala
            self.assertEqual(len(sala["jugadores"]), 2)
            a.enviar({"t": "empezar", "zona": "ESTADIO"})
            ea, eb = esperar(a, "empezar"), esperar(b, "empezar")
            self.assertEqual(ea["semilla"], eb["semilla"])        # todos juegan con lo mismo
            a.enviar({"t": "ataque"})
            ataque = esperar(b, "ataque")
            self.assertEqual(ataque["de"], "Ana")
            b.enviar({"t": "puntos", "puntos": 120, "salud": 80, "estado": "ganado"})
            marcador = None
            fin = time.time() + 3
            while time.time() < fin and not (marcador and marcador["jugadores"][0]["puntos"] == 120):
                marcador = esperar(a, "marcador", 0.5) or marcador
            self.assertEqual(marcador["jugadores"][0]["nombre"], "Beto")
            a.cerrar()
            b.cerrar()
        finally:
            srv.cerrar()


if __name__ == "__main__":
    unittest.main()
