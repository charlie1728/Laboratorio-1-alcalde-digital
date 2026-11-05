"""Pruebas de las estructuras de datos de Cazabulos."""
import random
import unittest

from cazabulos.estructuras.arbol_decision import arbol_noticia
from cazabulos.estructuras.arbol_mutaciones import ArbolMutaciones
from cazabulos.estructuras.avl import AVL
from cazabulos.estructuras.grafo import Grafo


def grafo_pdf():
    """El ejemplo del enunciado: Ana-Luis, Ana-Pedro, Luis-Carlos, Pedro-María, Carlos-María."""
    g = Grafo()
    for a, b in (("Ana", "Luis"), ("Ana", "Pedro"), ("Luis", "Carlos"), ("Pedro", "Maria"), ("Carlos", "Maria")):
        g.agregar_arista(a, b)
    return g


class TestGrafo(unittest.TestCase):
    def test_bfs_por_niveles(self):
        g = grafo_pdf()
        orden = g.bfs("Ana")
        niveles = {v: n for v, n, _ in orden}
        self.assertEqual(niveles, {"Ana": 0, "Luis": 1, "Pedro": 1, "Carlos": 2, "Maria": 2})
        self.assertEqual(orden[0][0], "Ana")

    def test_bfs_con_filtro_y_limite(self):
        g = grafo_pdf()
        # Pedro está protegido: la noticia falsa no pasa por él
        orden = [v for v, _, _ in g.bfs("Ana", filtro=lambda v: v != "Pedro")]
        self.assertNotIn("Pedro", orden)
        self.assertIn("Maria", orden)  # llega por Luis y Carlos
        self.assertEqual({v for v, _, _ in g.bfs("Ana", max_nivel=1)}, {"Ana", "Luis", "Pedro"})

    def test_eliminar_arista_parte_la_red(self):
        g = grafo_pdf()
        self.assertEqual(len(g.componentes()), 1)
        g.eliminar_arista("Ana", "Pedro")
        g.eliminar_arista("Carlos", "Maria")
        comps = sorted(sorted(c) for c in g.componentes())
        self.assertEqual(comps, [["Ana", "Carlos", "Luis"], ["Maria", "Pedro"]])

    def test_eliminar_vertice(self):
        g = grafo_pdf()
        g.eliminar_vertice("Luis")
        self.assertNotIn("Luis", g)
        self.assertFalse(g.tiene_arista("Ana", "Luis"))
        self.assertEqual(g.grado("Ana"), 1)

    def test_dijkstra_y_camino(self):
        g = Grafo()
        g.agregar_arista("A", "B", 4)
        g.agregar_arista("A", "C", 1)
        g.agregar_arista("C", "B", 1)
        g.agregar_arista("B", "D", 5)
        dist, _ = g.dijkstra("A")
        self.assertEqual(dist["B"], 2)
        self.assertEqual(g.camino("A", "D"), ["A", "C", "B", "D"])
        g.agregar_vertice("Z")
        self.assertEqual(g.camino("A", "Z"), [])

    def test_dfs_y_grado(self):
        g = grafo_pdf()
        self.assertEqual(set(g.dfs("Ana")), set(g.vertices()))
        g.agregar_arista("Ana", "Sofia")  # Ana pasa a tener 3 amigos
        self.assertEqual(g.mas_conectado(), "Ana")
        self.assertEqual(len(g.aristas()), 6)


class TestArbolMutaciones(unittest.TestCase):
    def setUp(self):
        self.a = ArbolMutaciones()
        self.a.crear_raiz(1)
        self.a.insertar(2, 1)
        self.a.insertar(3, 1)
        self.a.insertar(4, 2)
        self.a.insertar(5, 4)

    def test_recorridos(self):
        self.assertEqual(self.a.preorden(1), [1, 2, 4, 5, 3])
        self.assertEqual(self.a.postorden(1), [5, 4, 2, 3, 1])
        self.assertEqual([i for i, _ in self.a.por_niveles(1)], [1, 2, 3, 4, 5])
        self.assertEqual(self.a.altura(1), 3)
        self.assertEqual(self.a.raiz_de(5), 1)
        self.assertEqual(self.a.camino_a_raiz(5), [5, 4, 2, 1])

    def test_cortar_una_rama(self):
        self.assertEqual(self.a.eliminar_subarbol(2), [2, 4, 5])
        self.assertEqual(self.a.preorden(1), [1, 3])
        self.assertNotIn(5, self.a)

    def test_cortar_la_raiz_tumba_todo(self):
        self.assertEqual(len(self.a.eliminar_subarbol(1)), 5)
        self.assertEqual(len(self.a), 0)
        self.assertEqual(self.a.mayor_cadena, 5)

    def test_padre_perdido_queda_como_raiz(self):
        self.a.eliminar_subarbol(1)
        self.a.insertar(9, 1)
        self.assertTrue(self.a.es_raiz(9))


class TestArbolDecision(unittest.TestCase):
    def test_caminos_y_hojas(self):
        a = arbol_noticia()
        self.assertEqual(a.recorrer(["mirar", "real", "entregar"]).clave, "verdad")
        self.assertEqual(a.recorrer(["entregar", "falsa"]).clave, "bulo")
        self.assertEqual(a.recorrer(["mirar", "falsa"]).clave, "reporte")
        self.assertEqual(a.raiz.veces, 3)
        self.assertEqual(a.buscar("mirar").veces, 2)
        self.assertEqual(a.camino_a("verdad"), ["noticia", "mirar", "real", "verdad"])
        self.assertEqual(len(a.hojas()), 6)

    def test_compartir_sin_mirar_un_bulo_resta(self):
        a = arbol_noticia()
        self.assertLess(a.buscar("bulo").efecto["puntos"], 0)
        self.assertGreater(a.buscar("verdad").efecto["puntos"], a.buscar("suerte").efecto["puntos"])

    def test_eliminar_rama(self):
        a = arbol_noticia()
        a.eliminar("sin_mirar")
        self.assertIsNone(a.buscar("bulo"))
        self.assertEqual(len(a.hojas()), 4)


class TestAVL(unittest.TestCase):
    def test_orden_y_balance(self):
        t = AVL()
        datos = list(range(200))
        random.Random(3).shuffle(datos)
        for d in datos:
            t.insertar(d, f"j{d}")
        self.assertEqual([c for c, _ in t.en_orden()], list(range(200)))
        self.assertLessEqual(t.altura(), 10)
        self.assertEqual([c for c, _ in t.mejores(3)], [199, 198, 197])
        for d in range(0, 200, 2):
            t.eliminar(d)
        self.assertEqual(len(t), 100)
        self.assertEqual(t.menor(), 1)
        self.assertLessEqual(t.altura(), 9)


if __name__ == "__main__":
    unittest.main()
