import math

import pygame
import pygame.gfxdraw

from . import recursos
from .tema import TEMA

_ANCLAS = {"tl": "topleft", "tr": "topright", "c": "center", "ml": "midleft", "mr": "midright",
           "mt": "midtop", "mb": "midbottom", "bl": "bottomleft", "br": "bottomright"}


def texto(sup, s, pos, tam=16, color=None, negrita=False, centro=False, derecha=False,
          peso=None, fam="texto", ancla=None, alpha=None):
    peso = peso or (800 if negrita else 600)
    img = recursos.render_texto(str(s), tam, color or TEMA.c["texto"], peso, fam)
    if alpha is not None and alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    r = img.get_rect()
    ancla = ancla or ("c" if centro else "tr" if derecha else "tl")
    setattr(r, _ANCLAS[ancla], (round(pos[0]), round(pos[1])))
    sup.blit(img, r)
    return r


def titulo(sup, s, pos, tam=28, color=None, ancla="tl", peso=700, alpha=None):
    return texto(sup, s, pos, tam, color, peso=peso, fam="titulo", ancla=ancla, alpha=alpha)


def ancho_texto(s, tam, peso=600, fam="texto"):
    return recursos.fuente(tam, peso, fam).size(str(s))[0]


def envolver(s, tam, ancho, negrita=False, peso=None, fam="texto"):
    f = recursos.fuente(tam, peso or (800 if negrita else 600), fam)
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


def recortar(s, tam, ancho, peso=600, fam="texto"):
    f = recursos.fuente(tam, peso, fam)
    if f.size(s)[0] <= ancho:
        return s
    while s and f.size(s + "…")[0] > ancho:
        s = s[:-1]
    return s.rstrip() + "…"


def parrafo(sup, s, x, y, ancho, tam=15, color=None, interlineado=None, negrita=False, peso=None,
            max_lineas=None, fam="texto", centrado=False):
    lineas = envolver(s, tam, ancho, negrita, peso, fam)
    if max_lineas and len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        lineas[-1] = recortar(lineas[-1] + " …", tam, ancho, peso or 600, fam)
    paso = tam + (interlineado if interlineado is not None else round(tam * 0.38))
    for l in lineas:
        if centrado:
            texto(sup, l, (x + ancho / 2, y), tam, color, negrita, peso=peso, fam=fam, ancla="mt")
        else:
            texto(sup, l, (x, y), tam, color, negrita, peso=peso, fam=fam)
        y += paso
    return y


