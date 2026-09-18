"""Pruebas de las dos estructuras de árbol. Ejecutar:
    python -m unittest discover -s tests -v
"""
import random
import unittest

from alcalde.estructuras.arbol_mutaciones import ArbolMutaciones, NodoMutacion
from alcalde.estructuras.archivo_avl import ArchivoHechosAVL
from alcalde.modelo.hechos import catalogo


def _hecho():
    return next(h for h in catalogo() if h.id == "parque-fumigacion")


class TestArbolMutaciones(unittest.TestCase):
    """      R
           /   \\
          A     B(exageracion)
         / \\     \\
        C   D     E(sin_contexto)
    """

    def setUp(self):
        h, rng = _hecho(), random.Random(1)
        real = h.afirmacion_real()
        self.R = NodoMutacion(real, "Alcaldía", alcance=10)
        self.t = ArbolMutaciones("prueba", self.R)
        self.A = self.t.insertar(self.R.id, NodoMutacion(real, "Ana", alcance=5))
        exa = real.mutar("exageracion", h, rng)
        self.B = self.t.insertar(self.R.id, NodoMutacion(exa, "Beto", distorsion="exageracion", alcance=7))
        self.C = self.t.insertar(self.A.id, NodoMutacion(real, "Caro", alcance=1))
        self.D = self.t.insertar(self.A.id, NodoMutacion(real, "Dani", alcance=2))
        sc = exa.mutar("sin_contexto", h, rng)
        self.E = self.t.insertar(self.B.id, NodoMutacion(sc, "Eva", distorsion="sin_contexto", alcance=3))

    def nombres(self, nodos):
        return [n.autor for n in nodos]

    def test_recorridos(self):
        self.assertEqual(self.nombres(self.t.preorden()), ["Alcaldía", "Ana", "Caro", "Dani", "Beto", "Eva"])
        self.assertEqual(self.nombres(self.t.postorden()), ["Caro", "Dani", "Ana", "Eva", "Beto", "Alcaldía"])
        niveles = [[n.autor for n in nivel] for nivel in self.t.por_niveles()]
        self.assertEqual(niveles, [["Alcaldía"], ["Ana", "Beto"], ["Caro", "Dani", "Eva"]])

    def test_altura_y_tamano(self):
        self.assertEqual(len(self.t), 6)
        self.assertEqual(self.t.altura(), 2)
        self.assertEqual(self.E.profundidad, 2)

    def test_camino_y_punto_de_mutacion(self):
        self.assertEqual(self.nombres(self.t.camino_a_raiz(self.E.id)), ["Eva", "Beto", "Alcaldía"])
        pm = self.t.punto_de_mutacion(self.E.id)
        self.assertIs(pm["exageracion"], self.B)
        self.assertIs(pm["sin_contexto"], self.E)
        self.assertEqual(self.t.punto_de_mutacion(self.C.id), {})

    def test_ancestro_comun(self):
        self.assertIs(self.t.ancestro_comun(self.C.id, self.D.id), self.A)
        self.assertIs(self.t.ancestro_comun(self.C.id, self.E.id), self.R)

    def test_agregacion_postorden(self):
        tot = self.t.agregar(lambda n: n.alcance)
        self.assertEqual(tot[self.A.id], 8)
        self.assertEqual(tot[self.R.id], 28)
        self.assertEqual(self.t.estadisticas()["alcance_falso"], 10)   # B(7)+E(3)

    def test_podar_subarbol(self):
        eliminados = self.t.podar(self.B.id)
        self.assertEqual(self.nombres(eliminados), ["Eva", "Beto"])
        self.assertEqual(len(self.t), 4)
        self.assertNotIn(self.E.id, self.t)
        self.assertEqual(self.R.hijos, [self.A])

    def test_eliminar_nodo_reengancha_hijos(self):
        self.t.eliminar_nodo(self.A.id)
        self.assertEqual(self.nombres(self.R.hijos), ["Caro", "Dani", "Beto"])
        self.assertIs(self.C.padre, self.R)
        self.assertEqual(len(self.t), 5)

    def test_eliminar_raiz(self):
        self.t.eliminar_nodo(self.R.id)
        self.assertIs(self.t.raiz, self.A)
        self.assertEqual(self.nombres(self.A.hijos), ["Caro", "Dani", "Beto"])

    def test_inmunizar_preorden(self):
        marcados = self.t.inmunizar(self.B.id)
        self.assertEqual(self.nombres(marcados), ["Beto", "Eva"])
        self.assertNotIn(self.E, self.t.frontera())


