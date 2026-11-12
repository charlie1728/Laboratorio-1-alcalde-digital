"""Pruebas de los gráficos: bordes, la vida del barrio (palomas, agua, noche) y que nada de eso cambie
el juego ni haga crecer la memoria."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

pygame.init()
if pygame.display.get_surface() is None:
    pygame.display.set_mode((1, 1))

from cazabulos import recursos, sprites  # noqa: E402
from cazabulos.ambiente import Ambiente  # noqa: E402
from cazabulos.config import ALTO, ANCHO  # noqa: E402
from cazabulos.mundo import Mundo  # noqa: E402
from cazabulos.recursos import CONTORNO, borde  # noqa: E402

PASTO = (64, 156, 98)


def estado(m):
    """Lo que importa del juego: dónde está cada quien, quién está morado y los puntos."""
    return ([(n, round(v.x, 3), round(v.y, 3), v.bulo) for n, v in sorted(m.vecinos.items())],
            sorted((b.id, round(b.x, 3), round(b.y, 3), b.estado) for b in m.bulos.values()),
            m.jugador.puntos, dict(m.jugador.stats), round(m.jugador.x, 3), round(m.jugador.y, 3))


class TestBordes(unittest.TestCase):
    def test_todo_tiene_un_borde_oscuro_de_un_pixel(self):
        img = sprites.estrella()
        con = borde(img)
        self.assertEqual(con.get_size(), (img.get_width() + 2, img.get_height() + 2))
        # justo afuera de la punta de la estrella queda el borde oscuro
        punta = min(y for y in range(img.get_height()) for x in range(img.get_width()) if img.get_at((x, y))[3] > 40)
        xs = [x for x in range(img.get_width()) if img.get_at((x, punta))[3] > 40]
        self.assertEqual(tuple(con.get_at((xs[0] + 1, punta))[:3]), CONTORNO)
        self.assertIs(borde(img), con)          # se hace una sola vez

    def test_arboles_y_arbustos_se_distinguen_del_pasto(self):
        from cazabulos.mapa import VERDE_PASTO, Mapa, tile_cosa
        m = Mapa()
        for img, x, yb, tipo in m.props:
            if tipo == "arbol":
                colores = {tuple(img.get_at((i, j)))[:3] for i in range(img.get_width()) for j in range(img.get_height())
                           if img.get_at((i, j))[3] > 0}
                self.assertNotIn(PASTO, colores)
        for t in VERDE_PASTO:
            img = tile_cosa(t)
            self.assertFalse(any(tuple(img.get_at((i, j)))[:3] == PASTO and img.get_at((i, j))[3] > 0
                                 for i in range(16) for j in range(16)))
        # los árboles del mismo tipo comparten la imagen (así las cachés no se llenan)
        arboles = [img for img, *_, tipo in m.props if tipo == "arbol"]
        self.assertLessEqual(len({id(a) for a in arboles}), 6)


class TestBarrioVivo(unittest.TestCase):
    def setUp(self):
        self.m = Mundo(4, "caro", duracion=90)
        self.amb = Ambiente(self.m.mapa, ronda=1)
        self.todo = pygame.Rect(0, 0, 10 ** 5, 10 ** 5)

    def test_las_palomas_salen_volando_si_pasas_cerca(self):
        p = self.amb.palomas[0]
        x0, y0 = p["x"], p["y"]
        self.m.jugador.x, self.m.jugador.y = x0 + 10, y0
        self.amb.actualizar(1 / 60, self.m, self.todo)
        self.assertTrue(p["vuela"])
        self.m.jugador.x, self.m.jugador.y = 0, 0          # el jugador se va
        for _ in range(60 * 8):
            self.amb.actualizar(1 / 60, self.m, self.todo)
        self.assertFalse(p["vuela"])                       # y se posa en otro lado de la plaza
        self.assertEqual(p["alto"], 0.0)
        self.assertGreater(((p["x"] - x0) ** 2 + (p["y"] - y0) ** 2) ** 0.5, 20)
        self.assertTrue(self.m.mapa.libre(pygame.Rect(int(p["x"]) - 3, int(p["y"]) - 2, 6, 3)))

    def test_la_fuente_y_la_laguna_se_mueven(self):
        for _ in range(60):
            self.amb.actualizar(1 / 60, self.m, self.todo)
        self.assertTrue(self.amb.gotas)
        antes = (self.amb.pata["x"], self.amb.pata["y"])
        for _ in range(120):
            self.amb.actualizar(1 / 60, self.m, self.todo)
        self.assertNotEqual(antes, (self.amb.pata["x"], self.amb.pata["y"]))
        self.assertTrue(self.amb.mapa.agua[0].inflate(4, 4).collidepoint(self.amb.pata["x"], self.amb.pata["y"]))

    def test_de_noche_hay_luciernagas_y_no_nubes(self):
        noche = Ambiente(self.m.mapa, ronda=3)
        self.assertTrue(noche.de_noche and noche.luciernagas)
        self.assertFalse(self.amb.de_noche or self.amb.luciernagas)

    def test_la_hierba_alta_se_abre_y_suelta_hojitas(self):
        hierba = self.amb.hierba
        self.assertGreater(len(hierba.matas), 20)
        tx, ty = sorted(hierba.matas)[0]
        x, y = tx * 16 + 8, ty * 16 + 12
        hierba.actualizar(1 / 60, [("yo", x - 40, y)])          # todavía afuera
        self.assertFalse(hierba.hojitas)
        hierba.actualizar(1 / 60, [("yo", x, y)])               # entra
        self.assertTrue(hierba.matas[(tx, ty)]["dentro"])
        self.assertTrue(hierba.hojitas)
        n = len(hierba.hojitas)
        hierba.actualizar(1 / 60, [("yo", x + 1, y)])           # sigue adentro: no suelta más
        self.assertEqual(len(hierba.hojitas), n)
        hierba.actualizar(1 / 60, [("yo", x - 40, y)])          # sale: tiembla un rato y se calma
        self.assertFalse(hierba.matas[(tx, ty)]["dentro"])
        self.assertGreater(hierba.matas[(tx, ty)]["agitada"], 0)
        for _ in range(90):
            hierba.actualizar(1 / 60, [])
        self.assertEqual(hierba.matas[(tx, ty)]["agitada"], 0)
        self.assertFalse(hierba.hojitas)
        # nunca está en un camino ni encima de un objeto
        for tx, ty in hierba.matas:
            self.assertEqual(self.m.mapa.suelo[ty][tx], "g")
            self.assertIsNone(self.m.mapa.capa[ty][tx])


class TestSuelo(unittest.TestCase):
    def test_suelo_con_texturas_y_laguna_redondeada(self):
        from cazabulos.mapa import Mapa
        m = Mapa()
        # el pasto ya no es un tile repetido de tres colores: tiene varios verdes, hojitas y florecitas
        pasto = [(tx, ty) for ty in range(26, 45) for tx in range(1, 41) if m.suelo[ty][tx] == "g"][:30]
        colores = set()
        for tx, ty in pasto:
            tile = m.superficie.subsurface((tx * 16, ty * 16, 16, 16))
            colores |= {tuple(tile.get_at((x, y)))[:3] for x in range(16) for y in range(16)}
        self.assertGreater(len(colores), 8)
        # la laguna tiene agua, orilla de piedras y queda dentro de sus tiles (que son sólidos)
        e = m.estanque
        self.assertIsNotNone(e)
        self.assertTrue(e["agua"].any() and e["piedra"].any())
        r = m.agua[0]
        for x, y in (r.topleft, r.bottomright, r.center):
            self.assertEqual(m.suelo[y // 16][x // 16], "w")

    def test_sin_numpy_se_dibuja_como_antes(self):
        import cazabulos.mapa as mapa_mod
        guardado = mapa_mod.texturas
        mapa_mod.texturas = None
        try:
            m = mapa_mod.Mapa()
            self.assertIsNone(m.estanque)
            amb = Ambiente(m, ronda=1)
            self.assertEqual(amb.agua_cuadros, [])
            amb.actualizar(1 / 60, Mundo(4, "caro", duracion=90), pygame.Rect(0, 0, 10 ** 5, 10 ** 5))
        finally:
            mapa_mod.texturas = guardado


class TestBrillo(unittest.TestCase):
    def test_el_brillo_se_apaga_si_el_computador_va_lento(self):
        from cazabulos.render import Render
        pant = pygame.Surface((ANCHO, ALTO))
        r = Render(Mundo(3, "beto", duracion=90), None, {})
        self.assertTrue(r.bloom)
        r.t = 5.0
        r.lentos = 25.0                                         # muchos cuadros lentos, pero no seguidos
        r.dibujar(pant)
        r.dibujar(pant)
        self.assertTrue(r.bloom)                                # un tirón suelto no lo apaga
        r.lentos = 45.0                                         # lento de verdad, un buen rato
        r.dibujar(pant)
        self.assertFalse(r.bloom)
        self.assertFalse(Render(Mundo(3, "beto", duracion=90), None, {"demo": True}).bloom)


class TestNoCambiaElJuego(unittest.TestCase):
    def test_los_graficos_no_cambian_el_juego(self):
        """Con o sin dibujar, la misma semilla da exactamente el mismo partido."""
        from cazabulos.render import Render
        pant = pygame.Surface((ANCHO, ALTO))
        a, b = Mundo(21, "ana", duracion=90), Mundo(21, "ana", duracion=90)
        r = Render(a, None, {})
        for k in range(60 * 12):
            # camina y lanza en distintas direcciones (así también hay polvo, palomas y estelas)
            ent = [{"der": True, "accion": True}, {"abajo": True}, {"izq": True, "accion": True},
                   {"arriba": True}][(k // 90) % 4]
            a.actualizar(1 / 60, ent)
            r.actualizar(1 / 60)
            if k % 6 == 0:
                r.dibujar(pant)
            b.actualizar(1 / 60, ent)
            b.fx.clear()
        self.assertEqual(estado(a), estado(b))


class TestMemoria(unittest.TestCase):
    def test_las_imagenes_no_se_acumulan_en_cada_cuadro(self):
        # el Bulo gigante y el que viaja por los hilos son siempre las mismas imágenes
        self.assertIs(sprites.bulo_gigante(0.0), sprites.bulo_gigante(0.1))
        self.assertIs(sprites.bulo_chico(1, False), sprites.bulo_chico(1, False))
        from cazabulos import personajes
        self.assertIs(personajes.retrato("ana"), personajes.retrato("ana"))
        # la tabla de récords dibujada muchas veces no llena la caché
        import cazabulos.guardado as guardado
        with tempfile.TemporaryDirectory() as tmp:
            viejo = guardado.DATOS
            guardado.DATOS = Path(tmp)
            try:
                from cazabulos.app import App
                from cazabulos.pantallas.menu import RecordsPantalla
                app = App(semilla=2)
                for n, c in (("ANA", "ana"), ("BETO", "beto"), ("CARO", "caro")):
                    app.records.agregar(n, c, 500, 10)
                app.escena = RecordsPantalla(app)
                for _ in range(5):
                    app.escena.dibujar(app.pantalla)
                antes = len(recursos._escaladas)
                for _ in range(200):
                    app.escena.dibujar(app.pantalla)
                self.assertEqual(len(recursos._escaladas), antes)
            finally:
                guardado.DATOS = viejo


if __name__ == "__main__":
    unittest.main()


class TestPoderes(unittest.TestCase):
    def _usar(self, clave):
        from cazabulos.render import Render
        m = Mundo(5, clave, duracion=90)
        m.antenas.clear()
        m.t_antena = 1e9
        m.guion.clear()
        for v in m.vecinos.values():
            v.espera = 1e9
        j = m.jugador
        j.x, j.y = 27 * 16, 15.5 * 16
        for dx, dy in ((-60, -30), (50, -40), (70, 30)):
            m.nuevo_bulo(j.x + dx, j.y + dy)
        cerca = sorted(m.vecinos.values(), key=lambda v: (v.x - j.x) ** 2 + (v.y - j.y) ** 2)[:3]
        for k, v in enumerate(cerca):
            v.x, v.y = j.x + (-90, 50, 95)[k], j.y + (20, -50, 25)[k]
        r = Render(m, None, {})
        r.actualizar(1 / 60)
        j.carga = 100
        m.actualizar(1 / 60, {"poder": True})
        r.actualizar(1 / 60)
        r.al_usar = {"poderes": [p["clave"] for p in r.poderes], "viajes": len(r.viajes), "empujados": len(r.empujados)}
        pant = pygame.Surface((ANCHO, ALTO))
        for _ in range(30):                         # se dibuja sin fallar mientras dura
            m.actualizar(1 / 60, {})
            r.actualizar(1 / 60)
            r.dibujar(pant)
        return m, r

    def test_cada_poder_se_ve_distinto(self):
        m, r = self._usar("ana")
        self.assertEqual(r.al_usar["poderes"], ["ana"])
        self.assertTrue(any(b.congelado > 0 for b in m.bulos.values()))
        m, r = self._usar("beto")
        self.assertEqual(r.al_usar["poderes"], ["beto"])
        self.assertGreaterEqual(r.al_usar["viajes"], 3)                 # un corazón por cada vecino protegido
        self.assertTrue(r.burbujas)                                     # y al llegar, la burbuja dorada
        m, r = self._usar("caro")
        self.assertEqual(r.al_usar["poderes"], ["caro"])
        m, r = self._usar("dani")
        self.assertEqual(r.al_usar["poderes"], ["dani"])
        self.assertGreaterEqual(r.al_usar["empujados"], 1)              # estela en los Bulos que empujó
        for _ in range(90):                         # al terminar no queda nada colgado
            r.actualizar(1 / 60)
        self.assertFalse(r.poderes or r.viajes or r.burbujas or r.empujados)
