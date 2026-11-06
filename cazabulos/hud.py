"""Lo que se ve encima del juego: tarjeta del jugador, reloj, minimapa, indicadores, poder y avisos."""
import math

import pygame

from . import personajes
from .config import ALTO, ANCHO, TILE, TINTA
from .mundo import ROLES
from .personajes import PERSONAJES
from .recursos import escalar
from .ui import barra, panel, render, tecla, texto

INDICADORES = [("informacion", "Información", (90, 200, 255), True), ("confianza", "Confianza", (120, 220, 140), True),
               ("convivencia", "Convivencia", (255, 196, 80), True), ("bienestar", "Bienestar", (255, 130, 190), True),
               ("desinformacion", "Desinformación", (170, 110, 255), False), ("conflictos", "Conflictos", (255, 100, 90), False)]

_mini = None


def minimapa_base(mapa, escala=3):
    global _mini
    if _mini is None:
        s = mapa.superficie
        _mini = pygame.transform.smoothscale(s, (s.get_width() * escala // TILE, s.get_height() * escala // TILE))
    return _mini


# Las pistas nombran teclas; con un control USB se dicen con sus botones.
CON_MANDO = (("con las FLECHAS", "con la CRUCETA"), ("ESPACIO", "A"), ("Pulsa X", "Pulsa B o X"))


class Hud:
    def __init__(self, mundo, render, nombre=None, ronda=1, rondas=1, opciones=None):
        self.m = mundo
        self.r = render
        self.nombre = nombre or PERSONAJES[mundo.jugador.clave]["nombre"]
        self.ronda = ronda
        self.rondas = rondas
        self.op = opciones or {}
        self.t = 0.0
        self.puntos_vis = 0.0
        self.marcador = []          # en línea: [(nombre, clave, puntos)]
        self.mando = False          # True si hay un control USB conectado (cambia las teclas que se muestran)
        self.sin_controles = False  # en la cuenta regresiva y en la pausa las teclas ya se ven en el centro
        self.alfas = {}             # qué tan visible está cada panel (se aclaran si tapan algo importante)
        self._lienzo = None
        self.retrato = escalar(personajes.retrato(mundo.jugador.clave, mundo.jugador.piel, mundo.jugador.pelo), 5)

    def _zonas(self):
        """Dónde está cada panel en la pantalla (con un poco de margen)."""
        base = minimapa_base(self.m.mapa)
        alto_reloj = 76 + (58 if self.m.viral else 0)
        return {"tarjeta": pygame.Rect(10, 8, 310, 106),
                "reloj": pygame.Rect(ANCHO // 2 - 176, 6, 352, alto_reloj + 10),
                "mapa": pygame.Rect(ANCHO - base.get_width() - 32, 4, base.get_width() + 30, 330),
                "poder": pygame.Rect(ANCHO - 140, ALTO - 160, 136, 156)}

    def _importantes(self):
        """Lo que no debe quedar escondido detrás de un panel: tú, los morados, el viral, las estrellas y la antena."""
        r, m = self.r, self.m
        j = m.jugador
        x, y = r.a_pantalla(j.x - 9, j.y - 26)
        res = [pygame.Rect(int(x), int(y), 54, 84)]
        puntos = [v.cuerpo for v in m.infectados()] + [(s.x, s.y) for s in m.estrellas]
        puntos += [(a.x, a.y - 20) for a in m.antenas]
        if m.viral:
            puntos.append((m.viral.x, m.viral.y))
        for px, py in puntos:
            sx, sy = r.a_pantalla(px, py)
            res.append(pygame.Rect(int(sx) - 24, int(sy) - 30, 48, 60))
        return res

    def actualizar(self, dt):
        self.t += dt
        importantes = self._importantes()
        for clave, zona in self._zonas().items():
            meta = 0.22 if zona.collidelist(importantes) != -1 else 1.0
            a = self.alfas.get(clave, 1.0)
            self.alfas[clave] = a + (meta - a) * min(1.0, dt * 7)
        objetivo = self.m.jugador.puntos
        self.puntos_vis += (objetivo - self.puntos_vis) * min(1.0, dt * 8)
        if abs(objetivo - self.puntos_vis) < 1:
            self.puntos_vis = objetivo

    def dibujar(self, pant):
        zonas = self._zonas()
        self._pieza(pant, "tarjeta", zonas["tarjeta"], self._tarjeta)
        self._pieza(pant, "reloj", zonas["reloj"], self._reloj)
        self._pieza(pant, "mapa", zonas["mapa"], lambda p: (self._minimapa(p), self._indicadores(p)))
        self._pieza(pant, "poder", zonas["poder"], self._poder)
        self._controles(pant)
        self._avisos(pant)
        self._pista(pant)
        if self.marcador:
            self._marcador(pant)

    def _pieza(self, pant, clave, zona, dibujar):
        """Dibuja un panel; si algo importante quedó debajo, el panel se vuelve casi transparente."""
        a = self.alfas.get(clave, 1.0)
        if a > 0.97:
            dibujar(pant)
            return
        if self._lienzo is None:
            self._lienzo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        zona = zona.clip(pant.get_rect())
        self._lienzo.fill((0, 0, 0, 0), zona)
        dibujar(self._lienzo)
        self._lienzo.set_alpha(int(255 * a))
        pant.blit(self._lienzo, zona, zona)

    # ------------------------------------------------------------- piezas
    def _tarjeta(self, pant):
        j = self.m.jugador
        p = PERSONAJES[j.clave]
        panel(pant, (14, 12, 300, 96), borde=p["color"])
        fondo = pygame.Rect(24, 22, 76, 76)
        pygame.draw.rect(pant, p["color"], fondo, border_radius=12)
        pant.blit(self.retrato, self.retrato.get_rect(midbottom=(fondo.centerx, fondo.bottom + 2)))
        texto(pant, self.nombre, (112, 18), 24, p["color"])
        texto(pant, p["rol"], (112, 46), 16, (220, 214, 240), peso=600)
        texto(pant, f"{int(self.puntos_vis)}", (112, 64), 30, (255, 255, 255))
        if j.combo >= 2:
            mult = 1 + min(3, (j.combo - 1) // 4)
            c = (255, 160, 60) if mult > 1 else (255, 220, 120)
            texto(pant, f"x{j.combo}", (300, 70), 22, c, "topright")
            if mult > 1:
                texto(pant, f"COMBO x{mult}", (300, 50), 15, c, "topright")

    def _reloj(self, pant):
        m = self.m
        r = panel(pant, (ANCHO // 2 - 170, 10, 340, 76), borde=(255, 255, 255, 60))
        seg = max(0, math.ceil(m.tiempo))
        color = (255, 90, 90) if seg <= 10 and int(self.t * 4) % 2 else (255, 255, 255)
        texto(pant, f"{seg // 60}:{seg % 60:02d}", (r.x + 22, r.y + 8), 40, color)
        texto(pant, f"Ronda {self.ronda} de {self.rondas}", (r.right - 18, r.y + 10), 15, (200, 196, 230), "topright", 600)
        salvados = m.salvados()
        texto(pant, f"A salvo {salvados}/{len(m.vecinos)}", (r.right - 18, r.y + 32), 22,
              (140, 240, 160) if salvados > len(m.vecinos) * 0.6 else (255, 220, 120) if salvados > len(m.vecinos) * 0.3 else (255, 120, 120),
              "topright")
        barra(pant, (r.x + 20, r.bottom - 16, r.w - 40, 8), m.tiempo / m.duracion, (255, 205, 50))
        if m.viral:
            v = m.viral
            rr = panel(pant, (ANCHO // 2 - 150, 94, 300, 50), (120, 20, 60), 235, borde=(255, 120, 160))
            texto(pant, f"¡VIRAL! {max(0, math.ceil(v.t))} s", (rr.centerx, rr.centery), 28, (255, 255, 255), "center")

    def _minimapa(self, pant):
        m = self.m
        base = minimapa_base(m.mapa)
        w, h = base.get_size()
        x0, y0 = ANCHO - w - 18, 14
        panel(pant, (x0 - 8, y0 - 6, w + 16, h + 14), radio=12, borde=(255, 255, 255, 70))
        pant.blit(base, (x0, y0))
        k = 3 / TILE

        def punto(x, y, color, r=3):
            pygame.draw.circle(pant, color, (int(x0 + x * k), int(y0 + y * k)), r)
        for v in m.vecinos.values():
            punto(v.x, v.y, (170, 100, 255) if v.bulo is not None else (255, 214, 70) if v.escudo > 0 else (240, 240, 240), 3)
        for s in m.estrellas:
            punto(s.x, s.y, (255, 240, 120), 3)
        if m.jugador.clave == "ana":
            for b in m.bulos.values():
                if b.estado == "libre":
                    punto(b.x, b.y, (190, 110, 255), 2)
        for a in m.antenas:
            if int(self.t * 4) % 2:
                punto(a.x, a.y, (255, 60, 60), 5)
            punto(a.x, a.y, (255, 255, 255), 2)
        if m.viral:
            punto(m.viral.x, m.viral.y, (255, 60, 140), 6 if int(self.t * 6) % 2 else 4)
        for f in self.r.fantasmas:
            punto(f["x"], f["y"], PERSONAJES[f["clave"]]["color"], 3)
        j = m.jugador
        if len(self.r.guia) >= 2:
            pts = [(x0 + x * k, y0 + y * k) for x, y in self.r.guia]
            pygame.draw.lines(pant, (255, 255, 255), False, pts, 2)
        punto(j.x, j.y, (20, 14, 40), 6)
        punto(j.x, j.y, PERSONAJES[j.clave]["color"], 4)

    def _indicadores(self, pant):
        if self.op.get("ocultar_indicadores"):
            return
        ind = self.m.indicadores()
        base = minimapa_base(self.m.mapa)
        x0 = ANCHO - base.get_width() - 26
        y0 = 14 + base.get_height() + 16
        w = base.get_width() + 16
        panel(pant, (x0, y0, w, 26 + 22 * len(INDICADORES)), radio=12)
        texto(pant, "Estado del barrio", (x0 + 10, y0 + 5), 14, (220, 214, 240), peso=600)
        for k, (clave, nombre, color, bueno) in enumerate(INDICADORES):
            y = y0 + 26 + k * 22
            texto(pant, nombre, (x0 + 10, y), 13, (240, 240, 250), peso=600)
            barra(pant, (x0 + 104, y + 3, w - 146, 10), ind[clave] / 100, color)
            texto(pant, str(ind[clave]), (x0 + w - 8, y - 1), 14, (255, 255, 255), "topright")

    def _poder(self, pant):
        j = self.m.jugador
        p = PERSONAJES[j.clave]
        cx, cy = ANCHO - 76, ALTO - 78
        listo = j.carga >= 100
        r = 52 + (math.sin(self.t * 8) * 3 if listo else 0)
        pygame.draw.circle(pant, (20, 14, 40), (cx + 3, cy + 5), int(r))
        pygame.draw.circle(pant, p["color"] if listo else (60, 52, 96), (cx, cy), int(r))
        if not listo:
            pygame.draw.arc(pant, p["color"], (cx - r, cy - r, 2 * r, 2 * r), math.pi / 2,
                            math.pi / 2 + j.carga / 100 * math.tau, 8)
        texto(pant, ROLES[j.clave]["poder"], (cx, cy - 8), 17, TINTA if listo else (255, 255, 255), "center", borde=None if listo else TINTA)
        tecla(pant, "X", (cx, cy + 26), 16, "center")
        if listo:
            texto(pant, "¡LISTO!", (cx, cy - r - 4), 18, p["color"], "midbottom")

    def _controles(self, pant):
        if self.sin_controles or (self.m.t > 25 and not self.op.get("contraste")):
            return
        r = panel(pant, (14, ALTO - 62, 520, 48), radio=12)
        x = r.x + 12
        filas = ((("CRUCETA", "moverse"), ("A", "lanzar"), ("B / X", "poder")) if self.mando
                 else (("FLECHAS", "moverse"), ("ESPACIO", "lanzar"), ("X", "poder")))
        for t_, desc in filas:
            rr = tecla(pant, t_, (x, r.y + 8), 15)
            texto(pant, desc, (rr.right + 8, r.y + 12), 17, (240, 240, 250), peso=600)
            x = rr.right + 18 + render(desc, 17, peso=600).get_width()

    def _avisos(self, pant):
        """Una o dos palabras grandes que entran y salen rápido, debajo del reloj (nunca párrafos)."""
        y = 100 + (58 if self.m.viral else 0)
        for palabra, color, t in self.r.avisos[-1:]:
            entra = min(1.0, t / 0.15)
            sale = min(1.0, max(0.0, (1.8 - t) / 0.3))
            tam = int(44 + 14 * (1 - entra))
            while tam > 20 and render(palabra, tam, peso=700).get_width() > 760:   # avisos largos del modo en línea
                tam -= 4
            texto(pant, palabra, (ANCHO // 2, y), tam, color, "midtop", grosor=4, alfa=int(255 * sale))

    def _pista(self, pant):
        """La única pista que queda durante el juego: corta y arriba, para no tapar la acción."""
        p = self.m.pista
        if not p or self.r.avisos:
            return
        txt, teclas, t = p
        if self.mando:
            for tecla_, boton_ in CON_MANDO:
                txt = txt.replace(tecla_, boton_)
        alfa = int(255 * min(1.0, (3.5 - t) / 0.3, t / 0.4))
        ancho = render(txt, 22, peso=700).get_width() + 40
        r = pygame.Rect(0, 0, ancho, 44)
        r.midtop = (ANCHO // 2, 100 + (58 if self.m.viral else 0))
        panel(pant, r, (255, 248, 230), min(240, alfa), borde=(255, 205, 50))
        texto(pant, txt, r.center, 22, TINTA, "center", borde=None, alfa=alfa)

    def _marcador(self, pant):
        x0, y0 = 14, 120
        filas = sorted(self.marcador, key=lambda f: -f[2])
        panel(pant, (x0, y0, 220, 30 + 28 * len(filas)), radio=12)
        texto(pant, "En vivo", (x0 + 12, y0 + 6), 15, (220, 214, 240), peso=600)
        for k, (nombre, clave, pts) in enumerate(filas):
            y = y0 + 30 + k * 28
            pygame.draw.circle(pant, PERSONAJES[clave]["color"], (x0 + 20, y + 10), 8)
            texto(pant, nombre, (x0 + 34, y), 17, (255, 255, 255), peso=600)
            texto(pant, str(pts), (x0 + 206, y), 17, (255, 230, 120), "topright")
