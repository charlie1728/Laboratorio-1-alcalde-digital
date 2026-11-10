"""Lo que se ve encima del juego: tarjeta del jugador, reloj, minimapa, indicadores, poder y avisos."""
import math

import pygame

from . import personajes, sprites
from .config import ALTO, ANCHO, TILE, TINTA
from .mundo import ROLES
from .personajes import PERSONAJES
from .recursos import borde, escalar
from .ui import barra, panel, parrafo, render, tecla, texto

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
    # El panel "Estado del barrio" tapa mucho: empieza oculto y se abre con TAB (o Y en el control).
    # Se recuerda entre turnos mientras el juego esté abierto.
    ver_estado = False

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
        alto_mapa = 330 if Hud.ver_estado else base.get_height() + 62
        return {"tarjeta": pygame.Rect(10, 8, 310, 106),
                "reloj": pygame.Rect(ANCHO // 2 - 176, 6, 352, alto_reloj + 10),
                "mapa": pygame.Rect(ANCHO - base.get_width() - 32, 4, base.get_width() + 30, alto_mapa),
                "poder": pygame.Rect(ANCHO - 140, ALTO - 160, 136, 156),
                "lado": self._caja_lado()}

    def _y_lado(self):
        """Dónde empieza la columna de la izquierda (debajo de la tarjeta y del marcador en línea)."""
        y = 118
        if self.marcador:
            y += 30 + 28 * len(self.marcador) + 8
        return y

    def _caja_lado(self):
        """La columna de la izquierda: misión, avisos y pista. Así nada sale en el centro de la pantalla."""
        alto = 0
        if getattr(self.m, "encargo", None):
            alto += 82
        if self.r.avisos:
            alto += 44
        if self.m.pista and not self.r.avisos:
            alto += 86
        return pygame.Rect(10, self._y_lado() - 4, 316, max(1, alto + 8))

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
        self._pieza(pant, "lado", zonas["lado"], self._lado)
        self._controles(pant)
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
        texto(pant, self.nombre, (112, 14), 24, p["color"])
        texto(pant, p["rol"], (302, 20), 14, (220, 214, 240), "topright", 600)
        self._municion(pant, 112, 46, p["color"])
        texto(pant, f"{int(self.puntos_vis)}", (112, 62), 30, (255, 255, 255))
        if j.combo >= 2:
            mult = 1 + min(3, (j.combo - 1) // 4)
            c = (255, 160, 60) if mult > 1 else (255, 220, 120)
            texto(pant, f"x{j.combo}", (300, 64), 22, c, "topright")
            if mult > 1:
                texto(pant, f"COMBO x{mult}", (300, 88), 13, c, "topright")

    def _municion(self, pant, x, y, color):
        """Los datos verificados que te quedan para lanzar, en barritas (no son infinitos)."""
        from .mundo import MUNICION_MAX
        j = self.m.jugador
        n = getattr(j, "municion", MUNICION_MAX)
        ic = escalar(borde(sprites.herramienta(j.clave)), 2)
        pant.blit(ic, ic.get_rect(midleft=(x, y + 5)))
        x0 = x + ic.get_width() + 6
        poco = n <= 2 and int(self.t * 6) % 2
        if n == 0 and int(self.t * 4) % 2:
            pygame.draw.rect(pant, (255, 90, 90), (x0 - 4, y - 3, MUNICION_MAX * 12 + 4, 16), 2, border_radius=5)
        for k in range(MUNICION_MAX):
            caja = pygame.Rect(x0 + k * 12, y, 9, 10)
            lleno = k < n
            pygame.draw.rect(pant, ((255, 120, 120) if poco else color) if lleno else (60, 52, 96), caja, border_radius=3)

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
        if getattr(m, "encargo", None):
            e = m.encargo
            punto(e.x, e.y, e.color, 6 if int(self.t * 5) % 2 else 4)
            punto(e.x, e.y, (20, 14, 40), 2)
        for f in self.r.fantasmas:
            punto(f["x"], f["y"], PERSONAJES[f["clave"]]["color"], 3)
        j = m.jugador
        if len(self.r.guia) >= 2:
            pts = [(x0 + x * k, y0 + y * k) for x, y in self.r.guia]
            es_mision = getattr(self.r, "guia_mision", False) and getattr(m, "encargo", None)
            pygame.draw.lines(pant, m.encargo.color if es_mision else (255, 255, 255), False, pts, 2)
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
        boton = "Y" if self.mando else "TAB"
        if not Hud.ver_estado:
            # oculto: solo una pestañita que dice cómo abrirlo
            panel(pant, (x0, y0, w, 30), radio=10)
            texto(pant, "Estado del barrio", (x0 + 10, y0 + 7), 14, (220, 214, 240), peso=600)
            tecla(pant, boton, (x0 + w - 8, y0 + 5), 12, "topright")
            return
        panel(pant, (x0, y0, w, 26 + 22 * len(INDICADORES)), radio=12)
        texto(pant, "Estado del barrio", (x0 + 10, y0 + 5), 14, (220, 214, 240), peso=600)
        tecla(pant, boton, (x0 + w - 8, y0 + 3), 11, "topright")
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
        filas = ((("CRUCETA", "moverse"), ("A", "lanzar"), ("B / X", "poder"), ("Y", "estado")) if self.mando
                 else (("FLECHAS", "moverse"), ("ESPACIO", "lanzar"), ("X", "poder"), ("TAB", "estado")))
        ancho = sum(max(render(t_, 15, peso=700).get_width() + 18, 28) + 26 + render(d, 17, peso=600).get_width()
                    for t_, d in filas) + 6
        r = panel(pant, (14, ALTO - 62, ancho, 48), radio=12)
        x = r.x + 12
        for t_, desc in filas:
            rr = tecla(pant, t_, (x, r.y + 8), 15)
            texto(pant, desc, (rr.right + 8, r.y + 12), 17, (240, 240, 250), peso=600)
            x = rr.right + 18 + render(desc, 17, peso=600).get_width()

    def _lado(self, pant):
        """Columna de la izquierda: la misión, los avisos y la pista (nada en el centro de la pantalla)."""
        y = self._y_lado()
        y = self._encargo(pant, y)
        y = self._avisos(pant, y)
        self._pista(pant, y)

    def _encargo(self, pant, y):
        """La misión activa: qué rumor o tarea es, qué hacer ahora, sus barritas y el tiempo."""
        e = getattr(self.m, "encargo", None)
        if not e:
            return y
        r = pygame.Rect(14, y, 300, 76)
        col = e.color
        panel(pant, r, (20, 24, 52), 230, radio=12, borde=col, grosor=2)
        ic = escalar(borde(sprites.encargo(e.icono)), 2)
        pant.blit(ic, ic.get_rect(midleft=(r.x + 10, r.y + 24)))
        tam = 17
        while tam > 12 and render(e.titulo, tam, peso=700).get_width() > 200:
            tam -= 1
        texto(pant, e.titulo, (r.x + 48, r.y + 7), tam, (255, 255, 255), peso=700)
        texto(pant, e.texto_hud, (r.x + 48, r.y + 29), 14, col, peso=600)
        seg = max(0, math.ceil(e.t))
        texto(pant, f"{seg}s", (r.right - 10, r.y + 7), 16, (255, 120, 120) if seg <= 8 else col, "topright", 700)
        # barritas: cada parada tiene las suyas; las de paradas ya hechas quedan llenas
        x = r.x + 48
        for parada in range(e.paradas):
            if parada < e.etapa:
                llenas = e.barritas
            elif parada == e.etapa:
                llenas = int(e.progreso * e.barritas + 1e-6)
            else:
                llenas = 0
            for k in range(e.barritas):
                pygame.draw.rect(pant, col if k < llenas else (66, 60, 98), (x, r.y + 50, 14, 9), border_radius=3)
                x += 17
            x += 10
        barra(pant, (r.x + 10, r.bottom - 9, r.w - 20, 4), max(0.0, e.t / max(1.0, e.duracion)), col)
        return r.bottom + 6

    def _avisos(self, pant, y):
        """Una o dos palabras que entran desde el costado y se van (nunca en el centro)."""
        for palabra, color, t in self.r.avisos[-1:]:
            entra = min(1.0, t / 0.15)
            sale = min(1.0, max(0.0, (1.8 - t) / 0.3))
            tam = 30
            while tam > 16 and render(palabra, tam, peso=700).get_width() > 296:
                tam -= 2
            x = 18 - int(40 * (1 - entra))
            texto(pant, palabra, (x, y), tam, color, grosor=4, alfa=int(255 * sale))
            return y + 44
        return y

    def _pista(self, pant, y):
        """La única pista del juego: corta, al costado, para no tapar la acción."""
        p = self.m.pista
        if not p or self.r.avisos:
            return
        txt, teclas, t = p
        if self.mando:
            for tecla_, boton_ in CON_MANDO:
                txt = txt.replace(tecla_, boton_)
        alfa = int(255 * min(1.0, (3.5 - t) / 0.3, t / 0.4))
        r = pygame.Rect(14, y, 300, 78)
        panel(pant, r, (255, 248, 230), min(240, alfa), radio=12, borde=(255, 205, 50))
        parrafo(pant, txt, (r.x + 14, r.y + 10), 17, r.w - 28, TINTA, 700)

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
