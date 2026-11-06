"""La aplicación: ventana, bucle principal y cambio entre pantallas."""
import time
import traceback
from pathlib import Path

import pygame

from .config import ALTO, ANCHO, ASSETS, FPS, TITULO
from .guardado import Logros, Records, cargar_opciones, guardar_opciones
from .mando import EVENTOS as EVENTOS_MANDO
from .mando import Mandos
from .sonido import Sonido

REGISTRO = Path(__file__).resolve().parent.parent / "cazabulos_error.log"
INACTIVIDAD = 90          # segundos sin tocar nada para volver solo al inicio (modo feria)
TOQUES = (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL, pygame.JOYBUTTONDOWN)


def _nombre_en_windows():
    """En Windows la barra de tareas agrupa por programa: sin esto muestra el ícono de Python.
    Con un identificador propio muestra el ícono del juego."""
    import sys
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Uninorte.Cazabulos.AlcaldeDigital")
        except (AttributeError, OSError):
            pass


class App:
    def __init__(self, semilla=None):
        _nombre_en_windows()
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption(TITULO)
        self._icono()                       # antes de abrir la ventana, para que Windows lo tome
        self.op = cargar_opciones()
        # El juego se dibuja siempre en un lienzo de 1280x720 y, al final de cada cuadro, se estira al
        # tamaño exacto de la ventana: así llena la ventana grande sin franjas negras a los lados.
        try:
            pygame.display.set_mode((ANCHO, ALTO), pygame.RESIZABLE)
        except pygame.error:
            pygame.display.set_mode((ANCHO, ALTO))
        self.pantalla = pygame.Surface((ANCHO, ALTO)).convert()
        try:
            from pygame._sdl2.video import Window
            self.ventana = Window.from_display_module()
        except Exception:
            self.ventana = None
        self.poner_pantalla(self.op.get("pantalla_completa", False))
        self.reloj = pygame.time.Clock()
        self.son = Sonido()
        self.aplicar_volumen()
        self.records = Records()
        self.logros = Logros()
        self.semilla = semilla
        self.corriendo = True
        self.siguiente = None
        self.fundido = 0.0
        self.red = None            # conexión en línea activa (si hay)
        self.mando = Mandos()      # controles USB (si hay alguno conectado)
        self.quieto = 0.0          # segundos sin que nadie toque nada
        # el puntero del mouse empieza escondido: solo aparece si alguien mueve el mouse de verdad
        # (en pantalla completa quedaba encima de un botón y lo seleccionaba solo)
        self.t_inicio = time.monotonic()
        self.recorrido_raton = 0.0
        pygame.mouse.set_visible(False)
        from .pantallas.menu import Titulo
        self.escena = Titulo(self)
        self.escena.al_entrar()

    def _icono(self):
        """El Bulo con corona (cazabulos/assets/icono32.png), agrandado sin difuminar."""
        try:
            ico = pygame.image.load(str(ASSETS / "icono32.png"))
            pygame.display.set_icon(pygame.transform.scale(ico, (64, 64)))
        except (pygame.error, FileNotFoundError):
            pass

    def poner_pantalla(self, completa):
        """Ventana grande (maximizada: se ven la barra de título y la de tareas) o pantalla completa.
        La pantalla completa es "de escritorio" (no cambia la resolución del monitor): así, al volver a
        la ventana con F11, no queda pegada en el fondo la imagen vieja del juego."""
        self.op["pantalla_completa"] = bool(completa)
        w = self.ventana
        try:
            if w is None:
                if bool(completa) != bool(pygame.display.is_fullscreen()):
                    pygame.display.toggle_fullscreen()
            elif completa:
                w.set_fullscreen(desktop=True)
            else:
                w.set_windowed()
                w.maximize()
        except (pygame.error, AttributeError):
            pass
        self.pantalla.fill((16, 10, 36))
        self._presentar()

    def _presentar(self):
        """Muestra el lienzo del juego estirado al tamaño de la ventana (sin franjas negras)."""
        ventana = pygame.display.get_surface()
        if ventana is None:
            return
        if ventana.get_size() == (ANCHO, ALTO):
            ventana.blit(self.pantalla, (0, 0))
        else:
            pygame.transform.scale(self.pantalla, ventana.get_size(), ventana)
        pygame.display.flip()

    def _al_lienzo(self, e):
        """El mouse se mueve en la ventana estirada: su posición se pasa a la del lienzo de 1280x720."""
        ventana = pygame.display.get_surface()
        w, h = ventana.get_size() if ventana else (ANCHO, ALTO)
        if (w, h) == (ANCHO, ALTO) or not hasattr(e, "pos"):
            return e
        fx, fy = ANCHO / w, ALTO / h
        datos = dict(e.dict)
        datos["pos"] = (int(e.pos[0] * fx), int(e.pos[1] * fy))
        if "rel" in datos:
            datos["rel"] = (round(e.rel[0] * fx), round(e.rel[1] * fy))
        return pygame.event.Event(e.type, datos)

    def aplicar_volumen(self):
        self.son.vol_efectos = self.op["efectos"]
        self.son.volumen_musica(self.op["musica"])

    def guardar_opciones(self):
        guardar_opciones(self.op)

    def cambiar(self, escena):
        """Cambia de pantalla con un fundido corto."""
        self.siguiente = escena
        self.fundido = 0.0
        self.quieto = 0.0

    def _eventos(self):
        """Los eventos de la ventana, con los del control USB convertidos en teclas."""
        for e in pygame.event.get():
            if e.type in EVENTOS_MANDO:
                yield from self.mando.traducir(e, getattr(self.escena, "mando_juego", False))
                if e.type == pygame.JOYBUTTONDOWN:
                    self.quieto = 0.0
            elif e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                yield self._al_lienzo(e)
            else:
                if e.type == pygame.KEYDOWN:
                    self.mando.usado = False         # tocaron el teclado: las ayudas vuelven a mostrar teclas
                yield e

    def _revisar_inactividad(self, dt):
        """En la feria un niño puede irse a mitad de pantalla: tras un rato sin tocar nada se vuelve al inicio."""
        self.quieto += dt
        limite = getattr(self.escena, "inactividad", INACTIVIDAD)
        if (limite and self.quieto > limite and self.op.get("volver_inicio", True)
                and self.red is None and self.siguiente is None):
            from .pantallas.menu import Titulo
            self.cambiar(Titulo(self))

    def _raton(self, e):
        """Muestra el puntero solo cuando se usa el mouse y lo esconde al usar el teclado o el control."""
        if e.type == pygame.MOUSEMOTION:
            if time.monotonic() - self.t_inicio < 1.0:     # el movimiento falso que llega al abrir la ventana
                return
            self.recorrido_raton += abs(e.rel[0]) + abs(e.rel[1])
            if self.recorrido_raton > 8 and not pygame.mouse.get_visible():
                pygame.mouse.set_visible(True)
        elif e.type == pygame.MOUSEBUTTONDOWN:
            pygame.mouse.set_visible(True)
        elif e.type == pygame.KEYDOWN:
            self.recorrido_raton = 0.0
            if pygame.mouse.get_visible():
                pygame.mouse.set_visible(False)

    def _cuadro(self, dt, velo):
        for e in self._eventos():
            self._raton(e)
            if e.type in TOQUES:
                self.quieto = 0.0
            if e.type == pygame.QUIT:
                self.corriendo = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                self.poner_pantalla(not self.op.get("pantalla_completa", False))
                self.guardar_opciones()
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_m and getattr(self.escena, "permite_mute", True):
                self.op["musica"] = 0.0 if self.op["musica"] > 0 else 0.45
                self.aplicar_volumen()
                self.guardar_opciones()
            elif self.siguiente is None:
                self.escena.evento(e)
        if self.escena.musica and self.op["musica"] > 0:
            self.son.musica_on()
        elif not self.escena.musica:
            self.son.musica_off()
        self._revisar_inactividad(dt)
        self.escena.actualizar(dt)
        self.escena.dibujar(self.pantalla)
        if self.siguiente is not None:
            self.fundido += dt / 0.18
            velo.set_alpha(int(255 * min(1.0, self.fundido)))
            self.pantalla.blit(velo, (0, 0))
            if self.fundido >= 1.0:
                self.escena = self.siguiente
                self.siguiente = None
                self.fundido = 1.0
                self.escena.al_entrar()
        elif self.fundido > 0:
            self.fundido -= dt / 0.18
            velo.set_alpha(int(255 * max(0.0, self.fundido)))
            self.pantalla.blit(velo, (0, 0))

    def _rescatar(self):
        """Si una pantalla falla, se anota el error y se vuelve al inicio en vez de cerrar el juego.
        En la feria no hay nadie mirando la consola: mejor seguir jugando y revisar el registro después."""
        try:
            with open(REGISTRO, "a", encoding="utf-8") as f:
                f.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')} en {type(self.escena).__name__}\n")
                f.write(traceback.format_exc() + "\n")
        except OSError:
            pass
        if self.red:
            try:
                self.red.cerrar()
            except Exception:
                pass
            self.red = None
        from .pantallas.menu import Titulo
        self.escena = Titulo(self)
        self.siguiente = None
        self.fundido = 1.0
        self.quieto = 0.0
        self.escena.al_entrar()

    def ejecutar(self):
        from .pantallas.menu import Titulo
        velo = pygame.Surface((ANCHO, ALTO))
        velo.fill((16, 10, 36))
        fallos = []
        while self.corriendo:
            dt = min(self.reloj.tick(FPS) / 1000.0, 0.1)      # si la ventana se congela un rato, no saltar de golpe
            try:
                self._cuadro(dt, velo)
            except Exception:
                ahora = time.monotonic()
                fallos = [t for t in fallos if ahora - t < 30] + [ahora]
                # si falla el inicio o falla seguido, no hay a dónde volver: main.py muestra el error
                if isinstance(self.escena, Titulo) or len(fallos) >= 3:
                    raise
                self._rescatar()
            self._presentar()
        if self.red:
            self.red.cerrar()
        pygame.quit()
