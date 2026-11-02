"""Juego rápido (pensado para la feria): escoges personaje, juegas un barrio y entras a la tabla de récords.

Las primeras publicaciones vienen marcadas (córtala / déjala pasar) para que quien nunca ha jugado
aprenda en segundos, y en la mitad del nivel salta la alerta viral.
"""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.mapa import crear_mapa, nombre_zona
from ..modelo.red_social import conectar_jugador, generar_red
from ..ui import personajes
from ..ui.dibujo import BLANCO, LILA, MANGO, ROJO, TINTA, TINTA2, VERDE, icono, mezclar, pildora, rebote, texto
from ..ui.tema import TEMA
from . import records
from .logros import REGISTRO
from .comunes import Boton, Escala, estrellas, panel, titulo_grande
from .nivel import Nivel
from .pantalla_nivel import PantallaNivel

# Barrios con reglas fáciles de entender a la primera (nada de avalanchas ni de recreo acelerado).
ZONAS_RAPIDO = ["PARQUE", "TERMINAL", "PRADO", "PLAZA"]
DORADO = (255, 200, 40)


class PantallaRapido:
    def __init__(self, app, jugador: dict):
        self.app = app
        self.jugador = dict(jugador)
        self.t = 0.0
        self.res = None
        self.nombre = ""
        self.puesto = None
        self.confeti = []
        self.btn_guardar = Boton("Guardar mi récord", "guardar", MANGO, "trophy",
                                 tecla=[pygame.K_RETURN, pygame.K_KP_ENTER])
        self.btn_otra = Boton("¡Otra vez!", "otra", MANGO, "rotate-ccw", tecla=[pygame.K_RETURN, pygame.K_SPACE])
        self.btn_menu = Boton("Menú", "menu", (236, 238, 248), "log-out", tecla=pygame.K_ESCAPE)
        self.partidas = 0
        self._jugar()

    def _jugar(self):
        # Con semilla fija (python main.py 42) la primera partida se repite igual; las siguientes cambian.
        base = self.app.semilla if self.app.semilla is not None else random.randrange(1 << 30)
        semilla = base + self.partidas * 7919
        self.partidas += 1
        rng = random.Random(semilla)
        zona = rng.choice(ZONAS_RAPIDO)
        mapa = crear_mapa()
        nombre = self.jugador.get("nombre", "Tú")
        red = generar_red(random.Random(semilla), mapa, {nombre})
        conectar_jugador(red, mapa, random.Random(semilla + 1), nombre, 0, self.jugador.get("rol", "periodista"),
                         self.jugador.get("look") or {}, zona)
        kw = {} if self.app.duracion is None else dict(duracion=self.app.duracion)
        n = Nivel(zona, self.jugador, semilla=semilla, red=red, guia=4, tranquilo=TEMA.op["tranquilo"], **kw)
        self.zona = zona
        self.app.sonar("turno")
        self.app.cambiar(PantallaNivel(self.app, n, self._fin, titulo=f"Juego rápido · {nombre_zona(zona)}"))

    def _fin(self, res):
        if res is None:
            self.app.ir_menu()
            return
        REGISTRO.ver_resultado(res, "rapido")
        self.res = res
        self.t = 0.0
        self.puesto = None
        self.nombre = ""
        self.app.cambiar(self)

    def escribiendo(self):
        return self.res is not None and self.puesto is None

    # -------------------------------------------------------------- entrada
    def evento(self, e):
        if self.puesto is None:
            if self.btn_guardar.toca(e):
                self._guardar()
                return
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.app.ir_menu()
                elif e.key == pygame.K_BACKSPACE:
                    self.nombre = self.nombre[:-1]
                elif e.unicode and e.unicode.isprintable() and len(self.nombre) < 14 and self.t > 0.3:
                    self.nombre += e.unicode
            elif self.btn_menu.toca(e):
                self.app.ir_menu()
            return
        if self.btn_otra.toca(e):
            self._jugar()
        elif self.btn_menu.toca(e):
            self.app.ir_menu()

    def _guardar(self):
        nombre = self.nombre.strip() or self.jugador.get("nombre", "Jugador")
        self.puesto = records.agregar(nombre, self.res["puntos"], self.jugador.get("rol", ""), self.zona,
                                      self.res["estrellas"])
        self.nombre = nombre
        self.app.sonar("victoria" if self.puesto <= 3 else "logro")

    def actualizar(self, dt):
        self.t += dt
        if self.puesto is not None and self.puesto <= 3 and not self.app.menos_movimiento and random.random() < 0.6:
            self.confeti.append(dict(x=random.random(), y=-0.05, v=random.uniform(0.15, 0.35), r=random.uniform(0, 6.3),
                                     c=random.choice([MANGO, ROJO, LILA, VERDE, (96, 190, 255)])))
        for c in self.confeti:
            c["y"] += c["v"] * dt
            c["r"] += dt * 5
        self.confeti = [c for c in self.confeti if c["y"] < 1.1][-200:]

    # -------------------------------------------------------------- dibujo
    def dibujar(self, sup):
        E = Escala(sup)
        U = E.U
        for y in range(0, E.H, 4):
            pygame.draw.rect(sup, mezclar((108, 77, 245), (255, 150, 190), y / E.H), (0, y, E.W, 4))
        res = self.res
        gano = res["estado"] == "ganado"
        titulo_grande(sup, "¡Barrio salvado!" if gano else "¡Buen intento!", (E.W / 2, 64 * U), 50 * U)
        # tarjeta del jugador
        r = panel(sup, E.r(70, 110, 520, 520), BLANCO, round(32 * U))
        k = rebote(min(1, self.t / 0.5))
        img = personajes.cuerpo(self.jugador.get("look") or {}, self.jugador.get("rol", "periodista"),
                                "feliz" if gano else "preocupado", round(190 * U * k))
        sup.blit(img, (r.centerx - img.get_width() / 2, r.y + 20 * U + math.sin(self.t * 3) * 4 * U))
        estrellas(sup, (r.centerx, r.y + 240 * U), 46 * U, res["estrellas"], t=self.t)
        puntos = round(res["puntos"] * min(1, self.t / 1.0))
        texto(sup, f"{puntos:,}".replace(",", "."), (r.centerx, r.y + 312 * U), 64 * U, TINTA, 700, "titulo")
        texto(sup, "puntos", (r.centerx, r.y + 356 * U), 18 * U, TINTA2, 900)
        datos = [("scissors", res["cortadas"], "mentiras"), ("badge-check", res["salvadas"], "verdades"),
                 ("flame", f"x{res['mejor_combo']}", "combo")]
        for i, (ic, v, et) in enumerate(datos):
            cx = r.x + r.w * (i + 0.5) / 3
            icono(sup, ic, (cx, r.y + 400 * U), 24 * U, LILA, 2.6)
            texto(sup, v, (cx, r.y + 432 * U), 24 * U, TINTA, 700, "titulo")
            texto(sup, et, (cx, r.y + 456 * U), 13 * U, TINTA2, 900)
        decis = res.get("decisiones") or []
        if decis:
            d = decis[0]
            txt = "Alerta viral: ¡bien decidido!" if d["bien"] else "Alerta viral: ¡a verificar la próxima!" \
                if d["bien"] is False else "Alerta viral: la dejaste pasar"
            texto(sup, txt, (r.centerx, r.bottom - 50 * U), 15 * U, VERDE if d["bien"] else ROJO if d["bien"] is False
                  else TINTA2, 900)
        m = res.get("mision")
        if m:
            texto(sup, f"Misión {'cumplida' if m['cumplida'] else 'sin cumplir'}: {m['texto']}", (r.centerx, r.bottom - 26 * U), 15 * U,
                  VERDE if m["cumplida"] else TINTA2, 900)
        # tabla de récords
        r2 = panel(sup, E.r(620, 110, 590, 520), BLANCO, round(32 * U))
        icono(sup, "trophy", (r2.x + 46 * U, r2.y + 44 * U), 34 * U, DORADO, 2.8)
        texto(sup, "Récords de la feria", (r2.x + 76 * U, r2.y + 44 * U), 28 * U, TINTA, 700, "titulo", "midleft")
        if self.puesto is None:
            self._pedir_nombre(sup, r2, U)
        else:
            self._tabla(sup, r2, U)
        for c in self.confeti:
            x, y = c["x"] * E.W, c["y"] * E.H
            pygame.draw.polygon(sup, c["c"], [(x + math.cos(c["r"] + a) * 8 * U, y + math.sin(c["r"] + a) * 5 * U)
                                              for a in (0, 2, 3.5, 5)])

    def _pedir_nombre(self, sup, r, U):
        texto(sup, "Escribe tu nombre para la tabla:", (r.centerx, r.y + 120 * U), 20 * U, TINTA2, 900)
        caja = pygame.Rect(r.x + 60 * U, r.y + 150 * U, r.w - 120 * U, 70 * U)
        pygame.draw.rect(sup, (246, 247, 255), caja, border_radius=round(18 * U))
        pygame.draw.rect(sup, LILA, caja, max(3, round(4 * U)), border_radius=round(18 * U))
        cursor = "|" if int(self.t * 2) % 2 == 0 else ""
        if self.nombre:
            texto(sup, self.nombre + cursor, caja.center, 34 * U, TINTA, 700, "titulo")
        else:
            texto(sup, f"{self.jugador.get('nombre', '')}{cursor}", caja.center, 34 * U, (190, 192, 214), 700, "titulo")
        texto(sup, "(o pulsa Enter para usar el de tu personaje)", (r.centerx, r.y + 244 * U), 14 * U, TINTA2, 800)
        self.btn_guardar.latir = True
        self.btn_guardar.dibujar(sup, pygame.Rect(r.centerx - 190 * U, r.y + 290 * U, 380 * U, 76 * U), self.t)
        self.btn_menu.dibujar(sup, pygame.Rect(r.centerx - 100 * U, r.bottom - 90 * U, 200 * U, 56 * U), self.t)

    def _tabla(self, sup, r, U):
        lista = records.mejores(8)
        mio = self.puesto
        msg = f"¡Quedaste en el puesto {mio}!" if mio <= 8 else f"Quedaste en el puesto {mio}. ¡Inténtalo otra vez!"
        texto(sup, msg, (r.centerx, r.y + 92 * U), 20 * U, LILA, 900)
        for i, d in enumerate(lista):
            y = r.y + 130 * U + i * 36 * U
            yo = i + 1 == mio
            if yo:
                pildora(sup, (r.x + 24 * U, y - 16 * U, r.w - 48 * U, 32 * U), (255, 240, 200), con_sombra=False)
            col = DORADO if i == 0 else (160, 166, 196) if i == 1 else (205, 127, 50) if i == 2 else TINTA2
            texto(sup, f"{i + 1}", (r.x + 50 * U, y), 20 * U, col, 700, "titulo")
            texto(sup, d["nombre"], (r.x + 84 * U, y), 19 * U, TINTA, 900 if yo else 800, ancla="midleft")
            texto(sup, f"{d['puntos']:,}".replace(",", "."), (r.right - 50 * U, y), 20 * U, TINTA, 700, "titulo",
                  "midright")
        self.btn_otra.latir = True
        self.btn_otra.dibujar(sup, pygame.Rect(r.x + 40 * U, r.bottom - 84 * U, 300 * U, 64 * U), self.t)
        self.btn_menu.dibujar(sup, pygame.Rect(r.right - 230 * U, r.bottom - 80 * U, 190 * U, 56 * U), self.t)
