"""Pantalla de juego de Corta la mentira: cielo, ciudad, publicaciones volando, el tajo y los efectos."""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.apariencia import look_aleatorio
from ..modelo.mapa import nombre_zona
from ..ui import personajes, recursos
from ..vivo.dibujo import (AZUL, BLANCO, LILA, MANGO, ROJO, TINTA, TINTA2, VERDE, anillo, ancho_texto, circulo,
                           icono, mezclar, oscuro, pildora, rebote, sombra, suave, texto)
from .ciudad import Horizonte
from .contenido import ESPECIALES
from .partida import ALTO, ANCHO, BARRIOS, FIEBRE_SEG, NIVEL_MAX, Partida

_rng_caras = random.Random(17)
CARAS = [look_aleatorio(_rng_caras, i % 2 == 0) for i in range(24)]
DORADO = (255, 200, 40)


def _partir_lineas(s, tam, ancho, peso=800):
    palabras, lineas, actual = s.split(), [], ""
    for p in palabras:
        prueba = (actual + " " + p).strip()
        if ancho_texto(prueba, tam, peso) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


class PantallaCorta:
    def __init__(self, app, jugadores, semilla=None, dia_seg=None, demo=False):
        self.app = app
        self.demo = demo
        kw = {} if dia_seg is None else dict(dia_seg=dia_seg)
        self.p = Partida(jugadores, semilla=semilla, **kw)
        self.t = 0.0
        self.tam = None
        self.cache = {}
        self.trazo = []              # puntos recientes del mouse: (x, y, t) en coordenadas de pantalla
        self.mitades = []
        self.particulas = []
        self.textos = []             # textos que flotan (+puntos, ¡Era verdad!)
        self.rayos = []              # contagios entre barrios
        self.destellos = {}          # barrio -> (color, t0)
        self.temblor = 0.0
        self.parada = 0.0            # congelar un instante al cortar varias (se siente el golpe)
        self.raton_prev = None
        self.raton_t = 0.0
        self.estado_previo = self.p.estado
        self.estado_t = 0.0
        self.tutorial = not demo
        self.tut_t = 0.0
        self.mascota = []            # globos de la lechuza
        self.decir("¡Corta lo falso! No cortes lo verdadero.", 5)
        self._demo_rng = random.Random(3)

    # -------------------------------------------------------------- geometría de pantalla
    def _preparar(self, sup):
        tam = sup.get_size()
        if tam != self.tam:
            self.tam = tam
            W, H = tam
            self.U = H / ALTO
            self.ox = (W - ANCHO * self.U) / 2
            self.horizonte = Horizonte(self.U, self.ox, W, H)
            self.cache.clear()
            self.cielo = None

    def a_pantalla(self, x, y):
        return self.ox + x * self.U, y * self.U

    def a_campo(self, x, y):
        return (x - self.ox) / self.U, y / self.U

    def decir(self, txt, dur=3.5):
        self.mascota = [dict(texto=txt, t0=getattr(self, "t", 0.0), dur=dur)]

    # -------------------------------------------------------------- entrada
    def evento(self, e):
        if self.demo:
            return
        if self.tutorial:
            if (e.type == pygame.MOUSEBUTTONDOWN or (e.type == pygame.KEYDOWN and e.key in (
                    pygame.K_RETURN, pygame.K_SPACE))) and self.tut_t > 0.6:
                self.tutorial = False
                self.app.sonar("turno")
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.app.ir_menu()
            elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._continuar()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.p.estado != "jugando":
                self._continuar()

    def _continuar(self):
        if self.estado_t < 1.0:
            return
        if self.p.estado == "fin_dia":
            self.p.siguiente_dia()
            self.app.sonar("turno")
            if len(self.p.jugadores) > 1:
                self.decir(f"¡Turno de {self.p.jugador.nombre}!", 3)
        elif self.p.estado == "fin":
            self.app.ir_menu()

    def _leer_raton(self, dt):
        pos = pygame.mouse.get_pos()
        apretado = pygame.mouse.get_pressed()[0]
        ahora = self.t
        if self.raton_prev is not None:
            dx, dy = pos[0] - self.raton_prev[0], pos[1] - self.raton_prev[1]
            vel = math.hypot(dx, dy) / max(dt, 1e-3) / self.U
            if (apretado and math.hypot(dx, dy) > 3 * self.U) or vel > 2400:
                self.trazo.append((pos[0], pos[1], ahora))
                a = self.a_campo(*self.raton_prev)
                b = self.a_campo(*pos)
                n = self.p.cortar(a, b)
                if n and vel > 0:
                    pass
            elif not apretado:
                self.trazo.append((pos[0], pos[1], ahora)) if self.trazo and ahora - self.trazo[-1][2] < 0.05 else None
        self.raton_prev = pos
        self.trazo = [q for q in self.trazo if ahora - q[2] < 0.13]

    def _demo(self, dt):
        """En el menú la partida se juega sola: un tajo de vez en cuando sobre una falsa."""
        for pub in self.p.pubs:
            if pub.tipo == "falsa" and 120 < pub.y < 520 and self._demo_rng.random() < dt * 0.9:
                a = (pub.x - 160, pub.y - 50)
                b = (pub.x + 160, pub.y + 50)
                self.p.cortar(a, b)
                sa, sb = self.a_pantalla(*a), self.a_pantalla(*b)
                for k in range(6):
                    f = k / 5
                    self.trazo.append((sa[0] + (sb[0] - sa[0]) * f, sa[1] + (sb[1] - sa[1]) * f, self.t - 0.1 + f * 0.1))
                break
        self.trazo = [q for q in self.trazo if self.t - q[2] < 0.13]
        if self.p.estado == "fin_dia":
            self.p.siguiente_dia()
        if self.p.estado == "fin" or self.p.salud() < 40:
            for z in BARRIOS:
                self.p.nivel[z] = 0

    # -------------------------------------------------------------- bucle
    def actualizar(self, dt):
        self.t += dt
        if self.tutorial:
            self.tut_t += dt
            return
        if self.parada > 0:
            self.parada -= dt
            dt_juego = 0.0
        else:
            dt_juego = dt
        if self.demo:
            self._demo(dt)
        elif self.p.estado == "jugando":
            self._leer_raton(dt)
        self.p.actualizar(dt_juego)
        if self.p.estado != self.estado_previo:
            self.estado_previo = self.p.estado
            self.estado_t = 0.0
            if not self.demo:
                self.app.sonar("noche" if self.p.estado == "fin_dia" else "victoria" if self.p.estado == "fin" else "turno")
        self.estado_t += dt
        for ev in self.p.eventos:
            self._evento_juego(ev)
        self.p.eventos.clear()
        self._fisica(dt)
        self.temblor = max(0.0, self.temblor - dt * 3)

    def _sonar(self, nombre):
        if not self.demo:
            self.app.sonar(nombre)

    def _evento_juego(self, ev):
        t = ev["t_"]
        U = self.U
        if t == "corte":
            pub = ev["pub"]
            self._partir(pub, ev["dir"])
            x, y = self.a_pantalla(pub.x, pub.y)
            if pub.tipo == "falsa":
                self._chispas(x, y, ROJO, 18)
                if ev.get("puntos"):
                    combo = ev.get("combo", 1)
                    self._flotar(f"+{ev['puntos']}", x, y - 30 * U, MANGO, 30)
                    if combo >= 3:
                        self._flotar(f"¡COMBO x{combo}!", x, y - 72 * U, (255, 120, 40), 36)
                self._sonar("pop")
            elif pub.tipo == "especial":
                self._chispas(x, y, DORADO, 30)
                self._sonar("logro")
            else:
                self._chispas(x, y, (170, 176, 200), 14)
                self._sonar("malo")
                self.temblor = 0.6
        elif t == "error":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            self._flotar(ev["texto"], x, y - 10 * self.U, ROJO, 40, sub=ev.get("sub"), dur=2.0)
            self.decir("¡Ojo! Esa venía de una fuente oficial: era verdad.", 3.5)
        elif t == "multi":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            nombre = {2: "¡DOBLE!", 3: "¡TRIPLE!"}.get(ev["n"], f"¡x{ev['n']}!")
            self._flotar(nombre, x, y - 110 * U, (255, 90, 160), 48, dur=1.2)
            self.parada = 0.07
            self.temblor = 0.4
            self._sonar("logro")
        elif t == "cadena":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            self._flotar(f"¡Cortaste el ORIGEN! −{ev['n']} copias", x, y - 120 * U, DORADO, 30, dur=1.6)
            self.parada = 0.1
            self.decir("Cortar el origen tumba todas sus copias.", 3)
        elif t == "copia":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            self._flotar("¡Se copió!", x, y - 50 * U, ROJO, 26)
            self._sonar("rama")
            self.decir("Un ORIGEN que llega arriba se copia. ¡Córtalo antes!", 3.5)
        elif t == "cae":
            x = self.ox + ev["x"] * U
            y = self.horizonte.base
            self._chispas(x, y - 20 * U, (120, 110, 130), 24, arriba=True)
            self.destellos[ev["barrio"]] = (ROJO, self.t)
            self.temblor = 1.0 if ev.get("viral") else 0.5
            self._flotar(f"¡Cayó en {nombre_zona(ev['barrio'])}!", x, y - 210 * U, ROJO, 24, dur=1.6)
            self._sonar("malo")
        elif t == "contagio":
            self.rayos.append(dict(de=ev["de"], a=ev["a"], t0=self.t))
            self.destellos[ev["a"]] = (ROJO, self.t)
            self._sonar("rama")
        elif t == "sana":
            self.destellos[ev["barrio"]] = (VERDE, self.t)
            x = self.horizonte.x_barrio(ev["barrio"])
            self._chispas(x, self.horizonte.base - 80 * U, VERDE, 16, arriba=True)
        elif t == "fiebre":
            self._flotar("¡FIEBRE! Puntos x2", self.tam[0] / 2, 210 * U, (255, 90, 160), 54, dur=1.8)
            self._sonar("victoria")
        elif t == "poder":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            info = ESPECIALES[ev["especial"]]
            self._flotar(info["texto"] + "!", x, y - 60 * U, DORADO, 40, sub=info["ayuda"], dur=2.0)
            if ev["especial"] == "megafono":
                self.temblor = 0.8
        elif t == "golpe":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            self._chispas(x, y, (255, 120, 40), 10)
            self._sonar("tick")
        elif t == "bloqueo":
            x = self.ox + ev["x"] * U
            self._flotar("¡Bloqueado!", x, self.horizonte.base - 200 * U, AZUL, 28)

    # -------------------------------------------------------------- piezas, chispas y textos
    def _tarjeta(self, pub):
        """La imagen de una publicación (se dibuja una vez y se gira en cada cuadro)."""
        U = self.U
        clave = ("pub", pub.id, round(U * 100), self.p.lento > 0)
        img = self.cache.get(clave)
        if img is not None:
            return img
        if len(self.cache) > 400:
            self.cache = {k: v for k, v in self.cache.items() if k[0] != "pub"}
        w, h = round(pub.ancho * U), round(pub.alto * U)
        pad = round(14 * U)
        s = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        r = pygame.Rect(pad, pad, w, h)
        if pub.tipo == "especial":
            info = ESPECIALES[pub.especial]
            c = (pad + w // 2, pad + h // 2)
            for k, a in ((1.0, 255),):
                pygame.draw.circle(s, (255, 236, 150), c, w // 2)
            pygame.draw.circle(s, DORADO, c, w // 2 - round(6 * U))
            pygame.draw.circle(s, BLANCO, c, w // 2, max(2, round(4 * U)))
            ic = recursos.icono(info["icono"], round(54 * U), TINTA, 2.8)
            s.blit(ic, ic.get_rect(center=c))
        else:
            borde = (255, 90, 40) if pub.viral else (220, 214, 250)
            pygame.draw.rect(s, (40, 30, 90, 70), r.move(0, round(5 * U)), border_radius=round(18 * U))
            pygame.draw.rect(s, BLANCO, r, border_radius=round(18 * U))
            pygame.draw.rect(s, borde, r, max(2, round((5 if pub.viral else 3) * U)), border_radius=round(18 * U))
            if self.p.lento > 0:
                col = ROJO if pub.tipo == "falsa" else VERDE
                pygame.draw.rect(s, col, r.inflate(round(8 * U), round(8 * U)), max(3, round(6 * U)),
                                 border_radius=round(22 * U))
            av = personajes.avatar(CARAS[pub.autor % len(CARAS)], round(58 * U), (236, 231, 255), "npc", "neutral")
            s.blit(av, (r.x + round(12 * U), r.y + round(12 * U)))
            tx = r.x + round(80 * U)
            fuente = pub.fuente
            while ancho_texto(fuente, 13 * U, 900) > w - 96 * U and len(fuente) > 6:
                fuente = fuente[:-2]
            if fuente != pub.fuente:
                fuente = fuente[:-1] + "…"
            img_f = recursos.render_texto(
                fuente, max(6, round(13 * U)), TINTA2, 900, "texto")
            s.blit(img_f, (tx, r.y + round(12 * U)))
            lineas = _partir_lineas(pub.texto, 17 * U, w - 96 * U)[:3]
            tam = 17 * U if len(lineas) <= 2 else 15 * U
            for i, l in enumerate(lineas):
                img_t = recursos.render_texto(
                    l, max(6, round(tam)), TINTA, 800, "texto")
                s.blit(img_t, (tx, r.y + round(34 * U) + round(i * tam * 1.25)))
            if pub.origen:
                cr = pygame.Rect(0, 0, round(86 * U), round(24 * U))
                cr.midbottom = (r.centerx, r.y + round(8 * U))
                pygame.draw.rect(s, DORADO, cr, border_radius=round(12 * U))
                t = recursos.render_texto(
                    "ORIGEN", max(6, round(13 * U)), TINTA, 900, "texto")
                s.blit(t, t.get_rect(center=cr.center))
            if pub.viral:
                cr = pygame.Rect(0, 0, round(90 * U), round(24 * U))
                cr.midbottom = (r.centerx, r.y + round(8 * U))
                pygame.draw.rect(s, (255, 90, 40), cr, border_radius=round(12 * U))
                t = recursos.render_texto(
                    "¡VIRAL!", max(6, round(13 * U)), BLANCO, 900, "texto")
                s.blit(t, t.get_rect(center=cr.center))
            if pub.copia:
                cr = pygame.Rect(0, 0, round(62 * U), round(22 * U))
                cr.midbottom = (r.centerx, r.y + round(8 * U))
                pygame.draw.rect(s, (255, 214, 214), cr, border_radius=round(11 * U))
                t = recursos.render_texto(
                    "copia", max(6, round(12 * U)), ROJO, 900, "texto")
                s.blit(t, t.get_rect(center=cr.center))
        s = s.convert_alpha()
        self.cache[clave] = s
        return s

    def _partir(self, pub, direccion):
        """Corta la imagen en dos mitades que salen volando hacia lados opuestos."""
        img = pygame.transform.rotate(self._tarjeta(pub), -pub.rot)
        w, h = img.get_size()
        dx, dy = direccion
        horizontal = abs(dx) >= abs(dy)
        x, y = self.a_pantalla(pub.x, pub.y)
        if horizontal:
            partes = [(img.subsurface((0, 0, w, h // 2)).copy(), (0, -h / 4), (0, -1)),
                      (img.subsurface((0, h // 2, w, h - h // 2)).copy(), (0, h / 4), (0, 1))]
        else:
            partes = [(img.subsurface((0, 0, w // 2, h)).copy(), (-w / 4, 0), (-1, 0)),
                      (img.subsurface((w // 2, 0, w - w // 2, h)).copy(), (w / 4, 0), (1, 0))]
        U = self.U
        for s, (ox, oy), (nx, ny) in partes:
            self.mitades.append(dict(img=s, x=x + ox, y=y + oy, vx=nx * 260 * U + pub.vx * U * 0.5,
                                     vy=ny * 160 * U - 120 * U + pub.vy * U * 0.3,
                                     rot=0.0, vrot=random.uniform(-260, 260), t=0.0))

    def _chispas(self, x, y, color, n, arriba=False):
        U = self.U
        for _ in range(n):
            ang = random.uniform(-math.pi, 0) if arriba else random.uniform(0, math.tau)
            v = random.uniform(150, 520) * U
            self.particulas.append(dict(x=x, y=y, vx=math.cos(ang) * v, vy=math.sin(ang) * v,
                                        t=0.0, dur=random.uniform(0.4, 0.9), r=random.uniform(3, 8) * U,
                                        color=mezclar(color, BLANCO, random.uniform(0, 0.4))))

    def _flotar(self, txt, x, y, color, tam, sub=None, dur=1.1):
        U = getattr(self, "U", 1)
        y = max(170 * U, y)
        if self.tam:
            x = max(220 * U, min(self.tam[0] - 220 * U, x))
        self.textos.append(dict(txt=txt, x=x, y=y, color=color, tam=tam, sub=sub, t0=self.t, dur=dur))
        self.textos = self.textos[-12:]

    def _fisica(self, dt):
        U = self.U if self.tam else 1
        for m in self.mitades:
            m["t"] += dt
            m["vy"] += 1400 * U * dt
            m["x"] += m["vx"] * dt
            m["y"] += m["vy"] * dt
            m["rot"] += m["vrot"] * dt
        self.mitades = [m for m in self.mitades if m["t"] < 1.2][-40:]
        for q in self.particulas:
            q["t"] += dt
            q["vy"] += 900 * U * dt
            q["x"] += q["vx"] * dt
            q["y"] += q["vy"] * dt
        self.particulas = [q for q in self.particulas if q["t"] < q["dur"]][-400:]
        self.rayos = [r for r in self.rayos if self.t - r["t0"] < 0.8]

    # -------------------------------------------------------------- dibujo
    def dibujar(self, sup):
        self._preparar(sup)
        U = self.U
        W, H = sup.get_size()
        sx = sy = 0
        if self.temblor > 0 and not getattr(self.app, "menos_movimiento", False):
            sx = random.uniform(-1, 1) * 10 * U * self.temblor
            sy = random.uniform(-1, 1) * 7 * U * self.temblor
        self._cielo(sup)
        self._nubes(sup)
        self._pajaros(sup)
        self.horizonte.dibujar(sup, self.p.nivel, self.t, (sx, sy))
        self._estado_barrios(sup, sx, sy)
        self._vecinos(sup, sx, sy)
        for pub in self.p.pubs:
            self._pub(sup, pub, sx, sy)
        for m in self.mitades:
            img = pygame.transform.rotate(m["img"], m["rot"])
            img.set_alpha(round(255 * max(0, 1 - m["t"] / 1.2)))
            sup.blit(img, img.get_rect(center=(m["x"] + sx, m["y"] + sy)))
        for q in self.particulas:
            circulo(sup, (q["x"] + sx, q["y"] + sy), q["r"] * (1 - q["t"] / q["dur"]) + 1, q["color"])
        self._textos(sup)
        self._tajo(sup)
        if self.p.lento > 0:
            velo = pygame.Surface((W, H), pygame.SRCALPHA)
            velo.fill((60, 120, 255, 28))
            sup.blit(velo, (0, 0))
        if self.p.fiebre > 0:
            fase = self.t * 6
            col = tuple(round(127 + 127 * math.sin(fase + k * 2.1)) for k in range(3))
            pygame.draw.rect(sup, col, (0, 0, W, H), max(6, round(12 * U)))
        if self.demo:
            return
        self._hud(sup)
        self._lechuza(sup)
        if self.tutorial:
            self._tutorial(sup)
        elif self.p.estado == "fin_dia":
            self._fin_dia(sup)
        elif self.p.estado == "fin":
            self._fin(sup)
        else:
            self._cursor(sup)

    def _cielo(self, sup):
        W, H = sup.get_size()
        frac = min(1.0, self.p.reloj / self.p.dia_seg)
        dia = self.p.dia
        clave = ("cielo", W, H, dia, round(frac * 12))
        img = self.cache.get(clave)
        if img is None:
            arriba = mezclar((110, 200, 245), (120, 110, 210), max(0, frac - 0.6) / 0.4)
            abajo = mezclar((210, 240, 255), (255, 190, 150), max(0, frac - 0.55) / 0.45)
            img = pygame.Surface((W, H))
            for y in range(0, H, 4):
                pygame.draw.rect(img, mezclar(arriba, abajo, y / H), (0, y, W, 4))
            U = self.U
            sol_y = H * (0.16 + 0.22 * frac)
            for rr, a in ((92, 26), (66, 46), (44, 255)):
                s = pygame.Surface((rr * 2 * U, rr * 2 * U), pygame.SRCALPHA)
                pygame.draw.circle(s, (255, 232, 150, a), (rr * U, rr * U), rr * U)
                img.blit(s, (W * 0.86 - rr * U, sol_y - rr * U))
            # Colinas y una ciudad lejana, para que el fondo no quede vacío.
            base = self.horizonte.base
            lejos = mezclar(abajo, (150, 140, 220), 0.3)
            r = random.Random(9)
            x = -40 * U
            while x < W:
                w = r.uniform(40, 90) * U
                h = r.uniform(30, 120) * U
                pygame.draw.rect(img, lejos, (x, base - 120 * U - h, w, h + 40 * U))
                for k in range(int(h // (22 * U))):
                    if r.random() < 0.4:
                        pygame.draw.rect(img, mezclar(lejos, (255, 240, 200), 0.35),
                                         (x + w * 0.3, base - 110 * U - h + k * 22 * U, w * 0.18, 8 * U))
                x += w + r.uniform(4, 16) * U
            colina = mezclar(abajo, (120, 200, 140), 0.55)
            pts = [(0, H)] + [(xx, base - 120 * U - math.sin(xx / W * 7 + 1.3) * 26 * U - math.sin(xx / W * 17) * 10 * U)
                              for xx in range(0, W + 20, 20)] + [(W, H)]
            pygame.draw.polygon(img, colina, pts)
            img = img.convert()
            self.cache = {k: v for k, v in self.cache.items() if k[0] != "cielo"}
            self.cache[clave] = img
        sup.blit(img, (0, 0))

    def _nubes(self, sup):
        U = self.U
        W, H = sup.get_size()
        for k, (vel, y, tam) in enumerate(((14, 110, 1.0), (9, 190, 0.7), (20, 60, 0.8), (6, 260, 1.2))):
            x = ((self.t * vel * U + k * 470 * U) % (W + 400 * U)) - 200 * U
            clave = ("nube", round(tam * 100), round(U * 100))
            img = self.cache.get(clave)
            if img is None:
                img = pygame.Surface((round(220 * U * tam), round(90 * U * tam)), pygame.SRCALPHA)
                for dx, dy, r in ((50, 56, 32), (95, 40, 42), (140, 54, 34), (180, 64, 22), (24, 66, 20)):
                    pygame.draw.circle(img, (255, 255, 255, 220), (round(dx * U * tam), round(dy * U * tam)),
                                       round(r * U * tam))
                self.cache[clave] = img
            sup.blit(img, (x, y * U))

    def _pajaros(self, sup):
        U = self.U
        W, H = sup.get_size()
        for k in range(5):
            x = ((self.t * (40 + k * 7) * U + k * 380 * U) % (W + 200 * U)) - 100 * U
            y = (130 + k * 37 + math.sin(self.t + k) * 10) * U
            ala = math.sin(self.t * 9 + k) * 6 * U
            pygame.draw.lines(sup, (70, 70, 110), False, [(x - 10 * U, y - ala), (x, y), (x + 10 * U, y - ala)],
                              max(1, round(2 * U)))

    def _estado_barrios(self, sup, sx, sy):
        """Nubes de tormenta sobre los barrios enfermos y destellos cuando algo les pasa."""
        U = self.U
        hz = self.horizonte
        for z in BARRIOS:
            n = self.p.nivel[z]
            x = hz.x_barrio(z) + sx
            if n >= 2:
                y = hz.base - hz.alto - 10 * U + math.sin(self.t * 2 + x) * 3 * U + sy
                for dx, r in ((-26, 22), (0, 30), (26, 22)):
                    circulo(sup, (x + dx * U, y), r * U, (110, 110, 130) if n == 2 else (80, 76, 100))
                if n >= NIVEL_MAX and int(self.t * 4 + x) % 7 == 0:
                    pygame.draw.lines(sup, MANGO, False, [(x, y + 20 * U), (x - 8 * U, y + 40 * U), (x + 6 * U, y + 42 * U),
                                                          (x - 4 * U, y + 66 * U)], max(2, round(4 * U)))
                for i in range(6):
                    rx = x - 40 * U + i * 16 * U
                    ry = y + 24 * U + ((self.t * 260 * U + i * 37 * U) % (60 * U))
                    pygame.draw.line(sup, (150, 170, 220), (rx, ry), (rx - 3 * U, ry + 10 * U), max(1, round(2 * U)))
            d = self.destellos.get(z)
            if d and self.t - d[1] < 0.7:
                k = (self.t - d[1]) / 0.7
                r = pygame.Rect(0, 0, ANCHO / len(BARRIOS) * U, hz.alto)
                r.midbottom = (x, hz.base + sy)
                s = pygame.Surface(r.size, pygame.SRCALPHA)
                s.fill((*d[0], round(120 * (1 - k))))
                sup.blit(s, r)
        for ry in self.rayos:
            k = (self.t - ry["t0"]) / 0.8
            a = (hz.x_barrio(ry["de"]) + sx, hz.base - hz.alto * 0.6 + sy)
            b = (hz.x_barrio(ry["a"]) + sx, hz.base - hz.alto * 0.6 + sy)
            pts = []
            for i in range(13):
                f = i / 12
                pts.append((a[0] + (b[0] - a[0]) * f, a[1] - math.sin(math.pi * f) * 90 * U + random.uniform(-6, 6) * U))
            pygame.draw.lines(sup, ROJO, False, pts, max(2, round(5 * U * (1 - k)) + 1))

    def _vecinos(self, sup, sx, sy):
        """Dos vecinos por barrio en el andén: se alegran o se enojan según cómo esté su barrio."""
        U = self.U
        hz = self.horizonte
        alto = round(58 * U)
        for i, z in enumerate(BARRIOS):
            n = self.p.nivel[z]
            exp = "feliz" if n == 0 else "preocupado" if n == 1 else "enojado"
            for k in range(2):
                look = CARAS[(i * 2 + k) % len(CARAS)]
                clave = ("vec", i, k, exp, alto)
                img = self.cache.get(clave)
                if img is None:
                    img = personajes.cuerpo(look, "npc", exp, alto)
                    if k:
                        img = pygame.transform.flip(img, True, False)
                    self.cache[clave] = img
                x = hz.x_barrio(z) + (-34 if k == 0 else 30) * U + sx
                bote = abs(math.sin(self.t * (3 if n == 0 else 7) + i + k)) * (4 if n == 0 else 2) * U
                sup.blit(img, (x - img.get_width() / 2, hz.base + 18 * U - img.get_height() - bote + sy))

    def _pub(self, sup, pub, sx, sy):
        img = self._tarjeta(pub)
        rot = pygame.transform.rotozoom(img, -pub.rot, 1.0)
        x, y = self.a_pantalla(pub.x, pub.y)
        if pub.golpe > 0:
            rot = rot.copy()
            rot.fill((255, 120, 40, 0), special_flags=pygame.BLEND_RGBA_ADD)
        sup.blit(rot, rot.get_rect(center=(x + sx, y + sy)))
        if pub.viral:
            U = self.U
            for i in range(3):
                circulo(sup, (x - 20 * U + i * 20 * U + sx, y + pub.alto * U / 2 + 16 * U + sy), 7 * U,
                        (255, 90, 40) if i < pub.vida else (220, 220, 230))

    def _textos(self, sup):
        U = self.U
        vivos = []
        for t in self.textos:
            edad = self.t - t["t0"]
            if edad > t["dur"]:
                continue
            vivos.append(t)
            k = rebote(min(1, edad / 0.25))
            alfa = round(255 * min(1, (t["dur"] - edad) / 0.3))
            y = t["y"] - edad * 40 * U
            tam = t["tam"] * U * k
            texto(sup, t["txt"], (t["x"] + 3 * U, y + 3 * U), tam, (40, 20, 90), 700, "titulo", alfa=alfa)
            texto(sup, t["txt"], (t["x"], y), tam, t["color"], 700, "titulo", alfa=alfa)
            if t.get("sub"):
                w = ancho_texto(t["sub"], 15 * U, 900) + 24 * U
                pildora(sup, (t["x"] - w / 2, y + tam * 0.55, w, 28 * U), BLANCO, con_sombra=False, alfa=min(240, alfa))
                texto(sup, t["sub"], (t["x"], y + tam * 0.55 + 14 * U), 15 * U, TINTA, 900, alfa=alfa)
        self.textos = vivos

    def _tajo(self, sup):
        """La estela del corte: una cuchilla de luz que se afina hacia atrás."""
        pts = self.trazo
        if len(pts) < 2:
            return
        U = self.U
        if self.p.fiebre > 0:
            color = tuple(round(127 + 127 * math.sin(self.t * 8 + k * 2.1)) for k in range(3))
        else:
            color = self.p.jugador.color if not self.demo else (120, 220, 255)
        n = len(pts)
        for capa, (ancho, col) in enumerate(((14, color), (6, BLANCO))):
            izq, der = [], []
            for i, (x, y, _) in enumerate(pts):
                if i == 0:
                    nx, ny = pts[1][0] - x, pts[1][1] - y
                else:
                    nx, ny = x - pts[i - 1][0], y - pts[i - 1][1]
                L = math.hypot(nx, ny) or 1
                px, py = -ny / L, nx / L
                w = ancho * U * (i + 1) / n
                izq.append((x + px * w, y + py * w))
                der.append((x - px * w, y - py * w))
            poligono = izq + der[::-1]
            if len(poligono) >= 3:
                pygame.draw.polygon(sup, col, poligono)

    def _cursor(self, sup):
        x, y = pygame.mouse.get_pos()
        U = self.U
        col = self.p.jugador.color
        anillo(sup, (x, y), 12 * U, col, 3 * U)
        circulo(sup, (x, y), 4 * U, BLANCO)

    # -------------------------------------------------------------- barra de arriba
    def _hud(self, sup):
        U = self.U
        W, H = sup.get_size()
        p = self.p
        j = p.jugador
        # jugador y puntos
        r = pildora(sup, (18 * U, 16 * U, 330 * U, 76 * U), BLANCO, round(24 * U))
        av = personajes.avatar(j.look, round(60 * U), j.color, j.rol, "feliz")
        sup.blit(av, (r.x + 10 * U, r.y + 8 * U))
        texto(sup, j.nombre, (r.x + 82 * U, r.y + 22 * U), 17 * U, TINTA2, 900, ancla="midleft")
        texto(sup, f"{j.puntos:,}".replace(",", "."), (r.x + 82 * U, r.y + 50 * U), 34 * U, TINTA, 700, "titulo", "midleft")
        if p.combo >= 2:
            cr = pildora(sup, (r.right - 96 * U, r.y + 14 * U, 84 * U, 48 * U), (255, 120, 40), round(16 * U))
            texto(sup, f"x{p.combo}", cr.center, 26 * U, BLANCO, 700, "titulo")
        # día y reloj
        w = 330 * U
        r = pildora(sup, (W / 2 - w / 2, 16 * U, w, 64 * U), BLANCO, round(22 * U))
        falta = max(0, p.dia_seg - p.reloj)
        texto(sup, f"Día {p.dia} de {p.dias}", (r.x + 22 * U, r.y + 22 * U), 22 * U, TINTA, 700, "titulo", "midleft")
        barra = pygame.Rect(r.x + 22 * U, r.y + 42 * U, r.w - 100 * U, 10 * U)
        pygame.draw.rect(sup, (232, 234, 246), barra, border_radius=round(5 * U))
        relleno = barra.copy()
        relleno.w = round(barra.w * falta / p.dia_seg)
        pygame.draw.rect(sup, MANGO, relleno, border_radius=round(5 * U))
        texto(sup, f"{int(math.ceil(falta))}", (r.right - 38 * U, r.centery), 30 * U, TINTA, 700, "titulo")
        # salud de la ciudad
        salud = p.salud()
        w = 330 * U
        r = pildora(sup, (W - 18 * U - w, 16 * U, w, 76 * U), BLANCO, round(24 * U))
        col = VERDE if salud >= 60 else MANGO if salud >= 30 else ROJO
        icono(sup, "heart-handshake", (r.x + 36 * U, r.centery), 34 * U, col, 2.6)
        texto(sup, "Ciudad Nova", (r.x + 66 * U, r.y + 22 * U), 15 * U, TINTA2, 900, ancla="midleft")
        barra = pygame.Rect(r.x + 66 * U, r.y + 40 * U, r.w - 140 * U, 18 * U)
        pygame.draw.rect(sup, (232, 234, 246), barra, border_radius=round(9 * U))
        relleno = barra.copy()
        relleno.w = round(barra.w * salud / 100)
        pygame.draw.rect(sup, col, relleno, border_radius=round(9 * U))
        texto(sup, f"{salud}", (r.right - 38 * U, r.centery), 28 * U, col, 700, "titulo")
        # poderes activos
        y = 104 * U
        for k, ic, nombre, col, total in (("lento", "search", "Lupa", AZUL, 6.0), ("escudo", "shield", "Escudo", VERDE, 10.0),
                                          ("fiebre", "flame", "Fiebre x2", (255, 90, 160), FIEBRE_SEG)):
            v = getattr(p, k)
            if v > 0:
                pr = pildora(sup, (W / 2 - 90 * U, y, 180 * U, 36 * U), BLANCO, round(18 * U))
                icono(sup, ic, (pr.x + 22 * U, pr.centery), 20 * U, col, 2.6)
                texto(sup, nombre, (pr.x + 40 * U, pr.centery), 15 * U, TINTA, 900, ancla="midleft")
                anillo(sup, (pr.right - 22 * U, pr.centery), 12 * U, col, 4 * U, v / total)
                y += 44 * U

    def _lechuza(self, sup):
        U = self.U
        W, H = sup.get_size()
        x, y = 30 * U, H - 170 * U
        img = personajes.civi("feliz" if self.p.salud() >= 50 else "preocupado", round(110 * U),
                              parpadeo=int(self.t * 3) % 11 == 0, ala=math.sin(self.t * 3) * 0.3)
        sup.blit(img, (x, y + math.sin(self.t * 2) * 4 * U))
        vivos = []
        for g in self.mascota:
            edad = self.t - g["t0"]
            if edad > g["dur"]:
                continue
            vivos.append(g)
            k = rebote(min(1, edad / 0.3))
            lineas = _partir_lineas(g["texto"], 17 * U, 330 * U, 900)
            w = max(ancho_texto(l, 17 * U, 900) for l in lineas) + 34 * U
            h = (len(lineas) * 24 + 22) * U
            r = pygame.Rect(x + 100 * U, y - h + 10 * U, w * k, h * k)
            sombra(sup, r, round(18 * U))
            pygame.draw.polygon(sup, BLANCO, [(r.x + 4 * U, r.bottom - 22 * U), (r.x + 4 * U, r.bottom - 4 * U),
                                              (r.x - 18 * U, r.bottom + 6 * U)])
            pygame.draw.rect(sup, BLANCO, r, border_radius=round(18 * U))
            if k > 0.8:
                for i, l in enumerate(lineas):
                    texto(sup, l, (r.x + 17 * U, r.y + 22 * U + i * 24 * U), 17 * U, TINTA, 900, ancla="midleft")
        self.mascota = vivos

    # -------------------------------------------------------------- pantallas encima
    def _velo(self, sup, alfa=170):
        s = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
        s.fill((30, 20, 80, alfa))
        sup.blit(s, (0, 0))

    def _tutorial(self, sup):
        U = self.U
        W, H = sup.get_size()
        self._velo(sup, 175)
        texto(sup, "¿Cómo se juega?", (W / 2, 150 * U), 50 * U, BLANCO, 700, "titulo")
        pasos = [("scissors", ROJO, "Corta lo falso", "Arrastra el mouse sobre las publicaciones falsas."),
                 ("badge-check", VERDE, "No cortes lo verdadero", "Las que vienen de una fuente oficial, déjalas pasar."),
                 ("cloud-lightning", (120, 110, 160), "Cuida la ciudad", "Si algo falso cae, el barrio se enferma y contagia.")]
        w, h = 330 * U, 300 * U
        x0 = W / 2 - (3 * w + 2 * 30 * U) / 2
        for i, (ic, col, titulo, desc) in enumerate(pasos):
            k = rebote(min(1, max(0, self.tut_t - i * 0.15) / 0.4))
            r = pygame.Rect(x0 + i * (w + 30 * U), 220 * U + (1 - k) * 40 * U, w, h)
            pildora(sup, r, BLANCO, round(28 * U))
            circulo(sup, (r.centerx, r.y + 80 * U), 50 * U, mezclar(col, BLANCO, 0.75))
            icono(sup, ic, (r.centerx, r.y + 80 * U), 56 * U, col, 2.6)
            texto(sup, titulo, (r.centerx, r.y + 168 * U), 24 * U, TINTA, 700, "titulo")
            for j, l in enumerate(_partir_lineas(desc, 16 * U, w - 50 * U)):
                texto(sup, l, (r.centerx, r.y + 210 * U + j * 24 * U), 16 * U, TINTA2, 800)
        if self.tut_t > 0.6:
            lat = 1 + 0.04 * math.sin(self.t * 5)
            texto(sup, "Haz clic para empezar", (W / 2, 590 * U), 30 * U * lat, MANGO, 700, "titulo")

    def _fin_dia(self, sup):
        U = self.U
        W, H = sup.get_size()
        k = suave(min(1, self.estado_t / 0.6))
        self._velo(sup, round(180 * k))
        res = self.p.resumen or {}
        w, h = 760 * U, 520 * U
        r = pildora(sup, (W / 2 - w / 2, H / 2 - h / 2 + (1 - k) * 50 * U, w, h), BLANCO, round(30 * U))
        texto(sup, f"Termina el día {res.get('dia', self.p.dia)}", (r.centerx, r.y + 52 * U), 36 * U, TINTA, 700, "titulo")
        fila = [("scissors", f"{res.get('cortadas', 0)}", "falsas cortadas", ROJO),
                ("badge-check", f"{res.get('errores', 0)}", "verdades cortadas", MANGO),
                ("cloud-lightning", f"{res.get('caidas', 0)}", "cayeron en la ciudad", (120, 110, 160)),
                ("heart-handshake", f"{res.get('salud', 0)}", "salud de la ciudad", VERDE)]
        cw = (w - 60 * U) / 4
        for i, (ic, num, et, col) in enumerate(fila):
            cx = r.x + 30 * U + cw * (i + 0.5)
            icono(sup, ic, (cx, r.y + 112 * U), 30 * U, col, 2.6)
            texto(sup, num, (cx, r.y + 152 * U), 34 * U, TINTA, 700, "titulo")
            texto(sup, et, (cx, r.y + 182 * U), 13 * U, TINTA2, 900)
        y = r.y + 226 * U
        pistas = res.get("pistas") or []
        texto(sup, "Pistas de mentira que descubriste hoy", (r.x + 40 * U, y), 18 * U, TINTA, 700, "titulo", "midleft")
        y += 32 * U
        if not pistas:
            texto(sup, "Ninguna nueva. ¡Mañana corta más!", (r.x + 40 * U, y), 15 * U, TINTA2, 800, ancla="midleft")
            y += 28 * U
        for pista in pistas[:4]:
            icono(sup, "search", (r.x + 52 * U, y), 18 * U, ROJO, 2.6)
            texto(sup, pista, (r.x + 72 * U, y), 15 * U, TINTA, 800, ancla="midleft")
            y += 28 * U
        mal = res.get("equivocadas") or []
        if mal:
            y += 8 * U
            fuente, txt = mal[0]
            texto(sup, "Ojo: cortaste algo verdadero", (r.x + 40 * U, y), 18 * U, MANGO, 700, "titulo", "midleft")
            y += 28 * U
            linea = f"«{txt}» venía de {fuente}: una fuente oficial."
            for l in _partir_lineas(linea, 15 * U, w - 90 * U)[:2]:
                texto(sup, l, (r.x + 40 * U, y), 15 * U, TINTA, 800, ancla="midleft")
                y += 24 * U
        if self.estado_t > 1.0:
            siguiente = self.p.jugadores[(self.p.turno + 1) % len(self.p.jugadores)]
            msg = "Haz clic para el siguiente día" if len(self.p.jugadores) == 1 else \
                f"Le pasa el mouse a {siguiente.nombre} · haz clic para seguir"
            texto(sup, msg, (r.centerx, r.bottom - 36 * U), 18 * U, LILA, 900)

    def _fin(self, sup):
        U = self.U
        W, H = sup.get_size()
        k = suave(min(1, self.estado_t / 0.6))
        self._velo(sup, round(190 * k))
        perdio = getattr(self.p, "perdio", False)
        w, h = 760 * U, 560 * U
        r = pildora(sup, (W / 2 - w / 2, H / 2 - h / 2, w, h), BLANCO, round(30 * U))
        if perdio:
            texto(sup, "La mentira ganó esta vez", (r.centerx, r.y + 56 * U), 38 * U, ROJO, 700, "titulo")
            texto(sup, f"Ciudad Nova se llenó de rumores en el día {self.p.dia}.", (r.centerx, r.y + 100 * U), 18 * U,
                  TINTA2, 900)
        else:
            texto(sup, "¡Ciudad Nova vota informada!", (r.centerx, r.y + 56 * U), 38 * U, VERDE, 700, "titulo")
            texto(sup, f"Salud final de la ciudad: {self.p.salud()}", (r.centerx, r.y + 100 * U), 18 * U, TINTA2, 900)
        orden = sorted(self.p.jugadores, key=lambda j: -j.puntos)
        y = r.y + 150 * U
        for i, j in enumerate(orden):
            av = personajes.avatar(j.look, round(64 * U), j.color, j.rol, "feliz" if i == 0 else "neutral")
            sup.blit(av, (r.x + 60 * U, y))
            if i == 0 and len(orden) > 1:
                icono(sup, "crown", (r.x + 92 * U, y - 6 * U), 30 * U, DORADO, 3)
            texto(sup, j.nombre, (r.x + 140 * U, y + 22 * U), 24 * U, TINTA, 700, "titulo", "midleft")
            texto(sup, f"{j.cortadas} falsas cortadas · mejor combo x{j.mejor_combo} · {j.errores} errores",
                  (r.x + 140 * U, y + 48 * U), 14 * U, TINTA2, 800, ancla="midleft")
            texto(sup, f"{j.puntos:,}".replace(",", "."), (r.right - 60 * U, y + 32 * U), 32 * U, TINTA, 700, "titulo",
                  "midright")
            y += 84 * U
        ganador = orden[0]
        if not perdio:
            texto(sup, f"¡{ganador.nombre} es el Alcalde Digital!" if len(orden) > 1 else "¡Eres el Alcalde Digital!",
                  (r.centerx, r.bottom - 90 * U), 28 * U, LILA, 700, "titulo")
        if self.estado_t > 1.2:
            texto(sup, "Haz clic para volver al menú", (r.centerx, r.bottom - 36 * U), 17 * U, LILA, 900)
