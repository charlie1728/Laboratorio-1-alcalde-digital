"""Pruebas de los grafos y de su integración con los árboles. Ejecutar:
    python -m unittest discover -s tests -v
"""
import json
import math
import unittest

from alcalde.estructuras.grafo import Grafo
from alcalde.modelo.mapa import CALLES, ZONAS, crear_mapa

JUGADORES = [("Ana", "ciudadano", (0, 0, 0)), ("Beto", "periodista", (0, 0, 0)),
             ("Caro", "influencer", (0, 0, 0)), ("Dani", "candidato", (0, 0, 0))]


class TestGrafo(unittest.TestCase):
    """      COLEGIO
               |  2
            BARRIO
          1 /    \\ 4
       PARQUE --- PLAZA
               1    | 3
                 ALCALDIA
    """

    def setUp(self):
        self.g = Grafo()
        for a, b, w in [("COLEGIO", "BARRIO", 2), ("BARRIO", "PARQUE", 1), ("BARRIO", "PLAZA", 4),
                        ("PARQUE", "PLAZA", 1), ("PLAZA", "ALCALDIA", 3)]:
            self.g.agregar_arista(a, b, w)

    def test_tamano_y_grados(self):
        self.assertEqual(len(self.g), 5)
        self.assertEqual(self.g.num_aristas(), 5)
        self.assertEqual(self.g.grado("BARRIO"), 3)
        self.assertEqual(self.g.centralidad_grado(1)[0][0], "BARRIO")

    def test_bfs_por_niveles(self):
        niveles = self.g.bfs_niveles("COLEGIO")
        self.assertEqual([sorted(n) for n in niveles],
                         [["COLEGIO"], ["BARRIO"], ["PARQUE", "PLAZA"], ["ALCALDIA"]])
        _, nivel, padre = self.g.bfs("COLEGIO")
        self.assertEqual(nivel["ALCALDIA"], 3)
        self.assertEqual(padre["ALCALDIA"], "PLAZA")
        self.assertEqual(self.g.bfs_niveles("COLEGIO", max_nivel=1), [["COLEGIO"], ["BARRIO"]])

    def test_dfs(self):
        orden = self.g.dfs("COLEGIO")
        self.assertEqual(orden[0], "COLEGIO")
        self.assertEqual(set(orden), set(self.g.vertices()))
        self.assertEqual(orden[:2], ["COLEGIO", "BARRIO"])

    def test_dijkstra_y_camino(self):
        dist, camino = self.g.camino_mas_corto("COLEGIO", "ALCALDIA")
        self.assertEqual(dist, 7)                                   # 2 + 1 + 1 + 3
        self.assertEqual(camino, ["COLEGIO", "BARRIO", "PARQUE", "PLAZA", "ALCALDIA"])
        alc = self.g.alcanzables("COLEGIO", 4)
        self.assertEqual(set(alc), {"COLEGIO", "BARRIO", "PARQUE", "PLAZA"})

    def test_eliminar_arista_parte_el_grafo(self):
        self.assertTrue(self.g.es_conexo())
        self.g.eliminar_arista("PLAZA", "ALCALDIA")
        comps = self.g.componentes_conexas()
        self.assertEqual(len(comps), 2)
        self.assertEqual(comps[1], ["ALCALDIA"])
        self.assertEqual(self.g.camino_mas_corto("COLEGIO", "ALCALDIA"), (math.inf, []))

    def test_eliminar_vertice(self):
        quitadas = self.g.eliminar_vertice("BARRIO")
        self.assertEqual(len(quitadas), 3)
        self.assertNotIn("BARRIO", self.g)
        self.assertFalse(self.g.tiene_arista("COLEGIO", "BARRIO"))
        self.assertEqual(len(self.g.componentes_conexas()), 2)

    def test_dirigido_y_confianza_maxima(self):
        g = Grafo(dirigido=True)
        g.agregar_arista("A", "B", 0.9)
        g.agregar_arista("B", "C", 0.9)
        g.agregar_arista("A", "C", 0.5)       # directo, pero con menos confianza
        g.agregar_arista("C", "D", 0.2)
        self.assertEqual(g.grado_salida("A"), 2)
        self.assertEqual(set(g.predecesores("C")), {"A", "B"})
        conf, prev = g.confianza_maxima("A")
        self.assertAlmostEqual(conf["C"], 0.81)
        self.assertEqual(Grafo.reconstruir(prev, "C"), ["A", "B", "C"])
        self.assertAlmostEqual(conf["D"], 0.162)
        g.ajustar_peso("A", "B", -0.5)
        self.assertAlmostEqual(g.peso("A", "B"), 0.4)

    def test_serializar(self):
        g2 = Grafo.desde_dict(json.loads(json.dumps(self.g.a_dict())))
        self.assertEqual(g2.camino_mas_corto("COLEGIO", "ALCALDIA"), self.g.camino_mas_corto("COLEGIO", "ALCALDIA"))


class TestMapa(unittest.TestCase):
    def test_mapa_conexo_y_completo(self):
        m = crear_mapa()
        self.assertEqual(len(m), len(ZONAS))
        self.assertEqual(m.num_aristas(), len(CALLES))
        self.assertTrue(m.es_conexo())
