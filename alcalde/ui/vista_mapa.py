"""Mapa de Ciudad Nova: el grafo de la ciudad dibujado como un pueblo con calles."""
import math
import random

import pygame
import pygame.gfxdraw

from ..modelo.mapa import CALLES, ZONAS, nombre_zona
from ..modelo.red_social import residentes
from . import edificios, personajes, recursos
from .efectos import suave
from .juego_comun import EXPRESION, cara, color_estado
from .tema import TEMA
from .widgets import Boton, chip, circulo, recortar, sticker, texto

ICONO_EVENTO = dict(falsa="triangle-alert", rumor="message-square-warning", verdadera="newspaper", viral="flame",
                    discusion="zap", campana="heart-handshake", reporte="flag", vence="archive", bot="bot",
                    vecino="house")
RIO = [(0.67, -0.06), (0.63, 0.10), (0.69, 0.27), (0.77, 0.36), (1.06, 0.34)]


def _dist_segmento(px, py, a, b):
    (x1, y1), (x2, y2) = a, b
    dx, dy = x2 - x1, y2 - y1
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / max(1e-9, dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


class VistaMapa:
    def __init__(self, juego, rect):
        self.j = juego
        self.rect = pygame.Rect(rect)
        self.area = pygame.Rect(self.rect.x + 58, self.rect.y + 84, self.rect.w - 116, 376)
        self._fondo = None
        self._fondo_clave = None
        self.tokens = {}
        self.eventos = []
        self.hover = None
        self.btn_conversar = Boton((self.rect.right - 214, self.rect.bottom - 70, 196, 50), "Conversar", "conversar",
                                   costo=1, icono="message-circle", estilo="primario", tam=17)

    @property
    def p(self):
        return self.j.p

    def pos_zona(self, z):
        x, y = ZONAS[z]["pos"]
        return self.area.x + x * self.area.w, self.area.y + y * self.area.h

    def _norm(self, x, y):
        return self.rect.x + x * self.rect.w, self.rect.y + y * self.rect.h

    # ------------------------------------------------------------------ fondo fijo
    def _construir_fondo(self):
        c = TEMA.c
        s = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        ox, oy = self.rect.topleft
        pygame.draw.rect(s, c["pasto"], s.get_rect(), border_radius=18)
        rng = random.Random(3)
        if not TEMA.alto_contraste:
            for _ in range(160):
                x, y = rng.uniform(10, self.rect.w - 10), rng.uniform(10, self.rect.h - 10)
                pygame.draw.circle(s, c["pasto2"], (x, y), rng.choice((2, 3)))
        rio = [(x * self.rect.w, y * self.rect.h) for x, y in RIO]
        pygame.draw.lines(s, c["tinta"], False, rio, 40)
        pygame.draw.lines(s, c["agua"], False, rio, 33)
        for q in rio:
            pygame.draw.circle(s, c["agua"], q, 16)
        pygame.draw.lines(s, (255, 255, 255), False, [(x + 6, y - 2) for x, y in rio], 3)
        pts = {z: (self.pos_zona(z)[0] - ox, self.pos_zona(z)[1] - oy) for z in ZONAS}
        for a, b, _ in CALLES:
            pygame.draw.line(s, c["tinta"], pts[a], pts[b], 30)
        for z in ZONAS:
            pygame.draw.circle(s, c["tinta"], pts[z], 15)
        for a, b, _ in CALLES:
            pygame.draw.line(s, c["calle"], pts[a], pts[b], 23)
        for z in ZONAS:
            pygame.draw.circle(s, c["calle"], pts[z], 11)
        for a, b, _ in CALLES:
            (x1, y1), (x2, y2) = pts[a], pts[b]
            largo = math.hypot(x2 - x1, y2 - y1)
            for k in range(int(largo // 22)):
                t1, t2 = (k * 22 + 4) / largo, (k * 22 + 13) / largo
                pygame.draw.line(s, c["papel"], (x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1),
                                 (x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2), 3)
        arboles = 0
        intentos = 0
        while arboles < 22 and intentos < 600:
            intentos += 1
            x, y = rng.uniform(20, self.rect.w - 20), rng.uniform(30, self.rect.h - 130)
            if any(math.hypot(x - px, y - py) < 78 for px, py in pts.values()):
                continue
            if any(_dist_segmento(x, y, pts[a], pts[b]) < 26 for a, b, _ in CALLES):
                continue
            if any(_dist_segmento(x, y, rio[k], rio[k + 1]) < 30 for k in range(len(rio) - 1)):
                continue
            img = edificios.arbolito(34, palma=rng.random() < 0.35, tono=rng.randrange(3))
            s.blit(img, (x - 17, y - 34))
            arboles += 1
        pygame.draw.rect(s, c["tinta"], s.get_rect(), 3, border_radius=18)
        return s

    def fondo(self):
        clave = (TEMA.alto_contraste,)
        if self._fondo is None or self._fondo_clave != clave:
            self._fondo = self._construir_fondo()
            self._fondo_clave = clave
        return self._fondo

    # ------------------------------------------------------------------ animación
    def animar(self, ev):
        t = ev.get("t")
        ahora = pygame.time.get_ticks()
        if t == "mover":
            self.tokens[ev["jugador"]] = dict(ruta=ev["ruta"], t0=ahora)
        elif t == "evento" and ev.get("zona") in ZONAS:
            self.eventos.append((ev["zona"], ev.get("tipo"), ahora))
            self.eventos = self.eventos[-8:]

    def _pos_token(self, i, j, ahora):
        base_x, base_y = self.pos_zona(j.zona)
        ox, oy = ((-52, 14), (52, 14), (-36, 30), (36, 30))[i % 4]
        anim = self.tokens.get(i)
        if anim and not TEMA.op["menos_movimiento"]:
            ruta = anim["ruta"]
            seg = 420
            e = (ahora - anim["t0"]) / seg
            if e < len(ruta) - 1:
                k = int(e)
                f = suave(e - k)
                (x1, y1), (x2, y2) = self.pos_zona(ruta[k]), self.pos_zona(ruta[k + 1])
                return x1 + (x2 - x1) * f + ox * 0.4, y1 + (y2 - y1) * f + oy * 0.4, x2 < x1, True
        return base_x + ox, base_y + oy, False, False

    def zona_en(self, punto):
        mejor, dmin = None, 56
        for z in ZONAS:
            x, y = self.pos_zona(z)
            d = math.hypot(punto[0] - x, punto[1] - (y - 10))
            if d < dmin:
                mejor, dmin = z, d
        return mejor

    # ------------------------------------------------------------------ eventos
    def evento(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.zona_en(e.pos) if self.rect.collidepoint(e.pos) else None
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.btn_conversar.clic(e.pos):
                self.j.conversar()
                return True
            z = self.zona_en(e.pos)
            if z is not None and self.j.puedo_actuar():
                if z != self.p.jugador_actual.zona and z in self.p.destinos():
                    self.j.mover(z)
                elif z != self.p.jugador_actual.zona:
                    dist = self.p.mapa.camino_mas_corto(self.p.jugador_actual.zona, z)[0]
                    self.j.app.toasts.agregar(f"{nombre_zona(z)} queda a {int(dist)} min y te quedan "
                                              f"{self.p.jugador_actual.minutos} min este turno.", "malo")
                return True
        return False

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, sup):
        p = self.p
        c = TEMA.c
        ahora = pygame.time.get_ticks()
        mov = not TEMA.op["menos_movimiento"]
        sup.blit(self.fondo(), self.rect)
        pts = {z: self.pos_zona(z) for z in ZONAS}
        mi_turno = self.j.puedo_actuar()
        j = p.jugador_actual
        destinos = p.destinos() if mi_turno else {}
        ruta_prev = []
        if mi_turno and self.hover and self.hover in destinos and self.hover != j.zona:
            _, ruta_prev = p.mapa.camino_mas_corto(j.zona, self.hover)
        for k in range(len(ruta_prev) - 1):
            (x1, y1), (x2, y2) = pts[ruta_prev[k]], pts[ruta_prev[k + 1]]
            largo = math.hypot(x2 - x1, y2 - y1)
            fase = (ahora / 30) % 20 if mov else 0
            d = fase
            while d < largo:
                t1, t2 = d / largo, min(1, (d + 10) / largo)
                pygame.draw.line(sup, c["acento"], (x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1),
                                 (x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2), 7)
                d += 20
        for (mx, my), minutos in self._etiquetas_calles(pts):
            chip(sup, f"{minutos} min", (mx, my), c["papel"], c["tinta2"], None, 11, ancla="c", alto=20)
        for z in sorted(ZONAS, key=lambda z: pts[z][1]):
            self._zona(sup, z, pts[z], destinos, j, ahora, mov)
        for i, jj in sorted(enumerate(p.jugadores), key=lambda t: self._pos_token(t[0], t[1], ahora)[1]):
            self._token(sup, i, jj, ahora, mov)
        self._tarjeta_zona(sup, destinos)

    def _etiquetas_calles(self, pts):
        if getattr(self, "_etiquetas", None) is None:
            puestas = []
            for a, b, minutos in CALLES:
                (x1, y1), (x2, y2) = pts[a], pts[b]
                mejor, holgura = None, -1
                for t in (0.5, 0.42, 0.58, 0.34, 0.66, 0.28, 0.72):
                    x, y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
                    d = min([math.hypot(x - px, y - (py + 20)) for px, py in pts.values()] +
                            [math.hypot(x - qx, y - qy) * 1.6 for (qx, qy), _ in puestas] + [999])
                    if d > holgura:
                        mejor, holgura = (x, y), d
                    if d > 70:
                        break
                puestas.append((mejor, minutos))
            self._etiquetas = puestas
        return self._etiquetas

    def _zona(self, sup, z, pos, destinos, j, ahora, mov):
        p = self.p
        c = TEMA.c
        x, y = pos
        info = ZONAS[z]
        alcanzable = z in destinos and z != j.zona
        if alcanzable:
            pul = 3 * math.sin(ahora / 200) if mov else 0
            pygame.gfxdraw.filled_ellipse(sup, round(x), round(y + 20), round(56 + pul), round(20 + pul / 2),
                                          (*c["mango"], 150))
        if z == self.hover:
            pygame.draw.ellipse(sup, c["acento"], (x - 60, y + 2, 120, 38), 4)
        edif = edificios.edificio(info["tipo"], 90)
        arriba = y - edif.get_height() + 22
        sup.blit(edif, (x - edif.get_width() / 2, arriba))
        tension = p.tension(z)
        if tension >= 40:
            bob = math.sin(ahora / 400 + x) * 3 if mov else 0
            nube = edificios.nube(64, gris=True)
            sup.blit(nube, (x - 4, arriba - 22 + bob))
            if tension >= 70 and (ahora // 260) % 5 == 0:
                sup.blit(recursos.icono("zap", 22, c["mango"], 3), (x + 30, arriba + 12))
        nombre = info["nombre"]
        if alcanzable:
            chip(sup, f"{nombre}  {int(destinos[z])} min", (x, y + 32), c["mango"], c["texto"], "clock", 12,
                 ancla="c", alto=22)
        else:
            chip(sup, nombre, (x, y + 32), c["papel"], c["texto"], None, 12, ancla="c", alto=22)
        gente = residentes(p.red, z)
        n = len(gente)
        for k, v in enumerate(gente):
            est = p.estado_ciudadano(v)
            vx = x + (k - (n - 1) / 2) * 23
            vy = y + 56
            img = cara(p, v, 22, expresion=EXPRESION.get(est, "neutral"),
                       borde=color_estado(est) if est != "nada" else c["borde"], grosor=3 if est != "nada" else 2)
            sup.blit(img, (vx - 11, vy - 11))
        for zona, tipo, t0 in self.eventos:
            if zona == z and ahora - t0 < 5000:
                e = (ahora - t0) / 5000
                esc = suave(min(1, (ahora - t0) / 300))
                yy = arriba - 4 - (8 * math.sin(ahora / 200) if mov else 0)
                circulo(sup, (x + 44, yy), 17 * esc, c["malo"] if tipo in ("discusion", "falsa", "rumor", "bot", "viral")
                        else c["bueno"], c["borde"], 3)
                if esc > 0.6:
                    sup.blit(recursos.icono(ICONO_EVENTO.get(tipo, "sparkles"), 18, c["sobre_color"], 2.6),
                             (x + 35, yy - 9))

    def _token(self, sup, i, jj, ahora, mov):
        c = TEMA.c
        x, y, izquierda, caminando = self._pos_token(i, jj, ahora)
        actual = jj is self.p.jugador_actual
        expresion = self.j.expresion_de(jj) if actual else "neutral"
        bob = abs(math.sin(ahora / 90)) * 4 if caminando else (math.sin(ahora / 500 + i) * 1.5 if mov else 0)
        img = personajes.cuerpo(jj.look, jj.rol, expresion, alto=64 if actual else 54,
                                parpadeo=(ahora // 130 + i * 7) % 36 == 0, color_extra=(58, 110, 230))
        if izquierda:
            img = pygame.transform.flip(img, True, False)
        pygame.draw.ellipse(sup, jj.color, (x - 18, y - 6, 36, 12))
        pygame.draw.ellipse(sup, c["tinta"], (x - 18, y - 6, 36, 12), 2)
        sup.blit(img, (x - img.get_width() / 2, y - img.get_height() + 4 - bob))
        if actual:
            ay = y - img.get_height() - 14 - (abs(math.sin(ahora / 250)) * 6 if mov else 0)
            pygame.draw.polygon(sup, c["mango"], [(x - 9, ay), (x + 9, ay), (x, ay + 11)])
            pygame.draw.polygon(sup, c["tinta"], [(x - 9, ay), (x + 9, ay), (x, ay + 11)], 2)

    def _tarjeta_zona(self, sup, destinos):
        p = self.p
        c = TEMA.c
        j = p.jugador_actual
        z = self.hover or j.zona
        r = pygame.Rect(self.rect.x + 14, self.rect.bottom - 84, self.rect.w - 28, 74)
        sticker(sup, r, c["papel"], 16, 4, 3)
        img = edificios.edificio(ZONAS[z]["tipo"], 64)
        sup.blit(img, (r.x + 10, r.y + 8))
        gente = residentes(p.red, z)
        creen = sum(1 for v in gente if p.estado_ciudadano(v) == "falso")
        objetivo = p.objetivo_charla(z)
        aqui = z == j.zona
        titulo = (f"Estás en {nombre_zona(z)}" if aqui else nombre_zona(z))
        if self.j.en_red() and not self.j.puedo_actuar():
            titulo = f"{j.nombre} está en {nombre_zona(j.zona)}" if aqui else titulo
        texto(sup, titulo, (r.x + 84, r.y + 10), 16, c["texto"], peso=900)
        linea = f"{len(gente)} vecinos, {creen} creen algo falso. Tensión {p.tension(z)}."
        texto(sup, linea, (r.x + 84, r.y + 32), 13, c["tinta2"], peso=700)
        hechos = [cs.hecho for cs in p.casos_abiertos() if cs.hecho.lugar == z]
        if hechos:
            h = hechos[0]
            falta = h.id not in p.archivo
            extra = " Falta en el Archivo: si verificas aquí, lo registras." if falta else ""
            texto(sup, recortar(f"Aquí pasó: {h.titulo}.{extra}", 12, r.w - 320, 700), (r.x + 84, r.y + 51), 12,
                  c["aviso"] if falta else c["tinta2"], peso=800)
        self.btn_conversar.visible = aqui and self.j.puedo_actuar()
        if aqui and self.j.puedo_actuar():
            ok, motivo = p.puede_conversar()
            self.btn_conversar.activo = ok
            self.btn_conversar.etiqueta = f"Conversar ({len(objetivo)})" if ok else "Conversar"
            self.btn_conversar.rect.topright = (r.right - 12, r.y + 12)
            self.btn_conversar.dibujar(sup)
            if not ok and self.btn_conversar.rect.collidepoint(pygame.mouse.get_pos()):
                from .widgets import tooltip
                tooltip(sup, motivo, self.btn_conversar.rect.midtop, 240)
        elif not aqui and self.j.puedo_actuar():
            if z in destinos:
                msg = f"Clic para ir: {int(destinos[z])} min de {j.minutos}"
                col = c["bueno"]
            else:
                dist = p.mapa.camino_mas_corto(j.zona, z)[0]
                msg = f"Queda a {int(dist)} min: no alcanzas este turno"
                col = c["malo"]
            texto(sup, msg, (r.right - 16, r.centery), 14, col, peso=900, ancla="mr")
