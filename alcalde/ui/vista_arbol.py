"""Vista del árbol de mutaciones: cada nodo es la cara de quien reenvió."""
import math

import pygame

from . import recursos
from .juego_comun import cara, color_estado, estado_nodo
from .tema import TEMA
from .widgets import circulo, envolver, forma_estado, sticker, texto

R = 17


class VistaArbol:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.pos = {}
        self.objetivo = {}
        self.nacimiento = {}
        self.fantasmas = []
        self.seleccionado = None
        self.hover = None
        self.secuencia = []
        self.sec_nombre = ""
        self.sec_t0 = 0
        self.resaltes = {}
        self.resaltes_t0 = 0
        self._arbol_id = None

    def calcular_layout(self, arbol):
        self.objetivo = {}
        if arbol is None or arbol.raiz is None:
            return
        col = [0]
        xs = {}
        for n in arbol.postorden():
            if n.es_hoja:
                xs[n.id] = col[0]
                col[0] += 1
            else:
                xs[n.id] = (xs[n.hijos[0].id] + xs[n.hijos[-1].id]) / 2
        columnas = max(1, col[0] - 1)
        alt = max(1, arbol.altura())
        margen_x, margen_y = 54, 46
        dx = min(70, (self.rect.w - 2 * margen_x) / columnas)
        dy = min(84, (self.rect.h - margen_y - 40) / alt)
        ancho = dx * columnas
        x0 = self.rect.x + (self.rect.w - ancho) / 2
        for n in arbol.preorden():
            self.objetivo[n.id] = (x0 + xs[n.id] * dx, self.rect.y + margen_y + n.profundidad * dy)
        ahora = pygame.time.get_ticks()
        for nid, (x, y) in self.objetivo.items():
            if nid not in self.pos:
                nodo = arbol.buscar(nid)
                padre = nodo.padre
                inicio = self.pos.get(padre.id, (x, y)) if padre else (x, y)
                self.pos[nid] = list(inicio)
                self.nacimiento[nid] = ahora
        for nid in list(self.pos):
            if nid not in self.objetivo:
                self.fantasmas.append((*self.pos[nid], ahora))
                del self.pos[nid]

    def olvidar(self):
        self.pos.clear()
        self.nacimiento.clear()
        self.fantasmas.clear()
        self.secuencia = []

    def nodo_en(self, arbol, punto):
        if arbol is None:
            return None
        for nid, (x, y) in self.pos.items():
            if (x - punto[0]) ** 2 + (y - punto[1]) ** 2 <= (R + 4) ** 2:
                return arbol.buscar(nid)
        return None

    def animar_recorrido(self, nombre, ids):
        self.sec_nombre = nombre
        self.secuencia = list(ids)
        self.sec_t0 = pygame.time.get_ticks()

    def resaltar(self, **grupos):
        self.resaltes = {k: set(v) for k, v in grupos.items()}
        self.resaltes_t0 = pygame.time.get_ticks()

    def paso_actual(self):
        if not self.secuencia:
            return -1
        vel = 120 if TEMA.op["menos_movimiento"] else 380
        return min(len(self.secuencia), (pygame.time.get_ticks() - self.sec_t0) // vel)

    def dibujar(self, sup, arbol, p):
        c = TEMA.c
        ahora = pygame.time.get_ticks()
        if arbol is None or arbol.raiz is None:
            texto(sup, "Esta historia ya no circula.", self.rect.center, 16, c["tinta2"], peso=700, ancla="c")
            return
        mov = not TEMA.op["menos_movimiento"]
        ys = {}
        for n in arbol.preorden():
            ys.setdefault(n.profundidad, self.objetivo.get(n.id, (0, 0))[1])
        for d, y in ys.items():
            pygame.draw.line(sup, c["papel3"], (self.rect.x + 12, y), (self.rect.right - 12, y), 2)
            texto(sup, "Origen" if d == 0 else f"Ola {d}", (self.rect.x + 14, y - 22), 12, c["tinta2"], peso=800)
        for nid, (tx, ty) in self.objetivo.items():
            q = self.pos[nid]
            k = 1 if not mov else 0.18
            q[0] += (tx - q[0]) * k
            q[1] += (ty - q[1]) * k

        paso = self.paso_actual()
        visitados = {nid: i for i, nid in enumerate(self.secuencia[:paso])}
        vigente = (ahora - self.resaltes_t0) < 9000
        camino = self.resaltes.get("camino", set()) if vigente else set()

        for n in arbol.preorden():
            if n.padre is None or n.id not in self.pos or n.padre.id not in self.pos:
                continue
            a, b = self.pos[n.padre.id], self.pos[n.id]
            col, ancho = c["arista"], 3
            if n.verificado and not n.es_veraz and n.distorsion:
                col = c["arista_falsa"]
            if n.es_correccion:
                col = c["n_correccion"]
            if n.id in camino and n.padre.id in camino:
                col, ancho = c["resalte"], 7
                pygame.draw.line(sup, c["tinta"], a, b, ancho + 4)
            pygame.draw.line(sup, col, a, b, ancho)
            if n.distorsion and n.verificado:
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                circulo(sup, (mx, my), 7, c["n_falso"], c["borde"], 2)
                sup.blit(recursos.icono("zap", 10, c["sobre_color"], 3), (mx - 5, my - 5))

        vivos = []
        for x, y, t0 in self.fantasmas:
            e = (ahora - t0) / 650
            if e < 1:
                vivos.append((x, y, t0))
                pygame.draw.circle(sup, c["malo"], (x, y + e * 34), max(1, int(R * (1 - e))), 3)
        self.fantasmas = vivos

        for n in arbol.preorden():
            if n.id not in self.pos:
                continue
            x, y = self.pos[n.id]
            edad = ahora - self.nacimiento.get(n.id, 0)
            esc = 1 + 0.3 * math.sin(math.pi * min(1, edad / 280)) if (edad < 280 and mov) else 1
            r = R * esc
            self._nodo(sup, p, n, x, y, r, ahora)
            if n.id in camino:
                pygame.draw.circle(sup, c["resalte"], (x, y), r + 7, 4)
            if vigente and n.id in self.resaltes.get("mutacion", set()):
                pulso = 5 + 3 * math.sin(ahora / 120) if mov else 5
                pygame.draw.circle(sup, c["malo"], (x, y), r + 8 + pulso, 3)
                rr = pygame.Rect(0, 0, 92, 22)
                rr.midbottom = (x, y - r - 10)
                sticker(sup, rr, c["malo"], 11, 0, 2)
                texto(sup, "Mutó aquí", rr.center, 12, c["sobre_color"], peso=800, ancla="c")
            if n.id in visitados:
                i = visitados[n.id]
                ultimo = i == paso - 1 and paso < len(self.secuencia)
                pygame.draw.circle(sup, c["resalte"], (x, y), r + (9 if ultimo else 5), 4 if ultimo else 2)
                circulo(sup, (x + r + 3, y - r - 2), 10, c["resalte"], c["borde"], 2)
                texto(sup, str(i + 1), (x + r + 3, y - r - 2), 12, c["texto"], peso=900, ancla="c")
            if self.seleccionado is not None and n.id == self.seleccionado:
                pygame.draw.circle(sup, c["acento"], (x, y), r + 6, 4)

        if self.hover is not None and self.hover.id in self.pos:
            self._tooltip(sup, self.hover)

    def _nodo(self, sup, p, n, x, y, r, ahora):
        c = TEMA.c
        est = estado_nodo(n)
        if n.viral and not n.inmune:
            pulso = r + 6 + 4 * math.sin(ahora / 90)
            pygame.draw.circle(sup, c["mango"], (x, y), pulso, 4)
        img = cara(p, n.autor, round(2 * r), fondo=color_estado(est) if est != "nada" else c["papel2"],
                   expresion="confundido" if est == "falso" else "feliz" if est == "correccion" else "neutral",
                   grosor=3)
        sup.blit(img, (x - img.get_width() / 2, y - img.get_height() / 2))
        if n.inmune and not n.es_correccion:
            for k in range(8):
                a0 = k * math.pi / 4 + ahora / 1500
                pygame.draw.arc(sup, c["n_inmune"], (x - r - 6, y - r - 6, 2 * r + 12, 2 * r + 12), a0, a0 + 0.45, 3)
        forma_estado(sup, est, (x + r * 0.72, y + r * 0.72), 6)

    def _tooltip(self, sup, n):
        c = TEMA.c
        x, y = self.pos[n.id]
        ancho = 300
        lineas = envolver('"' + n.afirmacion.texto() + '"', 14, ancho - 24)
        cab = f"{n.autor}, {'origen' if n.es_raiz else 'ola ' + str(n.profundidad)}, le llegó a {n.alcance}"
        h = 36 + 19 * len(lineas)
        bx = min(max(self.rect.x + 4, x - ancho / 2), self.rect.right - ancho - 4)
        by = y + R + 14 if y < self.rect.centery else y - R - 14 - h
        sticker(sup, (bx, by, ancho, h), c["papel"], 12, 3, 2)
        texto(sup, cab, (bx + 12, by + 8), 12, c["tinta2"], peso=800)
        yy = by + 28
        for l in lineas:
            texto(sup, l, (bx + 12, yy), 14, c["texto"])
            yy += 19
