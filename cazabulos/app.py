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
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.op.get("pantalla_completa") else 0)
        try:
            self.pantalla = pygame.display.set_mode((ANCHO, ALTO), flags)
        except pygame.error:
            self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
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

    def _cuadro(self, dt, velo):
        for e in self._eventos():
            if e.type in TOQUES:
                self.quieto = 0.0
            if e.type == pygame.QUIT:
                self.corriendo = False
            elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
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
            pygame.display.flip()
        if self.red:
            self.red.cerrar()
        pygame.quit()
