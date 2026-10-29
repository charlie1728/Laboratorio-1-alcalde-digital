"""Guía de Civi: indicaciones paso a paso en el primer turno (se puede saltar)."""
import pygame

from . import personajes
from .escena import lienzo_total
from .tema import TEMA
from .widgets import Boton, parrafo, sticker, texto, titulo


class Guia:
    bloquea = True

    def __init__(self, juego):
        self.j = juego
        J = juego
        self.pasos = [
            (J.celular.r_post, "Te llegó una publicación", "En cada turno te llega una publicación de la zona "
                                                           "donde estás. Puede ser verdadera o falsa.", "mapa"),
            (J.r_centro, "Camina por Ciudad Nova", "Caminar cuesta minutos: cada zona muestra los suyos. Los globitos "
                                                   "morados dicen cuántas publicaciones circulan allí. Clic para ir.",
             "mapa"),
            (J.celular.b_verificar.rect.inflate(12, 12), "¿Será verdad?",
             "Verificar te dice la verdad, pero cuesta 3 puntos. Si te acuerdas de lo que descubrieron los "
             "otros jugadores, te los ahorras.", None),
            (pygame.Rect(J.celular.botones[0].rect.topleft,
                         (J.celular.r_acciones.w, 116)).inflate(12, 12), "Decide qué hacer",
             "Compártela si es verdadera y repórtala si es falsa. Atiendes hasta 2 por turno. Frenar un rumor "
             "desde lejos de su zona rinde la mitad. ¡Todos ven si acertaste!", None),
            (J.r_jugador, "Tu turno", "Aquí ves tus minutos, tus 2 publicaciones y tus puntos. Arriba corre "
                                      "el reloj: si llega a cero, pasa el turno. P pausa.", None),
        ]
        self.i = 0
        self.b_sig = Boton((0, 0, 140, 44), "Siguiente", "sig", icono="arrow-right", estilo="primario", tam=16)
        self.b_saltar = Boton((0, 0, 120, 44), "Saltar guía", "saltar", tam=15, estilo="suave", sombra=3)
        self._aplicar()

    def _aplicar(self):
        vista = self.pasos[self.i][3]
        if vista:
            self.j.cambiar_vista(vista)

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.b_saltar.clic(e.pos):
                self.j.cerrar_modal()
            elif self.b_sig.clic(e.pos):
                self.siguiente()
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_RIGHT):
                self.siguiente()
            elif e.key == pygame.K_ESCAPE:
                self.j.cerrar_modal()

    def siguiente(self):
        self.j.app.sonar("click")
        self.i += 1
        if self.i >= len(self.pasos):
            self.j.cerrar_modal()
            self.j.cambiar_vista("mapa")
        else:
            self._aplicar()

    def dibujar(self, sup):
        c = TEMA.c
        foco, tit, cuerpo, _ = self.pasos[self.i]
        foco = pygame.Rect(foco)
        base, ox = lienzo_total(sup)
        capa = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        capa.fill((*c["tinta"], 165))
        pygame.draw.rect(capa, (0, 0, 0, 0), foco.inflate(10, 10).move(ox, 0), border_radius=22)
        base.blit(capa, (0, 0))
        pygame.draw.rect(sup, c["mango"], foco.inflate(14, 14), 4, border_radius=24)
        w, h = 400, 170
        if foco.right + w + 40 < 1280:
            x = foco.right + 34
        elif foco.x - w - 40 > 0:
            x = foco.x - w - 34
        else:
            x = foco.centerx - w // 2
        y = max(80, min(720 - h - 40, foco.centery - h // 2))
        if foco.w > 500 and foco.h > 400:
            x, y = foco.centerx - w // 2, foco.bottom - h - 30
        caja = pygame.Rect(x, y, w, h)
        sticker(sup, caja, c["papel"], 20, 6, 3)
        img = personajes.civi("feliz", 120)
        sup.blit(img, (caja.x - 44, caja.y - 70))
        titulo(sup, tit, (caja.x + 46, caja.y + 14), 22, c["texto"])
        texto(sup, f"{self.i + 1} de {len(self.pasos)}", (caja.right - 16, caja.y + 20), 12, c["tinta2"], peso=800,
              ancla="tr")
        parrafo(sup, cuerpo, caja.x + 18, caja.y + 50, w - 36, 14, c["tinta2"], peso=700, max_lineas=4)
        self.b_sig.etiqueta = "Listo" if self.i == len(self.pasos) - 1 else "Siguiente"
        self.b_sig.rect.bottomright = (caja.right - 14, caja.bottom - 12)
        self.b_saltar.rect.bottomleft = (caja.x + 14, caja.bottom - 12)
        self.b_saltar.dibujar(sup)
        self.b_sig.dibujar(sup)
