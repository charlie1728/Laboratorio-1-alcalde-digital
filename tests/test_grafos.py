"""Pruebas de los grafos y de su integración con los árboles. Ejecutar:
    python -m unittest discover -s tests -v
"""
import json
import math
import random
import unittest

from alcalde.estructuras.archivo_avl import ArchivoHechosAVL
from alcalde.estructuras.grafo import Grafo
from alcalde.modelo.mapa import CALLES, ZONAS, crear_mapa
from alcalde.modelo.partida import Partida
from alcalde.modelo.serializacion import partida_a_dict, partida_desde_dict

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

    def test_mover_usa_dijkstra(self):
        p = Partida(JUGADORES, semilla=3)
        j = p.jugador_actual
        destinos = p.destinos()
        self.assertEqual(set(destinos), set(ZONAS) - {j.zona})
        z = max(destinos, key=destinos.get)                      # la zona más lejana
        p.mover(z)
        ruta = p.ultimo_resaltado["ruta"]
        self.assertEqual(ruta, p.mapa.camino_mas_corto(ruta[0], z)[1])   # camina por la ruta más corta
        self.assertEqual(j.zona, z)
        self.assertEqual(p.red.dato(j.nombre).zona, z)
        otra = next(x for x in ZONAS if x != z)
        self.assertEqual(p.mover(otra)[0].tipo, "malo")          # una caminata por turno
        self.assertEqual(p.destinos(), {})

    def test_turno_reparte_una_publicacion(self):
        p = Partida(JUGADORES, semilla=4)
        vistas = set()
        for _ in range(8):
            caso, nodo = p.publicacion_turno()
            self.assertIsNotNone(nodo)
            self.assertNotIn(nodo.id, vistas)                    # nunca se repite
            vistas.add(nodo.id)
            antes = p.jugador_actual.puntos
            p.ejecutar("verificar", caso, nodo)
            self.assertEqual(p.jugador_actual.puntos, antes - 3)  # verificar cuesta 3 puntos
            self.assertFalse(next(a for a in p.acciones_para(nodo) if a["clave"] == "verificar")["ok"])
            p.ejecutar("ignorar", caso, nodo)
            self.assertTrue(all(not a["ok"] for a in p.acciones_para(nodo)))  # una decisión por turno
            p.terminar_turno()
            if p.evento_viral:
                p.resolver_viral(None)


class TestVerificarEnTerreno(unittest.TestCase):
    def test_verificacion_sin_datos_no_gasta_el_turno(self):
        for semilla in range(40):
            p = Partida([("Ana", "ciudadano", (0, 0, 0)), ("Beto", "influencer", (0, 0, 0))], semilla=semilla)
            caso, nodo = p.publicacion_turno()
            if nodo is None or caso.hecho.id in p.archivo:
                continue
            j = p.jugador_actual
            if j.zona == caso.hecho.lugar:
                continue
            p.ejecutar("verificar", caso, nodo)
            self.assertFalse(nodo.verificado)
            self.assertFalse(p.turno["verifico"])          # sin datos: no cuenta
            p.mover(caso.hecho.lugar)                       # va al lugar de los hechos
            p.ejecutar("verificar", caso, nodo)
            self.assertTrue(nodo.verificado)                # ahí sí se verifica
            self.assertIn(caso.hecho.id, p.archivo)         # y el hecho queda en el AVL
            return
        self.skipTest("ninguna semilla repartió un hecho que faltara en el Archivo")


