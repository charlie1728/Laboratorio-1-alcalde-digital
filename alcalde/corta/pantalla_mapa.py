"""El mapa de la campaña: la isla de Ciudad Nova con sus barrios.

  * Los barrios liberados tienen bandera verde y sus estrellas.
  * Se puede jugar en los barrios vecinos de uno liberado (aristas del grafo de la ciudad).
  * Las nubes de tormenta muestran cuánto rumor hay en cada barrio. Cada noche el rumor salta
    por una calle hacia un barrio vecino (se ve un rayo rojo de un barrio a otro).
"""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.apariencia import look_aleatorio
from ..modelo.mapa import CALLES, ZONAS, nombre_zona
from ..ui import personajes
from ..ui.dibujo import (BLANCO, LILA, MANGO, ROJO, TINTA, TINTA2, VERDE, anillo, ancho_texto, circulo, icono,
                         mezclar, pildora, rebote, suave, texto)
from . import geometria as geo
from .campana import DIAS as DIAS_TOTAL, FINAL, PARA_EL_JEFE
from .comunes import Boton, chips_efectos, estrellas, panel, parrafo, velo
from .contenido import BARRIOS_JUEGO, MISIONES, SENALES
from .isla import Escenario

DORADO = (255, 200, 40)
LOOK_CANDIDATO = {"valentina": look_aleatorio(random.Random(41), True),
                  "tomas": look_aleatorio(random.Random(42), False),
                  "luz": look_aleatorio(random.Random(43), True),
                  # Emilio es una persona: el que regala las mentiras es el Bot Supremo, que hace campaña por él.
                  "emilio": dict(piel=1, pelo="rapado", color_pelo=0, ropa=1, extra="gafas")}


def color_indicador(valor, sube_bien):
    """Verde si a la ciudad le va bien en ese indicador, amarillo si más o menos y rojo si mal."""
    bueno = valor if sube_bien else 100 - valor
    return VERDE if bueno >= 60 else MANGO if bueno >= 40 else ROJO


