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

    def test_el_puntero_no_selecciona_botones_solo(self):
        import time
        from cazabulos.pantallas.menu import Titulo
        app = self.app
        pygame.mouse.set_visible(False)
        titulo = Titulo(app)
        app.escena = titulo
        boton = titulo.botones.rects[5]
        quieto = E(pygame.MOUSEMOTION, pos=boton.center, rel=(640, 360), buttons=(0, 0, 0))
        app.t_inicio = time.monotonic()                 # recién abierta la ventana
        app._raton(quieto)
        titulo.evento(quieto)
        self.assertFalse(pygame.mouse.get_visible())
        self.assertEqual(titulo.botones.sel, 0)          # sigue en "¡Jugar ya!"
        app.t_inicio = time.monotonic() - 5
        movido = E(pygame.MOUSEMOTION, pos=boton.center, rel=(12, 3), buttons=(0, 0, 0))
        app._raton(movido)
        titulo.evento(movido)
        self.assertTrue(pygame.mouse.get_visible())
        self.assertEqual(titulo.botones.sel, 5)          # ahora sí lo movieron a propósito
        app._raton(E(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode="", scancode=0))
        self.assertFalse(pygame.mouse.get_visible())

    def test_jugando_solo_no_muestra_tabla_de_una_fila(self):
        from cazabulos.mundo import Mundo
        from cazabulos.pantallas.final import Eleccion, ResultadoTurno, TablaRonda
        from cazabulos.partida import Partida
        res = Mundo(3, "caro", duracion=1, pistas=False).resumen()
        for jugadores, esperado in ((1, Eleccion), (2, TablaRonda)):
            js = [{"clave": c, "piel": None, "pelo": None, "nombre": c} for c in ("caro", "beto")[:jugadores]]
            pa = Partida(js, 1, 90, semilla=3)
            pa.paso = jugadores - 1                       # ya jugó el último turno de la ronda
            pa.guardar(pa.actual, res)
            self.app.siguiente = None
            ResultadoTurno(self.app, pa, pa.actual, res)._seguir()
            self.assertIsInstance(self.app.siguiente, esperado)

    def test_salir_pregunta_antes(self):
        from cazabulos.pantallas.menu import Titulo
        titulo = Titulo(self.app)
        self.app.corriendo = True
        titulo._salir()
        self.assertTrue(self.app.corriendo)                         # todavía no se cierra
        aceptar = E(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode="", scancode=0)
        titulo.evento(aceptar)                                      # la opción marcada es "No, seguir aquí"
        self.assertTrue(self.app.corriendo)
        self.assertIsNone(titulo.confirmar)
        titulo._salir()
        titulo.evento(E(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode="", scancode=0))
        titulo.evento(aceptar)
        self.assertFalse(self.app.corriendo)
        self.app.corriendo = True

    def test_las_opciones_viejas_pasan_a_ventana_grande(self):
        import json
        (guardado.DATOS / "opciones.json").write_text(json.dumps({"pantalla_completa": True, "version": 2}),
                                                       encoding="utf-8")
        op = guardado.cargar_opciones()
        self.assertFalse(op["pantalla_completa"])
        self.assertEqual(op["version"], guardado.VERSION_OPCIONES)
        (guardado.DATOS / "opciones.json").write_text(json.dumps({"pantalla_completa": True, "version": 3}),
                                                       encoding="utf-8")
        self.assertTrue(guardado.cargar_opciones()["pantalla_completa"])      # si la eligió después, se respeta
        (guardado.DATOS / "opciones.json").unlink()

    def test_el_mouse_apunta_bien_en_la_ventana_estirada(self):
        pygame.display.set_mode((1920, 1009))                       # como la ventana grande de 1920x1080
        try:
            clic = self.app._al_lienzo(E(pygame.MOUSEBUTTONDOWN, pos=(960, 1008), button=1))
            self.assertEqual(clic.pos, (640, 719))                   # el mismo punto en el lienzo de 1280x720
            movido = self.app._al_lienzo(E(pygame.MOUSEMOTION, pos=(1919, 0), rel=(30, 14), buttons=(0, 0, 0)))
            self.assertEqual(movido.pos, (1279, 0))
            self.assertEqual(movido.rel, (20, 10))
            self.app._presentar()                                   # el lienzo se estira sin errores
        finally:
            pygame.display.set_mode((1280, 720))

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