def luminancia(c):
    r, g, b = (v / 255 for v in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def legible(fondo, color):
    """En alto contraste, el texto sobre fondos claros pasa a negro (y sobre oscuros, a blanco)."""
    if not TEMA.alto_contraste:
        return color
    return (0, 0, 0) if luminancia(fondo) > 0.5 else (255, 255, 255)


def _hex(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c[:3])


def sticker(sup, rect, fill=None, radio=16, sombra=4, borde=3, color_borde=None, color_sombra=None,
            alpha=None):
    """Panel con contorno de tinta y sombra dura (antialias, en caché)."""
    c = TEMA.c
    rect = pygame.Rect(rect)
    fill = fill or c["papel"]
    color_borde = color_borde or c["borde"]
    color_sombra = color_sombra or c["sombra"]
    w, h = rect.w, rect.h
    m = 3
    radio = min(radio, h // 2, w // 2)
    d = ""
    if sombra:
        d += (f'<rect x="{m}" y="{m + sombra}" width="{w}" height="{h}" rx="{radio}" '
              f'fill="{_hex(color_sombra)}"/>')
    trazo = f'stroke="{_hex(color_borde)}" stroke-width="{borde}"' if borde else ""
    d += f'<rect x="{m}" y="{m}" width="{w}" height="{h}" rx="{radio}" fill="{_hex(fill)}" {trazo}/>'
    img = recursos.svg(d, w + 2 * m, h + 2 * m + sombra)
    if alpha is not None:
        img = img.copy()
        img.set_alpha(alpha)
    sup.blit(img, (rect.x - m, rect.y - m))
    return rect


def panel(sup, rect, color=None, radio=16, borde=True, sombra=4):
    return sticker(sup, rect, color, radio, sombra, 3 if borde else 0)


def circulo(sup, centro, r, color, borde=None, grosor=3):
    x, y = round(centro[0]), round(centro[1])
    r = round(r)
    if r < 1:
        return
    pygame.gfxdraw.filled_circle(sup, x, y, r, color)
    pygame.gfxdraw.aacircle(sup, x, y, r, color)
    if borde:
        for k in range(min(grosor, r)):
            pygame.gfxdraw.aacircle(sup, x, y, r - k, borde)


def chip(sup, s, pos, fondo, color=None, icono=None, tam=13, ancla="tl", borde=True, alto=None, punto=None):
    c = TEMA.c
    w_txt = ancho_texto(s, tam, 800) if s else 0
    alto = alto or tam + 12
    w = w_txt + 20 + (tam + 6 if icono else 0) - (6 if not s and icono else 0) + (14 if punto else 0)
    r = pygame.Rect(0, 0, w, alto)
    setattr(r, _ANCLAS[ancla], pos)
    sticker(sup, r, fondo, radio=alto // 2, sombra=0, borde=2 if borde else 0)
    color = legible(fondo, color or c["texto"])
    x = r.x + 10
    if punto:
        circulo(sup, (x + 4, r.centery), 5, punto)
        x += 14
    if icono:
        sup.blit(recursos.icono(icono, tam + 2, color or c["texto"], 2.4), (x - 1, r.centery - (tam + 2) // 2))
        x += tam + 6
    if s:
        texto(sup, s, (x, r.centery), tam, color or c["texto"], peso=800, ancla="ml")
    return r


def barra(sup, rect, valor, color, fondo=None, rayas=False, borde=True):
    c = TEMA.c
    rect = pygame.Rect(rect)
    pygame.draw.rect(sup, fondo or c["papel3"], rect, border_radius=rect.h // 2)
    w = round(rect.w * max(0, min(100, valor)) / 100)
    if w > 0:
        lleno = pygame.Rect(rect.x, rect.y, max(rect.h, w), rect.h)
        pygame.draw.rect(sup, color, lleno, border_radius=rect.h // 2)
        if rayas:
            capa = pygame.Surface(lleno.size, pygame.SRCALPHA)
            for xx in range(-lleno.h, lleno.w, 8):
                pygame.draw.line(capa, (255, 255, 255, 110), (xx, lleno.h), (xx + lleno.h, 0), 3)
            mascara = pygame.Surface(lleno.size, pygame.SRCALPHA)
            pygame.draw.rect(mascara, (255, 255, 255, 255), mascara.get_rect(), border_radius=rect.h // 2)
            capa.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            sup.blit(capa, lleno)
    if borde:
        pygame.draw.rect(sup, c["borde"], rect, 2, border_radius=rect.h // 2)


def poligono_regular(centro, radio, lados, rot=0.0):
    cx, cy = centro
    return [(cx + radio * math.cos(rot + 2 * math.pi * i / lados),
             cy + radio * math.sin(rot + 2 * math.pi * i / lados)) for i in range(lados)]


def forma_estado(sup, estado, centro, r, color=None, borde=None):
    """Cada estado tiene su forma además de su color (no depende solo del color)."""
    c = TEMA.c
    col = color or {"falso": c["n_falso"], "veraz": c["n_veraz"], "correccion": c["n_correccion"],
                    "nada": c["n_desconocido"], "duda": c["n_duda"]}.get(estado, c["n_desconocido"])
    borde = borde or c["borde"]
    x, y = centro
    if estado == "veraz":
        pts = [(x - r, y - r), (x + r, y - r), (x + r, y + r), (x - r, y + r)]
    elif estado == "falso":
        pts = poligono_regular((x, y + r * 0.2), r * 1.25, 3, -math.pi / 2)
    elif estado == "correccion":
        pts = poligono_regular((x, y), r * 1.25, 4)
    else:
        circulo(sup, (x, y), r, col, borde, 2)
        return
    pygame.gfxdraw.filled_polygon(sup, [(round(a), round(b)) for a, b in pts], col)
    pygame.draw.polygon(sup, borde, pts, 2)


def tooltip(sup, s, pos, ancho=260, tam=13):
    c = TEMA.c
    lineas = envolver(s, tam, ancho - 24)
    h = 16 + len(lineas) * (tam + 5)
    w = min(ancho, max(ancho_texto(l, tam) for l in lineas) + 26) if lineas else ancho
    x = min(max(8, pos[0] - w // 2), sup.get_width() - w - 8)
    y = pos[1] - h - 12 if pos[1] - h - 12 > 8 else pos[1] + 22
    sticker(sup, (x, y, w, h), c["tinta"] if not TEMA.alto_contraste else c["papel"], radio=10, sombra=0,
            borde=2, color_borde=c["tinta"])
    yy = y + 8
    for l in lineas:
        texto(sup, l, (x + 12, yy), tam, c["sobre_color"] if not TEMA.alto_contraste else c["texto"])
        yy += tam + 5


ESTILOS = {
    "primario": ("acento", "sobre_color"), "especial": ("mango", "texto"), "secundario": ("papel", "texto"),
    "peligro": ("malo", "sobre_color"), "bueno": ("bueno", "sobre_color"), "suave": ("papel2", "texto"),
}


class Boton:
    def __init__(self, rect, etiqueta, clave=None, costo=None, tam=16, color=None, icono=None,
                 estilo="secundario", atajo=None, radio=14, sombra=4):
        self.rect = pygame.Rect(rect)
        self.etiqueta = etiqueta
        self.clave = etiqueta if clave is None else clave
        self.costo = costo
        self.tam = tam
        self.color = color
        self.icono = icono
        self.estilo = estilo
        self.atajo = atajo
        self.radio = radio
        self.sombra = sombra
        self.activo = True
        self.motivo = ""
        self.hover = False
        self.seleccionado = False
        self.visible = True

    def colores(self):
        c = TEMA.c
        fondo_k, txt_k = ESTILOS.get(self.estilo, ESTILOS["secundario"])
        fondo, txt = c[fondo_k], c[txt_k]
        if self.color is not None:
            fondo = self.color
        if self.seleccionado and self.estilo in ("secundario", "suave"):
            fondo, txt = c["acento"], c["sobre_color"]
        if not self.activo:
            fondo, txt = c["boton_off"], c["tenue"]
        elif self.hover and self.estilo in ("secundario", "suave") and not self.seleccionado:
            fondo = c["boton_hover"]
        return fondo, legible(fondo, txt) if self.activo else txt

    def dibujar(self, sup):
        if not self.visible:
            return
        c = TEMA.c
        self.hover = self.rect.collidepoint(pygame.mouse.get_pos())
        presionado = self.hover and self.activo and pygame.mouse.get_pressed()[0]
        fondo, txt = self.colores()
        dy = self.sombra if presionado else (-1 if self.hover and self.activo else 0)
        r = self.rect.move(0, dy)
        sombra = 0 if presionado else (self.sombra if self.activo else 2)
        sticker(sup, r, fondo, self.radio, sombra, 3 if self.activo else 2,
                color_borde=c["borde"] if self.activo else c["tenue"])
        contenido_w = ancho_texto(self.etiqueta, self.tam, 800, "titulo") if self.etiqueta else 0
        ic = round(self.tam * 1.25)
        if self.icono:
            contenido_w += ic + (8 if self.etiqueta else 0)
        alineado_izq = self.costo is not None or self.atajo is not None
        x = r.x + 14 if alineado_izq else r.centerx - contenido_w / 2
        if self.icono:
            sup.blit(recursos.icono(self.icono, ic, txt, 2.4), (round(x), r.centery - ic // 2))
            x += ic + 8
        if self.etiqueta:
            ancho_max = r.right - x - (14 + 13 * (self.costo or 0) + (22 if self.atajo else 0))
            et = recortar(self.etiqueta, self.tam, ancho_max, 600, "titulo") if alineado_izq else self.etiqueta
            texto(sup, et, (x, r.centery + 1), self.tam, txt, peso=600, fam="titulo", ancla="ml")
        xr = r.right - 12
        if self.atajo:
            k = pygame.Rect(0, 0, 20, 20)
            k.midright = (xr, r.centery)
            pygame.draw.rect(sup, c["papel2"] if self.activo else c["boton_off"], k, border_radius=6)
            pygame.draw.rect(sup, txt, k, 1, border_radius=6)
            texto(sup, self.atajo, k.center, 12, c["texto"] if self.activo else c["tenue"], peso=800, ancla="c")
            xr = k.left - 6
        if self.costo:
            for i in range(self.costo):
                sup.blit(recursos.icono("zap", 15, c["mango"] if self.activo else c["tenue"], 2.6),
                         (xr - 15 - i * 13, r.centery - 8))

    def clic(self, pos):
        return self.visible and self.activo and self.rect.collidepoint(pos)


class Toasts:
    ICONOS = {"bueno": "circle-check", "malo": "triangle-alert", "logro": "trophy",
              "evento": "sparkles", "info": "info"}

    def __init__(self):
        self.items = []

    def agregar(self, s, tipo):
        if self.items and self.items[-1][0] == s:
            return
        self.items.append([s, tipo, pygame.time.get_ticks()])
        self.items = self.items[-4:]

    def dibujar(self, sup, x, y, ancho, abajo=False, max_items=2):
        c = TEMA.c
        ahora = pygame.time.get_ticks()
        self.items = [it for it in self.items if ahora - it[2] <= 5200][-max_items:]
        bloques = []
        for s, tipo, t0 in self.items:
            lineas = envolver(s, 14, ancho - 62, peso=700)
            bloques.append((lineas, tipo, t0, 20 + 19 * len(lineas)))
        if abajo:
            y -= sum(b[3] + 8 for b in bloques)
        for lineas, tipo, t0, h in bloques:
            edad = ahora - t0
            alpha = 255 if edad < 4500 else int(255 * (5200 - edad) / 700)
            desliz = 0 if TEMA.op["menos_movimiento"] else max(0, 24 - edad / 8)
            color = {"bueno": c["bueno"], "malo": c["malo"], "logro": c["logro"],
                     "evento": c["acento"]}.get(tipo, c["tinta2"])
            capa = pygame.Surface((ancho + 8, h + 10), pygame.SRCALPHA)
            sticker(capa, (3, 3, ancho, h), c["papel"], 14, 4, 3)
            pygame.draw.rect(capa, color, (6, 6, 8, h - 6), border_radius=4)
            circulo(capa, (34, 3 + h // 2), 13, color)
            capa.blit(recursos.icono(self.ICONOS.get(tipo, "info"), 16, c["sobre_color"], 2.6), (26, h // 2 - 5))
            yy = 13
            for l in lineas:
                texto(capa, l, (56, yy), 14, c["texto"], peso=700)
                yy += 19
            capa.set_alpha(alpha)
            sup.blit(capa, (x + desliz, y))
            y += h + 8