class PantallaMapa:
    def __init__(self, app, campana, resultado=None, cambios=None):
        self.app = app
        self.c = campana
        self.t = 0.0
        self.tam = None
        self.sel = None
        self.hover = None
        self.overlay = None
        self.resultado = resultado          # lo que pasó en el último nivel (se muestra primero)
        self.cambios = cambios or {}
        self.fase = "resultado" if resultado else ("noche" if cambios else "mapa")
        self.fase_t = 0.0
        self.btn_jugar = Boton("¡Jugar aquí!", "jugar", MANGO, "play", tecla=pygame.K_RETURN)
        self.btn_seguir = Boton("Continuar", "seguir", MANGO, "chevron-right", tecla=[pygame.K_RETURN, pygame.K_SPACE])
        self.botones = [Boton("Tienda", "tienda", (255, 236, 180), "store"),
                        Boton("Álbum", "album", (226, 220, 255), "book-open"),
                        Boton("Ayuda", "ayuda", (214, 240, 255), "circle-help"),
                        Boton("Menú", "menu", (236, 238, 248), "log-out")]
        if self.fase == "mapa" and self.c.disponibles():
            self.sel = self.c.disponibles()[0]
        self.confeti = []

    # -------------------------------------------------------------- geometría
    def _preparar(self, sup):
        tam = sup.get_size()
        if tam != self.tam:
            self.tam = tam
            self.U = tam[1] / 720
            self.esc = Escenario(tam[0], tam[1], round(96 * self.U), round(200 * self.U))

    def pos(self, z, alto=0.0):
        cx, cy = geo.CENTRO[z]
        return self.esc.pr.p(cx + 0.2, cy + 0.2, alto)

    def zona_en(self, punto):
        mejor, dmin = None, 60 * self.U
        for z in ZONAS:
            x, y = self.pos(z, 118)
            d = math.hypot(punto[0] - x, punto[1] - y)
            if d < dmin:
                mejor, dmin = z, d
        return mejor

    # -------------------------------------------------------------- entrada
    def evento(self, e):
        if self.overlay is not None:
            if self.overlay.evento(e) == "cerrar":
                self.overlay = None
            return
        if self.fase in ("resultado", "noche"):
            if self.btn_seguir.toca(e) or (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.fase_t > 1.2
                                           and self.fase == "noche"):
                self._avanzar()
            return
        if self.fase == "eleccion":
            if self.btn_seguir.toca(e) and self.fase_t > 3:
                from .periodico import PantallaPeriodico
                self.app.cambiar(PantallaPeriodico(self.app, self.c))
            return
        for b in self.botones:
            if b.toca(e):
                self._boton(b.accion)
                return
        if self.sel and self.c.estado_zona(self.sel) == "disponible" and self.btn_jugar.toca(e):
            self.app.jugar_zona(self.c, self.sel)
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            z = self.zona_en(e.pos)
            if z:
                self.sel = z
                self.app.sonar("click")
        elif e.type == pygame.MOUSEMOTION:
            self.hover = self.zona_en(e.pos)
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.ir_menu()

    def _boton(self, accion):
        from .paneles import Album, Ayuda, Tienda
        self.app.sonar("click")
        if accion == "tienda":
            self.overlay = Tienda(self.app, self.c)
        elif accion == "album":
            self.overlay = Album(self.app, self.c)
        elif accion == "ayuda":
            self.overlay = Ayuda(self.app)
        elif accion == "menu":
            self.c.guardar()
            self.app.ir_menu()

    def _avanzar(self):
        self.app.sonar("click")
        if self.fase == "resultado":
            # La noche siempre se muestra (sale el Diario Nova), salvo cuando ya terminó la campaña.
            self.fase = "mapa" if self.c.terminada else "noche"
            self.fase_t = 0.0
            if self.fase == "noche":
                self.app.sonar("noche")
        elif self.fase == "noche":
            self.fase = "mapa"
        if self.fase == "mapa":
            if self.c.terminada:
                self.fase = "eleccion"
                self.fase_t = 0.0
                self.app.sonar("votos")
            elif self.c.disponibles():
                # Se selecciona un barrio que se acaba de abrir (vecino del liberado), si lo hay.
                lib = self.cambios.get("liberada")
                nuevos = [z for z in self.c.disponibles() if lib and z in self.c.mapa.vecinos(lib)]
                self.sel = (nuevos or self.c.disponibles())[0]

    def actualizar(self, dt):
        self.t += dt
        self.fase_t += dt
        if self.overlay is not None and hasattr(self.overlay, "actualizar"):
            self.overlay.actualizar(dt)
        if self.fase == "eleccion" and self.fase_t > 3 and (self.c.eleccion or {}).get("final") != "derrota" \
                and not self.app.menos_movimiento and random.random() < 0.6:
            self.confeti.append(dict(x=random.random(), y=-0.05, v=random.uniform(0.15, 0.35), r=random.uniform(0, 6.3),
                                     c=random.choice([MANGO, ROJO, LILA, VERDE, (96, 190, 255)])))
        for c in self.confeti:
            c["y"] += c["v"] * dt
            c["r"] += dt * 5
        self.confeti = [c for c in self.confeti if c["y"] < 1.1][-220:]

    # -------------------------------------------------------------- dibujo
    def dibujar(self, sup):
        self._preparar(sup)
        U = self.U
        W, H = sup.get_size()
        sup.blit(self.esc.suelo, (0, 0))
        self._calles(sup)
        self._manchas(sup)
        for p in sorted(self.esc.piezas, key=lambda p: p.clave):
            sup.blit(p.img, p.pos)
        self._marcadores(sup)
        if self.fase == "noche":
            self._noche(sup)
        self._barra(sup)
        if self.fase == "mapa":
            self._indicadores(sup)
            self._tarjeta(sup)
        elif self.fase == "noche":
            self._indicadores(sup)
        elif self.fase == "resultado":
            self._resultado(sup)
        elif self.fase == "eleccion":
            self._eleccion(sup)
        for c in self.confeti:
            x, y = c["x"] * W, c["y"] * H
            pygame.draw.polygon(sup, c["c"], [(x + math.cos(c["r"] + a) * 8 * U, y + math.sin(c["r"] + a) * 5 * U)
                                              for a in (0, 2, 3.5, 5)])
        if self.overlay is not None:
            self.overlay.dibujar(sup)

    def _indicadores(self, sup):
        """Panel de la izquierda: cómo está Ciudad Nova hoy (los seis indicadores de la ciudad)."""
        U = self.U
        filas = self.c.indicadores_lista()
        r = pildora(sup, (16 * U, 100 * U, 236 * U, (58 + 46 * len(filas)) * U), BLANCO, round(22 * U), alfa=235)
        icono(sup, "landmark", (r.x + 24 * U, r.y + 26 * U), 22 * U, LILA, 2.6)
        texto(sup, "Ciudad Nova hoy", (r.x + 44 * U, r.y + 26 * U), 18 * U, TINTA, 700, "titulo", "midleft")
        for i, (k, nombre, ic, valor, sube_bien) in enumerate(filas):
            y = r.y + 64 * U + i * 46 * U
            col = color_indicador(valor, sube_bien)
            icono(sup, ic, (r.x + 24 * U, y + 8 * U), 20 * U, col, 2.6)
            texto(sup, nombre, (r.x + 44 * U, y), 13 * U, TINTA2, 900, ancla="midleft")
            texto(sup, str(valor), (r.right - 16 * U, y), 15 * U, col, 900, ancla="midright")
            barra = pygame.Rect(r.x + 44 * U, y + 12 * U, r.w - 60 * U, 9 * U)
            pygame.draw.rect(sup, (232, 234, 246), barra, border_radius=round(5 * U))
            relleno = barra.copy()
            relleno.w = round(barra.w * valor / 100)
            pygame.draw.rect(sup, col, relleno, border_radius=round(5 * U))
        texto(sup, "Desinformación y conflictos: mejor bajos", (r.centerx, r.bottom + 14 * U), 11 * U, BLANCO, 900)

    def _calles(self, sup):
        """Calles del grafo: verdes entre barrios liberados, amarillas hacia los que se pueden jugar."""
        U = self.U
        lib = set(self.c.liberadas)
        disp = set(self.c.disponibles())
        ruta = self.c.ruta_desde_inicio(self.sel) if self.sel else []
        en_ruta = {frozenset(par) for par in zip(ruta, ruta[1:])}
        for a, b, minutos in CALLES:
            pa, pb = self.pos(a, 2), self.pos(b, 2)
            if a in lib and b in lib:
                col, ancho = VERDE, 7
            elif (a in lib and b in disp) or (b in lib and a in disp):
                col, ancho = MANGO, 6
            else:
                col, ancho = (255, 255, 255), 3
            if frozenset((a, b)) in en_ruta:
                pygame.draw.line(sup, LILA, pa, pb, max(2, round(10 * U)))
            pygame.draw.line(sup, col, pa, pb, max(1, round(ancho * U)))
            mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
            circulo(sup, (mx, my), 13 * U, BLANCO)
            texto(sup, minutos, (mx, my), 12 * U, TINTA2, 900)

    def _manchas(self, sup):
        """El piso alrededor de cada barrio se tiñe: verde si está liberado, rojo según el rumor."""
        U = self.U
        for z in ZONAS:
            n = self.c.infeccion.get(z, 0)
            if z in self.c.liberadas:
                col, a = VERDE, 60
            elif n:
                col, a = ROJO, 35 + 30 * n
            else:
                continue
            x, y = self.pos(z)
            r = pygame.Rect(0, 0, 260 * U, 130 * U)
            r.center = (x, y)
            s = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.ellipse(s, (*col, a), (0, 0, r.w, r.h))
            sup.blit(s, r)

    def _marcadores(self, sup):
        U = self.U
        disp = set(self.c.disponibles())
        for z in ZONAS:
            x, y = self.pos(z, 118)
            estado = "liberada" if z in self.c.liberadas else "disponible" if z in disp else "bloqueada"
            n = self.c.infeccion.get(z, 0)
            if n and estado != "liberada":
                self._nube(sup, x, y - 40 * U, n)
            elegido = z == self.sel
            bote = math.sin(self.t * 4) * 5 * U if estado == "disponible" else 0
            col = {"liberada": VERDE, "disponible": MANGO, "bloqueada": (170, 172, 196)}[estado]
            if estado == "disponible":
                anillo(sup, (x, y + bote), (34 + 6 * math.sin(self.t * 5)) * U, MANGO, 4 * U)
            circulo(sup, (x, y + bote), 27 * U, BLANCO)
            circulo(sup, (x, y + bote), 23 * U, col)
            ic = {"liberada": "flag", "disponible": BARRIOS_JUEGO[z]["icono"], "bloqueada": "lock"}[estado]
            if z == "ALCALDIA" and estado != "liberada":
                ic = "bot"
            icono(sup, ic, (x, y + bote), 26 * U, BLANCO if estado != "bloqueada" else TINTA2, 2.8)
            if elegido:
                anillo(sup, (x, y + bote), 36 * U, LILA, 5 * U)
            nombre = nombre_zona(z)
            w = ancho_texto(nombre, 14 * U, 900) + 20 * U
            pildora(sup, (x - w / 2, y + 32 * U + bote, w, 26 * U), BLANCO if not elegido else LILA, con_sombra=False)
            texto(sup, nombre, (x, y + 45 * U + bote), 14 * U, TINTA if not elegido else BLANCO, 900)
            if estado == "liberada":
                estrellas(sup, (x, y + 72 * U), 18 * U, self.c.estrellas.get(z, 1))

    def _nube(self, sup, x, y, n):
        U = self.U
        col = (120, 120, 140) if n == 1 else (90, 86, 110) if n == 2 else (60, 54, 84)
        for dx, r in ((-24, 20), (0, 27), (24, 20)):
            circulo(sup, (x + dx * U * (0.8 + 0.15 * n), y), r * U * (0.8 + 0.15 * n), col)
        for i in range(2 + 2 * n):
            rx = x - 30 * U + i * 60 * U / (1 + 2 * n)
            ry = y + 18 * U + ((self.t * 200 * U + i * 31 * U) % (30 * U))
            pygame.draw.line(sup, (150, 170, 220), (rx, ry), (rx - 3 * U, ry + 9 * U), max(1, round(2 * U)))
        if n >= 3 and int(self.t * 3 + x) % 5 == 0:
            pygame.draw.lines(sup, MANGO, False, [(x, y + 14 * U), (x - 7 * U, y + 30 * U), (x + 5 * U, y + 32 * U),
                                                  (x - 3 * U, y + 50 * U)], max(2, round(3 * U)))

    # -------------------------------------------------------------- barra de arriba
    def _barra(self, sup):
        U = self.U
        W, H = sup.get_size()
        c = self.c
        r = pildora(sup, (16 * U, 14 * U, 300 * U, 70 * U), BLANCO, round(22 * U))
        av = personajes.avatar(c.personaje.get("look") or {}, round(56 * U), tuple(c.personaje.get("color", MANGO)),
                               c.personaje.get("rol", "periodista"), "feliz")
        sup.blit(av, (r.x + 8 * U, r.y + 7 * U))
        texto(sup, c.personaje.get("nombre", ""), (r.x + 76 * U, r.y + 22 * U), 17 * U, TINTA, 700, "titulo", "midleft")
        from .campana import DIAS
        texto(sup, f"Día {min(c.dia, DIAS)} de {DIAS} · faltan {max(0, DIAS - c.dia)} para votar",
              (r.x + 76 * U, r.y + 47 * U), 13 * U, TINTA2, 900, ancla="midleft")
        r2 = pildora(sup, (r.right + 12 * U, 14 * U, 270 * U, 70 * U), BLANCO, round(22 * U))
        icono(sup, "coins", (r2.x + 30 * U, r2.centery), 28 * U, (230, 159, 0), 2.6)
        texto(sup, f"{c.monedas}", (r2.x + 52 * U, r2.centery), 26 * U, TINTA, 700, "titulo", "midleft")
        icono(sup, "star", (r2.x + 150 * U, r2.centery), 28 * U, (255, 196, 40), 2.8)
        texto(sup, f"{sum(c.estrellas.values())}/27", (r2.x + 172 * U, r2.centery), 22 * U, TINTA, 700, "titulo", "midleft")
        x = W - 16 * U
        for b in reversed(self.botones):
            w = ancho_texto(b.etiqueta, 22 * U, 700, "titulo") + 70 * U
            b.dibujar(sup, pygame.Rect(x - w, 18 * U, w, 58 * U), self.t)
            x -= w + 10 * U

    def _tarjeta(self, sup):
        """Abajo: el barrio elegido, su regla, cuánto rumor tiene y el botón de jugar."""
        U = self.U
        W, H = sup.get_size()
        z = self.sel
        if z is None:
            return
        info = BARRIOS_JUEGO[z]
        estado = self.c.estado_zona(z)
        r = panel(sup, (W / 2 - 520 * U, H - 186 * U, 1040 * U, 170 * U), BLANCO, round(28 * U))
        circulo(sup, (r.x + 70 * U, r.centery), 46 * U, mezclar(MANGO, BLANCO, 0.6))
        icono(sup, info["icono"], (r.x + 70 * U, r.centery), 50 * U, TINTA, 2.6)
        texto(sup, nombre_zona(z), (r.x + 136 * U, r.y + 34 * U), 28 * U, TINTA, 700, "titulo", "midleft")
        texto(sup, info["titulo"], (r.x + 136 * U, r.y + 66 * U), 18 * U, LILA, 900, ancla="midleft")
        parrafo(sup, info["texto"], r.x + 136 * U, r.y + 82 * U, 520 * U, 15 * U, TINTA2, max_lineas=2)
        n = self.c.infeccion.get(z, 0)
        if estado == "liberada":
            texto(sup, "Liberado", (r.x + 136 * U, r.bottom - 26 * U), 15 * U, VERDE, 900, ancla="midleft")
            estrellas(sup, (r.x + 250 * U, r.bottom - 26 * U), 16 * U, self.c.estrellas.get(z, 1))
        else:
            txt = ["Sin rumores", "Rumor: poco", "Rumor: mucho", "Rumor: muchísimo"][n]
            fin = texto(sup, txt + " (más difícil)" if n else txt, (r.x + 136 * U, r.bottom - 26 * U), 15 * U,
                        ROJO if n else VERDE, 900, ancla="midleft")
            if estado == "disponible":
                texto_m, ic_m, _ = MISIONES[self.c.mision(z)]
                x = fin.right + 24 * U
                icono(sup, ic_m, (x + 10 * U, fin.centery), 18 * U, LILA, 2.6)
                texto(sup, f"Misión: {texto_m}", (x + 26 * U, fin.centery), 15 * U, LILA, 900, ancla="midleft")
        bx = r.right - 300 * U
        if estado == "disponible":
            self.btn_jugar.latir = True
            self.btn_jugar.dibujar(sup, pygame.Rect(bx, r.y + 40 * U, 270 * U, 84 * U), self.t)
        elif estado == "bloqueada" and z == FINAL and any(v in self.c.liberadas for v in self.c.mapa.vecinos(z)):
            n = self.c.liberados_sin_jefe()
            parrafo(sup, f"El Bot Supremo te espera. Libera {PARA_EL_JEFE} barrios para entrar.", bx, r.y + 34 * U,
                    270 * U, 17 * U, TINTA2, centrado=True)
            for i in range(PARA_EL_JEFE):
                lleno = i < n
                cx = bx + 135 * U + (i - (PARA_EL_JEFE - 1) / 2) * 44 * U
                circulo(sup, (cx, r.y + 120 * U), 17 * U, VERDE if lleno else (226, 228, 240))
                icono(sup, "flag" if lleno else "lock", (cx, r.y + 120 * U), 18 * U, BLANCO if lleno else TINTA2, 2.6)
        elif estado == "bloqueada":
            parrafo(sup, "Todavía no llegas. Libera un barrio vecino para abrir el camino.", bx, r.y + 50 * U,
                    270 * U, 17 * U, TINTA2, centrado=True)
        else:
            parrafo(sup, "¡Ya lo liberaste! Puedes seguir con un barrio vecino.", bx, r.y + 50 * U, 270 * U, 17 * U,
                    VERDE, centrado=True)

    # -------------------------------------------------------------- después del nivel
    def _resultado(self, sup):
        U = self.U
        W, H = sup.get_size()
        res = self.resultado
        velo(sup, 150)
        r = panel(sup, (W / 2 - 440 * U, 84 * U, 880 * U, 580 * U), BLANCO, round(32 * U))
        gano = res["estado"] == "ganado"
        texto(sup, ("¡Barrio salvado!" if gano else "El rumor ganó esta vez"), (r.centerx, r.y + 46 * U), 40 * U,
              VERDE if gano else ROJO, 700, "titulo")
        m = res.get("mision")
        if m:
            linea = f"{nombre_zona(res['zona'])} · Misión {'cumplida: +20 monedas' if m['cumplida'] else 'sin cumplir'}"
            texto(sup, linea, (r.centerx, r.y + 84 * U), 18 * U, VERDE if m["cumplida"] else TINTA2, 900)
        else:
            texto(sup, nombre_zona(res["zona"]), (r.centerx, r.y + 84 * U), 18 * U, TINTA2, 900)
        estrellas(sup, (r.centerx, r.y + 136 * U), 56 * U, res["estrellas"], t=self.fase_t)
        datos = [("scissors", res["cortadas"], "mentiras cortadas"), ("badge-check", res["salvadas"], "verdades salvadas"),
                 ("circle-x", res["errores"], "verdades cortadas"), ("flame", f"x{res['mejor_combo']}", "mejor combo"),
                 ("hand-heart", res.get("calmadas", 0), "peleas calmadas")]
        cw = (r.w - 60 * U) / len(datos)
        for i, (ic, v, et) in enumerate(datos):
            cx = r.x + 30 * U + cw * (i + 0.5)
            icono(sup, ic, (cx, r.y + 198 * U), 26 * U, LILA, 2.6)
            texto(sup, v, (cx, r.y + 230 * U), 28 * U, TINTA, 700, "titulo")
            texto(sup, et, (cx, r.y + 256 * U), 13 * U, TINTA2, 900)
        k = min(1, self.fase_t / 1.2)
        texto(sup, f"+{round(res['monedas'] * k)} monedas", (r.centerx - 130 * U, r.y + 298 * U), 24 * U, (200, 140, 0),
              700, "titulo")
        texto(sup, f"{res['puntos']:,} puntos".replace(",", "."), (r.centerx + 130 * U, r.y + 298 * U), 24 * U, TINTA, 700,
              "titulo")
        # Lo que cambió en Ciudad Nova (los indicadores de la ciudad).
        y = r.y + 336 * U
        texto(sup, "Así cambió Ciudad Nova:", (r.x + 50 * U, y), 16 * U, TINTA, 900, ancla="midleft")
        fin = chips_efectos(sup, res.get("efectos", {}), r.x + 250 * U, y - 16 * U, r.w - 290 * U, U)
        nuevas = self.cambios.get("senales_nuevas", [])[:5]
        y = max(fin + 22 * U, r.y + 400 * U)
        if nuevas:
            texto(sup, "¡Nuevas pistas en tu álbum!", (r.centerx, y), 18 * U, ROJO, 900)
            x0 = r.centerx - (len(nuevas) - 1) * 70 * U
            for i, s in enumerate(nuevas):
                circulo(sup, (x0 + i * 140 * U, y + 38 * U), 22 * U, (255, 230, 226))
                icono(sup, SENALES[s][1], (x0 + i * 140 * U, y + 38 * U), 24 * U, ROJO, 2.6)
                texto(sup, SENALES[s][0], (x0 + i * 140 * U, y + 72 * U), 13 * U, TINTA, 900)
        elif not gano:
            texto(sup, "No pasa nada: el barrio sigue en el mapa para intentarlo otra vez.", (r.centerx, y + 20 * U),
                  16 * U, TINTA2, 800)
        if self.fase_t > 0.8:
            self.btn_seguir.dibujar(sup, pygame.Rect(r.centerx - 150 * U, r.bottom - 34 * U, 300 * U, 66 * U), self.t)

    def _noche(self, sup):
        """La noche: el rumor salta por las calles a barrios vecinos."""
        U = self.U
        W, H = sup.get_size()
        k = suave(min(1, self.fase_t / 0.6))
        v = pygame.Surface((W, H), pygame.SRCALPHA)
        v.fill((20, 16, 70, round(110 * k)))
        sup.blit(v, (0, 0))
        for i, (a, b) in enumerate(self.cambios.get("contagios", [])):
            e = (self.fase_t - 0.6 - i * 0.5) / 0.8
            if e <= 0:
                continue
            pa, pb = self.pos(a, 60), self.pos(b, 60)
            f = min(1, e)
            pts = []
            for s in range(13):
                q = s / 12 * f
                pts.append((pa[0] + (pb[0] - pa[0]) * q + random.uniform(-4, 4) * U,
                            pa[1] + (pb[1] - pa[1]) * q - math.sin(math.pi * q) * 60 * U))
            if len(pts) >= 2:
                pygame.draw.lines(sup, ROJO, False, pts, max(3, round(6 * U)))
            if e >= 1:
                anillo(sup, pb, (30 + 20 * min(1, e - 1)) * U, ROJO, 5 * U)
        for z in self.cambios.get("focos", []):
            x, y = self.pos(z, 120)
            texto(sup, "¡Nuevo rumor!", (x, y - 70 * U), 18 * U, ROJO, 900)
        r = panel(sup, (W / 2 - 560 * U, H - 236 * U, 1120 * U, 214 * U), (250, 246, 236), round(22 * U))
        # el Diario Nova de la mañana
        texto(sup, "DIARIO NOVA", (r.x + 40 * U, r.y + 34 * U), 30 * U, TINTA, 700, "titulo", "midleft")
        texto(sup, f"Edición de la mañana · día {min(self.c.dia, DIAS_TOTAL)} de {DIAS_TOTAL}",
              (r.right - 40 * U, r.y + 34 * U), 14 * U, TINTA2, 900, ancla="midright")
        pygame.draw.line(sup, TINTA, (r.x + 40 * U, r.y + 58 * U), (r.right - 40 * U, r.y + 58 * U), max(2, round(3 * U)))
        titulo, bajada = self.cambios.get("titular") or ("Llega la noche en Ciudad Nova", "")
        k = suave(min(1, self.fase_t / 0.5))
        texto(sup, titulo, (r.x + 40 * U, r.y + 94 * U), 32 * U * (0.9 + 0.1 * k), TINTA, 700, "titulo", "midleft")
        if bajada:
            parrafo(sup, bajada, r.x + 40 * U, r.y + 116 * U, 680 * U, 16 * U, TINTA2, max_lineas=2)
        n = len(self.cambios.get("contagios", []))
        if n:
            txt = f"Esta noche: {n} barrio{'s' if n != 1 else ''} enfermo{'s' if n != 1 else ''} contagiaron a un vecino."
        elif self.cambios.get("focos"):
            txt = "Esta noche: apareció un rumor nuevo en la ciudad."
        else:
            txt = "Esta noche el rumor no logró avanzar: los barrios liberados hacen de muro."
        icono(sup, "moon", (r.x + 52 * U, r.bottom - 32 * U), 22 * U, LILA, 2.6)
        texto(sup, txt, (r.x + 72 * U, r.bottom - 32 * U), 15 * U, LILA, 900, ancla="midleft")
        if self.fase_t > 1.2:
            self.btn_seguir.dibujar(sup, pygame.Rect(r.right - 300 * U, r.y + 86 * U, 260 * U, 70 * U), self.t)

    # -------------------------------------------------------------- final
    def _eleccion(self, sup):
        U = self.U
        W, H = sup.get_size()
        el = self.c.eleccion or self.c.votar()
        velo(sup, 120)
        orden = sorted(ZONAS, key=lambda z: geo.CENTRO[z][0] + geo.CENTRO[z][1])
        for i, z in enumerate(orden):
            e = self.fase_t - 0.4 - i * 0.25
            if e <= 0:
                continue
            x, y = self.pos(z, 200)
            pct = el["zonas"][z]
            col = VERDE if pct >= 60 else MANGO if pct >= 45 else ROJO
            k = rebote(min(1, e / 0.4))
            r = pygame.Rect(0, 0, 90 * U * k, 44 * U * k)
            r.center = (x, y)
            pygame.draw.rect(sup, col, r, border_radius=round(14 * U))
            if k > 0.6:
                texto(sup, f"{pct}%", r.center, 22 * U, BLANCO, 700, "titulo")
        if self.fase_t > 3.0:
            self._votos(sup, el)

    def _votos(self, sup, el):
        """El conteo: los cuatro candidatos, sus barras de votos, el ganador y cómo quedó la ciudad."""
        U = self.U
        W, H = sup.get_size()
        e = self.fase_t - 3.0
        r = panel(sup, (W / 2 - 590 * U, H - 420 * U, 1180 * U, 400 * U), BLANCO, round(32 * U))
        final = el["final"]
        candidatos = self.c.candidatos()
        votos = el.get("votos") or {}
        ganador = el.get("ganador")
        nombre_ganador = next((c["nombre"] for c in candidatos if c["id"] == ganador), "")
        titulo = {"oro": "¡Ciudad Nova votó informada!", "plata": "¡Buena elección!",
                  "bronce": "La ciudad votó dividida", "derrota": "Ganó la desinformación"}[final]
        col = {"oro": DORADO, "plata": (150, 160, 190), "bronce": (205, 127, 50), "derrota": ROJO}[final]
        icono(sup, "medal" if final != "derrota" else "cloud-lightning", (r.x + 60 * U, r.y + 52 * U), 60 * U, col, 2.6)
        texto(sup, titulo, (r.x + 104 * U, r.y + 38 * U), 30 * U, TINTA, 700, "titulo", "midleft")
        sub = (f"{el['porcentaje']}% votó con información verdadera · Alcaldía: {nombre_ganador}" if votos
               else f"{el['porcentaje']}% de la ciudad votó con información verdadera")
        texto(sup, sub, (r.x + 104 * U, r.y + 72 * U), 16 * U, TINTA2, 900, ancla="midleft")
        linea = (f"{el['liberadas']} barrios liberados · {el['estrellas']} estrellas · {el['hechos']} hechos en el "
                 f"Archivo · {el['senales']} pistas")
        texto(sup, linea, (r.x + 104 * U, r.y + 96 * U), 14 * U, LILA, 900, ancla="midleft")
        # barras de los candidatos
        maximo = max(votos.values()) if votos else 1
        for i, c in enumerate(candidatos):
            y = r.y + 144 * U + i * 52 * U
            k = suave(min(1, max(0, e - i * 0.15) / 1.2))
            if c.get("bot"):
                av = personajes.avatar(LOOK_CANDIDATO["emilio"], round(42 * U), (255, 226, 226), "candidato", "feliz")
            elif c.get("jugador"):
                av = personajes.avatar(self.c.personaje.get("look") or {}, round(42 * U), tuple(c["color"]),
                                       self.c.personaje.get("rol", "candidato"), "feliz")
            else:
                av = personajes.avatar(LOOK_CANDIDATO[c["id"]], round(42 * U), mezclar(c["color"], BLANCO, 0.7),
                                       "candidato", "feliz" if c["id"] == ganador else "neutral")
            sup.blit(av, (r.x + 30 * U, y - 21 * U))
            if c.get("bot"):
                circulo(sup, (r.x + 68 * U, y + 14 * U), 11 * U, ROJO)
                icono(sup, "bot", (r.x + 68 * U, y + 14 * U), 14 * U, BLANCO, 2.6)
            texto(sup, c["nombre"], (r.x + 82 * U, y - 9 * U), 17 * U, TINTA, 700, "titulo", "midleft")
            texto(sup, c["lema"], (r.x + 82 * U, y + 11 * U), 12 * U, TINTA2, 900, ancla="midleft")
            barra = pygame.Rect(r.x + 280 * U, y - 13 * U, 360 * U, 26 * U)
            pygame.draw.rect(sup, (238, 240, 248), barra, border_radius=round(13 * U))
            pct = votos.get(c["id"], 0)
            relleno = barra.copy()
            relleno.w = max(round(26 * U), round(barra.w * pct / maximo * k))
            pygame.draw.rect(sup, c["color"], relleno, border_radius=round(13 * U))
            texto(sup, f"{round(pct * k)}%", (barra.right + 12 * U, y), 18 * U, TINTA, 700, "titulo", "midleft")
            if c["id"] == ganador and e > 1.4:
                icono(sup, "crown", (barra.right + 86 * U, y), 30 * U, DORADO, 3)
        # cómo quedó la ciudad
        x0 = r.x + 760 * U
        texto(sup, "Así quedó la ciudad", (x0, r.y + 130 * U), 17 * U, TINTA, 700, "titulo", "midleft")
        for i, (_, nombre, ic, valor, sube_bien) in enumerate(self.c.indicadores_lista()):
            y = r.y + 162 * U + i * 30 * U
            colv = color_indicador(valor, sube_bien)
            icono(sup, ic, (x0 + 10 * U, y), 18 * U, colv, 2.6)
            texto(sup, nombre, (x0 + 28 * U, y), 13 * U, TINTA2, 900, ancla="midleft")
            barra = pygame.Rect(x0 + 140 * U, y - 5 * U, 200 * U, 10 * U)
            pygame.draw.rect(sup, (232, 234, 246), barra, border_radius=round(5 * U))
            relleno = barra.copy()
            relleno.w = round(barra.w * valor / 100)
            pygame.draw.rect(sup, colv, relleno, border_radius=round(5 * U))
            texto(sup, str(valor), (barra.right + 10 * U, y), 13 * U, colv, 900, ancla="midleft")
        self.btn_seguir.etiqueta = "Volver al menú"
        if e > 1.5:
            self.btn_seguir.dibujar(sup, pygame.Rect(r.centerx - 150 * U, r.bottom - 42 * U, 300 * U, 62 * U), self.t)
