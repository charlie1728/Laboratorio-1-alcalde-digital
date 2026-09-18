"""Bucle principal y cambio de pantallas."""
import pygame

from ..modelo.partida import Partida
from .ayuda import Ayuda
from .pantalla_inicio import PantallaInicio
from .pantalla_juego import PantallaJuego
from .pantalla_resumen import PantallaResumen
from .sonido import sonidos
from .tema import TEMA
from .widgets import Toasts

ANCHO, ALTO = 1280, 760


class App:
    def __init__(self, semilla=None, rondas=8):
        pygame.init()
        pygame.display.set_caption("Alcalde Digital — El árbol de mutaciones")
        try:
            self.pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        self.reloj = pygame.time.Clock()
        self.snd = sonidos()
        self.toasts = Toasts()
        self.ayuda = Ayuda((140, 90, 1000, 580))
        self.mostrar_ayuda = False
        self.semilla = semilla
        self.rondas = rondas
        self.corriendo = True
        self.actual = PantallaInicio(self)

    def iniciar_partida(self, cfg):
        self.toasts.items.clear()
        self.actual = PantallaJuego(self, Partida(cfg, rondas=self.rondas, semilla=self.semilla))

    def fin_partida(self, partida):
        self.toasts.items.clear()
        self.actual = PantallaResumen(self, partida)

    def ir_inicio(self):
        self.actual = PantallaInicio(self)

    def paso(self, eventos):
        for e in eventos:
            if e.type == pygame.QUIT:
                self.corriendo = False
                continue
            if self.mostrar_ayuda:
                if self.ayuda.evento(e) == "cerrar" or (
                        e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_h)):
                    self.mostrar_ayuda = False
                continue
            escribiendo = isinstance(self.actual, PantallaInicio) and self.actual.editando is not None
            if e.type == pygame.KEYDOWN and not escribiendo:
                if e.key == pygame.K_h:
                    self.mostrar_ayuda = True
                    continue
                if e.key == pygame.K_c:
                    TEMA.alternar_contraste()
                    continue
                if e.key == pygame.K_m:
                    self.snd.activo = not self.snd.activo
                    continue
            self.actual.evento(e)
        if hasattr(self.actual, "actualizar") and not self.mostrar_ayuda:
            self.actual.actualizar()
        self.actual.dibujar(self.pantalla)
        if not isinstance(self.actual, PantallaJuego):
            self.toasts.dibujar(self.pantalla, 440, 750, 400, abajo=True)
        if self.mostrar_ayuda:
            self.ayuda.dibujar(self.pantalla)

    def ejecutar(self):
        while self.corriendo:
            self.paso(pygame.event.get())
            pygame.display.flip()
            self.reloj.tick(60)
        pygame.quit()
