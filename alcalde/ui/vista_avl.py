"""Ventana del Archivo de Hechos (AVL): muestra la forma del árbol, altura y
factor de balance de cada nodo, la ruta de la última búsqueda y las
rotaciones realizadas."""
import pygame

from .tema import TEMA
from .widgets import texto, panel, parrafo


def dibujar_avl(sup, archivo, rect, ruta=(), hechos=None):
    c = TEMA.c
    capa = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
    capa.fill((0, 0, 0, 170))
    sup.blit(capa, (0, 0))
    panel(sup, rect, c["panel"], 14)
    texto(sup, "ARCHIVO DE HECHOS  ·  árbol AVL", (rect.x + 20, rect.y + 14), 22, c["acento"], True)
    texto(sup, f"{len(archivo)} hechos  ·  altura {archivo.altura}  ·  "
               f"válido: {'sí' if archivo.es_avl_valido() else 'NO'}   (Esc para cerrar)",
          (rect.x + 20, rect.y + 44), 14, c["tenue"])
    area = pygame.Rect(rect.x + 20, rect.y + 80, rect.w - 300, rect.h - 100)
    ruta = list(ruta)

    def _dib(n, x, y, dx):
        if n is None:
            return
        for hijo, sx in ((n.izq, -1), (n.der, 1)):
            if hijo:
                hx, hy = x + sx * dx, y + 78
                en_ruta = n.clave in ruta and hijo.clave in ruta
                pygame.draw.line(sup, c["aviso"] if en_ruta else c["arista"], (x, y), (hx, hy),
                                 3 if en_ruta else 2)
                _dib(hijo, hx, hy, dx / 2)
        w, h = 128, 40
        r = pygame.Rect(0, 0, w, h)
        r.center = (x, y)
        en_ruta = n.clave in ruta
        pygame.draw.rect(sup, c["panel2"], r, border_radius=8)
        pygame.draw.rect(sup, c["aviso"] if en_ruta else c["borde"], r, 3 if en_ruta else 1, border_radius=8)
        titulo = hechos[n.clave].titulo if hechos and n.clave in hechos else n.clave
        if len(titulo) > 17:
            titulo = titulo[:16] + "…"
        texto(sup, titulo, (x, y - 8), 12, c["texto"], True, centro=True)
        bal = (n.izq.altura if n.izq else 0) - (n.der.altura if n.der else 0)
        texto(sup, f"h={n.altura}  fb={bal:+d}", (x, y + 9), 11, c["tenue"], centro=True)
        if en_ruta:
            texto(sup, str(ruta.index(n.clave) + 1), (r.right - 4, r.y - 8), 13, c["aviso"], True)

    if archivo.raiz:
        _dib(archivo.raiz, area.centerx, area.y + 20, area.w / 4)
    # panel lateral: inorden + bitácora
    lx = rect.right - 270
    texto(sup, "Recorrido INORDEN (A-Z)", (lx, rect.y + 80), 15, c["acento"], True)
    y = rect.y + 104
    for clave, h in archivo.inorden():
        texto(sup, "· " + h.titulo, (lx, y), 13)
        y += 18
    y += 14
    texto(sup, "Última búsqueda", (lx, y), 15, c["acento"], True)
    y += 22
    y = parrafo(sup, " > ".join(ruta) if ruta else "—", lx, y, 250, 12, c["aviso"])
    y += 10
    texto(sup, "Rotaciones recientes", (lx, y), 15, c["acento"], True)
    y += 22
    for l in (archivo.bitacora[-5:] or ["(ninguna todavía)"]):
        y = parrafo(sup, l, lx, y, 250, 12, c["tenue"])
