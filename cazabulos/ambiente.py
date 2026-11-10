"""La vida del barrio: todo lo que se mueve solo y no cambia el juego.

- Laguna: brillos que se corren, ondas, nenúfares que flotan y una pata con sus patitos.
- Fuente de la plaza: gotas que saltan de la estatua y hacen ondas al caer.
- Flores y matas de pasto que se mecen con el viento.
- Palomas en la plaza (si pasas cerca salen volando), mariposas en el parque, hojas que caen.
- Banderas que ondean en la alcaldía, sombras de nubes que cruzan la ciudad.
- Polvo cuando corres, estela de los Bulos y destellos de las estrellas.
- Hierba alta que se mece y se abre cuando alguien camina adentro (ver hierba.py); las flores se
  apartan cuando pasas.
- Agua con espuma que corre por la orilla, destellos que se mueven, reflejo de los patos y ondas
  alrededor de los nenúfares.
- Motas de luz: polen flotando de día y polvo en la luz de los faroles de noche.
- De noche: luciérnagas en el parque.

Usa su propio azar: no toca el de la partida, así la misma semilla sigue dando el mismo barrio.
Todo está en pixeles nativos del mapa (16 por tile) y se dibuja con la cámara del Render.
"""
import math
import random
from collections import deque

import pygame

from .config import ALTO, ANCHO, ESC, TILE
from .hierba import HierbaAlta
from .mapa import H, W
from .recursos import borde, escalar

try:
    import numpy as np

    from .texturas import encoger
except ImportError:                        # sin numpy el agua no lleva espuma animada
    np = None

# ----------------------------------------------------------------- dibujitos (pixel art hecho en código)
_cache = {}


def _pintar(filas, colores):
    s = pygame.Surface((max(len(f) for f in filas), len(filas)), pygame.SRCALPHA)
    for y, fila in enumerate(filas):
        for x, ch in enumerate(fila):
            if ch in colores:
                s.set_at((x, y), colores[ch])
    return s


def _guardar(clave, hacer):
    if clave not in _cache:
        _cache[clave] = hacer()
    return _cache[clave]


def _a_pantalla(img, izquierda=True):
    """Con borde oscuro, mirando hacia donde toca y escalada x3."""
    if not izquierda:
        img = pygame.transform.flip(img, True, False)
    return escalar(borde(img))


_PALOMA = {"g": (160, 162, 178), "o": (104, 110, 132), "c": (208, 210, 222), "p": (240, 150, 70),
           "n": (24, 20, 30), "r": (230, 120, 130), "v": (110, 170, 150)}
_PALOMA_DIB = [
    ["..oo.....", ".nvo.....", "poggggg..", "..gcccgg.", "...gggg..", "....r.r.."],      # parada
    [".........", ".........", "..vgggg..", ".ogcccgg.", "pnggggg..", "....r.r.."],      # picoteando
    ["....cc...", "...cccc..", ".oocccgg.", "pnggggggg", "..ggggg..", "........."],      # alas arriba
    [".........", ".........", ".oogggggg", "pnggccccg", "..gcccc..", "...cc...."],      # alas abajo
]


def paloma(cuadro, izquierda):
    """Paloma gris: 0 parada, 1 picoteando, 2-3 volando (alas arriba / abajo)."""
    return _guardar(("paloma", cuadro, izquierda),
                    lambda: _a_pantalla(_pintar(_PALOMA_DIB[cuadro], _PALOMA), izquierda))


def mariposa(cuadro, color):
    def hacer():
        claro = tuple(min(255, c + 70) for c in color)
        col = {"a": color, "c": claro, "n": (30, 24, 40)}
        dib = [["aa.aa", "acnca", ".ana.", "..n.."], [".....", "acnca", "aanaa", "..n.."]][cuadro]
        return escalar(borde(_pintar(dib, col)))
    return _guardar(("mariposa", cuadro, color), hacer)


_PATO = {"w": (250, 250, 246), "c": (210, 214, 222), "o": (255, 160, 40), "n": (20, 16, 26),
         "y": (255, 222, 70), "Y": (236, 180, 40)}


def pato(izquierda, chico=False):
    """La pata (blanca) y sus patitos (amarillos), mirando a la izquierda o a la derecha."""
    def hacer():
        if chico:
            dib = [".yy..", "ony..", ".yyyY", "..yYY"]
        else:
            dib = [".ww.......", "onww......", "..www...w.", "..wwwwwww.", "..wccccww.", "...wwwww.."]
        return _a_pantalla(_pintar(dib, _PATO), izquierda)
    return _guardar(("pato", izquierda, chico), hacer)


def nenufar(flor):
    def hacer():
        col = {"g": (62, 150, 84), "G": (98, 186, 104), "k": (40, 108, 66), "f": (255, 150, 200), "F": (255, 220, 240)}
        dib = [".gggg.", "gGGG.g", "gGGGGg", ".kkkk."]
        if flor:
            dib = [".gFg..", "gfFfGg", "gGfGGg", ".kkkk."]
        return escalar(_pintar(dib, col))
    return _guardar(("nenufar", flor), hacer)


