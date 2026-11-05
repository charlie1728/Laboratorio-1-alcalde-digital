"""Dibuja el barrio de un turno: cámara que sigue al jugador, sprites ordenados por profundidad,
hilos del grafo social, efectos, noche y flechas hacia lo importante."""
import math
import random

import pygame

from . import personajes, sprites
from .ciudad import ruta
from .config import ALTO, ANCHO, ESC, TILE
from .recursos import escalar
from .sonido import SUBTITULOS
from .ui import render, texto

_suelo_escalado = None


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
        self.anillos = []
        self.subs = []
        self.banners = []
        self.toasts = []
        self.brillos = {}
        self.burbujas = {}
        self.temblor = 0.0
        self.capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        self.oscuro = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        self.fantasmas = []
        self.guia = []
        self.t_guia = 0.0
        self.rng = random.Random(3)
        self.sx = self.sy = 0
        self.flash = 0.0

    # ------------------------------------------------------------- coordenadas
    def _limitar(self):
        mw = self.m.mapa.superficie.get_width() * ESC
        mh = self.m.mapa.superficie.get_height() * ESC
        self.cam[0] = max(0, min(mw - ANCHO, self.cam[0]))
        self.cam[1] = max(0, min(mh - ALTO, self.cam[1]))

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
            elif tipo == "banner":
                self.banners.append([fx[1], fx[2], fx[3], 0.0])
                if self.son:
                    self.son.tocar("alarma" if "VIRAL" in fx[1] else "fanfarria" if "Detuviste" in fx[1] else "cuenta")
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
                self.brillos[tuple(sorted((fx[1], fx[2])))] = [2.0, fx[3]]
            elif tipo == "ola":
                v = m.vecinos.get(fx[1])
                if v:
                    self.olas.append([fx[1], -fx[2] * 0.35, (255, 110, 160)])
            elif tipo == "poder":
                from .personajes import PERSONAJES
                color = PERSONAJES[fx[1]]["color"]
                radio = {"ana": 190, "beto": 160, "caro": 85, "dani": 95}[fx[1]]
                self.anillos.append([fx[2], fx[3] - 8, 0.0, 0.7, color, radio])
                self.anillos.append([fx[2], fx[3] - 8, -0.1, 0.7, (255, 255, 255), radio * 0.7])
                if fx[1] == "ana":
                    self.flash = 0.35
                self.temblor = max(self.temblor, 4)
            elif tipo == "puff":
                self._estallido(fx[1], fx[2], (230, 230, 240), 5, vel=20, grav=0)
            elif tipo == "decision":
                self.toasts.append([fx[2], 0.0])
            elif tipo == "burbuja":
                self.burbujas[fx[1]] = [fx[2], fx[3], 0.0]
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
        for lista, dur in ((self.textos, 1.3), (self.subs, 1.2), (self.toasts, 3.0)):
            for e in lista:
                e[-1] += dt
            lista[:] = [e for e in lista if e[-1] < dur]
        for b in self.burbujas.values():
            b[2] += dt
        self.burbujas = {k: b for k, b in self.burbujas.items() if b[2] < 2.8}
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
            v[0] -= dt
            if v[0] <= 0:
                del self.brillos[k_]
        for b in self.banners:
            b[3] += dt
        if self.banners and self.banners[0][3] > 3.2:
            self.banners.pop(0)
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
        if j.estrella and j.estrella.revelada:
            inf = m.infectados()
            if inf:
                return min(inf, key=lambda v: math.dist(v.pos, j.pos)).pos
        if m.antenas:
            a = min(m.antenas, key=lambda a: math.dist((a.x, a.y), j.pos))
            return (a.x, a.y + 4)
        return None

    def _calcular_guia(self):
        """Ruta más corta (Dijkstra en el grafo de la ciudad) hacia lo más urgente, si no se ve."""
        m = self.m
        obj = self._objetivo_urgente()
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
        m = self.m
        self.sx = int(self.rng.uniform(-self.temblor, self.temblor)) if self.temblor > 0.5 else 0
        self.sy = int(self.rng.uniform(-self.temblor, self.temblor)) if self.temblor > 0.5 else 0
        cx, cy = int(self.cam[0]), int(self.cam[1])
        pant.blit(self.suelo, (self.sx, self.sy), pygame.Rect(cx, cy, ANCHO, ALTO))
        self.capa.fill((0, 0, 0, 0))
        self._guia(self.capa)
        self._hilos(self.capa)
        pant.blit(self.capa, (0, 0))
        self._sprites(pant)
        self._pulsos(pant)
        self._proyectiles(pant)
        self._efectos(pant)
        self._luz_del_dia(pant)
        self._burbujas(pant)
        self._textos(pant)
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

    def _hilos(self, capa):
        """Grafo social: cada amistad es un hilo. Morado si pasa un Bulo, dorado si ambos están informados."""
        m = self.m
        for a, b, peso in m.social.aristas():
            va, vb = m.vecinos[a], m.vecinos[b]
            if not (self.visible(va.x, va.y, 40) or self.visible(vb.x, vb.y, 40)):
                continue
            clave = tuple(sorted((a, b)))
            infectado = va.bulo is not None or vb.bulo is not None
            if clave in self.brillos:
                color, alfa, grosor = self.brillos[clave][1], 255, 5
            elif infectado:
                color, alfa, grosor = (176, 110, 255), 190, 4
            elif va.escudo > 0 and vb.escudo > 0:
                color, alfa, grosor = (255, 214, 80), 190, 4
            else:
                color, alfa, grosor = (255, 255, 255), 45 + 20 * peso, 2 + (peso >= 3)
            (x0, y0), (x1, y1) = (va.x, va.y - 9), (vb.x, vb.y - 9)
            largo = math.dist((x0, y0), (x1, y1))
            curva = min(16, largo * 0.12)
            n = max(4, int(largo / 12))
            pts = []
            for k in range(n + 1):
                f = k / n
                pts.append(self.a_pantalla(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f - math.sin(f * math.pi) * curva))
            pygame.draw.lines(capa, (*color, alfa), False, pts, grosor)
            if infectado:
                # bolitas que corren por el hilo desde el vecino con Bulo
                desde_a = va.bulo is not None
                for k in range(3):
                    f = (self.t * 0.6 + k / 3) % 1.0
                    f = f if desde_a else 1 - f
                    x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f - math.sin(f * math.pi) * curva
                    sx, sy = self.a_pantalla(x, y)
                    pygame.draw.circle(capa, (*color, 230), (int(sx), int(sy)), 4)
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
        for img, x, yb in m.mapa.props:
            if vista.collidepoint(x + 8, yb - 8) or vista.collidepoint(x + 8, yb - img.get_height()):
                dib.append((yb, 0, img, x, yb - img.get_height()))
        for c in m.trafico.carros:
            x, y = c.topleft()
            dib.append((y + c.img.get_height() - 2, 0, c.img, x, y))
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
                pant.blit(escalar(img), self.a_pantalla(x, y))
            else:
                getattr(self, "_d_" + d[2])(pant, *d[3:])

    def _borde(self, pant, img, x, y):
        """Modo alto contraste: un borde blanco grueso alrededor de lo importante."""
        sil = escalar(sprites.silueta(img, (255, 255, 255)))
        sx, sy = self.a_pantalla(x, y)
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3)):
            pant.blit(sil, (sx + dx, sy + dy))

    def _sombra(self, pant, x, y, ancho=10):
        sx, sy = self.a_pantalla(x - ancho / 2, y - 2)
        pant.blit(escalar(sprites.sombra(ancho)), (sx, sy))

    def _d_semaforo(self, pant, x, yb):
        sx, sy = self.a_pantalla(x, yb)
        pygame.draw.rect(pant, (60, 60, 72), (sx - 3, sy - 66, 6, 66))
        pygame.draw.rect(pant, (34, 34, 44), (sx - 12, sy - 96, 24, 36), border_radius=5)
        verde = self.m.trafico.verde
        for k, (col, on) in enumerate((((240, 60, 60), verde != "h"), ((80, 230, 110), verde == "h"))):
            c = col if on else tuple(v // 4 for v in col)
            pygame.draw.circle(pant, c, (int(sx), int(sy - 87 + k * 17)), 6)

    def _d_vecino(self, pant, v):
        cuadro = int(v.paso) % 4 if v.mov else 0
        img = sprites.vecino(v.tipo, v.variante, v.dir, cuadro)
        if v.bulo is not None:
            img = sprites.desaturar(img)
        salto = math.sin(v.salto / 0.4 * math.pi) * 4 if v.salto > 0 else 0
        temblor = math.sin(self.t * 40) * 1 if (v.pelea and v.pelea.get("activa")) else 0
        self._sombra(pant, v.x, v.y, 10)
        if v.escudo > 0:
            r = 8 + math.sin(self.t * 5) * 1
            sx, sy = self.a_pantalla(v.x, v.y)
            alfa = 255 if v.escudo > 3 or int(self.t * 8) % 2 else 90
            pygame.draw.ellipse(pant, (255, 214, 70, alfa), (sx - r * ESC, sy - 3 * ESC, 2 * r * ESC, 6 * ESC), 3)
        x, y = v.x - 8 + temblor, v.y - 16 - salto
        if v.escudo > 0:
            pant.blit(escalar(sprites.silueta(img, (255, 226, 110))), self.a_pantalla(x - 0.34, y))
            pant.blit(escalar(sprites.silueta(img, (255, 226, 110))), self.a_pantalla(x + 0.34, y))
        pant.blit(escalar(img), self.a_pantalla(x, y))
        if v.bulo is not None and v.bulo in self.m.bulos:
            b = self.m.bulos[v.bulo]
            corona = self.m.arbol.es_raiz(b.id) and self.m.arbol.tiene_hijos(b.id)
            bob = math.sin(self.t * 4 + b.id) * 1.2
            ib = sprites.bulo(int(self.t * 3 + b.id) % 2, corona, False, (0, 1))
            pant.blit(escalar(ib), self.a_pantalla(v.x - 8, v.y - 31 - salto + bob))
        j = self.m.jugador
        if math.dist(v.pos, j.pos) < 60 or (v.pelea and v.pelea.get("activa")):
            sx, sy = self.a_pantalla(v.x, v.y - 33 if v.bulo is None else v.y - 37)
            texto(pant, v.nombre, (sx, sy), 15, (255, 255, 255), "midbottom", 600)
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

    def _d_estrella(self, pant, s):
        ana = self.m.jugador.clave == "ana"
        bob = math.sin(self.t * 3 + s.id) * 1.5
        sx, sy = self.a_pantalla(s.x, s.y)
        # columna de luz para verla de lejos
        col = pygame.Surface((10, 60), pygame.SRCALPHA)
        for yy in range(60):
            col.fill((255, 230, 120, int(70 * (yy / 60))), (0, yy, 10, 1))
        pant.blit(col, (sx - 5, sy - 80))
        self._sombra(pant, s.x, s.y + 6, 8)
        img = sprites.estrella(falsa=s.falsa, revelada_falsa=s.falsa and ana, brillo=int(self.t * 2) % 2)
        if s.vida < 5 and int(self.t * 8) % 2:
            return
        if self.op.get("contraste"):
            self._borde(pant, img, s.x - 8, s.y - 10 + bob)
        pant.blit(escalar(img), self.a_pantalla(s.x - 8, s.y - 10 + bob))
        if ana and s.falsa:
            texto(pant, "BULO", (sx, sy - 40), 13, (210, 170, 255), "midbottom")

    def _d_antena(self, pant, a):
        luz = int(self.t * 3) % 2 == 0
        img = sprites.antena(luz, a.golpe > 0)
        self._sombra(pant, a.x, a.y, 14)
        pant.blit(escalar(img), self.a_pantalla(a.x - 8, a.y - 40))
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
        pant.blit(escalar(img), self.a_pantalla(b.x - 8, b.y - 9 + bob))
        if b.candidato:
            sx, sy = self.a_pantalla(b.x, b.y - 12 + bob)
            texto(pant, f"rumor: {b.candidato}", (sx, sy), 13, (230, 200, 255), "midbottom", 600)

    def _d_viral(self, pant, v):
        img = sprites.bulo_gigante(self.t)
        golpe = v.golpe > 0
        self._sombra(pant, v.x, v.y + 14, 20)
        x, y = self.a_pantalla(v.x - 16, v.y - 22 + math.sin(self.t * 3) * 2)
        grande = escalar(img)
        if golpe:
            grande = escalar(sprites.silueta(img, (255, 255, 255)))
        pant.blit(grande, (x, y))
        cx, cy = self.a_pantalla(v.x, v.y - 30)
        r = 26 + math.sin(self.t * 10) * 3
        pygame.draw.circle(pant, (255, 60, 110), (int(cx), int(cy)), int(r), 4)
        texto(pant, str(max(0, math.ceil(v.t))), (cx, cy), 30, (255, 255, 255), "center")
        texto(pant, "¡VIRAL!", (cx, cy - 36), 18, (255, 120, 160), "center")
        obj = self.m.vecinos[v.objetivo]
        for k in range(10):
            f = k / 10
            if int(self.t * 6 + k) % 2:
                self._px(pant, v.x + (obj.x - v.x) * f, v.y + (obj.y - 20 - v.y) * f, (255, 90, 140))

    def _d_fantasma(self, pant, f):
        cs = personajes.cuadros(f["clave"])
        img = cs[f.get("dir", "abajo")][int(f.get("paso", 0)) % 4]
        g = escalar(img).copy()
        g.set_alpha(110)
        pant.blit(g, self.a_pantalla(f["x"] - 8, f["y"] - 23))
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
        pant.blit(escalar(img), self.a_pantalla(j.x - 8 + ox, j.y - 23 + bob))
        if (self.m.t < 4 or self.op.get("contraste")) and not self.op.get("demo"):
            texto(pant, "TÚ", (sx, sy - 27 * ESC), 18, color, "midbottom")
        if j.estrella:
            s = j.estrella
            bob2 = math.sin(self.t * 4) * 1.5
            img = sprites.estrella(falsa=s.falsa, revelada_falsa=s.falsa and s.revelada, brillo=1 if s.revelada else 0)
            px_, py_ = self.a_pantalla(j.x - 8, j.y - 40 + bob2)
            pant.blit(escalar(img), (px_, py_))
            if not s.revelada:
                frac = min(1.0, j.verif / 1.2)
                c = (int(px_ + 24), int(py_ + 24))
                pygame.draw.circle(pant, (30, 24, 60), c, 30, 5)
                if frac > 0:
                    pygame.draw.arc(pant, (255, 255, 255), (c[0] - 30, c[1] - 30, 60, 60), math.pi / 2,
                                    math.pi / 2 + frac * math.tau, 5)
                if j.mov:
                    texto(pant, "¡quieto para mirarla!", (c[0], c[1] - 40), 14, (255, 255, 255), "midbottom", 600)
            else:
                pygame.draw.circle(pant, (255, 240, 150), (int(px_ + 24), int(py_ + 24)),
                                   int(30 + math.sin(self.t * 8) * 4), 2)

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
            img = sprites.bulo(int(self.t * 8) % 2, False, p.congelado > 0, (1, 0))
            pequeno = pygame.transform.scale(img, (10, 11))
            pant.blit(escalar(pequeno), self.a_pantalla(x - 5, y - 6))

    def _proyectiles(self, pant):
        for pr in self.m.proyectiles:
            for k, (x, y) in enumerate(pr.rastro):
                sx, sy = self.a_pantalla(x, y)
                pygame.draw.circle(pant, pr.color, (int(sx), int(sy)), 2 + k)
            sx, sy = self.a_pantalla(pr.x, pr.y)
            pygame.draw.circle(pant, (30, 20, 50), (int(sx), int(sy)), 11)
            pygame.draw.circle(pant, pr.color, (int(sx), int(sy)), 9)
            pygame.draw.circle(pant, (255, 255, 255), (int(sx) - 2, int(sy) - 2), 4)

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
            for x, y, r in luces:
                if not self.visible(x, y, r * ESC):
                    continue
                sx, sy = self.a_pantalla(x, y)
                img = sprites.luz(r * ESC // 2)
                s.blit(img, (sx - img.get_width() // 2, sy - img.get_height() // 2), special_flags=pygame.BLEND_RGBA_SUB)
            pant.blit(s, (0, 0))

    def _burbujas(self, pant):
        """Lo que dicen los vecinos (el rumor que creyeron o la noticia que recibieron)."""
        for nombre, (txt, color, t) in self.burbujas.items():
            v = self.m.vecinos.get(nombre)
            if v is None or not self.visible(v.x, v.y, 0):
                continue
            sx, sy = self.a_pantalla(v.x, v.y - (40 if v.bulo is not None else 30))
            alfa = int(255 * max(0.0, min(1.0, t / 0.15, (2.8 - t) / 0.3)))
            img = render(txt, 16, (255, 255, 255), 700, None)
            r = img.get_rect(midbottom=(sx, sy - 10 - min(1.0, t / 0.15) * 4))
            caja = r.inflate(18, 10)
            caja.clamp_ip(pygame.Rect(6, 6, ANCHO - 12, ALTO - 12))
            s = pygame.Surface((caja.w, caja.h + 10), pygame.SRCALPHA)
            pygame.draw.rect(s, (*color, min(235, alfa)), (0, 0, caja.w, caja.h), border_radius=10)
            pygame.draw.rect(s, (255, 255, 255, alfa), (0, 0, caja.w, caja.h), 2, border_radius=10)
            cx = max(10, min(caja.w - 10, int(sx - caja.x)))
            pygame.draw.polygon(s, (*color, min(235, alfa)), [(cx - 7, caja.h - 1), (cx + 7, caja.h - 1), (cx, caja.h + 9)])
            pant.blit(s, caja.topleft)
            img2 = img.copy()
            img2.set_alpha(alfa)
            pant.blit(img2, img2.get_rect(center=caja.center))

    def _textos(self, pant):
        for x, y, s, color, grande, t in self.textos:
            f = t / 1.3
            sx, sy = self.a_pantalla(x, y - 22 * f)
            texto(pant, s, (sx, sy), 26 if grande else 20, color, "center", alfa=int(255 * min(1, 2 * (1 - f))))
        for x, y, s, t in self.subs:
            if x is None:
                continue
            sx, sy = self.a_pantalla(x, y - 30)
            img_r = texto(pant, s, (sx, sy - t * 10), 16, (255, 255, 255), "center", 700, (90, 40, 140))

    def _flechas(self, pant):
        m = self.m
        objetivos = [((a.x, a.y - 20), (255, 90, 90), "ANTENA") for a in m.antenas]
        if m.viral:
            objetivos.append(((m.viral.x, m.viral.y), (255, 80, 150), "VIRAL"))
        for p in m.peleas:
            if p.get("activa") and not p.get("fin"):
                a = m.vecinos[p["a"]]
                objetivos.append(((a.x, a.y), (255, 150, 80), "PELEA"))
        if not m.jugador.estrella and m.estrellas:
            s = min(m.estrellas, key=lambda s: math.dist((s.x, s.y), m.jugador.pos))
            objetivos.append(((s.x, s.y), (255, 214, 70), "NOTICIA"))
        cx, cy = ANCHO / 2, ALTO / 2
        for (x, y), color, etiqueta in objetivos:
            if self.visible(x, y, -30):
                continue
            sx, sy = self.a_pantalla(x, y)
            ang = math.atan2(sy - cy, sx - cx)
            mx, my = ANCHO / 2 - 60, ALTO / 2 - 70
            k = min(mx / max(1e-3, abs(math.cos(ang))), my / max(1e-3, abs(math.sin(ang))))
            px_, py_ = cx + math.cos(ang) * k, cy + math.sin(ang) * k + 10
            pulso = 4 * math.sin(self.t * 8)
            pts = [(px_ + math.cos(ang) * (22 + pulso), py_ + math.sin(ang) * (22 + pulso)),
                   (px_ + math.cos(ang + 2.4) * 16, py_ + math.sin(ang + 2.4) * 16),
                   (px_ + math.cos(ang - 2.4) * 16, py_ + math.sin(ang - 2.4) * 16)]
            pygame.draw.polygon(pant, (20, 14, 40), [(a + 2, b + 3) for a, b in pts])
            pygame.draw.polygon(pant, color, pts)
            texto(pant, etiqueta, (px_ - math.cos(ang) * 26, py_ - math.sin(ang) * 26), 14, color, "center")
