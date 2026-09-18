"""Dibujo del Árbol de Mutaciones.

El algoritmo de dibujo también usa recorridos del árbol:
  * POSTORDEN para ubicar x: cada hoja recibe la siguiente columna libre y
    cada padre se centra sobre sus hijos (ya ubicados).
  * La y es la profundidad (= ola de propagación).
"""
import math

import pygame

from .tema import TEMA
from .widgets import poligono_regular, texto, envolver

R = 15   # radio del nodo


class VistaArbol:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.pos = {}           # id -> [x, y] actual (animado)
        self.objetivo = {}      # id -> (x, y) calculado
        self.nacimiento = {}    # id -> ms
        self.fantasmas = []     # nodos podados que se desvanecen: (x, y, t0)
        self.seleccionado = None
        self.hover = None
        # animación de recorridos
        self.secuencia = []     # ids en orden
        self.sec_nombre = ""
        self.sec_t0 = 0
        self.resaltes = {}      # 'camino', 'mutacion', 'inmunes' -> set ids, con t0
        self.resaltes_t0 = 0

    # ------------------------------------------------------------ layout
    def calcular_layout(self, arbol):
        self.objetivo = {}
        if arbol is None or arbol.raiz is None:
            return
        col = [0]
        xs = {}
        for n in arbol.postorden():                 # <- POSTORDEN
            if n.es_hoja:
                xs[n.id] = col[0]
                col[0] += 1
            else:
                xs[n.id] = (xs[n.hijos[0].id] + xs[n.hijos[-1].id]) / 2
        columnas = max(1, col[0] - 1)
        alt = max(1, arbol.altura())
        margen_x, margen_y = 60, 40
        dx = min(64, (self.rect.w - 2 * margen_x) / columnas)
        dy = min(78, (self.rect.h - 2 * margen_y) / alt)
        ancho = dx * columnas
        x0 = self.rect.x + (self.rect.w - ancho) / 2
        for n in arbol.preorden():
            self.objetivo[n.id] = (x0 + xs[n.id] * dx,
                                   self.rect.y + margen_y + n.profundidad * dy)
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
        self.resaltes = {}

    # ------------------------------------------------------------ interacción
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
        return min(len(self.secuencia), (pygame.time.get_ticks() - self.sec_t0) // 380)

    # ------------------------------------------------------------ dibujo
    def dibujar(self, sup, arbol):
        c = TEMA.c
        ahora = pygame.time.get_ticks()
        pygame.draw.rect(sup, c["panel"], self.rect, border_radius=10)
        pygame.draw.rect(sup, c["borde"], self.rect, 1, border_radius=10)
        if arbol is None or arbol.raiz is None:
            texto(sup, "No hay publicaciones en este caso.", self.rect.center, 16, c["tenue"], centro=True)
            return
        # guías de olas (niveles)
        alt = arbol.altura()
        ys = {}
        for n in arbol.preorden():
            ys.setdefault(n.profundidad, self.objetivo.get(n.id, (0, 0))[1])
        for d, y in ys.items():
            pygame.draw.line(sup, c["panel2"], (self.rect.x + 8, y), (self.rect.right - 8, y), 1)
            texto(sup, "Origen" if d == 0 else f"Ola {d}", (self.rect.x + 10, y - 18), 12, c["tenue"])

        # mover posiciones hacia el objetivo (animación suave)
        for nid, (tx, ty) in self.objetivo.items():
            p = self.pos[nid]
            p[0] += (tx - p[0]) * 0.18
            p[1] += (ty - p[1]) * 0.18

        paso = self.paso_actual()
        visitados = {nid: i for i, nid in enumerate(self.secuencia[:paso])}
        vigente = (ahora - self.resaltes_t0) < 9000
        camino = self.resaltes.get("camino", set()) if vigente else set()

        # aristas
        for n in arbol.preorden():
            if n.padre is None or n.id not in self.pos:
                continue
            a, b = self.pos[n.padre.id], self.pos[n.id]
            col = c["arista"]
            ancho = 2
            if n.verificado and not n.es_veraz and n.distorsion:
                col = c["arista_falsa"]
            if n.id in camino and n.padre.id in camino:
                col, ancho = c["aviso"], 4
            if n.es_correccion:
                col = c["n_correccion"]
            pygame.draw.line(sup, col, a, b, ancho)
            if n.distorsion and n.verificado:
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                pygame.draw.circle(sup, c["n_falso"], (mx, my), 5)   # "aquí mutó"

        # fantasmas de nodos podados
        vivos = []
        for x, y, t0 in self.fantasmas:
            e = (ahora - t0) / 600
            if e < 1:
                vivos.append((x, y, t0))
                pygame.draw.circle(sup, c["malo"], (x, y + e * 30), int(R * (1 - e)) + 1, 2)
        self.fantasmas = vivos

        # nodos
        for n in arbol.preorden():
            if n.id not in self.pos:
                continue
            x, y = self.pos[n.id]
            edad = ahora - self.nacimiento.get(n.id, 0)
            esc = 1 + 0.25 * math.sin(math.pi * min(1, edad / 250)) if edad < 250 else 1
            r = R * esc
            self._dibujar_nodo(sup, n, x, y, r, ahora)
            if n.id in camino:
                pygame.draw.circle(sup, c["aviso"], (x, y), r + 6, 2)
            if vigente and n.id in self.resaltes.get("mutacion", set()):
                pulso = 6 + 3 * math.sin(ahora / 120)
                pygame.draw.circle(sup, c["malo"], (x, y), r + 6 + pulso, 3)
                texto(sup, "MUTÓ AQUÍ", (x, y - r - 22), 12, c["malo"], True, centro=True)
            if n.id in visitados:
                i = visitados[n.id]
                ultimo = i == paso - 1 and paso < len(self.secuencia)
                pygame.draw.circle(sup, c["aviso"], (x, y), r + (8 if ultimo else 4), 3 if ultimo else 1)
                texto(sup, str(i + 1), (x + r + 2, y - r - 4), 12, c["aviso"], True)
            if self.seleccionado is not None and n.id == self.seleccionado:
                pygame.draw.circle(sup, c["seleccion"], (x, y), r + 5, 2)
                pygame.draw.circle(sup, c["seleccion"], (x, y), r + 9, 1)

        # tooltip
        if self.hover is not None and self.hover.id in self.pos:
            self._tooltip(sup, self.hover)

    def _dibujar_nodo(self, sup, n, x, y, r, ahora):
        c = TEMA.c
        if n.viral and not n.inmune:
            pulso = r + 5 + 4 * math.sin(ahora / 90)
            pygame.draw.circle(sup, c["aviso"], (x, y), pulso, 2)
        if n.es_correccion:
            col = c["n_correccion"]
            pygame.draw.polygon(sup, col, poligono_regular((x, y), r + 3, 4, 0))
        elif not n.verificado:
            col = c["n_desconocido"]
            pygame.draw.circle(sup, col, (x, y), r)
        elif n.es_veraz:
            col = c["n_veraz"]
            pygame.draw.rect(sup, col, (x - r, y - r, 2 * r, 2 * r), border_radius=4)
        else:
            col = c["n_falso"]
            pygame.draw.polygon(sup, col, poligono_regular((x, y + 2), r + 4, 3, -math.pi / 2))
        if n.inmune and not n.es_correccion:
            for k in range(8):     # anillo punteado = rama contenida
                a0 = k * math.pi / 4 + ahora / 1500
                pygame.draw.arc(sup, c["n_inmune"], (x - r - 5, y - r - 5, 2 * r + 10, 2 * r + 10),
                                a0, a0 + 0.45, 2)
        inicial = n.autor[:1].upper()
        texto(sup, inicial, (x, y + (2 if n.verificado and not n.es_veraz else 0)), 14,
              (10, 12, 20), True, centro=True)

    def _tooltip(self, sup, n):
        c = TEMA.c
        x, y = self.pos[n.id]
        ancho = 300
        lineas = envolver('"' + n.afirmacion.texto() + '"', 14, ancho - 20)
        cab = f"{n.autor}  ·  {'origen' if n.es_raiz else 'ola ' + str(n.profundidad)}  ·  {n.alcance} personas"
        h = 34 + 18 * len(lineas)
        bx = min(max(self.rect.x + 4, x - ancho / 2), self.rect.right - ancho - 4)
        by = y + R + 12 if y < self.rect.centery else y - R - 12 - h
        pygame.draw.rect(sup, c["panel2"], (bx, by, ancho, h), border_radius=8)
        pygame.draw.rect(sup, c["acento"], (bx, by, ancho, h), 1, border_radius=8)
        texto(sup, cab, (bx + 10, by + 7), 12, c["tenue"], True)
        yy = by + 26
        for l in lineas:
            texto(sup, l, (bx + 10, yy), 14)
            yy += 18
