import random

import pygame

from ..modelo.apariencia import COLORES_JUGADOR, look_aleatorio
from ..modelo.roles import ORDEN_ROLES
from .escena import Escena
from .tarjeta_jugador import TarjetaJugador
from .tema import TEMA
from .widgets import Boton, sticker, texto, titulo

DURACIONES = [("Corta", 6), ("Normal", 8), ("Larga", 10)]
# Segundos que tiene cada jugador para decidir sobre cada publicación (0 = sin límite).
TIEMPOS = [("Sin límite", 0), ("20 s", 20), ("30 s", 30), ("45 s", 45)]


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
        aj = getattr(app, "ajustes", {})
        self.tiempo = next((i for i, (_, s) in enumerate(TIEMPOS) if s == aj.get("segundos", 20)), 1)
        self.pausa = bool(aj.get("pausa_dias", True))
        self.r_opciones = pygame.Rect(452, 12, 792, 50)
        x = 660
        self.b_tiempo = []
        for i, (n, _) in enumerate(TIEMPOS):
            w = 104 if i == 0 else 66
            self.b_tiempo.append(Boton((x, 18, w, 38), n, i, tam=14, estilo="suave", sombra=3))
            x += w + 6
        self.r_pausa = pygame.Rect(x + 14, 18, 1232 - (x + 14), 38)

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
            elif self.r_pausa.collidepoint(e.pos):
                self.pausa = not self.pausa
                self.app.sonar("click")
            for b in self.b_tiempo:
                if b.clic(e.pos):
                    self.tiempo = b.clave
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
        self.app.iniciar_local(cfg, rondas=DURACIONES[self.duracion][1], guia=self.guia,
                               segundos=TIEMPOS[self.tiempo][1], pausa_dias=self.pausa)

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
        self._opciones(sup)
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

    def _casilla(self, sup, r, marcada, etiqueta):
        c = TEMA.c
        sticker(sup, r, c["acento2"] if marcada else c["papel"], 14, 3, 2)
        caja = pygame.Rect(r.x + 12, r.centery - 12, 24, 24)
        pygame.draw.rect(sup, c["acento"] if marcada else c["papel"], caja, border_radius=7)
        pygame.draw.rect(sup, c["borde"], caja, 2, border_radius=7)
        if marcada:
            pygame.draw.lines(sup, c["sobre_color"], False, [(caja.x + 5, caja.centery), (caja.x + 10, caja.bottom - 6),
                                                             (caja.right - 5, caja.y + 6)], 3)
        texto(sup, etiqueta, (caja.right + 10, r.centery), 14, c["texto"], peso=800, ancla="ml")

    def _opciones(self, sup):
        """Reloj del turno y pausa entre días, arriba a la derecha."""
        c = TEMA.c
        sticker(sup, self.r_opciones, c["papel"], 18, 4, 3)
        texto(sup, "Tiempo por publicación", (self.r_opciones.x + 16, self.r_opciones.centery), 14, c["texto"],
              peso=900, ancla="ml")
        for b in self.b_tiempo:
            b.seleccionado = b.clave == self.tiempo
            b.dibujar(sup)
        self._casilla(sup, self.r_pausa, self.pausa, "Pausa entre días")