def bandera(cuadro):
    """Bandera de Colombia (amarillo, azul y rojo) ondeando: 8 cuadros."""
    def hacer():
        w, h = 14, 9
        s = pygame.Surface((w, h + 3), pygame.SRCALPHA)
        for x in range(w):
            ola = math.sin(cuadro / 8 * math.tau - x * 0.55)
            dy = round(ola * (x / w) * 1.6)
            sombra = 0.82 if math.cos(cuadro / 8 * math.tau - x * 0.55) > 0.35 else 1.0
            for y in range(h):
                c = (252, 209, 22) if y < 5 else (0, 56, 147) if y < 7 else (206, 17, 38)
                s.set_at((x, y + 1 + dy), tuple(int(v * sombra) for v in c))
        return escalar(borde(s))
    return _guardar(("bandera", cuadro), hacer)


def _nube_sombra():
    """Sombra suave de una nube (en pixeles de pantalla), hecha con varias elipses."""
    def hacer():
        w, h = 420, 230
        base = pygame.Surface((w, h), pygame.SRCALPHA)
        for alfa, encoge in ((16, 0), (18, 26)):
            figura = pygame.Surface((w, h), pygame.SRCALPHA)
            for cx, cy, rx, ry in ((150, 120, 120, 70), (240, 100, 110, 72), (310, 130, 95, 62),
                                   (90, 140, 80, 52), (200, 160, 130, 56)):
                pygame.draw.ellipse(figura, (255, 255, 255), (cx - rx + encoge, cy - ry + encoge,
                                                              2 * (rx - encoge), 2 * (ry - encoge)))
            mascara = pygame.mask.from_surface(figura)
            base.blit(mascara.to_surface(setcolor=(10, 14, 30, alfa), unsetcolor=(0, 0, 0, 0)), (0, 0))
        return base
    return _guardar("nube", hacer)


def _onda(r, alfa):
    """Anillo de agua visto desde arriba (elipse aplastada), en pixel grande."""
    def hacer():
        s = pygame.Surface((2 * r + 2, r + 2), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (230, 250, 255, alfa), (0, 0, 2 * r + 2, r + 2), 1)
        return escalar(s)
    return _guardar(("onda", r, alfa), hacer)


def bolita(r, color, alfa):
    """Circulito de polvo o de estela (pixeles de pantalla)."""
    def hacer():
        s = pygame.Surface((2 * r + 1, 2 * r + 1), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alfa), (r, r), r)
        return s
    return _guardar(("bolita", r, color, alfa), hacer)


def _destello(tam, color):
    """Brillito en cruz (+) para las estrellas."""
    def hacer():
        n = 2 * tam + 1
        s = pygame.Surface((n, n), pygame.SRCALPHA)
        s.fill(color, (tam, 0, 1, n))
        s.fill(color, (0, tam, n, 1))
        s.fill((255, 255, 255), (tam, tam, 1, 1))
        return escalar(s)
    return _guardar(("destello", tam, color), hacer)


def reflejo(img):
    """La imagen de cabeza y transparente: su reflejo en el agua."""
    def hacer():
        r = pygame.transform.flip(img, False, True)
        r.set_alpha(70)
        return r
    return _guardar(("reflejo", id(img)), hacer)


