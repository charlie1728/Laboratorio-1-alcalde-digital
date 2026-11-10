"""Dibuja el barrio de un turno: cámara que sigue al jugador, sprites ordenados por profundidad,
hilos del grafo social, efectos, noche y flechas hacia lo importante."""
import math
import random

import pygame

from . import personajes, sprites
from .ambiente import Ambiente, bolita, resplandor
from .ciudad import ruta
from .config import ALTO, ANCHO, ESC, TILE
from .recursos import CONTORNO, borde, escalar
from .sonido import SUBTITULOS
from .ui import render, texto

_suelo_escalado = None
# Cuánto puede pasarse la cámara del borde del mapa (en pixeles de pantalla). Así, cuando el jugador
# está en una orilla, los paneles del HUD (minimapa e indicadores a la derecha, reloj y tarjeta arriba)
# quedan encima de "las afueras" y no encima de donde se está jugando.
MARGEN_CAMARA = {"izq": 0, "der": 250, "arr": 110, "aba": 40}
AFUERAS = (26, 30, 44)


def suelo_escalado(mapa):
    global _suelo_escalado
    if _suelo_escalado is None:
        s = mapa.superficie
        _suelo_escalado = pygame.transform.scale(s, (s.get_width() * ESC, s.get_height() * ESC)).convert()
        for txt, x, y in mapa.carteles:
            img = render(txt, 18, (255, 255, 255), 700, (40, 26, 38), 2)
            r = img.get_rect(center=(int(x * ESC), int(y * ESC) - 6))
            fondo = r.inflate(18, 6)
            pygame.draw.rect(_suelo_escalado, (40, 26, 38), fondo.move(0, 3), border_radius=6)
            pygame.draw.rect(_suelo_escalado, (226, 72, 70), fondo, border_radius=6)
            pygame.draw.rect(_suelo_escalado, (255, 240, 220), fondo, 2, border_radius=6)
            _suelo_escalado.blit(img, r)
    return _suelo_escalado


_arboles = {}


def partes_arbol(img):
    """El árbol (ya con borde y escalado) partido en franjas: la punta se mece más que la mitad de la copa
    y el tronco no se mueve. Devuelve [(franja, y en pantalla, cuánto se mece)]."""
    hecho = _arboles.get(id(img))
    if hecho is None or hecho[1] is not img:
        grande = escalar(borde(img))
        w, h = grande.get_size()
        cortes = [(0, 12 * ESC, 1.0), (12 * ESC, 22 * ESC, 0.55), (22 * ESC, h, 0.0)]
        partes = [(grande.subsurface((0, y0, w, y1 - y0)), y0, f) for y0, y1, f in cortes]
        hecho = (partes, img)
        _arboles[id(img)] = hecho
    return hecho[0]


_vineta = []


def vineta():
    """Bordes de la pantalla un poquito más oscuros (como en una película). Son 4 franjas con degradado
    en vez de una imagen entera: cuesta menos dibujarlas y en las esquinas se suman solas."""
    if not _vineta:
        for lado, largo, grueso in (("arr", ANCHO, 110), ("aba", ANCHO, 110), ("izq", ALTO, 150), ("der", ALTO, 150)):
            horizontal = lado in ("arr", "aba")
            s = pygame.Surface((largo, grueso) if horizontal else (grueso, largo), pygame.SRCALPHA)
            for k in range(grueso):
                a = int(62 * (1 - k / grueso) ** 2.2)
                if horizontal:
                    s.fill((8, 6, 24, a), (0, k if lado == "arr" else grueso - 1 - k, largo, 1))
                else:
                    s.fill((8, 6, 24, a), (k if lado == "izq" else grueso - 1 - k, 0, 1, largo))
            pos = {"arr": (0, 0), "aba": (0, ALTO - grueso), "izq": (0, 0), "der": (ANCHO - grueso, 0)}[lado]
            _vineta.append((s, pos))
    return _vineta


_ventana_luz = []


def ventana_encendida():
    """La ventana de las casas con los vidrios prendidos (amarillo cálido) para la noche."""
    if not _ventana_luz:
        from .recursos import C
        img = C(617).copy()
        for y in range(img.get_height()):
            for x in range(img.get_width()):
                r, g, b, a = img.get_at((x, y))
                if a > 0 and r + g + b > 420:          # los vidrios son los pixeles claros
                    img.set_at((x, y), (255, 226, 120, 255) if y < 9 else (255, 196, 90, 255))
        _ventana_luz.append(escalar(img))
    return _ventana_luz[0]


