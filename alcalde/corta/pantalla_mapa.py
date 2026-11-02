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

from ..modelo.mapa import CALLES, ZONAS, nombre_zona
from ..ui import personajes
from ..ui.dibujo import (AZUL, BLANCO, LILA, MANGO, ROJO, TINTA, TINTA2, VERDE, anillo, ancho_texto, circulo, icono,
                         mezclar, pildora, rebote, suave, texto)
from . import geometria as geo
from .comunes import Boton, estrellas, panel, parrafo, partir, velo
from .contenido import BARRIOS_JUEGO, SENALES
from .isla import Escenario

DORADO = (255, 200, 40)


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
                self.app.ir_menu()
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
            self.fase = "noche" if (self.cambios.get("contagios") or self.cambios.get("focos")) else "mapa"
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
                self.sel = self.cambios.get("liberada") and self.c.disponibles()[0] or self.c.disponibles()[0]

    def actualizar(self, dt):
        self.t += dt
        self.fase_t += dt
        if self.overlay is not None and hasattr(self.overlay, "actualizar"):
            self.overlay.actualizar(dt)

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
            self._tarjeta(sup)
        elif self.fase == "resultado":
            self._resultado(sup)
        elif self.fase == "eleccion":
            self._eleccion(sup)
        if self.overlay is not None:
            self.overlay.dibujar(sup)

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
        from .comunes import ANCHO  # noqa: F401
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
            texto(sup, txt + " (más difícil)" if n else txt, (r.x + 136 * U, r.bottom - 26 * U), 15 * U,
                  ROJO if n else VERDE, 900, ancla="midleft")
        bx = r.right - 300 * U
        if estado == "disponible":
            self.btn_jugar.latir = True
            self.btn_jugar.dibujar(sup, pygame.Rect(bx, r.y + 40 * U, 270 * U, 84 * U), self.t)
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
        r = panel(sup, (W / 2 - 420 * U, 110 * U, 840 * U, 520 * U), BLANCO, round(32 * U))
        gano = res["estado"] == "ganado"
        texto(sup, ("¡Barrio salvado!" if gano else "El rumor ganó esta vez"), (r.centerx, r.y + 56 * U), 40 * U,
              VERDE if gano else ROJO, 700, "titulo")
        texto(sup, nombre_zona(res["zona"]), (r.centerx, r.y + 96 * U), 18 * U, TINTA2, 900)
        estrellas(sup, (r.centerx, r.y + 160 * U), 56 * U, res["estrellas"], t=self.fase_t)
        datos = [("scissors", res["cortadas"], "mentiras cortadas"), ("badge-check", res["salvadas"], "verdades salvadas"),
                 ("circle-x", res["errores"], "verdades cortadas"), ("flame", f"x{res['mejor_combo']}", "mejor combo")]
        cw = (r.w - 60 * U) / 4
        for i, (ic, v, et) in enumerate(datos):
            cx = r.x + 30 * U + cw * (i + 0.5)
            icono(sup, ic, (cx, r.y + 232 * U), 26 * U, LILA, 2.6)
            texto(sup, v, (cx, r.y + 266 * U), 28 * U, TINTA, 700, "titulo")
            texto(sup, et, (cx, r.y + 292 * U), 13 * U, TINTA2, 900)
        k = min(1, self.fase_t / 1.2)
        texto(sup, f"+{round(res['monedas'] * k)} monedas", (r.centerx - 120 * U, r.y + 340 * U), 24 * U, (200, 140, 0),
              700, "titulo")
        texto(sup, f"{res['puntos']:,} puntos".replace(",", "."), (r.centerx + 140 * U, r.y + 340 * U), 24 * U, TINTA, 700,
              "titulo")
        nuevas = self.cambios.get("senales_nuevas", [])
        y = r.y + 386 * U
        if nuevas:
            texto(sup, "¡Nuevas pistas en tu álbum!", (r.centerx, y), 18 * U, ROJO, 900)
            x0 = r.centerx - (len(nuevas) - 1) * 70 * U
            for i, s in enumerate(nuevas[:5]):
                circulo(sup, (x0 + i * 140 * U, y + 40 * U), 22 * U, (255, 230, 226))
                icono(sup, SENALES[s][1], (x0 + i * 140 * U, y + 40 * U), 24 * U, ROJO, 2.6)
                texto(sup, SENALES[s][0], (x0 + i * 140 * U, y + 74 * U), 13 * U, TINTA, 900)
        elif not gano:
            texto(sup, "No pasa nada: el barrio sigue en el mapa para intentarlo otra vez.", (r.centerx, y + 20 * U),
                  16 * U, TINTA2, 800)
        if self.fase_t > 0.8:
            self.btn_seguir.dibujar(sup, pygame.Rect(r.centerx - 150 * U, r.bottom - 30 * U, 300 * U, 66 * U), self.t)

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
        r = panel(sup, (W / 2 - 520 * U, H - 186 * U, 1040 * U, 150 * U), BLANCO, round(28 * U))
        icono(sup, "moon", (r.x + 70 * U, r.centery), 56 * U, LILA, 2.6)
        texto(sup, f"Noche {self.c.dia - 1}: el rumor se mueve", (r.x + 130 * U, r.y + 50 * U), 28 * U, TINTA, 700,
              "titulo", "midleft")
        n = len(self.cambios.get("contagios", []))
        txt = (f"{n} barrio{'s' if n != 1 else ''} enfermo{'s' if n != 1 else ''} contagiaron a un vecino por las calles. "
               "Los barrios liberados hacen de muro.") if n else "Apareció un rumor nuevo en la ciudad."
        parrafo(sup, txt, r.x + 130 * U, r.y + 72 * U, 560 * U, 16 * U, TINTA2, max_lineas=2)
        if self.fase_t > 1.2:
            self.btn_seguir.dibujar(sup, pygame.Rect(r.right - 300 * U, r.y + 40 * U, 270 * U, 74 * U), self.t)

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
            r = panel(sup, (W / 2 - 440 * U, H - 270 * U, 880 * U, 250 * U), BLANCO, round(32 * U))
            final = el["final"]
            titulo = {"oro": "¡Ciudad Nova votó informada!", "plata": "¡Buena elección!",
                      "bronce": "La ciudad votó dividida", "derrota": "Ganó la desinformación"}[final]
            col = {"oro": DORADO, "plata": (150, 160, 190), "bronce": (205, 127, 50), "derrota": ROJO}[final]
            icono(sup, "medal" if final != "derrota" else "cloud-lightning", (r.x + 80 * U, r.y + 80 * U), 80 * U, col, 2.6)
            texto(sup, titulo, (r.centerx + 50 * U, r.y + 60 * U), 34 * U, TINTA, 700, "titulo")
            texto(sup, f"{el['porcentaje']}% de la ciudad votó con información verdadera", (r.centerx + 50 * U,
                  r.y + 104 * U), 18 * U, TINTA2, 900)
            linea = (f"{el['liberadas']} barrios liberados · {el['estrellas']} estrellas · {el['hechos']} hechos en el "
                     f"Archivo · {el['senales']} pistas")
            texto(sup, linea, (r.centerx + 50 * U, r.y + 140 * U), 15 * U, TINTA, 800)
            self.btn_seguir.etiqueta = "Volver al menú"
            self.btn_seguir.dibujar(sup, pygame.Rect(r.centerx - 150 * U, r.bottom - 40 * U, 300 * U, 66 * U), self.t)
