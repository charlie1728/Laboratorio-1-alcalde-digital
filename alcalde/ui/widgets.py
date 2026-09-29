import math

import pygame

from .tema import TEMA

def texto(sup, s, pos, tam=16, color=None, negrita=False, centro=False, derecha=False):
    f = TEMA.fuente(tam, negrita)
    img = f.render(str(s), True, color or TEMA.c["texto"])
    r = img.get_rect()
    if centro:
        r.center = pos
    elif derecha:
        r.topright = pos
    else:
        r.topleft = pos
    sup.blit(img, r)
    return r

def envolver(s, tam, ancho, negrita=False):
    f = TEMA.fuente(tam, negrita)
    lineas, actual = [], ""
    for palabra in str(s).split():
        prueba = (actual + " " + palabra).strip()
        if f.size(prueba)[0] <= ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas

def parrafo(sup, s, x, y, ancho, tam=15, color=None, interlineado=4, negrita=False):
    for l in envolver(s, tam, ancho, negrita):
        texto(sup, l, (x, y), tam, color, negrita)
        y += tam + interlineado
    return y

def panel(sup, rect, color=None, radio=10, borde=True):
    pygame.draw.rect(sup, color or TEMA.c["panel"], rect, border_radius=radio)
    if borde:
        pygame.draw.rect(sup, TEMA.c["borde"], rect, 1, border_radius=radio)

def poligono_regular(centro, radio, lados, rot=0.0):
    cx, cy = centro
    return [(cx + radio * math.cos(rot + 2 * math.pi * i / lados),
             cy + radio * math.sin(rot + 2 * math.pi * i / lados)) for i in range(lados)]

class Boton:
    def __init__(self, rect, etiqueta, clave=None, costo=None, tam=15, color=None):
        self.rect = pygame.Rect(rect)
        self.etiqueta = etiqueta
        self.clave = etiqueta if clave is None else clave
        self.costo = costo
        self.tam = tam
        self.color = color
        self.activo = True
        self.motivo = ""
        self.hover = False
        self.seleccionado = False

    def dibujar(self, sup):
        c = TEMA.c
        self.hover = self.rect.collidepoint(pygame.mouse.get_pos())
        if not self.activo:
            fondo = c["boton_off"]
        elif self.seleccionado:
            fondo = self.color or c["acento"]
        else:
            fondo = c["boton_hover"] if self.hover else c["boton"]
        pygame.draw.rect(sup, fondo, self.rect, border_radius=8)
        borde = (self.color or c["acento"]) if (self.hover and self.activo) else c["borde"]
        pygame.draw.rect(sup, borde, self.rect, 2 if self.hover and self.activo else 1, border_radius=8)
        col = c["texto"] if self.activo else c["tenue"]
        if self.seleccionado and not TEMA.alto_contraste:
            col = (10, 14, 22)
        if self.costo is None:
            texto(sup, self.etiqueta, self.rect.center, self.tam, col, True, centro=True)
        else:
            texto(sup, self.etiqueta, (self.rect.x + 12, self.rect.centery - self.tam // 2 - 2),
                  self.tam, col, True)
            for i in range(self.costo):                                  
                cx = self.rect.right - 14 - i * 13
                pygame.draw.circle(sup, c["aviso"] if self.activo else c["tenue"],
                                   (cx, self.rect.centery), 4)

    def clic(self, pos):
        return self.activo and self.rect.collidepoint(pos)

class Toasts:

    def __init__(self):
        self.items = []                            

    def agregar(self, s, tipo):
        self.items.append([s, tipo, pygame.time.get_ticks()])
        self.items = self.items[-4:]

    def dibujar(self, sup, x, y, ancho, abajo=False):
        ahora = pygame.time.get_ticks()
        self.items = [it for it in self.items if ahora - it[2] <= 4200][-2:]
        vivos = self.items
        if abajo:
            total = sum(14 + 18 * len(envolver(s, 14, ancho - 50)) + 6 for s, _, _ in vivos)
            y -= total
        for s, tipo, t0 in vivos:
            edad = ahora - t0
            alpha = 255 if edad < 3600 else int(255 * (4200 - edad) / 600)
            desliz = max(0, 20 - edad / 10)
            color = {"bueno": TEMA.c["bueno"], "malo": TEMA.c["malo"],
                     "logro": TEMA.c["logro"], "evento": TEMA.c["acento"]}.get(tipo, TEMA.c["tenue"])
            lineas = envolver(s, 14, ancho - 50)
            h = 14 + 18 * len(lineas)
            capa = pygame.Surface((ancho, h), pygame.SRCALPHA)
            pygame.draw.rect(capa, (*TEMA.c["panel2"], 235), capa.get_rect(), border_radius=8)
            pygame.draw.rect(capa, (*color, 255), (0, 0, 6, h), border_top_left_radius=8,
                             border_bottom_left_radius=8)
            icono = {"bueno": "+", "malo": "-", "logro": "*", "evento": "!"}.get(tipo, "i")
            pygame.draw.circle(capa, color, (22, h // 2), 10)
            texto(capa, icono, (22, h // 2), 15, (10, 10, 10), True, centro=True)
            yy = 7
            for l in lineas:
                texto(capa, l, (40, yy), 14)
                yy += 18
            capa.set_alpha(alpha)
            sup.blit(capa, (x + desliz, y))
            y += h + 6
