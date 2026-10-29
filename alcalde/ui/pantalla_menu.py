import math

import pygame

from ..modelo.hechos import CANDIDATOS, LEMAS
from . import personajes
from .escena import Escena, texto_contorno
from .tema import TEMA
from .widgets import Boton, chip, parrafo, sticker, texto

# Cómo se ve cada candidato en los afiches (y en la noche de elecciones).
LOOK_CANDIDATOS = {
    "Valentina Rondón": dict(piel=2, pelo="largo", color_pelo=0, ropa=5, extra="aretes"),
    "Tomás Arrieta": dict(piel=1, pelo="corto", color_pelo=1, ropa=7, extra="bigote"),
    "Luz Marina Pacheco": dict(piel=3, pelo="mono", color_pelo=5, ropa=4, extra="gafas"),
    "Emilio Sarmiento": dict(piel=4, pelo="rapado", color_pelo=0, ropa=3, extra="barba"),
}
COLOR_CANDIDATO = {n: c for n, c in CANDIDATOS}

_afiches = {}


def afiche(nombre, ancho=150, rot=0.0, expresion="feliz"):
    clave = (nombre, ancho, round(rot, 1), expresion, TEMA.alto_contraste)
    if clave in _afiches:
        return _afiches[clave]
    c = TEMA.c
    alto = round(ancho * 1.3)
    s = pygame.Surface((ancho + 10, alto + 12), pygame.SRCALPHA)
    col = COLOR_CANDIDATO[nombre]
    sticker(s, (4, 4, ancho, alto), c["papel"], 14, 5, 3)
    pygame.draw.rect(s, col, (7, 7, ancho - 6, round(alto * 0.62)), border_top_left_radius=12,
                     border_top_right_radius=12)
    b = personajes.busto(LOOK_CANDIDATOS[nombre], "candidato", expresion, round(ancho * 0.72),
                         color_extra=col)
    s.blit(b, ((ancho + 10 - b.get_width()) // 2, 7 + round(alto * 0.62) - b.get_height()))
    pygame.draw.line(s, c["tinta"], (6, 7 + round(alto * 0.62)), (ancho + 2, 7 + round(alto * 0.62)), 3)
    nom = nombre.split()
    texto(s, " ".join(nom[:-1]) if len(nom) > 2 else nom[0], (ancho // 2 + 4, round(alto * 0.70)),
          round(ancho * 0.11), c["texto"], peso=700, fam="titulo", ancla="c")
    texto(s, nom[-1], (ancho // 2 + 4, round(alto * 0.70) + round(ancho * 0.13)), round(ancho * 0.13),
          col, peso=700, fam="titulo", ancla="c")
    texto(s, LEMAS[nombre], (ancho // 2 + 4, round(alto * 0.92)), round(ancho * 0.085), c["tinta2"],
          peso=800, ancla="c")
    if rot:
        s = pygame.transform.rotozoom(s, rot, 1)
    _afiches[clave] = s
    return s


class PantallaMenu:
    def __init__(self, app):
        self.app = app
        self.escena = Escena(semilla=11, gente=8, y_suelo=606)
        x, y = 92, 318
        self.btn_local = Boton((x, y, 396, 64), "Jugar en este computador", "local", icono="users",
                               estilo="primario", tam=21)
        self.btn_red = Boton((x, y + 80, 396, 56), "Jugar en red", "red", icono="wifi", tam=19)
        self.btn_ayuda = Boton((x, y + 150, 192, 52), "Cómo se juega", "ayuda", icono="circle-help", tam=16)
        self.btn_acc = Boton((x + 204, y + 150, 192, 52), "Accesibilidad", "acc", icono="accessibility", tam=16)
        self.botones = [self.btn_local, self.btn_red, self.btn_ayuda, self.btn_acc]
        self.btn_salir = Boton((1192, 18, 72, 40), "", "salir", icono="log-out", tam=16, sombra=3)
        self.btn_sonido = Boton((1032, 18, 150, 40), "Sonido", "sonido", icono="volume-2", tam=15, sombra=3)
        self.t0 = pygame.time.get_ticks()

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for b in self.botones + [self.btn_salir, self.btn_sonido]:
                if b.clic(e.pos):
                    self.app.sonar("click")
                    self._ir(b.clave)
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE):
            self._ir("local")

    def _ir(self, clave):
        if clave == "local":
            from .pantalla_seleccion import PantallaSeleccion
            self.app.cambiar(PantallaSeleccion(self.app))
        elif clave == "red":
            from .pantalla_red import PantallaRed
            self.app.cambiar(PantallaRed(self.app))
        elif clave == "ayuda":
            self.app.abrir(self.app.ayuda)
        elif clave == "acc":
            self.app.abrir(self.app.accesibilidad)
        elif clave == "salir":
            self.app.corriendo = False
        elif clave == "sonido":
            self.app.alternar_sonido()

    def dibujar(self, sup):
        c = TEMA.c
        t = (pygame.time.get_ticks() - self.t0) / 1000
        mov = not TEMA.op["menos_movimiento"]
        self.escena.dibujar(sup)
        # muro de afiches de campaña
        for i, (nombre, _) in enumerate(CANDIDATOS):
            rot = (-5, 3, -3, 5)[i]
            img = afiche(nombre, 132, rot)
            cx = 706 + i * 146
            cy = 214 + (i % 2) * 24 + (math.sin(t * 1.3 + i) * 2 if mov else 0)
            sup.blit(img, img.get_rect(center=(cx, cy)))
        # título
        texto_contorno(sup, "Alcalde", (92, 64), 92, c["tinta"], c["papel"], 5, ancla="tl")
        texto_contorno(sup, "Digital", (130, 152), 92, c["acento"], c["papel"], 5, ancla="tl")
        chip(sup, "Elecciones en Ciudad Nova", (96, 268), c["mango"], c["texto"], "vote", 15, ancla="ml", alto=34)
        # tarjeta de botones
        sticker(sup, (70, 300, 440, 236), c["papel"], 22, 6, 3)
        for b in self.botones:
            b.dibujar(sup)
        self.btn_salir.dibujar(sup)
        encendido = self.app.snd.activo
        self.btn_sonido.icono = "volume-2" if encendido else "volume-x"
        self.btn_sonido.etiqueta = "Sonido sí" if encendido else "Sin sonido"
        self.btn_sonido.dibujar(sup)
        # Civi saluda
        ala = (math.sin(t * 5) + 1) / 2 if mov else 0
        img = personajes.civi("feliz", 150, parpadeo=int(t * 1.7) % 6 == 0, ala=ala)
        sup.blit(img, (492, 392 + (math.sin(t * 2) * 3 if mov else 0)))
        burbuja = pygame.Rect(540, 344, 276, 82)
        sticker(sup, burbuja, c["papel"], 18, 4, 3)
        pygame.draw.polygon(sup, c["papel"], [(552, 422), (570, 422), (548, 444)])
        pygame.draw.lines(sup, c["tinta"], False, [(552, 425), (548, 444), (572, 425)], 3)
        parrafo(sup, "¡Hola! Soy Civi. En Civitas cada reenvío puede torcer la verdad: te ayudo a cuidarla.",
                burbuja.x + 14, burbuja.y + 11, burbuja.w - 26, 14, c["texto"], peso=700)
        texto(sup, "Estructura de Datos II, Universidad del Norte", (1266, 708), 12, c["tinta2"], peso=700,
              ancla="br")