class Render:
    def __init__(self, mundo, sonido=None, opciones=None):
        self.m = mundo
        self.son = sonido
        self.op = opciones or {}
        self.suelo = suelo_escalado(mundo.mapa)
        j = mundo.jugador
        self.cam = [j.x * ESC - ANCHO / 2, j.y * ESC - ALTO / 2]
        self._limitar()
        self.t = 0.0
        self.part = []
        self.textos = []
        self.cadenas = []
        self.olas = []
        self.rayos = []            # la verdad viajando de la estrella al vecino
        self.anillos = []
        self.subs = []
        self.avisos = []           # una o dos palabras grandes arriba ("¡VIRAL!", "¡PELEA!")
        self.brillos = {}
        self.temblor = 0.0
        self.capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        self.oscuro = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        self.fantasmas = []
        self.guia = []
        self.t_guia = 0.0
        self.rng = random.Random(3)
        self.sx = self.sy = 0
        self.flash = 0.0
        self.cuenta = False        # durante la cuenta regresiva no se muestra el "TÚ" (lo tapan las tarjetas)
        self.amb = Ambiente(mundo.mapa, mundo.ronda)      # agua, fuente, palomas, mariposas, hojas, nubes...
        # de noche no todas las ventanas están prendidas (y de vez en cuando alguien apaga o prende la luz)
        self.ventanas = [self.rng.random() < 0.7 for _ in mundo.mapa.ventanas_luz]
        self.t_ventanas = 3.0

    # ------------------------------------------------------------- coordenadas
    def _limitar(self):
        mw = self.m.mapa.superficie.get_width() * ESC
        mh = self.m.mapa.superficie.get_height() * ESC
        g = {"izq": 0, "der": 0, "arr": 0, "aba": 0} if self.op.get("demo") else MARGEN_CAMARA
        self.cam[0] = max(-g["izq"], min(mw - ANCHO + g["der"], self.cam[0]))
        self.cam[1] = max(-g["arr"], min(mh - ALTO + g["aba"], self.cam[1]))

    def a_pantalla(self, x, y):
        return (x * ESC - self.cam[0] + self.sx, y * ESC - self.cam[1] + self.sy)

    def visible(self, x, y, margen=80):
        px, py = self.a_pantalla(x, y)
        return -margen < px < ANCHO + margen and -margen < py < ALTO + margen

    # ------------------------------------------------------------- efectos que manda el mundo
    def procesar(self):
        m = self.m
        for fx in m.fx:
            tipo = fx[0]
            if tipo == "texto":
                _, x, y, s, color, grande = fx
                self.textos.append([x, y, s, color, grande, 0.0])
            elif tipo == "pop":
                self._estallido(fx[1], fx[2], fx[3], 14)
            elif tipo == "cadena":
                self.cadenas.append([fx[1], 0.0])
                for k, (x, y) in enumerate(fx[1]):
                    self._estallido(x, y, (170, 100, 255), 12, retraso=k * 0.08)
            elif tipo == "chispas":
                self._estallido(fx[1], fx[2], fx[3], 16, vel=60, grav=-20)
            elif tipo == "contagio":
                self._estallido(fx[1], fx[2], (150, 80, 220), 10, vel=30, grav=-30)
                self.anillos.append([fx[1], fx[2], 0.0, 0.5, (170, 100, 255), 18])
            elif tipo == "explosion":
                self._estallido(fx[1], fx[2], (255, 160, 60), 30, vel=110)
                self._estallido(fx[1], fx[2], (90, 90, 100), 16, vel=50, grav=-30, tam=2)
                self.anillos.append([fx[1], fx[2], 0.0, 0.5, (255, 220, 120), 40])
            elif tipo == "temblor":
                self.temblor = max(self.temblor, fx[1])
            elif tipo == "aviso":
                self.avisos = [a for a in self.avisos if a[0] != fx[1]][-1:] + [[fx[1], fx[2], 0.0]]
            elif tipo == "sonido":
                _, nombre, x, y = fx
                if self.son:
                    if nombre in ("pito", "antena", "reenvio") and x is not None and not self.visible(x, y, 0):
                        pass
                    else:
                        self.son.tocar(nombre)
                if self.op.get("subtitulos") and nombre in SUBTITULOS:
                    if x is None or self.visible(x, y, 0):
                        self.subs.append([x, y, SUBTITULOS[nombre], 0.0])
            elif tipo == "aparece":
                self.anillos.append([fx[1], fx[2], 0.0, 0.6, (255, 240, 150), 16])
                self._estallido(fx[1], fx[2], (255, 240, 160), 8, vel=40)
            elif tipo == "onda":
                self.anillos.append([fx[1], fx[2], 0.0, 0.8, (190, 120, 255), 24])
            elif tipo == "corazones":
                for k in range(6):
                    self.part.append({"x": fx[1] + self.rng.uniform(-10, 10), "y": fx[2], "vx": self.rng.uniform(-10, 10),
                                      "vy": self.rng.uniform(-40, -20), "vida": 1.4, "max": 1.4, "img": "corazon",
                                      "grav": 0, "ret": k * 0.08, "color": None, "tam": 1})
            elif tipo == "hilo":
                # el hilo se ilumina creciendo desde quien lo manda; por niveles del BFS, uno tras otro
                retraso = 0.28 * max(0, (fx[4] if len(fx) > 4 else 1) - 1)
                self.brillos[tuple(sorted((fx[1], fx[2])))] = {"t": 0.0, "fin": retraso + 1.5, "color": fx[3],
                                                               "desde": fx[1], "hasta": fx[2], "retraso": retraso}
            elif tipo == "ola":
                v = m.vecinos.get(fx[1])
                if v:
                    color = fx[3] if len(fx) > 3 else (255, 110, 160)
                    self.olas.append([fx[1], -fx[2] * 0.35, color])
            elif tipo == "verdad":
                # la estrella revienta en dorado y la verdad sale hacia el vecino más cercano
                self._estallido(fx[1], fx[2], (255, 220, 90), 22, vel=90)
                self.anillos.append([fx[1], fx[2], 0.0, 0.6, (255, 230, 120), 30])
                v = m.vecinos.get(fx[3])
                if v:
                    self.rayos.append([fx[1], fx[2] - 6, v.x, v.y - 14, 0.0])
            elif tipo == "poder":
                from .personajes import PERSONAJES
                color = PERSONAJES[fx[1]]["color"]
                radio = {"ana": 240, "beto": 230, "caro": 120, "dani": 110}[fx[1]]
                self.anillos.append([fx[2], fx[3] - 8, 0.0, 0.7, color, radio])
                self.anillos.append([fx[2], fx[3] - 8, -0.1, 0.7, (255, 255, 255), radio * 0.7])
                if fx[1] == "ana":
                    self.flash = 0.35
                self.temblor = max(self.temblor, 4)
            elif tipo == "puff":
                self._estallido(fx[1], fx[2], (230, 230, 240), 5, vel=20, grav=0)
        m.fx.clear()

    def _estallido(self, x, y, color, n, vel=80, grav=120, retraso=0.0, tam=1):
        for _ in range(n):
            a = self.rng.uniform(0, math.tau)
            v = self.rng.uniform(vel * 0.4, vel)
            vida = self.rng.uniform(0.35, 0.7)
            self.part.append({"x": x, "y": y, "vx": math.cos(a) * v, "vy": math.sin(a) * v - vel * 0.3,
                              "vida": vida, "max": vida, "color": color, "grav": grav, "ret": retraso,
                              "img": None, "tam": tam})

    # ------------------------------------------------------------- tiempo
    def actualizar(self, dt):
        self.t += dt
        self.procesar()
        j = self.m.jugador
        objetivo = (j.x * ESC - ANCHO / 2, j.y * ESC - ALTO / 2 - 10)
        k = min(1.0, dt * 6)
        self.cam[0] += (objetivo[0] - self.cam[0]) * k
        self.cam[1] += (objetivo[1] - self.cam[1]) * k
        self._limitar()
        vista = pygame.Rect(self.cam[0] / ESC - 24, self.cam[1] / ESC - 24, ANCHO / ESC + 48, ALTO / ESC + 56)
        self.amb.actualizar(dt, self.m, vista)
        self.t_ventanas -= dt
        if self.t_ventanas <= 0 and self.ventanas:
            self.t_ventanas = self.rng.uniform(2.0, 5.0)
            k = self.rng.randrange(len(self.ventanas))
            self.ventanas[k] = not self.ventanas[k]
        self.temblor = max(0.0, self.temblor - dt * 18)
        self.flash = max(0.0, getattr(self, "flash", 0.0) - dt)
        for p in self.part:
            if p["ret"] > 0:
                p["ret"] -= dt
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += p["grav"] * dt
            p["vida"] -= dt
        self.part = [p for p in self.part if p["vida"] > 0]
        for lista, dur in ((self.textos, 1.3), (self.subs, 1.2), (self.avisos, 1.8), (self.rayos, 0.45)):
            for e in lista:
                e[-1] += dt
            lista[:] = [e for e in lista if e[-1] < dur]
        for c in self.cadenas:
            c[1] += dt
        self.cadenas = [c for c in self.cadenas if c[1] < 0.8]
        for a in self.anillos:
            a[2] += dt
        self.anillos = [a for a in self.anillos if a[2] < a[3]]
        for o in self.olas:
            o[1] += dt
        self.olas = [o for o in self.olas if o[1] < 0.8]
        for k_, v in list(self.brillos.items()):
            v["t"] += dt
            if v["t"] >= v["fin"]:
                del self.brillos[k_]
        self.t_guia -= dt
        if self.t_guia <= 0:
            self.t_guia = 0.5
            self._calcular_guia()

    def _objetivo_urgente(self):
        m = self.m
        j = m.jugador
        if m.viral:
            return (m.viral.x, m.viral.y)
        for p in m.peleas:
            if p.get("activa") and not p.get("fin"):
                a, b = m.vecinos[p["a"]], m.vecinos[p["b"]]
                return ((a.x + b.x) / 2, (a.y + b.y) / 2)
        inf = m.infectados()
        if inf:
            cerca = min(inf, key=lambda v: math.dist(v.pos, j.pos))
            if not self.visible(*cerca.pos, -60):
                return cerca.pos
        if m.antenas:
            a = min(m.antenas, key=lambda a: math.dist((a.x, a.y), j.pos))
            return (a.x, a.y + 4)
        return None

    def _calcular_guia(self):
        """Ruta más corta (Dijkstra en el grafo de la ciudad) hacia lo más urgente, si no se ve."""
        m = self.m
        obj = None if self.op.get("demo") else self._objetivo_urgente()
        self.guia = []
        if obj is None or self.visible(*obj, -60):
            return
        j = m.jugador
        try:
            self.guia = [j.pos] + ruta(m.ciudad, m.mapa, j.pos, obj)
        except Exception:
            self.guia = []

    # ------------------------------------------------------------- dibujo
    def dibujar(self, pant):
        self.m
        self.sx = int(self.rng.uniform(-self.temblor, self.temblor)) if self.temblor > 0.5 else 0
        self.sy = int(self.rng.uniform(-self.temblor, self.temblor)) if self.temblor > 0.5 else 0
        cx, cy = int(self.cam[0]), int(self.cam[1])
        mw, mh = self.suelo.get_size()
        if 0 <= cx <= mw - ANCHO and 0 <= cy <= mh - ALTO:
            pant.blit(self.suelo, (self.sx, self.sy), pygame.Rect(cx, cy, ANCHO, ALTO))
        else:
            # en la orilla se ven las afueras de la ciudad, con un borde oscuro alrededor del mapa
            pant.fill(AFUERAS)
            borde = pygame.Rect(-cx + self.sx, -cy + self.sy, mw, mh)
            pygame.draw.rect(pant, (14, 16, 26), borde.inflate(12, 12), 6, border_radius=6)
            pant.blit(self.suelo, borde.topleft)
        self.amb.dibujar_suelo(pant, self)
        self.capa.fill((0, 0, 0, 0))
        self._guia(self.capa)
        self._hilos(self.capa)
        pant.blit(self.capa, (0, 0))
        self._sprites(pant)
        self.amb.dibujar_nubes(pant, self)
        self._pulsos(pant)
        self._proyectiles(pant)
        self._efectos(pant)
        self.amb.dibujar_aire(pant, self)
        self._luz_del_dia(pant)
        self._noche(pant)
        if not self.op.get("demo"):          # el menú ya tiene su propio velo
            for img, pos in vineta():
                pant.blit(img, pos)
        self._textos(pant)
        if not self.op.get("demo"):          # el mundo de fondo del menú no necesita guías
            self._flechas(pant)
        if getattr(self, "flash", 0) > 0:
            s = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            s.fill((255, 255, 255, int(200 * self.flash / 0.35)))
            pant.blit(s, (0, 0))

    def _px(self, surf, x, y, color, tam=1):
        sx, sy = self.a_pantalla(x, y)
        surf.fill(color, (int(sx), int(sy), ESC * tam, ESC * tam))

    def _guia(self, capa):
        if len(self.guia) < 2:
            return
        dist_total = 0.0
        for (x0, y0), (x1, y1) in zip(self.guia, self.guia[1:]):
            largo = math.dist((x0, y0), (x1, y1))
            n = int(largo / 9)
            for k in range(n):
                f = k / max(1, n)
                d = dist_total + largo * f
                if d > 260:
                    return
                fase = (d / 9 - self.t * 6) % 3
                alfa = int(200 * (1 - d / 260)) if fase < 1.2 else 60
                self._px(capa, x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, (255, 255, 255, max(0, alfa)), 1)
            dist_total += largo

    def _curva(self, va, vb):
        (x0, y0), (x1, y1) = (va.x, va.y - 9), (vb.x, vb.y - 9)
        largo = math.dist((x0, y0), (x1, y1))
        return x0, y0, x1, y1, largo, min(16, largo * 0.12)

    @staticmethod
    def _en_hilo(c, f):
        x0, y0, x1, y1, _, curva = c
        return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f - math.sin(f * math.pi) * curva

    def _linea_hilo(self, capa, c, color, alfa, grosor, punteada=False):
        n = max(4, int(c[4] / 12))
        pts = [self.a_pantalla(*self._en_hilo(c, k / n)) for k in range(n + 1)]
        if not punteada:
            pygame.draw.lines(capa, (*color, alfa), False, pts, grosor)
            return
        for k in range(0, n, 2):
            pygame.draw.line(capa, (*color, alfa), pts[k], pts[k + 1], grosor)

    def _brillo(self, capa, br):
        """Un hilo que se ilumina: crece desde quien manda (la verdad, una amistad nueva) y se apaga."""
        crece = min(1.0, max(0.0, (br["t"] - br["retraso"]) / 0.3))
        if crece <= 0:
            return
        c = self._curva(self.m.vecinos[br["desde"]], self.m.vecinos[br["hasta"]])
        alfa = int(255 * min(1.0, (br["fin"] - br["t"]) / 0.5))
        n = max(4, int(c[4] / 12))
        hasta = max(1, int(n * crece))
        pts = [self.a_pantalla(*self._en_hilo(c, k / n)) for k in range(hasta + 1)]
        pygame.draw.lines(capa, (*br["color"], alfa), False, pts, 5)
        if crece < 1:
            pygame.draw.circle(capa, (255, 255, 255, alfa), (int(pts[-1][0]), int(pts[-1][1])), 6)

    def _hilos(self, capa):
        """Grafo social. Para no llenar la pantalla de líneas solo resalta lo que importa en ese momento:
        - las amistades normales se ven tenues, y solo si los dos amigos están en pantalla;
        - el hilo por donde viaja un Bulo es morado;
        - en los últimos segundos antes de pasar el Bulo, el vecino morado marca con una línea punteada
          a qué amigo se lo va a pasar (así se alcanza a curarlo antes);
        - la verdad (dorado), las amistades nuevas (verde) y la cura de Beto (rosa) brillan un momento."""
        from .mundo import AVISO_REENVIO
        m = self.m
        activos = {tuple(sorted((p.desde, p.hasta))) for p in m.pulsos}
        for a, b, peso in m.social.aristas():
            va, vb = m.vecinos[a], m.vecinos[b]
            vis_a, vis_b = self.visible(va.x, va.y, 40), self.visible(vb.x, vb.y, 40)
            clave = tuple(sorted((a, b)))
            if clave in self.brillos:
                if vis_a or vis_b:
                    self._brillo(capa, self.brillos[clave])
                continue
            if clave in activos:
                if not (vis_a or vis_b):
                    continue
                color, alfa, grosor = (176, 110, 255), 200, 4
            else:
                if not (vis_a and vis_b):
                    continue
                color, alfa, grosor = (255, 255, 255), 22 + 8 * peso, 2
            self._linea_hilo(capa, self._curva(va, vb), color, alfa, grosor)
        # el aviso: a quién le va a pasar el Bulo este vecino morado
        for v in m.vecinos.values():
            if v.bulo is None or not v.siguiente or v.t_prop >= AVISO_REENVIO:
                continue
            u = m.vecinos[v.siguiente]
            if not (self.visible(v.x, v.y, 40) or self.visible(u.x, u.y, 40)):
                continue
            urgencia = 1 - v.t_prop / AVISO_REENVIO
            c = self._curva(v, u)
            alfa = int(150 + 90 * math.sin(self.t * (6 + 10 * urgencia)) ** 2)
            self._linea_hilo(capa, c, (190, 120, 255), alfa, 3, punteada=True)
            for k in range(2):
                f = (self.t * (0.5 + urgencia) + k / 2) % 1.0
                sx, sy = self.a_pantalla(*self._en_hilo(c, f))
                pygame.draw.circle(capa, (200, 140, 255, 230), (int(sx), int(sy)), 4)
        # peleas: hilo rojo que tiembla
        for p in m.peleas:
            if p.get("activa") and not p.get("fin"):
                va, vb = m.vecinos[p["a"]], m.vecinos[p["b"]]
                for k in range(12):
                    f = k / 12
                    self._px(capa, va.x + (vb.x - va.x) * f, va.y - 10 + (vb.y - va.y) * f + math.sin(self.t * 30 + k) * 1.5,
                             (255, 70, 70, 220))

    def _sprites(self, pant):
        m = self.m
        dib = []
        vista = pygame.Rect(self.cam[0] / ESC - 40, self.cam[1] / ESC - 40, ANCHO / ESC + 80, ALTO / ESC + 100)
        for img, x, yb, tipo in m.mapa.props:
            if vista.collidepoint(x + 8, yb - 8) or vista.collidepoint(x + 8, yb - img.get_height()):
                dib.append((yb, 0, "prop", img, x, yb, tipo))
        for c in m.trafico.carros:
            x, y = c.topleft()
            img = c.img
            if vista.colliderect((x, y, img.get_width(), img.get_height())):
                dib.append((y + img.get_height() - 2, 0, img, x, y))
        for sx_, sy_ in m.mapa.semaforos:
            dib.append(((sy_ + 1) * TILE, 1, "semaforo", sx_ * TILE + 8, (sy_ + 1) * TILE - 2))
        for v in m.vecinos.values():
            if vista.collidepoint(v.x, v.y):
                dib.append((v.y, 2, "vecino", v))
        for s in m.estrellas:
            if vista.collidepoint(s.x, s.y):
                dib.append((s.y + 6, 2, "estrella", s))
        for a in m.antenas:
            dib.append((a.y, 2, "antena", a))
        for b in m.bulos.values():
            if b.estado == "libre" and vista.collidepoint(b.x, b.y):
                dib.append((b.y + 10, 3, "bulo", b))
        if m.viral:
            dib.append((m.viral.y + 14, 3, "viral", m.viral))
        for f in self.fantasmas:
            dib.append((f["y"], 2, "fantasma", f))
        dib.append((m.jugador.y, 2, "jugador", m.jugador))
        dib.sort(key=lambda d: (d[0], d[1]))
        for d in dib:
            if isinstance(d[2], pygame.Surface):
                img, x, y = d[2], d[3], d[4]
                pant.blit(escalar(borde(img)), self.a_pantalla(x - 1, y - 1))
            else:
                getattr(self, "_d_" + d[2])(pant, *d[3:])

    def _borde(self, pant, img, x, y):
        """Modo alto contraste: un borde blanco grueso alrededor de lo importante (por fuera del borde
        oscuro que ya tiene todo)."""
        sil = escalar(sprites.silueta(borde(img), (255, 255, 255)))
        sx, sy = self.a_pantalla(x - 1, y - 1)
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
            pant.blit(sil, (sx + dx, sy + dy))

    def _sombra(self, pant, x, y, ancho=10):
        sx, sy = self.a_pantalla(x - ancho / 2, y - 2)
        pant.blit(escalar(sprites.sombra(ancho)), (sx, sy))

    def _d_prop(self, pant, img, x, yb, tipo):
        """Árboles, postes, el paradero y lo alto: todo con borde oscuro. Los árboles se mecen con el
        viento (la punta más que el medio; el tronco queda quieto)."""
        y = yb - img.get_height()
        sx, sy = self.a_pantalla(x - 1, y - 1)
        if tipo != "arbol":
            pant.blit(escalar(borde(img)), (sx, sy))
            return
        viento = math.sin(self.t * 1.5 + x * 0.045) * 0.75 + math.sin(self.t * 3.3 + x * 0.13) * 0.25
        for parte, oy, fuerza in partes_arbol(img):
            pant.blit(parte, (sx + round(viento * fuerza * 3), sy + oy))

    def _d_semaforo(self, pant, x, yb):
        sx, sy = self.a_pantalla(x, yb)
        pygame.draw.rect(pant, CONTORNO, (sx - 6, sy - 66, 12, 69), border_radius=2)
        pygame.draw.rect(pant, (60, 60, 72), (sx - 3, sy - 66, 6, 66))
        pygame.draw.rect(pant, (90, 92, 106), (sx - 3, sy - 66, 2, 66))
        pygame.draw.rect(pant, CONTORNO, (sx - 15, sy - 99, 30, 42), border_radius=7)
        pygame.draw.rect(pant, (34, 34, 44), (sx - 12, sy - 96, 24, 36), border_radius=5)
        verde = self.m.trafico.verde
        for k, (col, on) in enumerate((((240, 60, 60), verde != "h"), ((80, 230, 110), verde == "h"))):
            c = col if on else tuple(v // 4 for v in col)
            cy_ = int(sy - 87 + k * 17)
            if on:     # la luz que está prendida brilla alrededor
                pant.blit(bolita(14, col, 70), (int(sx) - 14, cy_ - 14))
            pygame.draw.circle(pant, c, (int(sx), cy_), 6)
            if on:
                pygame.draw.circle(pant, (255, 255, 255), (int(sx) - 2, cy_ - 2), 2)

    def _d_vecino(self, pant, v):
        cuadro = int(v.paso) % 4 if v.mov else 0
        img = sprites.vecino(v.tipo, v.variante, v.dir, cuadro)
        if v.bulo is not None:
            img = sprites.morado(img)
        salto = math.sin(v.salto / 0.4 * math.pi) * 4 if v.salto > 0 else 0
        temblor = math.sin(self.t * 40) * 1 if (v.pelea and v.pelea.get("activa")) else 0
        self._sombra(pant, v.x, v.y, 10)
        if v.escudo > 0:
            r = 8 + math.sin(self.t * 5) * 1
            sx, sy = self.a_pantalla(v.x, v.y)
            alfa = 255 if v.escudo > 3 or int(self.t * 8) % 2 else 90
            pygame.draw.ellipse(pant, (255, 214, 70, alfa), (sx - r * ESC, sy - 3 * ESC, 2 * r * ESC, 6 * ESC), 3)
        x, y = v.x - 8 + temblor, v.y - 16 - salto
        con_borde = borde(img)
        if v.escudo > 0:
            sil = escalar(sprites.silueta(con_borde, (255, 226, 110)))
            for dx, dy in ((-0.67, 0), (0.67, 0), (0, -0.67)):
                pant.blit(sil, self.a_pantalla(x - 1 + dx, y - 1 + dy))
        if v.bulo is not None:
            # un aura morada que palpita: "a este hay que curarlo"
            sx, sy = self.a_pantalla(v.x, v.y - 10)
            r = int(13 * ESC + math.sin(self.t * 6 + len(v.nombre)) * 4)
            aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (170, 90, 255, 55), (r, r), r)
            pygame.draw.circle(aura, (200, 140, 255, 150), (r, r), r, 3)
            pant.blit(aura, (sx - r, sy - r))
        pant.blit(escalar(con_borde), self.a_pantalla(x - 1, y - 1))
        if v.bulo is not None and v.bulo in self.m.bulos:
            b = self.m.bulos[v.bulo]
            corona = self.m.arbol.es_raiz(b.id) and self.m.arbol.tiene_hijos(b.id)
            bob = math.sin(self.t * 4 + b.id) * 1.2
            ib = sprites.bulo(int(self.t * 3 + b.id) % 2, corona, False, (0, 1))
            pant.blit(escalar(borde(ib)), self.a_pantalla(v.x - 9, v.y - 32 - salto + bob))
        if v.pelea and v.pelea.get("activa") and v.pelea["a"] == v.nombre:
            otro = self.m.vecinos[v.pelea["b"]]
            mx, my = (v.x + otro.x) / 2, min(v.y, otro.y) - 34
            nube = sprites.nube_pelea(self.t)
            sx, sy = self.a_pantalla(mx - 13, my - 8)
            pant.blit(pygame.transform.scale(nube, (nube.get_width() * ESC, nube.get_height() * ESC)), (sx, sy))
            frac = max(0.0, v.pelea["t"] / 15.0)
            cx_, cy_ = self.a_pantalla(mx, my - 12)
            pygame.draw.arc(pant, (255, 90, 90), (cx_ - 16, cy_ - 16, 32, 32), math.pi / 2, math.pi / 2 + frac * math.tau, 5)
            texto(pant, "!!", (cx_, cy_), 22, (255, 230, 80), "center")
            # cuántos golpes faltan para calmarlos: casillas que se llenan de verde
            from .mundo import GOLPES_PELEA
            for k in range(GOLPES_PELEA):
                px_ = int(cx_ - 10 * (GOLPES_PELEA - 1) + k * 20)
                lleno = k < v.pelea.get("golpes", 0)
                pygame.draw.circle(pant, (20, 14, 40), (px_, int(cy_ + 38)), 8)
                pygame.draw.circle(pant, (120, 235, 150) if lleno else (90, 84, 110), (px_, int(cy_ + 38)), 6)

    def _d_estrella(self, pant, s):
        bob = math.sin(self.t * 3 + s.id) * 1.5
        sx, sy = self.a_pantalla(s.x, s.y)
        # columna de luz para verla de lejos
        col = pygame.Surface((10, 60), pygame.SRCALPHA)
        for yy in range(60):
            col.fill((255, 230, 120, int(70 * (yy / 60))), (0, yy, 10, 1))
        pant.blit(col, (sx - 5, sy - 80))
        self._sombra(pant, s.x, s.y + 6, 8)
        img = sprites.estrella(brillo=int(self.t * 2) % 2)
        if s.vida < 5 and int(self.t * 8) % 2:
            return
        if self.op.get("contraste"):
            self._borde(pant, img, s.x - 8, s.y - 10 + bob)
        pant.blit(escalar(borde(img)), self.a_pantalla(s.x - 9, s.y - 11 + bob))

    def _d_antena(self, pant, a):
        luz = int(self.t * 3) % 2 == 0
        img = sprites.antena(luz, a.golpe > 0)
        self._sombra(pant, a.x, a.y, 14)
        pant.blit(escalar(borde(img)), self.a_pantalla(a.x - 9, a.y - 41))
        sx, sy = self.a_pantalla(a.x, a.y - 40)
        for k in range(3):
            r = ((self.t * 30 + k * 12) % 36) + 6
            alfa = int(255 * (1 - r / 42))
            s = pygame.Surface((int(r * 2 * ESC), int(r * 2 * ESC)), pygame.SRCALPHA)
            pygame.draw.arc(s, (190, 120, 255, alfa), s.get_rect(), math.radians(35), math.radians(145), 3)
            pant.blit(s, (sx - r * ESC, sy - r * ESC + 10))
        for k in range(a.vida_max):
            c = (255, 90, 90) if k < a.vida else (70, 50, 70)
            pygame.draw.rect(pant, c, (sx - a.vida_max * 7 + k * 14, sy - 26, 11, 8), border_radius=3)

    def _d_bulo(self, pant, b):
        m = self.m
        j = m.jugador
        corona = m.arbol.es_raiz(b.id) and m.arbol.tiene_hijos(b.id)
        mir = (1 if j.x > b.x else -1, 1 if j.y > b.y else 0)
        bob = math.sin(b.t * 4) * 2
        self._sombra(pant, b.x, b.y + 10, 9)
        img = sprites.bulo(int(b.t * 5) % 2, corona, b.congelado > 0, mir)
        if self.op.get("contraste"):
            self._borde(pant, img, b.x - 8, b.y - 9 + bob)
        pant.blit(escalar(borde(img)), self.a_pantalla(b.x - 9, b.y - 10 + bob))
        if b.candidato:
            from .partida import CANDIDATOS as INFO
            color = INFO.get(b.candidato, ("", "", (255, 255, 255)))[2]
            pant.blit(escalar(sprites.bandera(color)), self.a_pantalla(b.x + 3, b.y - 15 + bob))

    def _d_viral(self, pant, v):
        img = sprites.bulo_gigante(self.t)
        golpe = v.golpe > 0
        self._sombra(pant, v.x, v.y + 14, 20)
        x, y = self.a_pantalla(v.x - 17, v.y - 23 + math.sin(self.t * 3) * 2)
        grande = escalar(borde(img))
        if golpe:
            grande = escalar(sprites.silueta(borde(img), (255, 255, 255)))
        pant.blit(grande, (x, y))
        cx, cy = self.a_pantalla(v.x, v.y - 30)
        r = 26 + math.sin(self.t * 10) * 3
        pygame.draw.circle(pant, (255, 60, 110), (int(cx), int(cy)), int(r), 4)
        texto(pant, str(max(0, math.ceil(v.t))), (cx, cy), 30, (255, 255, 255), "center")
        for k in range(v.vida):
            pygame.draw.circle(pant, (255, 90, 140), (int(cx - 14 + k * 14), int(cy - 40)), 5)
        obj = self.m.vecinos[v.objetivo]
        for k in range(10):
            f = k / 10
            if int(self.t * 6 + k) % 2:
                self._px(pant, v.x + (obj.x - v.x) * f, v.y + (obj.y - 20 - v.y) * f, (255, 90, 140))

    def _d_fantasma(self, pant, f):
        cs = personajes.cuadros(f["clave"])
        img = cs[f.get("dir", "abajo")][int(f.get("paso", 0)) % 4]
        g = escalar(borde(img)).copy()
        g.set_alpha(110)
        pant.blit(g, self.a_pantalla(f["x"] - 9, f["y"] - 24))
        sx, sy = self.a_pantalla(f["x"], f["y"] - 26)
        texto(pant, f["nombre"], (sx, sy), 14, (220, 220, 255), "midbottom", 600, alfa=170)

    def _d_jugador(self, pant, j):
        from .personajes import PERSONAJES
        color = PERSONAJES[j.clave]["color"]
        sx, sy = self.a_pantalla(j.x, j.y)
        r = 9 + math.sin(self.t * 6) * 1
        pygame.draw.ellipse(pant, (0, 0, 0, 90), (sx - 6 * ESC, sy - 2 * ESC, 12 * ESC, 4 * ESC))
        pygame.draw.ellipse(pant, color, (sx - r * ESC, sy - 3.3 * ESC, 2 * r * ESC, 6.6 * ESC), 4)
        cs = personajes.cuadros(j.clave, j.piel, j.pelo)
        cuadro = int(j.paso) % 4 if j.mov else 0
        img = cs[j.dir][cuadro]
        ox = j.vec[0] * 1.5 if j.lanzo > 0 else 0
        bob = -1 if (j.mov and cuadro in (1, 3)) else 0
        pant.blit(escalar(borde(img)), self.a_pantalla(j.x - 9 + ox, j.y - 24 + bob))
        if (self.m.t < 4 or self.op.get("contraste")) and not self.op.get("demo") and not self.cuenta:
            texto(pant, "TÚ", (sx, sy - 27 * ESC), 18, color, "midbottom")

    def _pulsos(self, pant):
        m = self.m
        for p in m.pulsos:
            x, y = m._pos_pulso(p)
            if not self.visible(x, y):
                continue
            for k in range(1, 5):
                f2 = max(0.0, p.f - k * 0.03)
                a, b = m.vecinos[p.desde], m.vecinos[p.hasta]
                (x0, y0), (x1, y1) = a.cabeza, b.cabeza
                tx, ty = x0 + (x1 - x0) * f2, y0 + (y1 - y0) * f2 - math.sin(f2 * math.pi) * 14
                self._px(pant, tx, ty, (180, 110, 255))
            pequeno = sprites.bulo_chico(int(self.t * 8) % 2, p.congelado > 0)
            pant.blit(escalar(borde(pequeno)), self.a_pantalla(x - 6, y - 7))

    def _proyectiles(self, pant):
        for pr in self.m.proyectiles:
            for k, (x, y) in enumerate(pr.rastro):
                sx, sy = self.a_pantalla(x, y)
                pygame.draw.circle(pant, pr.color, (int(sx), int(sy)), 2 + k)
            sx, sy = self.a_pantalla(pr.x, pr.y)
            img = escalar(sprites.herramienta(pr.clave))
            giro = (0.5 - pr.vida) * 900 * (1 if pr.vx >= 0 else -1)
            rot = pygame.transform.rotate(img, giro)
            pant.blit(rot, rot.get_rect(center=(int(sx), int(sy))))

    def _efectos(self, pant):
        for p in self.part:
            if p["ret"] > 0:
                continue
            sx, sy = self.a_pantalla(p["x"], p["y"])
            if p["img"] == "corazon":
                img = escalar(sprites.corazon())
                pant.blit(img, (sx, sy))
                continue
            t = max(1, int(ESC * p["tam"] * (0.6 + p["vida"] / p["max"])))
            pant.fill(p["color"], (int(sx), int(sy), t, t))
        for x, y, t, dur, color, radio in self.anillos:
            if t < 0:
                continue
            f = t / dur
            sx, sy = self.a_pantalla(x, y)
            r = int(radio * ESC * (0.3 + 0.7 * f))
            if r > 2:
                s = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(s, (*color, int(255 * (1 - f))), (r + 4, r + 4), r, max(2, int(6 * (1 - f))))
                pant.blit(s, (sx - r - 4, sy - r - 4))
        for o in self.olas:
            if o[1] < 0:
                continue
            v = self.m.vecinos.get(o[0])
            if not v:
                continue
            f = o[1] / 0.8
            sx, sy = self.a_pantalla(v.x, v.y - 10)
            pygame.draw.circle(pant, o[2], (int(sx), int(sy)), int(20 + 50 * f), max(1, int(6 * (1 - f))))
        for x0, y0, x1, y1, t in self.rayos:
            f = min(1.0, t / 0.25)
            a = self.a_pantalla(x0, y0)
            b = self.a_pantalla(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
            pygame.draw.line(pant, (255, 236, 150), a, b, 7)
            pygame.draw.line(pant, (255, 255, 255), a, b, 3)
        for pos, t in self.cadenas:
            n = min(len(pos), int(t / 0.08) + 1)
            for (x0, y0), (x1, y1) in zip(pos[:n], pos[1:n]):
                a = self.a_pantalla(x0, y0)
                b = self.a_pantalla(x1, y1)
                pygame.draw.line(pant, (220, 180, 255), a, b, 4)

    def _luz_del_dia(self, pant):
        ronda = self.m.ronda
        if ronda == 2:
            s = self.oscuro
            s.fill((255, 140, 60, 30))
            pant.blit(s, (0, 0))
        elif ronda >= 3:
            s = self.oscuro
            s.fill((14, 18, 52, 128))
            luces = [(x, y, 70) for x, y in self.m.mapa.luces]
            j = self.m.jugador
            luces.append((j.x, j.y - 10, 110))
            luces += [(e.x, e.y, 40) for e in self.m.estrellas]
            luces += [(a.x, a.y - 30, 50) for a in self.m.antenas]
            luces += [(x, y + 6, 26) for (x, y), on in zip(self.m.mapa.ventanas_luz, self.ventanas) if on]
            for c in self.m.trafico.carros:          # los faros alumbran adelante del carro
                luces.append((*self._faros(c)[1], 30))
            for x, y, r in luces:
                if not self.visible(x, y, r * ESC):
                    continue
                sx, sy = self.a_pantalla(x, y)
                img = sprites.luz(r * ESC // 2)
                s.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2), special_flags=pygame.BLEND_RGBA_SUB)
            pant.blit(s, (0, 0))

    def _noche(self, pant):
        """Ya oscuro: las ventanas prendidas, los bombillos de los postes y las luciérnagas brillan
        (la luz se suma a lo de abajo, así se ve que alumbra)."""
        if self.m.ronda < 3:
            return
        vidrio = ventana_encendida()
        for (x, y), on in zip(self.m.mapa.ventanas_luz, self.ventanas):
            if on and self.visible(x, y, 40):
                sx, sy = self.a_pantalla(x - 8, y - 8)
                pant.blit(vidrio, (int(sx), int(sy)))
                g = resplandor(30, (110, 80, 20))
                pant.blit(g, (int(sx) + 24 - 30, int(sy) + 24 - 30), special_flags=pygame.BLEND_RGB_ADD)
        bombillo = resplandor(20, (230, 190, 90))
        charco = resplandor(80, (56, 42, 12))          # la luz cálida que cae al piso
        for x, y in self.m.mapa.luces:
            if not self.visible(x, y - 30, 120):
                continue
            sx, sy = self.a_pantalla(x, y)
            pant.blit(charco, (int(sx) - 80, int(sy) - 80), special_flags=pygame.BLEND_RGB_ADD)
            for dx in (-6, 5):                         # los dos bombillos en las puntas de la T del poste
                bx, by = self.a_pantalla(x + dx, y - 29)
                pant.blit(bombillo, (int(bx) - 20 + 1, int(by) - 20), special_flags=pygame.BLEND_RGB_ADD)
        faro = resplandor(16, (200, 180, 100))
        charco_faro = resplandor(46, (64, 56, 28))
        for c in self.m.trafico.carros:               # los faros prendidos y la luz que echan al piso
            (fx, fy), (px, py) = self._faros(c)
            if self.visible(fx, fy, 60):
                sx, sy = self.a_pantalla(px, py)
                pant.blit(charco_faro, (int(sx) - 46, int(sy) - 46), special_flags=pygame.BLEND_RGB_ADD)
                sx, sy = self.a_pantalla(fx, fy)
                pant.blit(faro, (int(sx) - 16, int(sy) - 16), special_flags=pygame.BLEND_RGB_ADD)
        self.amb.dibujar_noche(pant, self)

    @staticmethod
    def _faros(c):
        """Dónde están los faros de un carro y dónde cae su luz (adelante, según para dónde va)."""
        x, y = c.topleft()
        w, h = c.img.get_size()
        return {"der": ((x + w - 2, y + h * 0.62), (x + w + 10, y + h / 2)),
                "izq": ((x + 2, y + h * 0.62), (x - 10, y + h / 2)),
                "abajo": ((x + w / 2, y + h - 3), (x + w / 2, y + h + 10)),
                "arriba": ((x + w / 2, y + 4), (x + w / 2, y - 10))}[c.carril.dir]

    def _textos(self, pant):
        for x, y, s, color, grande, t in self.textos:
            f = t / 1.3
            sx, sy = self.a_pantalla(x, y - 22 * f)
            texto(pant, s, (sx, sy), 26 if grande else 20, color, "center", alfa=int(255 * min(1, 2 * (1 - f))))
        for x, y, s, t in self.subs:
            if x is None:
                continue
            sx, sy = self.a_pantalla(x, y - 30)
            texto(pant, s, (sx, sy - t * 10), 16, (255, 255, 255), "center", 700, (90, 40, 140))

    def _flechas(self, pant):
        """Flechas en el borde hacia lo importante que no se ve, con un dibujito (sin palabras)."""
        m = self.m
        objetivos = [((a.x, a.y - 20), (255, 90, 90), sprites.antena()) for a in m.antenas]
        if m.viral:
            objetivos.append(((m.viral.x, m.viral.y), (255, 80, 150), sprites.bulo(0, True, False, (0, 1), color=(200, 60, 200))))
        for p in m.peleas:
            if p.get("activa") and not p.get("fin"):
                a = m.vecinos[p["a"]]
                objetivos.append(((a.x, a.y), (255, 150, 80), sprites.nube_pelea(self.t)))
        if m.estrellas:
            e = min(m.estrellas, key=lambda s: math.dist((s.x, s.y), m.jugador.pos))
            objetivos.append(((e.x, e.y), (255, 214, 70), sprites.estrella()))
        cx, cy = ANCHO / 2, ALTO / 2
        # zona segura: las flechas nunca tapan la tarjeta, el minimapa, los indicadores ni el botón de poder
        x0, x1, y0, y1 = 70, 1040, 185, 595
        for (x, y), color, icono in objetivos:
            if self.visible(x, y, -30):
                continue
            sx, sy = self.a_pantalla(x, y)
            ang = math.atan2(sy - cy, sx - cx)
            ca, sa = math.cos(ang), math.sin(ang)
            k = min((x1 - cx) / ca if ca > 1e-3 else (x0 - cx) / ca if ca < -1e-3 else 1e9,
                    (y1 - cy) / sa if sa > 1e-3 else (y0 - cy) / sa if sa < -1e-3 else 1e9)
            px_, py_ = cx + ca * k, cy + sa * k
            pulso = 4 * math.sin(self.t * 8)
            pts = [(px_ + math.cos(ang) * (22 + pulso), py_ + math.sin(ang) * (22 + pulso)),
                   (px_ + math.cos(ang + 2.4) * 16, py_ + math.sin(ang + 2.4) * 16),
                   (px_ + math.cos(ang - 2.4) * 16, py_ + math.sin(ang - 2.4) * 16)]
            pygame.draw.polygon(pant, (20, 14, 40), [(a + 2, b + 3) for a, b in pts])
            pygame.draw.polygon(pant, color, pts)
            ix, iy = px_ - math.cos(ang) * 30, py_ - math.sin(ang) * 30
            pygame.draw.circle(pant, (20, 14, 40), (int(ix), int(iy)), 19)
            pygame.draw.circle(pant, color, (int(ix), int(iy)), 19, 3)
            alto = 30
            img = pygame.transform.scale(icono, (max(1, icono.get_width() * alto // icono.get_height()), alto))
            if img.get_width() > 32:
                img = pygame.transform.scale(icono, (32, max(1, icono.get_height() * 32 // icono.get_width())))
            pant.blit(img, img.get_rect(center=(int(ix), int(iy))))