class TestArchivoAVL(unittest.TestCase):
    def test_insercion_en_orden_se_mantiene_balanceado(self):
        avl = ArchivoHechosAVL()
        claves = [f"h{i:03d}" for i in range(100)]      # peor caso para un BST normal
        for k in claves:
            avl.insertar(k, k)
        self.assertTrue(avl.es_avl_valido())
        self.assertLessEqual(avl.altura, 8)             # 1.44*log2(100) ~ 9.6
        self.assertEqual([k for k, _ in avl.inorden()], claves)
        self.assertTrue(any("Rotación" in r for r in avl.bitacora))

    def test_buscar_cuenta_comparaciones(self):
        avl = ArchivoHechosAVL()
        for k in ["m", "f", "t", "b", "h"]:
            avl.insertar(k, k.upper())
        valor, comps, ruta = avl.buscar("h")
        self.assertEqual((valor, comps, ruta), ("H", 3, ["m", "f", "h"]))
        self.assertIsNone(avl.buscar("z")[0])

    def test_eliminar_casos(self):
        avl = ArchivoHechosAVL()
        rng = random.Random(3)
        claves = [f"k{rng.randint(0, 999):03d}" for _ in range(60)]
        for k in claves:
            avl.insertar(k, 1)
        unicos = sorted(set(claves))
        for k in unicos[::2]:
            self.assertTrue(avl.eliminar(k))
            self.assertTrue(avl.es_avl_valido())
        self.assertFalse(avl.eliminar("no-existe"))
        self.assertEqual([k for k, _ in avl.inorden()], unicos[1::2])
        self.assertEqual(len(avl), len(unicos[1::2]))

    def test_rotaciones_LR_RL(self):
        avl = ArchivoHechosAVL()
        for k in ["c", "a", "b"]:          # LR
            avl.insertar(k, 0)
        self.assertEqual(avl.raiz.clave, "b")
        avl2 = ArchivoHechosAVL()
        for k in ["a", "c", "b"]:          # RL
            avl2.insertar(k, 0)
        self.assertEqual(avl2.raiz.clave, "b")


class TestPartida(unittest.TestCase):
    def test_partida_completa_sin_errores(self):
        from alcalde.modelo.partida import Partida
        for semilla in range(5):
            p = Partida([("A", "ciudadano", (0, 0, 0)), ("B", "periodista", (0, 0, 0)),
                         ("C", "influencer", (0, 0, 0)), ("D", "candidato", (0, 0, 0))], semilla=semilla)
            rng = random.Random(semilla)
            while not p.terminada:
                for _ in range(3):
                    casos = p.casos_abiertos()
                    if not casos:
                        break
                    c = rng.choice(casos)
                    n = rng.choice(list(c.arbol.preorden()))
                    ok = [a for a in p.acciones_para(n) if a["ok"]]
                    if ok:
                        p.ejecutar(rng.choice(ok)["clave"], c, n)
                if p.evento_viral:
                    p.resolver_viral(rng.choice([None, "verificar", "reportar", "compartir"]))
                p.terminar_turno()
            self.assertTrue(p.archivo.es_avl_valido())
            for v in p.ciudad.v.values():
                self.assertTrue(0 <= v <= 100)


if __name__ == "__main__":
    unittest.main()