def sombra_suave(ancho, alto, alfa=90):
    """Mancha de sombra con el borde difuminado (en pixeles de pantalla)."""
    def hacer():
        pad = 8
        s = pygame.Surface((ancho + 2 * pad, alto + 2 * pad), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, alfa), (pad, pad, ancho, alto))
        chico = pygame.transform.smoothscale(s, (max(1, s.get_width() // 4), max(1, s.get_height() // 4)))
        return pygame.transform.smoothscale(chico, s.get_size())
    return _guardar(("sombra_suave", ancho, alto, alfa), hacer)


def sombra_larga(largo, ancho, angulo, alfa=85):
    """Sombra alargada y difuminada que apunta en 'angulo' (grados, 0 = derecha, 90 = arriba).
    Devuelve (imagen, desplazamiento del centro respecto a los pies)."""
    def hacer():
        base = sombra_suave(largo, ancho, alfa)
        img = pygame.transform.rotate(base, angulo)
        rad = math.radians(angulo)
        d = max(0, largo / 2 - ancho / 2)
        return img, (math.cos(rad) * d, -math.sin(rad) * d)
    return _guardar(("sombra_larga", largo, ancho, angulo, alfa), hacer)


def resplandor(r, color):
    """Luz que se SUMA a lo que hay debajo (luciérnagas, faroles, ventanas de noche)."""
    def hacer():
        s = pygame.Surface((2 * r, 2 * r))
        s.fill((0, 0, 0))
        for k in range(r, 0, -1):
            f = (1 - k / r) ** 1.6
            pygame.draw.circle(s, tuple(int(c * f) for c in color), (r, r), k)
        return s
    return _guardar(("resplandor", r, color), hacer)


FLORES = [(255, 255, 255), (255, 214, 70), (255, 140, 190), (190, 150, 255), (255, 130, 90)]
TALLO = (46, 122, 74)
HOJITA = (88, 176, 104)


class Ambiente:
    def __init__(self, mapa, ronda=1):
        self.mapa = mapa
        self.ronda = ronda
        self.de_noche = ronda >= 3
        self.rng = random.Random(11)
        self.t = 0.0
        self.hierba = HierbaAlta(mapa)
        self.caminantes = []            # quiénes pueden pisar flores y hierba en este cuadro
        self.flores = self._sembrar()
        lago = mapa.agua[0]
        self.lago = lago
        self.brillos = [self._brillo() for _ in range(22)]
        self.nenufares = [(lago.x + 18, lago.y + 14, True), (lago.x + 30, lago.y + 22, False),
                          (lago.right - 26, lago.bottom - 18, True), (lago.right - 40, lago.bottom - 12, False),
                          (lago.x + 14, lago.bottom - 16, False)]
        self.t_nenufar = [self.rng.uniform(0.5, 4.0) for _ in self.nenufares]
        self.agua_cuadros = self._cuadros_agua()
        self.ondas = []                 # [x, y, t, dur, radio máximo]
        self.gotas = []                 # [x, y en el piso, alto, vx, vy, vz]
        self.t_gota = 0.0
        self.t_pez = 2.0
        # la pata y sus patitos
        self.pata = {"x": lago.centerx, "y": lago.centery, "dest": self._punto_lago(), "izq": True,
                     "rastro": deque(maxlen=40), "t": 0.0, "t_ola": 0.0}
        self.palomas = [self._paloma_nueva() for _ in range(7)]
        self.mariposas = [self._mariposa_nueva() for _ in range(6)]
        self.luciernagas = [self._luciernaga_nueva() for _ in range(16)] if self.de_noche else []
        self.hojas = []
        self.t_hoja = 0.0
        self.motas = []                 # polvo y estela (en el piso): [x, y, vx, vy, vida, max, tipo]
        self.destellos = []             # brillos de las estrellas (en el aire)
        self.t_polvo = 0.0
        self.t_rastro = 0.0
        self.t_destello = 0.0
        self.t_humo = 0.0
        self.arboles = [(x + 8, yb - 22) for img, x, yb, tipo in mapa.props if tipo == "arbol"]
        # dos banderas en las esquinas del techo de la alcaldía (el letrero queda en el centro)
        self.banderas = [(20 * TILE + 6, 5 * TILE + 2), (34 * TILE + 4, 5 * TILE + 2)]
        ancho, alto = W * TILE, H * TILE
        self.nubes = [[self.rng.uniform(0, ancho), self.rng.uniform(0, alto)] for _ in range(4)]

    # ------------------------------------------------------------- preparar
    def _sembrar(self):
        """Flores y matas de pasto en los prados (más en el parque), lejos de caminos y objetos."""
        m = self.mapa
        res = []
        parque = m.zonas.get("Parque", pygame.Rect(0, 0, 0, 0))
        for ty in range(H):
            for tx in range(W):
                if m.suelo[ty][tx] != "g" or m.solido[ty][tx] or m.capa[ty][tx] is not None:
                    continue
                if (tx, ty) in self.hierba.matas:          # ahí ya hay hierba alta
                    continue
                prob = 0.5 if parque.collidepoint(tx, ty) else 0.22
                if self.rng.random() > prob:
                    continue
                x, y = tx * TILE + self.rng.randint(3, 12), ty * TILE + self.rng.randint(5, 13)
                if not m.libre(pygame.Rect(x - 2, y - 2, 4, 3)):
                    continue
                if self.rng.random() < 0.42:
                    res.append(("flor", x, y, self.rng.choice(FLORES), self.rng.uniform(0, 6.3)))
                else:
                    res.append(("mata", x, y, None, self.rng.uniform(0, 6.3)))
        return res

    def _cuadros_agua(self):
        """Cuadros de la animación del agua (en pixeles nativos): espuma que corre por la orilla y
        rayitas de luz que se mueven en lo hondo. Se calculan una vez."""
        e = self.mapa.estanque
        if not e or np is None:
            return []
        agua, hondo = e["agua"], e["hondo"]
        hh, ww = agua.shape
        yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        cy, cx = yy[agua].mean(), xx[agua].mean()
        ang = np.arctan2(yy - cy, (xx - cx) * 0.7)
        banda = agua & ~encoger(agua, 4) & encoger(agua, 1)
        hondo_ok = agua & (hondo > 0.3)
        cuadros = []
        for k in range(24):
            f = k / 24 * math.tau
            rgba = np.zeros((hh, ww, 4), np.uint8)
            v = np.sin(xx * 0.33 + yy * 0.17 + f) + np.sin(-xx * 0.2 + yy * 0.35 + 2 * f) + np.sin(xx * 0.12 - yy * 0.11 - f)
            rgba[hondo_ok & (np.abs(v - 1.1) < 0.1)] = (204, 246, 252, 90)
            espuma = banda & (np.sin(ang * 18 + 2 * f) + 0.6 * np.sin(ang * 7 - f) > 0.95)
            rgba[espuma] = (238, 252, 252, 210)
            img = pygame.image.frombytes(rgba.tobytes(), (ww, hh), "RGBA")
            cuadros.append(img.convert_alpha() if pygame.display.get_surface() else img)
        return cuadros

    def _brillo(self):
        r = self.lago
        return [self.rng.uniform(r.left + 2, r.right - 8), self.rng.uniform(r.top + 3, r.bottom - 3),
                self.rng.randint(2, 5), self.rng.uniform(0, 6.3), self.rng.uniform(1.0, 2.2)]

    def _punto_lago(self):
        r = self.lago.inflate(-28, -24)
        return (self.rng.uniform(r.left, r.right), self.rng.uniform(r.top, r.bottom))

    def _punto_plaza(self):
        for _ in range(30):
            x, y = self.rng.uniform(17, 38) * TILE, self.rng.uniform(8.5, 17) * TILE
            if self.mapa.libre(pygame.Rect(int(x) - 3, int(y) - 2, 6, 3)):
                return x, y
        return 24 * TILE, 15 * TILE

    def _paloma_nueva(self):
        x, y = self._punto_plaza()
        return {"x": x, "y": y, "alto": 0.0, "vuela": False, "vx": 0.0, "vy": 0.0, "izq": self.rng.random() < 0.5,
                "t": self.rng.uniform(0, 3), "pica": 0.0, "dest": None}

    def _mariposa_nueva(self):
        r = self.mapa.zonas.get("Parque", pygame.Rect(1, 26, 40, 19))
        return {"x": self.rng.uniform(r.left + 1, r.right - 1) * TILE, "y": self.rng.uniform(r.top + 1, r.bottom - 1) * TILE,
                "dx": 0.0, "dy": 0.0, "t": self.rng.uniform(0, 5), "color": self.rng.choice(FLORES[1:]), "zona": r}

    def _luciernaga_nueva(self):
        m = self._mariposa_nueva()
        m["fase"] = self.rng.uniform(0, 6.3)
        return m

    # ------------------------------------------------------------- tiempo
    def actualizar(self, dt, mundo, vista, otros=()):
        """vista: rectángulo visible en pixeles nativos (lo que no se ve casi no gasta).
        otros: [(nombre, x, y)] de los rivales en línea (también pisan la hierba)."""
        self.t += dt
        j = mundo.jugador
        self.caminantes = [("yo", j.x, j.y)] + [(n, v.x, v.y) for n, v in mundo.vecinos.items()
                                                if vista.collidepoint(v.x, v.y)] + list(otros)
        self.hierba.actualizar(dt, self.caminantes)
        for b in self.brillos:
            b[0] += b[4] * dt * 2.2
            if b[0] > self.lago.right - 8:
                b[0] = self.lago.left + 2
        for o in self.ondas:
            o[2] += dt
        self.ondas = [o for o in self.ondas if o[2] < o[3]]
        lago_visible = vista.colliderect(self.lago)
        self._fuente(dt, vista)
        self._pata(dt, lago_visible)
        for i, (x, y, _) in enumerate(self.nenufares):    # el agua se mueve alrededor de los nenúfares
            self.t_nenufar[i] -= dt
            if self.t_nenufar[i] <= 0:
                self.t_nenufar[i] = self.rng.uniform(2.5, 4.5)
                if lago_visible:
                    self.ondas.append([x, y + 1, 0.0, 1.5, 6])
        if lago_visible:
            self.t_pez -= dt
            if self.t_pez <= 0:        # un pez se asoma: ondas que se abren en el agua
                self.t_pez = self.rng.uniform(1.6, 3.5)
                x, y = self._punto_lago()
                for k in range(2):
                    self.ondas.append([x, y, -0.25 * k, 1.2, 7])
        self._palomas(dt, mundo.jugador)
        if self.de_noche:
            for m in self.luciernagas:
                self._revolotear(m, dt, 8)
        else:
            for m in self.mariposas:
                self._revolotear(m, dt, 16)
        self._hojas(dt, vista)
        self._polvo(dt, mundo.jugador)
        self._rastros(dt, mundo, vista)
        if not self.de_noche:
            ancho, alto = W * TILE, H * TILE
            for n in self.nubes:
                n[0] = (n[0] + 7 * dt + 150) % (ancho + 300) - 150
                n[1] = (n[1] + 2 * dt + 100) % (alto + 200) - 100

    def _fuente(self, dt, vista):
        fx, fy = self.mapa.fuente
        if vista.collidepoint(fx, fy):
            self.t_gota -= dt
            while self.t_gota <= 0:
                self.t_gota += 0.03
                ang = self.rng.uniform(0, math.tau)
                v = self.rng.uniform(6, 15)
                # nace en la punta de la estatua (12 px sobre su base) y sube antes de caer
                self.gotas.append([fx + self.rng.uniform(-1, 1), fy + 12, 12.0, math.cos(ang) * v,
                                   math.sin(ang) * v * 0.6, self.rng.uniform(26, 40)])
        else:
            self.t_gota = 0.0
        vivas = []
        for g in self.gotas:
            g[0] += g[3] * dt
            g[1] += g[4] * dt
            g[5] -= 100 * dt
            g[2] += g[5] * dt
            if g[2] > 0:
                vivas.append(g)
            elif self.rng.random() < 0.35:
                self.ondas.append([g[0], g[1], 0.0, 0.45, 3])
        self.gotas = vivas

    def _pata(self, dt, visible):
        p = self.pata
        p["t"] += dt
        dx, dy = p["dest"][0] - p["x"], p["dest"][1] - p["y"]
        d = math.hypot(dx, dy)
        if d < 2:
            p["dest"] = self._punto_lago()
        else:
            vel = 7.0
            p["x"] += dx / d * vel * dt
            p["y"] += dy / d * vel * dt
            if abs(dx) > 1:
                p["izq"] = dx < 0
        if not p["rastro"] or math.dist(p["rastro"][-1], (p["x"], p["y"])) > 1.5:
            p["rastro"].append((p["x"], p["y"]))
        p["t_ola"] -= dt
        if visible and p["t_ola"] <= 0:
            p["t_ola"] = 0.7
            self.ondas.append([p["x"] + (4 if p["izq"] else -4), p["y"] + 1, 0.0, 1.0, 6])

    def _palomas(self, dt, jugador):
        for p in self.palomas:
            p["t"] -= dt
            p["pica"] = max(0.0, p["pica"] - dt)
            if not p["vuela"]:
                if math.hypot(p["x"] - jugador.x, p["y"] - jugador.y) < 34:
                    # sale volando lejos del jugador
                    p["vuela"] = True
                    for _ in range(4):
                        p["dest"] = self._punto_plaza()
                        if math.hypot(p["dest"][0] - jugador.x, p["dest"][1] - jugador.y) > 90:
                            break
                    p["izq"] = p["dest"][0] < p["x"]
                    continue
                if p["t"] <= 0:
                    p["t"] = self.rng.uniform(0.6, 2.4)
                    if self.rng.random() < 0.5:
                        p["pica"] = 0.6
                    else:
                        p["vx"] = self.rng.uniform(-9, 9)
                        p["vy"] = self.rng.uniform(-5, 5)
                        p["izq"] = p["vx"] < 0
                nx, ny = p["x"] + p["vx"] * dt, p["y"] + p["vy"] * dt
                if self.mapa.libre(pygame.Rect(int(nx) - 3, int(ny) - 2, 6, 3)):
                    p["x"], p["y"] = nx, ny
                p["vx"] *= 0.96
                p["vy"] *= 0.96
            else:
                dx, dy = p["dest"][0] - p["x"], p["dest"][1] - p["y"]
                d = math.hypot(dx, dy)
                if d < 3:
                    p["alto"] = max(0.0, p["alto"] - 30 * dt)
                    if p["alto"] <= 0:
                        p["vuela"] = False
                        p["vx"] = p["vy"] = 0.0
                        p["t"] = self.rng.uniform(1, 3)
                    continue
                vel = min(70.0, d * 3 + 10)
                p["x"] += dx / d * min(d, vel * dt)
                p["y"] += dy / d * min(d, vel * dt)
                meta = 22.0 if d > 30 else d * 0.7
                p["alto"] += (meta - p["alto"]) * min(1.0, dt * 4)

    def _revolotear(self, m, dt, vel):
        m["t"] += dt
        if self.rng.random() < dt * 0.8:
            ang = self.rng.uniform(0, math.tau)
            m["dx"], m["dy"] = math.cos(ang) * vel, math.sin(ang) * vel * 0.65
        r = m["zona"]
        m["x"] += m["dx"] * dt
        m["y"] += m["dy"] * dt + math.sin(m["t"] * 6) * 6 * dt
        if not (r.left * TILE < m["x"] < r.right * TILE):
            m["dx"] = -m["dx"]
            m["x"] = min(max(m["x"], r.left * TILE + 1), r.right * TILE - 1)
        if not (r.top * TILE < m["y"] < r.bottom * TILE):
            m["dy"] = -m["dy"]
            m["y"] = min(max(m["y"], r.top * TILE + 1), r.bottom * TILE - 1)

    def _hojas(self, dt, vista):
        self.t_hoja -= dt
        if self.t_hoja <= 0 and len(self.hojas) < 14:
            self.t_hoja = self.rng.uniform(0.3, 0.8)
            cerca = [a for a in self.arboles if vista.collidepoint(a)]
            if cerca:
                x, y = self.rng.choice(cerca)
                color = self.rng.choice(((214, 128, 46), (238, 168, 64), (122, 176, 70), (96, 156, 64)))
                self.hojas.append([x + self.rng.uniform(-5, 5), y + self.rng.uniform(-6, 4), color,
                                   self.rng.uniform(0, 6.3), 0.0])
        for h in self.hojas:
            h[4] += dt
            h[1] += 9 * dt
            h[0] += math.sin(h[4] * 2.4 + h[3]) * 10 * dt + 3 * dt
        self.hojas = [h for h in self.hojas if h[4] < 3.2]

    def _polvo(self, dt, j):
        """Nubecitas de polvo en los pies cuando el jugador corre."""
        self.t_polvo -= dt
        if getattr(j, "mov", False) and self.t_polvo <= 0:
            self.t_polvo = 0.14
            vx, vy = getattr(j, "vec", (0, 0))
            self.motas.append([j.x - vx * 3 + self.rng.uniform(-2, 2), j.y - 1, -vx * 6 + self.rng.uniform(-4, 4),
                               -4.0, 0.45, 0.45, "polvo"])
        for m in self.motas:
            m[0] += m[2] * dt
            m[1] += m[3] * dt
            m[4] -= dt
        self.motas = [m for m in self.motas if m[4] > 0]

    def _rastros(self, dt, mundo, vista):
        """Estela morada de los Bulos libres y destellos alrededor de las estrellas."""
        self.t_rastro -= dt
        if self.t_rastro <= 0:
            self.t_rastro = 0.09
            for b in mundo.bulos.values():
                if b.estado == "libre" and vista.collidepoint(b.x, b.y):
                    self.motas.append([b.x + self.rng.uniform(-3, 3), b.y + 6 + self.rng.uniform(-1, 1), 0.0, -3.0,
                                       0.5, 0.5, "rastro"])
        self.t_humo -= dt
        if self.t_humo <= 0:
            self.t_humo = 0.28
            for c in mundo.trafico.carros:
                x, y = c.topleft()
                w, h = c.img.get_size()
                if c.vel < 4 or not vista.colliderect((x, y, w, h)):
                    continue
                # el humito sale por detrás del carro y se queda atrás
                ex, ey, vx, vy = {"der": (x + 2, y + h - 8, -8, -2), "izq": (x + w - 2, y + h - 8, 8, -2),
                                  "abajo": (x + w / 2 - 6, y + 2, 0, -8), "arriba": (x + w / 2 + 6, y + h - 2, 0, 8)}[c.carril.dir]
                self.motas.append([ex, ey, vx + self.rng.uniform(-2, 2), vy + self.rng.uniform(-3, 0), 0.6, 0.6, "humo"])
        self.t_destello -= dt
        if self.t_destello <= 0:
            self.t_destello = 0.22
            for e in mundo.estrellas:
                if vista.collidepoint(e.x, e.y):
                    ang = self.rng.uniform(0, math.tau)
                    r = self.rng.uniform(7, 12)
                    self.destellos.append([e.x + math.cos(ang) * r, e.y - 4 + math.sin(ang) * r * 0.8, 0.0, 0.6])
        for d in self.destellos:
            d[2] += dt
            d[1] -= 4 * dt
        self.destellos = [d for d in self.destellos if d[2] < d[3]]

    # ------------------------------------------------------------- dibujo
    def dibujar_suelo(self, pant, render):
        """Lo que va pegado al piso, debajo de la gente."""
        ap = render.a_pantalla
        vis = render.visible
        if vis(self.lago.centerx, self.lago.centery, 260):
            self._dibujar_lago(pant, ap)
        # flores y matas que se mecen con el viento y se apartan cuando alguien pasa
        viento = self.t * 2.1
        pies = {}
        for _, px_, py_ in self.caminantes:
            pies.setdefault((int(px_ // TILE), int(py_ // TILE)), []).append((px_, py_))
        for tipo, x, y, color, fase in self.flores:
            if not vis(x, y, 12):
                continue
            sx, sy = ap(x, y)
            sx, sy = int(sx), int(sy)
            vaiven = round(math.sin(viento + fase + x * 0.02) * 1.6)
            for px_, py_ in pies.get((x // TILE, y // TILE), ()):
                if abs(px_ - x) < 8 and abs(py_ - y) < 6:
                    vaiven = 2 * ESC if x >= px_ else -2 * ESC       # se agacha hacia el otro lado
                    sy += ESC
            if tipo == "mata":
                pant.fill(TALLO, (sx - ESC, sy - ESC, ESC, ESC))
                pant.fill(TALLO, (sx + ESC, sy - ESC, ESC, ESC))
                pant.fill(HOJITA, (sx + vaiven, sy - 2 * ESC, ESC, 2 * ESC))
                pant.fill(HOJITA, (sx - ESC + vaiven // 2, sy - 2 * ESC, ESC, ESC))
            else:
                pant.fill(TALLO, (sx, sy - ESC, ESC, 2 * ESC))
                cx, cy = sx + vaiven, sy - 2 * ESC
                pant.fill(color, (cx - ESC, cy, 3 * ESC, ESC))
                pant.fill(color, (cx, cy - ESC, ESC, 3 * ESC))
                pant.fill((255, 226, 90) if color != (255, 214, 70) else (220, 120, 40), (cx, cy, ESC, ESC))
        self.hierba.dibujar(pant, render)
        # banderas de la alcaldía
        cuadro = int(self.t * 9) % 8
        for x, y in self.banderas:
            if not vis(x, y, 80):
                continue
            sx, sy = ap(x, y)
            sx, sy = int(sx), int(sy)
            pant.fill((34, 26, 44), (sx - 3, sy - 28 * ESC - 3, 2 * ESC, 28 * ESC + 6))       # asta con borde
            pant.fill((196, 200, 214), (sx - 2, sy - 28 * ESC, ESC, 28 * ESC))
            pant.fill((255, 214, 70), (sx - 4, sy - 29 * ESC - 4, 2 * ESC + 2, 2 * ESC))      # la bolita dorada
            pant.blit(bandera(cuadro), (sx + ESC - 2, sy - 28 * ESC))
        # la fuente: gotas que saltan y ondas donde caen
        for gx, gy, alto, *_ in self.gotas:
            sx, sy = ap(gx, gy - alto)
            pant.fill((236, 252, 255) if alto > 6 else (170, 226, 244), (int(sx), int(sy), ESC, ESC))
        # palomas en el piso
        for p in self.palomas:
            if not p["vuela"] and vis(p["x"], p["y"], 20):
                self._dibujar_paloma(pant, ap, p)
        # polvo y estela de los Bulos
        for x, y, _, _, vida, maxv, tipo in self.motas:
            f = vida / maxv
            sx, sy = ap(x, y)
            if tipo == "polvo":
                r = int(3 + 6 * (1 - f))
                img = bolita(r, (236, 230, 214), int(150 * f) // 30 * 30 + 30)
            elif tipo == "humo":
                r = int(3 + 7 * (1 - f))
                img = bolita(r, (196, 198, 210), int(120 * f) // 30 * 30 + 20)
            else:
                r = int(2 + 4 * f)
                img = bolita(r, (176, 110, 255), int(170 * f) // 30 * 30 + 20)
            pant.blit(img, (int(sx) - r, int(sy) - r))

    def _dibujar_lago(self, pant, ap):
        e = self.mapa.estanque
        if self.agua_cuadros and e:
            capa = self.agua_cuadros[int(self.t * 10) % len(self.agua_cuadros)]
            sx, sy = ap(e["x"], e["y"])
            pant.blit(pygame.transform.scale(capa, (capa.get_width() * ESC, capa.get_height() * ESC)), (int(sx), int(sy)))
        for x, y, largo, fase, vel in self.brillos:
            luz = math.sin(self.t * vel + fase)
            if luz < 0.15:
                continue
            sx, sy = ap(x, y)
            pant.fill((236, 252, 255) if luz > 0.7 else (176, 232, 240), (int(sx), int(sy), int(largo * ESC * luz) + ESC, ESC))
        for x, y, flor in self.nenufares:
            img = nenufar(flor)
            sx, sy = ap(x, y + math.sin(self.t * 1.3 + x) * 0.6)
            pant.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() // 2))
        for x, y, t, dur, rmax in self.ondas:
            if t < 0:
                continue
            f = t / dur
            img = _onda(max(1, int(1 + (rmax - 1) * f)), int(220 * (1 - f)) // 40 * 40 + 20)
            sx, sy = ap(x, y)
            pant.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() // 2))
        # la pata y sus patitos (cada patito va por donde pasó la mamá)
        p = self.pata
        rastro = p["rastro"]
        for k in (3, 2, 1):
            i = len(rastro) - 1 - k * 7
            if i < 1:
                continue
            x, y = rastro[i]
            izq = rastro[i][0] < rastro[i - 1][0] if abs(rastro[i][0] - rastro[i - 1][0]) > 0.01 else p["izq"]
            self._nadar(pant, ap, pato(izq, chico=True), x, y, k)
        self._nadar(pant, ap, pato(p["izq"]), p["x"], p["y"], 0)

    def _nadar(self, pant, ap, img, x, y, fase):
        sx, sy = ap(x, y)
        bob = round(math.sin(self.t * 3 + fase * 1.7) * 1.2)
        w, h = img.get_size()
        sx, sy = int(sx) - w // 2, int(sy) - h + bob
        pant.blit(reflejo(img), (sx, sy + h - 2 * ESC - bob))                            # su reflejo
        pygame.draw.ellipse(pant, (150, 214, 226), (sx + 2, sy + h - 7, w - 4, 8), 3)     # el agua alrededor
        pant.blit(img, (sx, sy))

    def dibujar_nubes(self, pant, render):
        """Sombras de nubes que cruzan la ciudad (encima de todo lo del piso, también de la gente)."""
        if self.de_noche:
            return
        nube = _nube_sombra()
        for x, y in self.nubes:
            sx, sy = render.a_pantalla(x, y)
            if -nube.get_width() < sx < ANCHO and -nube.get_height() < sy < ALTO:
                pant.blit(nube, (int(sx), int(sy)))

    def dibujar_aire(self, pant, render):
        """Lo que va por encima de la gente: palomas volando, mariposas, hojas y destellos."""
        ap = render.a_pantalla
        vis = render.visible
        for p in self.palomas:
            if p["vuela"] and vis(p["x"], p["y"], 30):
                self._dibujar_paloma(pant, ap, p)
        if not self.de_noche:
            for m in self.mariposas:
                if not vis(m["x"], m["y"], 20):
                    continue
                img = mariposa(int(m["t"] * 10) % 2, m["color"])
                sx, sy = ap(m["x"], m["y"])
                pant.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() // 2))
        for x, y, color, fase, vida in self.hojas:
            if not vis(x, y, 10):
                continue
            sx, sy = ap(x, y)
            ancho = 2 if math.sin(vida * 5 + fase) > 0 else 1
            pant.fill((34, 26, 44), (int(sx) - 1, int(sy) - 1, ancho * ESC + 2, ESC + 2))
            pant.fill(color, (int(sx), int(sy), ancho * ESC, ESC))
        self.hierba.dibujar_hojitas(pant, render)
        if not self.de_noche:                      # polen que flota con la luz del día
            for k in range(18):
                brillo = math.sin(self.t * (1.3 + k % 4 * 0.3) + k * 2.1)
                if brillo < 0.2:
                    continue
                x = (k * 211 + self.t * (9 + k % 5 * 3) - render.cam[0] * 0.35) % (ANCHO + 40) - 20
                y = (k * 127 + math.sin(self.t * 0.6 + k) * 30 - render.cam[1] * 0.35) % (ALTO + 40) - 20
                tam = 3 if brillo > 0.75 else 2
                pant.fill((255, 248, 206), (int(x), int(y), tam, tam))
        for x, y, t, dur in self.destellos:
            f = t / dur
            tam = 2 if 0.25 < f < 0.7 else 1
            img = _destello(tam, (255, 236, 140))
            sx, sy = ap(x, y)
            pant.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() // 2))

    def dibujar_noche(self, pant, render):
        """Después de oscurecer: polvo que flota en la luz de los faroles y luciérnagas."""
        if not self.de_noche:
            return
        for i, (lx, ly) in enumerate(self.mapa.luces):
            if not render.visible(lx, ly - 20, 60):
                continue
            for k in range(6):
                fase = i * 1.7 + k * 2.3
                x = lx + math.sin(self.t * 0.45 + fase) * 13 + math.sin(self.t * 1.3 + fase * 2) * 3
                y = ly - 26 + ((self.t * (3 + k % 3) + k * 7.0) % 30)
                luz = math.sin(self.t * 2.6 + fase * 3)
                if luz < -0.3:
                    continue
                sx, sy = render.a_pantalla(x, y)
                g = resplandor(5, (150, 130, 70) if luz > 0.4 else (90, 78, 42))
                pant.blit(g, (int(sx) - 5, int(sy) - 5), special_flags=pygame.BLEND_RGB_ADD)
        for m in self.luciernagas:
            if not render.visible(m["x"], m["y"], 20):
                continue
            luz = math.sin(self.t * 2.2 + m["fase"])
            if luz < -0.2:
                continue
            sx, sy = render.a_pantalla(m["x"], m["y"])
            g = resplandor(12, (170, 255, 90) if luz > 0.4 else (90, 150, 50))
            pant.blit(g, (int(sx) - 12, int(sy) - 12), special_flags=pygame.BLEND_RGB_ADD)
            pant.fill((236, 255, 170), (int(sx) - 1, int(sy) - 1, ESC, ESC))

    def _dibujar_paloma(self, pant, ap, p):
        if p["vuela"]:
            cuadro = 2 + int(self.t * 12) % 2
        else:
            cuadro = 1 if p["pica"] > 0 and int(p["pica"] * 8) % 2 else 0
        img = paloma(cuadro, p["izq"])
        sx, sy = ap(p["x"], p["y"])
        if p["alto"] > 1:   # su sombra en el piso
            pant.blit(bolita(7, (0, 0, 0), 60), (int(sx) - 7, int(sy) - 5))
        pant.blit(img, (int(sx) - img.get_width() // 2, int(sy) - img.get_height() - int(p["alto"] * ESC)))
