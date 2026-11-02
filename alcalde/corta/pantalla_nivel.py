"""Pantalla de un nivel: el barrio de fondo, las publicaciones volando, el tajo, el jefe y los efectos."""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.apariencia import look_aleatorio
from ..modelo.mapa import nombre_zona
from ..modelo.red_social import residentes
from ..ui import personajes, recursos
from ..ui.dibujo import (AZUL, BLANCO, LILA, MANGO, ROJO, TINTA, TINTA2, VERDE, anillo, ancho_texto, circulo, icono,
                         mezclar, pildora, rebote, sombra, suave, texto)
from .ciudad import Fondo
from .comunes import Boton, partir, velo
from .contenido import BARRIOS_JUEGO, ESPECIALES, PODERES, SENALES
from .nivel import ALTO, ANCHO, FIEBRE_SEG, Nivel

DORADO = (255, 200, 40)
AZUL_OK = (29, 155, 240)
_rng = random.Random(17)
CARAS = [look_aleatorio(_rng, i % 2 == 0) for i in range(24)]


class PantallaNivel:
    def __init__(self, app, nivel: Nivel, al_terminar=None, demo=False, titulo=None):
        self.app = app
        self.n = nivel
        self.al_terminar = al_terminar
        self.demo = demo
        self.titulo = titulo or nombre_zona(nivel.zona)
        self.t = 0.0
        self.tam = None
        self.cache = {}
        self.trazo = []
        self.mitades, self.particulas, self.textos = [], [], []
        self.temblor = 0.0
        self.parada = 0.0
        self.raton_prev = None
        self.fin_t = None
        self.pausa = False
        self.lechuza = []
        self.dichos = set()
        self.banner_t = 0.0
        self._demo_rng = random.Random(3)
        self.al_evento = None             # en el duelo: avisar a la red de los combos
        self.btn_seguir = Boton("Seguir", "seguir", MANGO, "play", tecla=[pygame.K_ESCAPE, pygame.K_RETURN])
        self.btn_salir = Boton("Salir del nivel", "salir", (236, 238, 248), "log-out")
        regla = BARRIOS_JUEGO.get(nivel.zona, {})
        if not demo:
            self.decir(regla.get("texto", ""), 5.5)

    # -------------------------------------------------------------- utilidades
    def _preparar(self, sup):
        tam = sup.get_size()
        if tam != self.tam:
            self.tam = tam
            W, H = tam
            self.U = H / ALTO
            self.ox = (W - ANCHO * self.U) / 2
            self.fondo = Fondo(self.n.zona, W, H, self.U, semilla=len(self.n.zona))
            self.cache.clear()
            gente = residentes(self.n.red, self.n.zona) if self.n.red is not None else []
            looks = [self.n.red.dato(v).look for v in gente][:6] if gente else []
            self.vecinos = (looks + CARAS)[:8]

    def a_pantalla(self, x, y):
        return self.ox + x * self.U, y * self.U

    def a_campo(self, x, y):
        return (x - self.ox) / self.U, y / self.U

    def decir(self, txt, dur=3.5, clave=None):
        if clave:
            if clave in self.dichos:
                return
            self.dichos.add(clave)
        if txt:
            self.lechuza = [dict(texto=txt, t0=self.t, dur=dur)]

    def _sonar(self, nombre):
        if not self.demo:
            self.app.sonar(nombre)

    # -------------------------------------------------------------- entrada
    def evento(self, e):
        if self.demo:
            return
        if self.pausa:
            if self.btn_seguir.toca(e):
                self.pausa = False
            elif self.btn_salir.toca(e):
                self.pausa = False
                if self.al_terminar:
                    self.al_terminar(None)
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.pausa = True
            elif e.key == pygame.K_SPACE:
                self.n.usar_poder()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
            self.n.usar_poder()

    def _leer_raton(self, dt):
        pos = pygame.mouse.get_pos()
        apretado = pygame.mouse.get_pressed()[0]
        if self.raton_prev is not None:
            dx, dy = pos[0] - self.raton_prev[0], pos[1] - self.raton_prev[1]
            vel = math.hypot(dx, dy) / max(dt, 1e-3) / self.U
            if (apretado and math.hypot(dx, dy) > 3 * self.U) or vel > 2600:
                self.trazo.append((pos[0], pos[1], self.t))
                self.n.cortar(self.a_campo(*self.raton_prev), self.a_campo(*pos))
        self.raton_prev = pos
        self.trazo = [q for q in self.trazo if self.t - q[2] < 0.13]

    def _demo(self, dt):
        for pub in self.n.pubs:
            if pub.tipo == "falsa" and 120 < pub.y < 520 and self._demo_rng.random() < dt * 0.9:
                a, b = (pub.x - 170, pub.y - 50), (pub.x + 170, pub.y + 50)
                self.n.cortar(a, b)
                sa, sb = self.a_pantalla(*a), self.a_pantalla(*b)
                for k in range(6):
                    f = k / 5
                    self.trazo.append((sa[0] + (sb[0] - sa[0]) * f, sa[1] + (sb[1] - sa[1]) * f, self.t - 0.1 + f * 0.1))
                break
        self.trazo = [q for q in self.trazo if self.t - q[2] < 0.13]
        if self.n.salud < self.n.salud_max * 0.5:
            self.n.salud = self.n.salud_max
        if self.n.reloj > self.n.duracion - 5:
            self.n.reloj = 0.0

    # -------------------------------------------------------------- bucle
    def actualizar(self, dt):
        self.t += dt
        if self.pausa:
            return
        dt_juego = 0.0 if self.parada > 0 else dt
        self.parada = max(0.0, self.parada - dt)
        if self.demo:
            self._demo(dt)
        elif self.n.estado == "jugando":
            self._leer_raton(dt)
        self.n.actualizar(dt_juego)
        for ev in self.n.eventos:
            self._evento(ev)
        self.n.eventos.clear()
        self._fisica(dt)
        self.temblor = max(0.0, self.temblor - dt * 3)
        if self.n.estado != "jugando" and not self.demo:
            if self.fin_t is None:
                self.fin_t = self.t
                self._sonar("victoria" if self.n.estado == "ganado" else "malo")
            elif self.t - self.fin_t > 1.6 and self.al_terminar:
                cb, self.al_terminar = self.al_terminar, None
                cb(self.n.resultado())

    def _evento(self, ev):
        t = ev["t_"]
        U = self.U
        if self.al_evento:
            self.al_evento(ev)
        if t == "corte":
            pub = ev["pub"]
            self._partir(pub, ev["dir"])
            x, y = self.a_pantalla(pub.x, pub.y)
            if pub.tipo == "falsa":
                self._chispas(x, y, ROJO, 18)
                if ev.get("puntos"):
                    self._flotar(f"+{ev['puntos']}", x, y - 30 * U, MANGO, 30)
                    if ev.get("combo", 1) >= 3:
                        self._flotar(f"¡COMBO x{ev['combo']}!", x, y - 72 * U, (255, 120, 40), 34)
                if pub.senales and not ev.get("cadena"):
                    nombre = SENALES[pub.senales[0]][0]
                    self._flotar(f"Pista: {nombre}", x, y + 40 * U, BLANCO, 18, dur=1.4, caja=ROJO)
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
            self._flotar("¡Era verdad!", x, y - 10 * U, ROJO, 40, sub=f"{ev['fuente']} tiene chulito azul ✓", dur=2.2)
            self.decir("Las fuentes oficiales tienen chulito azul. ¡Esas déjalas pasar!", 4, "error")
        elif t == "multi":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            self._flotar({2: "¡DOBLE!", 3: "¡TRIPLE!"}.get(ev["n"], f"¡x{ev['n']}!"), x, y - 110 * U, (255, 90, 160), 48)
            self.parada, self.temblor = 0.07, 0.4
            self._sonar("logro")
        elif t == "cadena":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            self._flotar(f"¡Cortaste el ORIGEN! Cayeron {ev['n']} copias", x, y - 120 * U, DORADO, 28, dur=1.6)
            self.parada = 0.1
            self.decir("Cortar el ORIGEN tumba todas las copias que salieron de él.", 3.5, "cadena")
        elif t == "copia":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            quienes = " y ".join(ev.get("a") or []) or "sus seguidores"
            self._flotar("¡Se reenvió!", x, y - 50 * U, ROJO, 26, sub=f"La reenviaron {quienes}")
            self._sonar("rama")
            self.decir("Un ORIGEN que llega arriba se lo reenvían sus seguidores. ¡Córtalo antes!", 4, "copia")
        elif t == "cae":
            x = self.ox + ev["x"] * U
            self._chispas(x, self.fondo.base - 20 * U, (120, 110, 130), 24, arriba=True)
            self.temblor = 1.0 if ev.get("viral") else 0.5
            self._flotar("¡Se regó en el barrio!", x, self.fondo.base - 140 * U, ROJO, 24, dur=1.4)
            self._sonar("malo")
            self.decir("Si una mentira cae, el barrio pierde confianza. ¡Córtalas antes!", 3.5, "cae")
        elif t == "salva":
            x = self.ox + ev["x"] * U
            self._chispas(x, self.fondo.base - 20 * U, VERDE, 10, arriba=True)
            self._flotar("+ noticia real", x, self.fondo.base - 120 * U, VERDE, 18, dur=1.0)
        elif t == "fiebre":
            self._flotar("¡FIEBRE! Puntos x2", self.tam[0] / 2, 220 * U, (255, 90, 160), 54, dur=1.8)
            self._sonar("victoria")
        elif t == "especial":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            self._flotar(ESPECIALES[ev["especial"]]["texto"], x, y - 50 * U, DORADO, 30)
        elif t == "poder":
            p = PODERES[ev["rol"]]
            self._flotar(f"¡{p['nombre']}!", self.tam[0] / 2, 260 * U, DORADO, 56, sub=p["texto"], dur=1.8)
            self.temblor = 0.5
            self._sonar("victoria")
        elif t == "sin_poder":
            self.decir("Tu poder se carga cortando mentiras. Mira el círculo de abajo a la derecha.", 3.5, "sin_poder")
        elif t == "golpe":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            self._chispas(x, y, (255, 120, 40), 10)
            self._sonar("tick")
        elif t == "bloqueo":
            x = self.ox + ev["x"] * U
            self._flotar("¡Rebotó en el escudo!", x, self.fondo.base - 200 * U, AZUL, 26)
        elif t == "viento":
            self.decir("¡Cambió el viento! Mira la flecha de arriba.", 2.5, None)
        elif t == "ataque_recibido":
            self._flotar(f"¡{ev['de']} te mandó un rumor!", self.tam[0] / 2, 230 * U, ROJO, 36)
            self._sonar("viral")
        elif t == "jefe_fase":
            self._flotar(ev["texto"], self.tam[0] / 2, 300 * U, ROJO, 46, dur=2.2)
            self._sonar("viral")
            self.temblor = 0.8
        elif t == "jefe_herido":
            self._sonar("tick")
        elif t == "jefe_cae":
            x, y = self.a_pantalla(ev["x"], ev["y"])
            for col in (DORADO, ROJO, BLANCO, AZUL):
                self._chispas(x, y, col, 50)
            self.temblor = 1.5
            self._flotar("¡Derrotaste al Bot Supremo!", self.tam[0] / 2, 320 * U, DORADO, 52, dur=2.5)
        elif t == "apagon":
            self.decir("¡Apagón! Mueve el mouse para alumbrar.", 3, "apagon")

    def _partir(self, pub, direccion):
        img = pygame.transform.rotate(self._tarjeta(pub), -pub.rot)
        w, h = img.get_size()
        dx, dy = direccion
        x, y = self.a_pantalla(pub.x, pub.y)
        if abs(dx) >= abs(dy):
            partes = [(img.subsurface((0, 0, w, h // 2)).copy(), (0, -h / 4), (0, -1)),
                      (img.subsurface((0, h // 2, w, h - h // 2)).copy(), (0, h / 4), (0, 1))]
        else:
            partes = [(img.subsurface((0, 0, w // 2, h)).copy(), (-w / 4, 0), (-1, 0)),
                      (img.subsurface((w // 2, 0, w - w // 2, h)).copy(), (w / 4, 0), (1, 0))]
        U = self.U
        for s, (ox, oy), (nx, ny) in partes:
            self.mitades.append(dict(img=s, x=x + ox, y=y + oy, vx=nx * 260 * U + pub.vx * U * 0.4,
                                     vy=ny * 160 * U - 120 * U, rot=0.0, vrot=random.uniform(-260, 260), t=0.0))

    def _chispas(self, x, y, color, n, arriba=False):
        U = self.U
        for _ in range(n):
            ang = random.uniform(-math.pi, 0) if arriba else random.uniform(0, math.tau)
            v = random.uniform(150, 520) * U
            self.particulas.append(dict(x=x, y=y, vx=math.cos(ang) * v, vy=math.sin(ang) * v, t=0.0,
                                        dur=random.uniform(0.4, 0.9), r=random.uniform(3, 8) * U,
                                        color=mezclar(color, BLANCO, random.uniform(0, 0.4))))

    def _flotar(self, txt, x, y, color, tam, sub=None, dur=1.1, caja=None):
        U = getattr(self, "U", 1)
        y = max(170 * U, y)
        if self.tam:
            x = max(240 * U, min(self.tam[0] - 240 * U, x))
        self.textos.append(dict(txt=txt, x=x, y=y, color=color, tam=tam, sub=sub, t0=self.t, dur=dur, caja=caja))
        self.textos = self.textos[-14:]

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

    # -------------------------------------------------------------- tarjetas
    def _tarjeta(self, pub):
        U = self.U
        lupa = self.n.lento > 0 and self.n.rol == "periodista"
        clave = ("pub", pub.id, round(U * 100), lupa)
        img = self.cache.get(clave)
        if img is not None:
            return img
        if len(self.cache) > 400:
            self.cache = {k: v for k, v in self.cache.items() if k[0] != "pub"}
        w, h = round(pub.ancho * U), round(pub.alto * U)
        pad = round(16 * U)
        s = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        r = pygame.Rect(pad, pad, w, h)
        if pub.tipo == "especial":
            c = r.center
            pygame.draw.circle(s, (255, 236, 150), c, w // 2)
            pygame.draw.circle(s, DORADO, c, w // 2 - round(6 * U))
            pygame.draw.circle(s, BLANCO, c, w // 2, max(2, round(4 * U)))
            ic = recursos.icono(ESPECIALES[pub.especial]["icono"], round(50 * U), TINTA, 2.8)
            s.blit(ic, ic.get_rect(center=c))
        else:
            borde = (255, 90, 40) if pub.viral else (220, 214, 250)
            pygame.draw.rect(s, (40, 30, 90, 70), r.move(0, round(5 * U)), border_radius=round(18 * U))
            pygame.draw.rect(s, BLANCO, r, border_radius=round(18 * U))
            pygame.draw.rect(s, borde, r, max(2, round((5 if pub.viral else 3) * U)), border_radius=round(18 * U))
            if lupa:
                col = ROJO if pub.tipo == "falsa" else VERDE
                pygame.draw.rect(s, col, r.inflate(round(8 * U), round(8 * U)), max(3, round(6 * U)),
                                 border_radius=round(22 * U))
            look = pub.look or CARAS[pub.id % len(CARAS)]
            av = personajes.avatar(look, round(54 * U), (236, 231, 255), "npc", "neutral")
            s.blit(av, (r.x + round(12 * U), r.y + round(12 * U)))
            tx = r.x + round(76 * U)
            ancho_txt = w - 88 * U
            # fuente (con chulito azul si es oficial)
            fuente = pub.fuente
            while ancho_texto(fuente, 14 * U, 900) > ancho_txt - 26 * U and len(fuente) > 6:
                fuente = fuente[:-2]
            if fuente != pub.fuente:
                fuente = fuente[:-1] + "…"
            img_f = recursos.render_texto(fuente, max(6, round(14 * U)), TINTA2, 900, "texto")
            s.blit(img_f, (tx, r.y + round(11 * U)))
            if pub.tipo == "verdad":
                cx = tx + img_f.get_width() + round(11 * U)
                cy = r.y + round(11 * U) + img_f.get_height() // 2
                pygame.draw.circle(s, AZUL_OK, (cx, cy), round(9 * U))
                pygame.draw.lines(s, BLANCO, False, [(cx - 4 * U, cy), (cx - 1 * U, cy + 3 * U), (cx + 4 * U, cy - 3 * U)],
                                  max(2, round(2.4 * U)))
            lineas = partir(pub.texto, 18 * U, ancho_txt)[:3]
            tam = 18 * U if len(lineas) <= 2 else 15.5 * U
            for i, l in enumerate(lineas):
                img_t = recursos.render_texto(l, max(6, round(tam)), TINTA, 800, "texto")
                s.blit(img_t, (tx, r.y + round(36 * U) + round(i * tam * 1.22)))
            # señales visibles en las mentiras fáciles
            if pub.tipo == "falsa" and pub.nivel <= 2:
                for i, sid in enumerate(pub.senales[:2]):
                    cxy = (r.right - round((16 + i * 30) * U), r.bottom - round(16 * U))
                    pygame.draw.circle(s, (255, 230, 226), cxy, round(13 * U))
                    ic = recursos.icono(SENALES[sid][1], round(16 * U), ROJO, 2.6)
                    s.blit(ic, ic.get_rect(center=cxy))
            cinta = None
            if pub.origen:
                cinta = ("ORIGEN", DORADO, TINTA)
            elif pub.viral:
                cinta = ("¡VIRAL!", (255, 90, 40), BLANCO)
            elif pub.copia_de:
                cinta = (f"Reenviado por {pub.autor or 'alguien'}", (255, 214, 214), ROJO)
            elif pub.enviado_por:
                cinta = (f"Te la mandó {pub.enviado_por}", ROJO, BLANCO)
            if cinta:
                t = recursos.render_texto(cinta[0], max(6, round(13 * U)), cinta[2], 900, "texto")
                cr = pygame.Rect(0, 0, t.get_width() + round(20 * U), round(24 * U))
                cr.midbottom = (r.centerx, r.y + round(8 * U))
                pygame.draw.rect(s, cinta[1], cr, border_radius=round(12 * U))
                s.blit(t, t.get_rect(center=cr.center))
        s = s.convert_alpha()
        self.cache[clave] = s
        return s

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
        self.fondo.dibujar(sup, 1 - self.n.salud / self.n.salud_max, (sx, sy))
        self._vecinos(sup, sx, sy)
        if self.n.jefe:
            self._jefe(sup, sx, sy)
        for pub in self.n.pubs:
            self._pub(sup, pub, sx, sy)
        for m in self.mitades:
            img = pygame.transform.rotate(m["img"], m["rot"])
            img.set_alpha(round(255 * max(0, 1 - m["t"] / 1.2)))
            sup.blit(img, img.get_rect(center=(m["x"] + sx, m["y"] + sy)))
        for q in self.particulas:
            circulo(sup, (q["x"] + sx, q["y"] + sy), q["r"] * (1 - q["t"] / q["dur"]) + 1, q["color"])
        if self.n.escudo > 0:
            self._escudo(sup)
        if self.n.jefe and self.n.jefe["apagon"] > 0:
            self._apagon(sup)
        self._textos(sup)
        self._tajo(sup)
        if self.n.lento > 0:
            v = pygame.Surface((W, H), pygame.SRCALPHA)
            v.fill((60, 120, 255, 26))
            sup.blit(v, (0, 0))
        if self.n.fiebre > 0:
            col = tuple(round(127 + 127 * math.sin(self.t * 6 + k * 2.1)) for k in range(3))
            pygame.draw.rect(sup, col, (0, 0, W, H), max(6, round(12 * U)))
        if self.demo:
            return
        self._hud(sup)
        self._lechuza(sup)
        self._banner(sup)
        if self.pausa:
            self._pausa(sup)
        elif self.n.estado == "jugando":
            self._cursor(sup)
        else:
            self._final(sup)

    def _cielo(self, sup):
        W, H = sup.get_size()
        frac = min(1.0, self.n.reloj / self.n.duracion) if not self.n.jefe else 0.85
        clave = ("cielo", W, H, round(frac * 12), self.n.jefe is not None)
        img = self.cache.get(clave)
        if img is None:
            U = self.U
            arriba = mezclar((110, 200, 245), (120, 110, 210), max(0, frac - 0.6) / 0.4)
            abajo = mezclar((210, 240, 255), (255, 190, 150), max(0, frac - 0.55) / 0.45)
            if self.n.jefe:
                arriba, abajo = (70, 50, 140), (200, 120, 170)
            img = pygame.Surface((W, H))
            for y in range(0, H, 4):
                pygame.draw.rect(img, mezclar(arriba, abajo, y / H), (0, y, W, 4))
            sol_y = H * (0.16 + 0.22 * frac)
            for rr, a in ((92, 26), (66, 46), (44, 255)):
                s = pygame.Surface((rr * 2 * U, rr * 2 * U), pygame.SRCALPHA)
                pygame.draw.circle(s, (255, 232, 150, a), (rr * U, rr * U), rr * U)
                img.blit(s, (W * 0.88 - rr * U, sol_y - rr * U))
            base = self.fondo.base
            lejos = mezclar(abajo, (150, 140, 220), 0.3)
            r = random.Random(9)
            x = -40 * U
            while x < W:
                w = r.uniform(40, 90) * U
                h = r.uniform(30, 120) * U
                pygame.draw.rect(img, lejos, (x, base - 250 * U - h, w, h + 40 * U))
                x += w + r.uniform(4, 16) * U
            colina = mezclar(abajo, (120, 200, 140), 0.55)
            pts = [(0, H)] + [(xx, base - 240 * U - math.sin(xx / W * 7 + 1.3) * 24 * U - math.sin(xx / W * 17) * 9 * U)
                              for xx in range(0, W + 20, 20)] + [(W, H)]
            pygame.draw.polygon(img, colina, pts)
            img = img.convert()
            self.cache = {k: v for k, v in self.cache.items() if k[0] != "cielo"}
            self.cache[clave] = img
        sup.blit(img, (0, 0))

    def _nubes(self, sup):
        U = self.U
        W, H = sup.get_size()
        empuje = self.n.viento * 0.4
        for k, (vel, y, tam) in enumerate(((14, 110, 1.0), (9, 190, 0.7), (20, 60, 0.8), (6, 250, 1.2))):
            x = ((self.t * (vel + empuje) * U + k * 470 * U) % (W + 400 * U)) - 200 * U
            clave = ("nube", round(tam * 100), round(U * 100))
            img = self.cache.get(clave)
            if img is None:
                img = pygame.Surface((round(220 * U * tam), round(90 * U * tam)), pygame.SRCALPHA)
                for dx, dy, r in ((50, 56, 32), (95, 40, 42), (140, 54, 34), (180, 64, 22), (24, 66, 20)):
                    pygame.draw.circle(img, (255, 255, 255, 220), (round(dx * U * tam), round(dy * U * tam)), round(r * U * tam))
                self.cache[clave] = img
            sup.blit(img, (x, y * U))
        if self.n.p["viento"]:
            for i in range(10):
                x = ((self.t * (300 + i * 20) * U * (1 if self.n.viento >= 0 else -1) + i * 211 * U) % W)
                y = (140 + (i * 53) % 380) * U
                largo = 40 * U * min(1, abs(self.n.viento) / 100)
                pygame.draw.line(sup, (255, 255, 255), (x, y), (x - largo * (1 if self.n.viento >= 0 else -1), y),
                                 max(1, round(2 * U)))

    def _vecinos(self, sup, sx, sy):
        """La gente del barrio en el andén: se alegra o se enoja según la confianza del barrio."""
        U = self.U
        W = self.tam[0]
        frac = self.n.salud / self.n.salud_max
        exp = "feliz" if frac > 0.7 else "preocupado" if frac > 0.4 else "enojado"
        alto = round(66 * U)
        n = len(self.vecinos)
        for i, look in enumerate(self.vecinos):
            clave = ("vec", i, exp, alto)
            img = self.cache.get(clave)
            if img is None:
                img = personajes.cuerpo(look, "npc", exp, alto)
                if i % 2:
                    img = pygame.transform.flip(img, True, False)
                self.cache[clave] = img
            x = W * (i + 0.5) / n + sx
            bote = abs(math.sin(self.t * (3 if frac > 0.7 else 7) + i)) * (4 if frac > 0.7 else 2) * U
            sup.blit(img, (x - img.get_width() / 2, self.fondo.base + 20 * U - img.get_height() - bote + sy))

    def _pub(self, sup, pub, sx, sy):
        U = self.U
        x, y = self.a_pantalla(pub.x, pub.y)
        if pub.bus:
            bus = pygame.Rect(0, 0, 330 * U, 70 * U)
            bus.midtop = (x + sx, y + pub.alto * U / 2 - 6 * U + sy)
            pygame.draw.rect(sup, (255, 194, 61), bus, border_radius=round(14 * U))
            for k in range(6):
                pygame.draw.rect(sup, (60, 70, 110), (bus.x + 14 * U + k * 50 * U, bus.y + 12 * U, 38 * U, 22 * U),
                                 border_radius=round(5 * U))
            for dx in (0.2, 0.8):
                circulo(sup, (bus.x + bus.w * dx, bus.bottom), 13 * U, (40, 40, 60))
        img = self._tarjeta(pub)
        rot = pygame.transform.rotozoom(img, -pub.rot, 1.0) if abs(pub.rot) > 0.5 else img
        if pub.golpe > 0:
            rot = rot.copy()
            rot.fill((255, 120, 40, 0), special_flags=pygame.BLEND_RGBA_ADD)
        sup.blit(rot, rot.get_rect(center=(x + sx, y + sy)))
        if pub.viral:
            for i in range(3):
                circulo(sup, (x - 20 * U + i * 20 * U + sx, y + pub.alto * U / 2 + 16 * U + sy), 7 * U,
                        (255, 90, 40) if i < pub.vida else (220, 220, 230))
        if pub.marca:
            falsa = pub.tipo == "falsa"
            txt = "FALSA: ¡córtala!" if falsa else "VERDADERA: déjala pasar"
            col = ROJO if falsa else VERDE
            w = ancho_texto(txt, 17 * U, 900) + 28 * U
            r = pygame.Rect(0, 0, w, 34 * U)
            r.midbottom = (x + sx, y - pub.alto * U / 2 - 14 * U + sy)
            pygame.draw.rect(sup, col, r, border_radius=round(17 * U))
            texto(sup, txt, r.center, 17 * U, BLANCO, 900)
            pygame.draw.polygon(sup, col, [(r.centerx - 9 * U, r.bottom), (r.centerx + 9 * U, r.bottom),
                                           (r.centerx, r.bottom + 10 * U)])

    def _jefe(self, sup, sx, sy):
        U = self.U
        j = self.n.jefe
        x, y = self.a_pantalla(j["x"], j["y"])
        alto = round(250 * U)
        clave = ("jefe", alto, j["fase"])
        img = self.cache.get(clave)
        if img is None:
            img = personajes.cuerpo({}, "npc", "enojado", alto, bot=True)
            self.cache[clave] = img
        flota = math.sin(self.t * 2) * 8 * U
        rr = img.get_rect(center=(x + sx, y + flota + sy))
        aura = pygame.Surface((rr.w + 80 * U, rr.h + 80 * U), pygame.SRCALPHA)
        pygame.draw.ellipse(aura, (255, 60, 90, 60 + 30 * j["fase"]), aura.get_rect())
        sup.blit(aura, aura.get_rect(center=rr.center))
        if j["golpe"] > 0:
            img = img.copy()
            img.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)
        sup.blit(img, rr)
        texto(sup, "Bot Supremo", (rr.centerx, rr.y - 10 * U), 18 * U, BLANCO, 700, "titulo")

    def _escudo(self, sup):
        U = self.U
        W = self.tam[0]
        base = self.fondo.base
        r = pygame.Rect(-W * 0.1, base - 360 * U, W * 1.2, 720 * U)
        s = pygame.Surface((r.w, r.h // 2), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (90, 180, 255, 50), (0, 0, r.w, r.h))
        pygame.draw.ellipse(s, (120, 200, 255, 160), (0, 0, r.w, r.h), max(3, round(5 * U)))
        sup.blit(s, (r.x, r.y))
        texto(sup, f"Escudo x{self.n.escudo}", (W / 2, base - 330 * U), 20 * U, AZUL, 900)

    def _apagon(self, sup):
        W, H = sup.get_size()
        U = self.U
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        s.fill((8, 6, 24, 235))
        mx, my = pygame.mouse.get_pos()
        for r, a in ((230, 160), (190, 90), (160, 0)):
            pygame.draw.circle(s, (8, 6, 24, a), (mx, my), round(r * U))
        sup.blit(s, (0, 0))

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
            if t.get("caja"):
                w = ancho_texto(t["txt"], tam, 900) + 22 * U
                pildora(sup, (t["x"] - w / 2, y - tam * 0.8, w, tam * 1.6), t["caja"], con_sombra=False, alfa=min(235, alfa))
                texto(sup, t["txt"], (t["x"], y), tam, t["color"], 900, alfa=alfa)
            else:
                texto(sup, t["txt"], (t["x"] + 3 * U, y + 3 * U), tam, (40, 20, 90), 700, "titulo", alfa=alfa)
                texto(sup, t["txt"], (t["x"], y), tam, t["color"], 700, "titulo", alfa=alfa)
            if t.get("sub"):
                w = ancho_texto(t["sub"], 15 * U, 900) + 24 * U
                pildora(sup, (t["x"] - w / 2, y + tam * 0.55, w, 28 * U), BLANCO, con_sombra=False, alfa=min(240, alfa))
                texto(sup, t["sub"], (t["x"], y + tam * 0.55 + 14 * U), 15 * U, TINTA, 900, alfa=alfa)
        self.textos = vivos

    def _tajo(self, sup):
        pts = self.trazo
        if len(pts) < 2:
            return
        U = self.U
        if self.n.fiebre > 0:
            color = tuple(round(127 + 127 * math.sin(self.t * 8 + k * 2.1)) for k in range(3))
        else:
            color = tuple(self.n.jugador.get("color", (120, 220, 255)))
        n = len(pts)
        for ancho, col in ((14 + 4 * self.n.mejoras.get("filo", 0), color), (6, BLANCO)):
            izq, der = [], []
            for i, (x, y, _) in enumerate(pts):
                nx, ny = (pts[1][0] - x, pts[1][1] - y) if i == 0 else (x - pts[i - 1][0], y - pts[i - 1][1])
                L = math.hypot(nx, ny) or 1
                px, py = -ny / L, nx / L
                w = ancho * U * (i + 1) / n
                izq.append((x + px * w, y + py * w))
                der.append((x - px * w, y - py * w))
            if len(izq) >= 2:
                pygame.draw.polygon(sup, col, izq + der[::-1])

    def _cursor(self, sup):
        x, y = pygame.mouse.get_pos()
        U = self.U
        anillo(sup, (x, y), 12 * U, tuple(self.n.jugador.get("color", MANGO)), 3 * U)
        circulo(sup, (x, y), 4 * U, BLANCO)

    # -------------------------------------------------------------- barra de arriba y poder
    def _hud(self, sup):
        U = self.U
        W, H = sup.get_size()
        n = self.n
        jug = n.jugador
        r = pildora(sup, (18 * U, 16 * U, 330 * U, 76 * U), BLANCO, round(24 * U))
        av = personajes.avatar(jug.get("look") or {}, round(60 * U), tuple(jug.get("color", MANGO)), n.rol, "feliz")
        sup.blit(av, (r.x + 10 * U, r.y + 8 * U))
        texto(sup, jug.get("nombre", ""), (r.x + 82 * U, r.y + 22 * U), 17 * U, TINTA2, 900, ancla="midleft")
        texto(sup, f"{n.puntos:,}".replace(",", "."), (r.x + 82 * U, r.y + 50 * U), 34 * U, TINTA, 700, "titulo", "midleft")
        if n.combo >= 2:
            cr = pildora(sup, (r.right - 96 * U, r.y + 14 * U, 84 * U, 48 * U), (255, 120, 40), round(16 * U))
            texto(sup, f"x{n.combo}", cr.center, 26 * U, BLANCO, 700, "titulo")
        # centro: barrio y tiempo (o vida del jefe)
        w = 380 * U
        r = pildora(sup, (W / 2 - w / 2, 16 * U, w, 64 * U), BLANCO, round(22 * U))
        icono(sup, BARRIOS_JUEGO.get(n.zona, {}).get("icono", "map-pin"), (r.x + 30 * U, r.centery), 28 * U, LILA, 2.6)
        texto(sup, self.titulo, (r.x + 54 * U, r.y + 22 * U), 20 * U, TINTA, 700, "titulo", "midleft")
        barra = pygame.Rect(r.x + 54 * U, r.y + 41 * U, r.w - 130 * U, 11 * U)
        pygame.draw.rect(sup, (232, 234, 246), barra, border_radius=round(5 * U))
        relleno = barra.copy()
        if n.jefe:
            relleno.w = round(barra.w * n.jefe["hp"] / 100)
            pygame.draw.rect(sup, ROJO, relleno, border_radius=round(5 * U))
            texto(sup, f"{math.ceil(n.jefe['hp'])}", (r.right - 38 * U, r.centery), 26 * U, ROJO, 700, "titulo")
        else:
            falta = max(0, n.duracion - n.reloj)
            relleno.w = round(barra.w * falta / n.duracion)
            pygame.draw.rect(sup, MANGO, relleno, border_radius=round(5 * U))
            texto(sup, f"{int(math.ceil(falta))}", (r.right - 38 * U, r.centery), 30 * U, TINTA, 700, "titulo")
        if n.p["viento"] and abs(n.viento) > 1:
            lado = 1 if n.viento > 0 else -1
            cx, cy = W / 2, 104 * U
            largo = 30 * U + abs(n.viento) * 0.4 * U
            pygame.draw.line(sup, BLANCO, (cx - lado * largo, cy), (cx + lado * largo, cy), max(3, round(6 * U)))
            pygame.draw.polygon(sup, BLANCO, [(cx + lado * (largo + 16 * U), cy), (cx + lado * largo, cy - 12 * U),
                                              (cx + lado * largo, cy + 12 * U)])
            texto(sup, "Viento", (cx, cy + 22 * U), 14 * U, BLANCO, 900)
        # derecha: confianza del barrio
        frac = n.salud / n.salud_max
        w = 330 * U
        r = pildora(sup, (W - 18 * U - w, 16 * U, w, 76 * U), BLANCO, round(24 * U))
        col = VERDE if frac >= 0.6 else MANGO if frac >= 0.3 else ROJO
        icono(sup, "heart-handshake", (r.x + 36 * U, r.centery), 34 * U, col, 2.6)
        texto(sup, f"Confianza en {nombre_zona(n.zona)}", (r.x + 66 * U, r.y + 22 * U), 14 * U, TINTA2, 900, ancla="midleft")
        barra = pygame.Rect(r.x + 66 * U, r.y + 40 * U, r.w - 140 * U, 18 * U)
        pygame.draw.rect(sup, (232, 234, 246), barra, border_radius=round(9 * U))
        relleno = barra.copy()
        relleno.w = round(barra.w * frac)
        pygame.draw.rect(sup, col, relleno, border_radius=round(9 * U))
        texto(sup, f"{round(frac * 100)}", (r.right - 38 * U, r.centery), 28 * U, col, 700, "titulo")
        # poder del personaje (abajo a la derecha)
        p = PODERES[n.rol]
        cx, cy = W - 80 * U, H - 120 * U
        listo = n.energia >= 1
        lat = 1 + (0.06 * math.sin(self.t * 6) if listo else 0)
        circulo(sup, (cx, cy), 50 * U * lat, DORADO if listo else BLANCO)
        anillo(sup, (cx, cy), 50 * U * lat, (230, 150, 0) if listo else LILA, 8 * U, n.energia)
        icono(sup, p["icono"], (cx, cy), 46 * U, TINTA if listo else TINTA2, 2.8)
        etiqueta = f"¡{p['nombre']}! Espacio" if listo else p["nombre"]
        w = ancho_texto(etiqueta, 14 * U, 900) + 24 * U
        pildora(sup, (cx - w / 2, cy + 56 * U, w, 28 * U), DORADO if listo else BLANCO)
        texto(sup, etiqueta, (cx, cy + 70 * U), 14 * U, TINTA, 900)

    def _lechuza(self, sup):
        U = self.U
        W, H = sup.get_size()
        x, y = 24 * U, H - 180 * U
        img = personajes.civi("feliz" if self.n.salud > self.n.salud_max * 0.5 else "preocupado", round(104 * U),
                              parpadeo=int(self.t * 3) % 11 == 0, ala=math.sin(self.t * 3) * 0.3)
        sup.blit(img, (x, y + math.sin(self.t * 2) * 4 * U))
        vivos = []
        for g in self.lechuza:
            edad = self.t - g["t0"]
            if edad > g["dur"]:
                continue
            vivos.append(g)
            k = rebote(min(1, edad / 0.3))
            lineas = partir(g["texto"], 17 * U, 360 * U, 900)
            w = max(ancho_texto(l, 17 * U, 900) for l in lineas) + 34 * U
            h = (len(lineas) * 24 + 22) * U
            r = pygame.Rect(x + 96 * U, y - h + 14 * U, w * k, h * k)
            sombra(sup, r, round(18 * U))
            pygame.draw.polygon(sup, BLANCO, [(r.x + 4 * U, r.bottom - 22 * U), (r.x + 4 * U, r.bottom - 4 * U),
                                              (r.x - 18 * U, r.bottom + 6 * U)])
            pygame.draw.rect(sup, BLANCO, r, border_radius=round(18 * U))
            if k > 0.5:
                for i, l in enumerate(lineas):
                    texto(sup, l, (r.x + 17 * U, r.y + 22 * U + i * 24 * U), 17 * U, TINTA, 900, ancla="midleft")
        self.lechuza = vivos

    def _banner(self, sup):
        """Al empezar: el nombre del barrio y su regla en grande."""
        edad = self.t
        if edad > 3.2 or self.demo:
            return
        U = self.U
        W, H = sup.get_size()
        k = suave(min(1, edad / 0.35)) * (1 - suave(max(0, edad - 2.8) / 0.4))
        regla = BARRIOS_JUEGO.get(self.n.zona, {})
        r = pygame.Rect(0, 0, 640 * U, 150 * U)
        r.center = (W / 2, 260 * U + (1 - k) * -60 * U)
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (40, 26, 110, round(230 * k)), (0, 0, r.w, r.h), border_radius=round(30 * U))
        sup.blit(s, r)
        if k > 0.5:
            icono(sup, regla.get("icono", "map-pin"), (r.x + 70 * U, r.centery), 64 * U, MANGO, 2.6)
            texto(sup, self.titulo, (r.x + 130 * U, r.y + 44 * U), 34 * U, BLANCO, 700, "titulo", "midleft")
            texto(sup, regla.get("titulo", ""), (r.x + 130 * U, r.y + 86 * U), 22 * U, MANGO, 700, "titulo", "midleft")
            parrafo_y = r.y + 116 * U
            l = partir(regla.get("texto", ""), 15 * U, r.w - 160 * U, 800)
            if l:
                texto(sup, l[0] + ("…" if len(l) > 1 else ""), (r.x + 130 * U, parrafo_y), 15 * U, BLANCO, 800, ancla="midleft")

    def _pausa(self, sup):
        U = self.U
        W, H = sup.get_size()
        velo(sup, 160)
        texto(sup, "Pausa", (W / 2, 230 * U), 54 * U, BLANCO, 700, "titulo")
        self.btn_seguir.dibujar(sup, pygame.Rect(W / 2 - 170 * U, 300 * U, 340 * U, 78 * U), self.t)
        self.btn_salir.dibujar(sup, pygame.Rect(W / 2 - 170 * U, 400 * U, 340 * U, 66 * U), self.t)
        texto(sup, "Clic izquierdo: cortar · Espacio o clic derecho: poder", (W / 2, 520 * U), 17 * U, BLANCO, 800)

    def _final(self, sup):
        U = self.U
        W, H = sup.get_size()
        if self.fin_t is None:
            return
        k = suave(min(1, (self.t - self.fin_t) / 0.5))
        velo(sup, round(120 * k))
        gano = self.n.estado == "ganado"
        txt = "¡Barrio salvado!" if gano else "El rumor ganó esta vez"
        texto(sup, txt, (W / 2 + 4 * U, H / 2 + 4 * U), 64 * U * k, (40, 20, 110), 700, "titulo")
        texto(sup, txt, (W / 2, H / 2), 64 * U * k, DORADO if gano else ROJO, 700, "titulo")
