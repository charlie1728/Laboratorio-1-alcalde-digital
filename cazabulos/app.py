"""La aplicación: ventana, bucle principal y cambio entre pantallas."""
import pygame

from .config import ALTO, ANCHO, FPS, TITULO
from .guardado import Logros, Records, cargar_opciones, guardar_opciones
from .sonido import Sonido


class App:
    def __init__(self, semilla=None):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption(TITULO)
        self.op = cargar_opciones()
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.op.get("pantalla_completa") else 0)
        try:
            self.pantalla = pygame.display.set_mode((ANCHO, ALTO), flags)
        except pygame.error:
            self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        self._icono()
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
        from .pantallas.menu import Titulo
        self.escena = Titulo(self)
        self.escena.al_entrar()

    def _icono(self):
        try:
            from .personajes import retrato
            img = pygame.transform.scale(retrato("caro"), (32, 28))
            ico = pygame.Surface((32, 32), pygame.SRCALPHA)
            ico.blit(img, (0, 2))
            pygame.display.set_icon(ico)
        except pygame.error:
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

    def ejecutar(self):
        velo = pygame.Surface((ANCHO, ALTO))
        velo.fill((16, 10, 36))
        while self.corriendo:
            dt = self.reloj.tick(FPS) / 1000.0
            for e in pygame.event.get():
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
            pygame.display.flip()
        if self.red:
            self.red.cerrar()
        pygame.quit()
