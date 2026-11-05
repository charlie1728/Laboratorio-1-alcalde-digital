"""Pruebas del control USB (se traduce a teclas) y del regreso solo al inicio en la feria."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

pygame.init()

import cazabulos.guardado as guardado  # noqa: E402
from cazabulos.mando import Mandos  # noqa: E402

E = pygame.event.Event


def teclas(eventos):
    return [(ev.type, ev.key) for ev in eventos]


class TestMando(unittest.TestCase):
    def setUp(self):
        self.m = Mandos()

    def test_botones_cambian_segun_la_pantalla(self):
        a = E(pygame.JOYBUTTONDOWN, button=0, instance_id=0, joy=0)
        b = E(pygame.JOYBUTTONDOWN, button=1, instance_id=0, joy=0)
        start = E(pygame.JOYBUTTONDOWN, button=7, instance_id=0, joy=0)
        self.assertEqual(teclas(self.m.traducir(a, en_juego=True)), [(pygame.KEYDOWN, pygame.K_SPACE)])
        self.assertEqual(teclas(self.m.traducir(b, en_juego=True)), [(pygame.KEYDOWN, pygame.K_x)])
        self.assertEqual(teclas(self.m.traducir(b, en_juego=False)), [(pygame.KEYDOWN, pygame.K_ESCAPE)])
        self.assertEqual(teclas(self.m.traducir(start, en_juego=True)), [(pygame.KEYDOWN, pygame.K_ESCAPE)])
        self.assertEqual(teclas(self.m.traducir(start, en_juego=False)), [(pygame.KEYDOWN, pygame.K_RETURN)])

    def test_a_sostenido_sirve_para_lanzar(self):
        self.m.traducir(E(pygame.JOYBUTTONDOWN, button=0, instance_id=0, joy=0))
        self.assertTrue(self.m.estado()["accion"])
        self.m.traducir(E(pygame.JOYBUTTONUP, button=0, instance_id=0, joy=0))
        self.assertFalse(self.m.estado()["accion"])

    def test_cruceta_presiona_y_suelta_flechas(self):
        sal = self.m.traducir(E(pygame.JOYHATMOTION, hat=0, value=(1, 1), instance_id=0, joy=0))
        self.assertEqual(sorted(teclas(sal)), sorted([(pygame.KEYDOWN, pygame.K_RIGHT), (pygame.KEYDOWN, pygame.K_UP)]))
        self.assertTrue(self.m.estado()["der"] and self.m.estado()["arriba"])
        sal = self.m.traducir(E(pygame.JOYHATMOTION, hat=0, value=(0, 1), instance_id=0, joy=0))
        self.assertEqual(teclas(sal), [(pygame.KEYUP, pygame.K_RIGHT)])

    def test_palanca_con_margen_para_que_no_tiemble(self):
        eje = lambda v: E(pygame.JOYAXISMOTION, axis=0, value=v, instance_id=0, joy=0)  # noqa: E731
        self.assertEqual(self.m.traducir(eje(0.3)), [])                       # poquito: nada
        self.assertEqual(teclas(self.m.traducir(eje(0.8))), [(pygame.KEYDOWN, pygame.K_RIGHT)])
        self.assertEqual(self.m.traducir(eje(0.45)), [])                      # sigue presionada
        self.assertEqual(teclas(self.m.traducir(eje(0.1))), [(pygame.KEYUP, pygame.K_RIGHT)])
        self.assertEqual(teclas(self.m.traducir(eje(-0.9))), [(pygame.KEYDOWN, pygame.K_LEFT)])

    def test_cruceta_y_palanca_juntas_no_repiten_tecla(self):
        self.m.traducir(E(pygame.JOYHATMOTION, hat=0, value=(1, 0), instance_id=0, joy=0))
        sal = self.m.traducir(E(pygame.JOYAXISMOTION, axis=0, value=0.9, instance_id=0, joy=0))
        self.assertEqual(sal, [])
        self.assertTrue(self.m.estado()["der"])

    def test_desconectar_suelta_todo(self):
        self.m.traducir(E(pygame.JOYHATMOTION, hat=0, value=(-1, 0), instance_id=0, joy=0))
        self.m.traducir(E(pygame.JOYBUTTONDOWN, button=0, instance_id=0, joy=0))
        self.m.traducir(E(pygame.JOYDEVICEREMOVED, instance_id=0))
        self.assertFalse(any(self.m.estado().values()))


class TestFeria(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        guardado.DATOS = Path(cls.tmp.name)
        from cazabulos.app import App
        cls.app = App(semilla=5)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.app.siguiente = None
        self.app.red = None
        self.app.op["volver_inicio"] = True

    def test_sin_tocar_nada_vuelve_al_inicio(self):
        from cazabulos.pantallas.menu import RecordsPantalla, Titulo
        self.app.escena = RecordsPantalla(self.app)
        self.app.quieto = 0.0
        self.app._revisar_inactividad(30)
        self.assertIsNone(self.app.siguiente)
        self.app._revisar_inactividad(61)
        self.assertIsInstance(self.app.siguiente, Titulo)

    def test_no_interrumpe_el_juego_ni_el_inicio_ni_en_linea(self):
        from cazabulos.pantallas.juego import PantallaJuego
        from cazabulos.pantallas.menu import RecordsPantalla, Titulo
        from cazabulos.partida import Partida
        pa = Partida([{"clave": "ana", "piel": None, "pelo": None, "nombre": "Ana"}], 1, 60, semilla=3)
        for escena in (PantallaJuego(self.app, pa), Titulo(self.app)):
            self.app.escena = escena
            self.app.quieto = 0.0
            self.app._revisar_inactividad(500)
            self.assertIsNone(self.app.siguiente)
        self.app.escena = RecordsPantalla(self.app)
        self.app.red = object()
        self.app.quieto = 0.0
        self.app._revisar_inactividad(500)
        self.assertIsNone(self.app.siguiente)
        self.app.red = None
        self.app.op["volver_inicio"] = False
        self.app._revisar_inactividad(500)
        self.assertIsNone(self.app.siguiente)

    def test_las_ayudas_siguen_a_lo_ultimo_que_se_toco(self):
        mando = self.app.mando
        mando.palancas[99] = object()                 # finge un control conectado
        try:
            pygame.event.clear()
            pygame.event.post(E(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, unicode="", scancode=0))
            list(self.app._eventos())
            self.assertFalse(mando.en_uso)
            pygame.event.post(E(pygame.JOYBUTTONDOWN, button=0, instance_id=99, joy=0))
            salida = list(self.app._eventos())
            self.assertTrue(mando.en_uso)
            self.assertEqual([(ev.type, ev.key) for ev in salida], [(pygame.KEYDOWN, pygame.K_SPACE)])
        finally:
            mando.palancas.pop(99, None)
            mando.boton_a = False

    def test_si_una_pantalla_falla_vuelve_al_inicio_y_lo_anota(self):
        import cazabulos.app as modulo
        from cazabulos.pantallas.menu import RecordsPantalla, Titulo
        registro = Path(self.tmp.name) / "error.log"
        antes, modulo.REGISTRO = modulo.REGISTRO, registro
        try:
            self.app.escena = RecordsPantalla(self.app)
            try:
                raise ValueError("falla de prueba")
            except ValueError:
                self.app._rescatar()
            self.assertIsInstance(self.app.escena, Titulo)
            texto = registro.read_text(encoding="utf-8")
            self.assertIn("RecordsPantalla", texto)
            self.assertIn("falla de prueba", texto)
        finally:
            modulo.REGISTRO = antes

    def test_el_control_mueve_al_jugador(self):
        from cazabulos.pantallas.juego import PantallaJuego
        from cazabulos.partida import Partida
        pa = Partida([{"clave": "beto", "piel": None, "pelo": None, "nombre": "Beto"}], 1, 60, semilla=3)
        juego = PantallaJuego(self.app, pa)
        juego.estado = "juego"
        self.app.mando.traducir(E(pygame.JOYHATMOTION, hat=0, value=(1, 0), instance_id=0, joy=0))
        try:
            x0 = juego.m.jugador.x
            for _ in range(30):
                juego.actualizar(1 / 60)
            self.assertGreater(juego.m.jugador.x, x0 + 10)
        finally:
            self.app.mando.traducir(E(pygame.JOYHATMOTION, hat=0, value=(0, 0), instance_id=0, joy=0))


if __name__ == "__main__":
    unittest.main()
