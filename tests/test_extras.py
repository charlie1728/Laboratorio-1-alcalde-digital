"""Pruebas de lo que hace al juego más completo: logros, misiones del día, Diario Nova, estadísticas de la
campaña y personajes personalizados.
    python -m unittest discover -s tests -v
"""
import random
import tempfile
import unittest
from pathlib import Path

from alcalde.corta.campana import Campana
from alcalde.corta.contenido import MISIONES, MISIONES_COMUNES, MISIONES_POR_REGLA
from alcalde.corta.logros import LOGROS, Registro
from alcalde.corta.nivel import PREMIO_MISION, Nivel, Pub, elegir_mision
from alcalde.modelo.mapa import ZONAS

ANA = dict(nombre="Ana", rol="periodista")


def _falsa(**kw):
    return Pub(1, "falsa", "Audio anónimo", "Algo falso", 0, 0, 0, 0, **kw)


class TestLogros(unittest.TestCase):
    def test_se_ganan_con_eventos_y_resultados(self):
        r = Registro(ruta=None)
        r.ver_evento({"t_": "corte", "bien": True, "pub": _falsa(), "combo": 10})
        self.assertIn("primer_corte", r)
        self.assertIn("combo10", r)
        r.ver_evento({"t_": "multi", "n": 3})
        r.ver_evento({"t_": "jefe_cae"})
        r.ver_resultado({"estado": "ganado", "errores": 0, "estrellas": 3})
        r.ver_resultado({"puntos": 600}, "rapido")
        for k in ("multi3", "heroe", "ojo", "perfecto", "record"):
            self.assertIn(k, r)
        self.assertEqual(r.sacar_nuevo(), "primer_corte")              # se anuncian en orden

    def test_los_contadores_llegan_a_la_meta(self):
        r = Registro(ruta=None)
        for _ in range(4):
            r.ver_evento({"t_": "paces"})
        self.assertNotIn("pacificador", r)
        self.assertEqual(r.progreso("pacificador"), (4, 5))
        r.ver_evento({"t_": "paces"})
        self.assertIn("pacificador", r)
        r.ver_evento({"t_": "decision", "clave": "v_si_compartir"})
        self.assertIn("buena_fuente", r)

    def test_no_se_gana_dos_veces_y_se_guarda(self):
        ruta = Path(tempfile.gettempdir()) / "alcalde_prueba_logros.json"
        ruta.unlink(missing_ok=True)
        r = Registro(ruta)
        self.assertTrue(r.ganar("estilo"))
        self.assertFalse(r.ganar("estilo"))
        self.assertFalse(r.ganar("no_existe"))
        self.assertIn("estilo", Registro(ruta))
        ruta.unlink()
        self.assertTrue(all(len(v) == 4 for v in LOGROS.values()))


class TestMisiones(unittest.TestCase):
    def test_cada_barrio_tiene_misiones_que_le_sirven(self):
        rng = random.Random(1)
        for z in ZONAS:
            for _ in range(20):
                self.assertIn(elegir_mision(z, rng), MISIONES)
        self.assertIn(elegir_mision("NORTE", rng), MISIONES_POR_REGLA["cadenas"])
        self.assertIn(elegir_mision("ALCALDIA", rng), MISIONES_POR_REGLA["jefe"])
        self.assertTrue(set(MISIONES_COMUNES) <= set(MISIONES))

    def test_cumplir_la_mision_da_premio(self):
        n = Nivel("PRADO", ANA, semilla=3, mision="calmar")
        self.assertEqual(n.progreso_mision(), (0, 2))
        antes = n.puntos
        n.calmadas = 2
        n._revisar_mision()
        self.assertTrue(n.mision["hecha"])
        self.assertGreater(n.puntos, antes)
        sin = Nivel("PRADO", ANA, semilla=3, mision="calmar")
        n.estado = sin.estado = "ganado"
        self.assertEqual(n.resultado()["monedas"] - sin.resultado()["monedas"], PREMIO_MISION["monedas"])
        self.assertTrue(n.resultado()["mision"]["cumplida"])

    def test_sin_errores_se_pierde_al_cortar_una_verdad(self):
        n = Nivel("PRADO", ANA, semilla=3, mision="sin_errores")
        n.errores = 1
        n._revisar_mision()
        self.assertTrue(n.mision["fallida"])
        self.assertFalse(n.mision["hecha"])

    def test_la_campana_muestra_la_misma_mision_que_se_juega(self):
        c = Campana.nueva(ANA, 4)
        self.assertEqual(c.mision("PLAZA"), c.mision("PLAZA"))
        self.assertIn(c.mision("PLAZA"), MISIONES_POR_REGLA["tutorial"])
        self.assertIsNone(Nivel("ESTADIO", ANA, semilla=1, alertas=False).mision)   # el fondo del menú no tiene


class TestDiario(unittest.TestCase):
    def _res(self, **kw):
        base = dict(zona="PLAZA", estado="ganado", estrellas=2, puntos=100, monedas=10, senales=[], hechos=[],
                    cortadas=12, salvadas=4, calmadas=1, decisiones=[], mision=dict(cumplida=True))
        base.update(kw)
        return base

    def test_titulares(self):
        c = Campana.nueva(ANA, 5)
        frenada = dict(clave="v_no_reportar", alcance=8, texto="El agua está envenenada")
        regada = dict(clave="c_no", alcance=14, texto="Cierran el colegio")
        self.assertIn("frenó", c.titular(self._res(decisiones=[frenada]), {})[0])
        self.assertIn("14 vecinos", c.titular(self._res(decisiones=[regada]), {})[0])
        self.assertIn("vuelve a confiar", c.titular(self._res(), {"liberada": "PLAZA"})[0])
        self.assertIn("ganan", c.titular(self._res(estado="perdido"), {})[0])

    def test_estadisticas_y_diario_se_guardan(self):
        c = Campana.nueva(ANA, 6)
        cambios = c.registrar(self._res(decisiones=[dict(clave="v_no_reportar", alcance=3, texto="x")]))
        self.assertIn("titular", cambios)
        self.assertEqual((c.stats["frenadas"], c.stats["verificadas"], c.stats["misiones"]), (1, 1, 1))
        self.assertEqual(len(c.diario), 1)
        ruta = Path(tempfile.gettempdir()) / "alcalde_prueba_diario.json"
        c.guardar(ruta)
        otra = Campana.cargar(ruta)
        self.assertEqual((otra.stats, otra.diario), (c.stats, c.diario))
        ruta.unlink()

    def test_la_leccion_final_depende_de_como_jugaste(self):
        from alcalde.corta.periodico import leccion
        self.assertIn("verifica", leccion(dict(mentiras_compartidas=3, frenadas=1), "plata").lower())
        self.assertIn("bots", leccion({}, "derrota"))
        self.assertIn("¡Así se cuida", leccion(dict(verificadas=2, frenadas=2), "oro"))


class TestPersonalizar(unittest.TestCase):
    def test_guardar_y_cargar_looks(self):
        from alcalde.corta.personalizar import cargar_looks, guardar_look
        ruta = Path(tempfile.gettempdir()) / "alcalde_prueba_looks.json"
        ruta.unlink(missing_ok=True)
        guardar_look("periodista", dict(piel=99, pelo="afro", color_pelo=2, ropa=3, extra="gafas"), ruta)
        look = cargar_looks(ruta)["periodista"]
        self.assertEqual(look["pelo"], "afro")
        self.assertLess(look["piel"], 6)                                 # se normaliza a un tono que existe
        ruta.unlink()


if __name__ == "__main__":
    unittest.main()
