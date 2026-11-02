"""Ventana del juego en vivo. Dibuja al tamaño real de la pantalla (sin estirar una imagen pequeña)."""
from __future__ import annotations

import sys

import pygame

from ..ui.personajes import civi
from ..ui.sonido import sonidos
from ..ui.tema import TEMA


class AppVivo:
    def __init__(self, semilla=None, dia_seg=None):
        pygame.init()
        pygame.display.set_caption("Alcalde Digital")
        self.completa = False
        self._maximizar = 0
        self.ventana = self._abrir_ventana()
        try:
            pygame.display.set_icon(civi("feliz", 64))
        except pygame.error:
            pass
        self.reloj = pygame.time.Clock()
        self.snd = sonidos()
        self.snd.activo = TEMA.op["sonido"]
        self.semilla = semilla
        self.dia_seg = dia_seg
        self.corriendo = True
        self.actual = self._menu_inicial()
        self.snd.musica(TEMA.op["musica"] and TEMA.op["sonido"])

    def _menu_inicial(self):
        from .menu import PantallaMenu
        return PantallaMenu(self)

    @property
    def menos_movimiento(self):
        return TEMA.op.get("menos_movimiento", False)

    def _abrir_ventana(self):
        if self.completa:
            try:
                return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except pygame.error:
                self.completa = False
        try:
            escritorio = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, IndexError, AttributeError):
            escritorio = (1280, 720)
        tam = (max(960, escritorio[0] - 40), max(540, escritorio[1] - 110))
        ventana = pygame.display.set_mode(tam, pygame.RESIZABLE)
        if sys.platform == "win32":
            # Maximizar con la API de Windows: ocupa la pantalla sin tapar la barra de tareas.
            try:
                import ctypes
                hwnd = pygame.display.get_wm_info().get("window")
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 1)
                    ctypes.windll.user32.ShowWindow(hwnd, 3)
            except (OSError, AttributeError, pygame.error):
                pass
            self._maximizar = 3
        return pygame.display.get_surface() or ventana

    def sonar(self, nombre):
        self.snd.play(nombre)

    def alternar_sonido(self):
        TEMA.cambiar("sonido", not TEMA.op["sonido"])
        self.snd.activo = TEMA.op["sonido"]
        self.snd.musica(TEMA.op["musica"] and TEMA.op["sonido"])

    def cambiar(self, pantalla):
        self.actual = pantalla

    def jugar(self, config):
        from .juego import PantallaJuego
        self.cambiar(PantallaJuego(self, config, semilla=self.semilla, dia_seg=self.dia_seg))

    def ir_menu(self):
        from .menu import PantallaMenu
        self.cambiar(PantallaMenu(self))

    def paso(self, eventos, dt):
        for e in eventos:
            if e.type == pygame.QUIT:
                self.corriendo = False
                continue
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    self.completa = not self.completa
                    self.ventana = self._abrir_ventana()
                    continue
                if e.key == pygame.K_m:
                    self.alternar_sonido()
                    continue
            self.actual.evento(e)
        self.actual.actualizar(dt)
        self.actual.dibujar(pygame.display.get_surface())

    def ejecutar(self):
        while self.corriendo:
            dt = self.reloj.tick(60) / 1000
            if self._maximizar:
                self._maximizar -= 1
                if self._maximizar == 0 and sys.platform == "win32" and not self.completa:
                    try:
                        import ctypes
                        hwnd = pygame.display.get_wm_info().get("window")
                        if pygame.display.get_surface().get_size() != pygame.display.get_desktop_sizes()[0]:
                            ctypes.windll.user32.ShowWindow(hwnd, 1)
                            ctypes.windll.user32.ShowWindow(hwnd, 3)
                    except (OSError, AttributeError, pygame.error):
                        pass
            self.paso(pygame.event.get(), dt)
            pygame.display.flip()
        pygame.quit()
