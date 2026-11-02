"""Ventana de Corta la mentira (reutiliza la ventana maximizada del juego en vivo)."""
from __future__ import annotations

import pygame

from ..vivo.app import AppVivo


class AppCorta(AppVivo):
    def _menu_inicial(self):
        from .menu import MenuCorta
        return MenuCorta(self)

    def jugar(self, jugadores):
        from .pantalla import PantallaCorta
        pygame.mouse.set_visible(False)
        self.cambiar(PantallaCorta(self, jugadores, semilla=self.semilla, dia_seg=self.dia_seg))

    def ir_menu(self):
        from .menu import MenuCorta
        pygame.mouse.set_visible(True)
        self.cambiar(MenuCorta(self))
