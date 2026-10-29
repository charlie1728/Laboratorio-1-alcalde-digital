import pygame

from . import recursos
from .tema import TEMA
from .widgets import Boton, parrafo, sticker, texto, titulo

OPCIONES = [
    ("alto_contraste", "contrast", "Alto contraste (tecla C)",
     "Fondo negro, texto blanco y bordes amarillos. Para baja visión o pantallas con reflejo."),
    ("texto_grande", "type", "Texto grande",
     "Publicaciones y ayudas con letra más grande. Para baja visión o para jugar en un proyector."),
    ("mas_tiempo", "hourglass", "Más tiempo en lo viral",
     "10 segundos extra para decidir. Para quien lee más despacio o tiene dificultades motoras."),
    ("subtitulos", "captions", "Subtítulos de sonidos",
     "Cada sonido importante aparece escrito arriba. Para personas sordas o si no hay parlantes."),
    ("menos_movimiento", "pause", "Reducir movimiento",
     "Quita sacudidas, confeti y animaciones de fondo. Para sensibilidad al movimiento."),
    ("sonido", "volume-2", "Sonido (tecla M)", "Efectos de sonido del juego."),
    ("musica", "music", "Música", "Música de fondo suave."),
    ("guia", "lightbulb", "Guía de Civi", "Indicaciones paso a paso en el primer turno."),
]


class PanelAccesibilidad:
    def __init__(self, app=None):
        self.app = app
        self.rect = pygame.Rect(170, 70, 940, 580)
        self.filas = []
        y = self.rect.y + 92
        for i, op in enumerate(OPCIONES):
            col, fila = i % 2, i // 2
            self.filas.append((op, pygame.Rect(self.rect.x + 26 + col * 452, y + fila * 112, 436, 100)))
        self.cerrar = Boton((self.rect.right - 66, self.rect.y + 18, 46, 42), "", "cerrar", icono="x", sombra=3)

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.cerrar.clic(e.pos) or not self.rect.collidepoint(e.pos):
                return "cerrar"
            for (clave, *_), r in self.filas:
                if r.collidepoint(e.pos):
                    self._alternar(clave)
        return None

    def _alternar(self, clave):
        if clave == "sonido" and self.app:
            self.app.alternar_sonido()
        else:
            TEMA.cambiar(clave, not TEMA.op[clave])
            if clave == "musica" and self.app:
                self.app.snd.musica(TEMA.op["musica"] and TEMA.op["sonido"])
        if self.app:
            self.app.sonar("click")

    def dibujar(self, sup):
        c = TEMA.c
        velo = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
        velo.fill((*c["tinta"], 150))
        sup.blit(velo, (0, 0))
        sticker(sup, self.rect, c["papel"], 26, 8, 3)
        sup.blit(recursos.icono("accessibility", 30, c["acento"], 2.6), (self.rect.x + 24, self.rect.y + 26))
        titulo(sup, "Accesibilidad", (self.rect.x + 64, self.rect.y + 22), 32, c["texto"])
        texto(sup, "Siempre activo: colores aptos para daltonismo y una forma distinta para cada estado.",
              (self.rect.x + 290, self.rect.y + 38), 14, c["tinta2"], peso=700)
        raton = pygame.mouse.get_pos()
        for (clave, ic, nombre, desc), r in self.filas:
            on = TEMA.op[clave]
            sticker(sup, r, c["acento2"] if on else c["papel2"], 18, 4 if r.collidepoint(raton) else 0, 2)
            sup.blit(recursos.icono(ic, 26, c["acento"] if on else c["tinta2"], 2.4), (r.x + 16, r.y + 16))
            texto(sup, nombre, (r.x + 54, r.y + 16), 17, c["texto"], peso=800)
            parrafo(sup, desc, r.x + 54, r.y + 42, r.w - 140, 13, c["tinta2"])
            sw = pygame.Rect(r.right - 74, r.y + 16, 56, 30)
            pygame.draw.rect(sup, c["bueno"] if on else c["boton_off"], sw, border_radius=15)
            pygame.draw.rect(sup, c["borde"], sw, 2, border_radius=15)
            pygame.draw.circle(sup, c["papel"] if not TEMA.alto_contraste else c["texto"],
                               (sw.right - 15 if on else sw.x + 15, sw.centery), 11)
            pygame.draw.circle(sup, c["borde"], (sw.right - 15 if on else sw.x + 15, sw.centery), 11, 2)
            texto(sup, "Sí" if on else "No", (sw.centerx, sw.bottom + 14), 12, c["tinta2"], peso=800, ancla="c")
        self.cerrar.dibujar(sup)
