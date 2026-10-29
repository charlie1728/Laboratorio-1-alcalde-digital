import random

import pygame

from ..modelo.apariencia import COLORES_JUGADOR, look_aleatorio
from ..modelo.roles import ORDEN_ROLES
from .escena import Escena
from .tarjeta_jugador import TarjetaJugador
from .tema import TEMA
from .widgets import Boton, sticker, texto, titulo

DURACIONES = [("Corta", 6), ("Normal", 8), ("Larga", 10)]


class PantallaSeleccion:
    def __init__(self, app):
        self.app = app
        self.escena = Escena(semilla=4, gente=0, y_suelo=760)
        rng = random.Random()
        self.tarjetas = []
        for i in range(4):
            self.tarjetas.append(TarjetaJugador(
                (36 + i * 306, 100, 290, 522), i, COLORES_JUGADOR[i], f"Jugador {i + 1}", ORDEN_ROLES[i],
                look_aleatorio(rng, i % 2 == 1), opcional=i >= 2, activo=i < 2))
        self.btn_volver = Boton((36, 26, 52, 48), "", "volver", icono="arrow-left", sombra=3)
        self.btn_jugar = Boton((952, 650, 290, 56), "Comenzar campaña", "jugar", icono="play",
                               estilo="primario", tam=20)
        self.duracion = 1
        self.b_dur = [Boton((136 + i * 112, 654, 104, 46), n, i, tam=16, estilo="suave", sombra=3)
                      for i, (n, _) in enumerate(DURACIONES)]
        self.guia = TEMA.op["guia"]
        self.r_guia = pygame.Rect(560, 654, 340, 46)

    def escribiendo(self):
        return any(t.editando for t in self.tarjetas)

    def activos(self):
        return [t for t in self.tarjetas if t.activo]

    def evento(self, e):
        for t in self.tarjetas:
            if t.evento(e, self.app.sonar):
                for otra in self.tarjetas:
                    if otra is not t and e.type == pygame.MOUSEBUTTONDOWN:
                        otra.editando = False
                return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.btn_volver.clic(e.pos):
                self.app.ir_menu()
            elif self.btn_jugar.clic(e.pos):
                self._comenzar()
            elif self.r_guia.collidepoint(e.pos):
                self.guia = not self.guia
                TEMA.cambiar("guia", self.guia)
                self.app.sonar("click")
            for b in self.b_dur:
                if b.clic(e.pos):
                    self.duracion = b.clave
                    self.app.sonar("click")
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_RETURN:
                self._comenzar()
            elif e.key == pygame.K_ESCAPE:
                self.app.ir_menu()

    def _comenzar(self):
        if not 2 <= len(self.activos()) <= 4:
            return
        cfg = [dict(nombre=t.perfil()["nombre"], rol=t.rol, color=t.color, look=t.look) for t in self.activos()]
        self.app.sonar("logro")
        self.app.iniciar_local(cfg, rondas=DURACIONES[self.duracion][1], guia=self.guia)

    def dibujar(self, sup):
        c = TEMA.c
        self.escena.dibujar(sup, sol=False)
        self.btn_volver.dibujar(sup)
        titulo(sup, "¿Quiénes juegan?", (106, 22), 38, c["texto"])
        texto(sup, "De 2 a 4 personas en este computador. Cada quien elige su personaje y su rol.",
              (108, 70), 16, c["tinta2"], peso=700)
        texto(sup, "Clic en el nombre para cambiarlo y en la varita para personalizar.", (1244, 70), 14,
              c["tinta2"], peso=700, ancla="tr")
        for t in self.tarjetas:
            t.dibujar(sup)
        sticker(sup, (24, 644, 896, 66), c["papel"], 20, 4, 3)
        texto(sup, "Duración", (44, 678), 16, c["texto"], peso=800, ancla="ml")
        for b in self.b_dur:
            b.seleccionado = b.clave == self.duracion
            b.dibujar(sup)
        texto(sup, f"{DURACIONES[self.duracion][1]} días", (136 + 3 * 112 + 2, 678), 14, c["tinta2"], peso=800,
              ancla="ml")
        rg = self.r_guia
        sticker(sup, rg, c["acento2"] if self.guia else c["papel"], 14, 3, 2)
        caja = pygame.Rect(rg.x + 12, rg.centery - 12, 24, 24)
        pygame.draw.rect(sup, c["acento"] if self.guia else c["papel"], caja, border_radius=7)
        pygame.draw.rect(sup, c["borde"], caja, 2, border_radius=7)
        if self.guia:
            pygame.draw.lines(sup, c["sobre_color"], False, [(caja.x + 5, caja.centery), (caja.x + 10, caja.bottom - 6),
                                                             (caja.right - 5, caja.y + 6)], 3)
        texto(sup, "Guía de Civi en el primer turno", (caja.right + 12, rg.centery), 15, c["texto"], peso=800, ancla="ml")
        self.btn_jugar.activo = 2 <= len(self.activos()) <= 4
        self.btn_jugar.dibujar(sup)