class TestIntegracionArbolGrafo(unittest.TestCase):
    def test_arbol_es_el_arbol_bfs_de_la_red(self):
        for semilla in range(6):
            p = Partida(JUGADORES, semilla=semilla)
            for caso in p.casos:
                autores = []
                for n in caso.arbol.preorden():
                    if n.padre is not None:
                        # cada reenvío lo hizo un seguidor del autor del padre
                        self.assertTrue(p.red.tiene_arista(n.padre.autor, n.autor))
                    autores.append(n.autor)
                # BFS: cada ciudadano se visita una sola vez por historia
                self.assertEqual(len(autores), len(set(autores)))
                for c, nid in caso.receptores.items():
                    nodo = caso.arbol.buscar(nid)
                    if nodo is not None and nodo.autor != c:
                        self.assertTrue(p.red.tiene_arista(nodo.autor, c))
                alcance = caso.arbol.agregar(lambda n: n.alcance)[caso.arbol.raiz.id]
                self.assertEqual(alcance + 1, len(caso.receptores))   # +1: el autor de la raíz

    def test_desinformacion_sale_de_la_red(self):
        p = Partida(JUGADORES, semilla=5)
        esperado = round(100 * len(p.desinformados()) / len(p.npcs()) * 0.85)
        self.assertEqual(p.ciudad.v["desinformacion"], max(0, min(100, esperado)))

    def test_reportar_avisa_a_quien_lo_recibio(self):
        for semilla in range(10):
            p = Partida(JUGADORES, semilla=semilla)
            caso = next(c for c in p.casos if not c.arbol.raiz.es_veraz)
            antes = len(caso.creyentes_falso())
            if antes == 0:
                continue
            p.ejecutar("reportar", caso, caso.arbol.raiz)
            self.assertFalse(caso.abierto)
            self.assertEqual(len(caso.creyentes_falso()), 0)
            return
        self.fail("ninguna semilla generó creyentes")

    def test_alertar_usa_los_contactos(self):
        p = Partida(JUGADORES, semilla=2)
        caso = next(c for c in p.casos if not c.arbol.raiz.es_veraz)
        p.ejecutar("verificar", caso, caso.arbol.raiz)
        p.ejecutar("alertar", caso, caso.arbol.raiz)
        for c in p.red.contactos("Ana"):
            if p.es_npc(c):
                self.assertIn(caso.creencia.get(c), ("corregido", "veraz", "duda", None))
                self.assertNotEqual(caso.creencia.get(c), "falso")

    def test_eleccion_suma_las_zonas(self):
        p = Partida(JUGADORES, rondas=2, semilla=7)
        while not p.terminada:
            if p.evento_viral:
                p.resolver_viral(None)
            p.terminar_turno()
        e = p.eleccion
        for c, total in e["totales"].items():
            self.assertEqual(total, sum(z["votos"][c] for z in e["zonas"].values()))
        self.assertIn(e["ganador"], e["totales"])
        self.assertEqual(e["ganador"], max(e["totales"], key=e["totales"].get))


class TestSerializacion(unittest.TestCase):
    def test_avl_desde_preorden_conserva_la_forma(self):
        avl = ArchivoHechosAVL()
        rng = random.Random(4)
        for k in rng.sample(range(1000), 40):
            avl.insertar(f"k{k:03d}", k)
        copia = ArchivoHechosAVL.desde_preorden(list(avl.preorden()), lambda k: int(k[1:]))
        self.assertEqual(list(copia.preorden()), list(avl.preorden()))
        self.assertTrue(copia.es_avl_valido())
        self.assertEqual(len(copia), len(avl))

    def test_partida_ida_y_vuelta(self):
        p = Partida(JUGADORES, semilla=11)
        for _ in range(5):
            p.terminar_turno()
            if p.evento_viral:
                p.resolver_viral("verificar")
        texto = json.dumps(partida_a_dict(p))
        q = partida_desde_dict(json.loads(texto))
        self.assertEqual(q.ciudad.v, p.ciudad.v)
        self.assertEqual(q.red.num_aristas(), p.red.num_aristas())
        self.assertEqual(list(q.archivo.preorden()), list(p.archivo.preorden()))
        for a, b in zip(p.casos_abiertos(), q.casos_abiertos()):
            self.assertEqual([n.id for n in a.arbol.preorden()], [n.id for n in b.arbol.preorden()])
            self.assertEqual(a.arbol.estadisticas(), b.arbol.estadisticas())
            na, nb = a.arbol.raiz, b.arbol.raiz
            self.assertEqual([x["ok"] for x in p.acciones_para(na)], [x["ok"] for x in q.acciones_para(nb)])
        self.assertEqual(q.desinformados(), p.desinformados())
        self.assertEqual(q.total_mensajes(), p.total_mensajes())


if __name__ == "__main__":
    unittest.main()
