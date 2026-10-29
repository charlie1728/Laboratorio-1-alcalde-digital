"""Noche de elecciones: se cuentan los votos zona por zona y se anuncia quién gana."""
import math
import random

import pygame

from ..modelo.hechos import CANDIDATOS
from ..modelo.mapa import ZONAS
from . import edificios, recursos
from .efectos import EFECTOS, CONFETI, rebote
from .escena import cielo
from .pantalla_menu import COLOR_CANDIDATO, afiche
from .tema import TEMA
from .widgets import Boton, chip, parrafo, sticker, texto, titulo

FEMENINO = {"Valentina Rondón", "Luz Marina Pacheco"}
PASO_ZONA = 950


def miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


class PantallaEleccion:
    def __init__(self, app, ctrl):
        self.app = app
        self.ctrl = ctrl
        self.p = ctrl.partida
        self.e = self.p.eleccion
        self.t0 = pygame.time.get_ticks()
        orden = sorted(ZONAS, key=lambda z: ZONAS[z]["poblacion"])
        self.zonas = orden
        self.contadas = 0
        self.anunciado = False
        rng = random.Random(7)
        self.estrellas = [(rng.uniform(0, 1280), rng.uniform(0, 380), rng.uniform(1, 2.6)) for _ in range(90)]
        self.btn = Boton((990, 640, 260, 58), "Ver resultados", "seguir", icono="arrow-right", estilo="primario", tam=19)
        self.btn_saltar = Boton((1100, 20, 156, 44), "Saltar conteo", "saltar", icono="skip-forward", tam=15, sombra=3)
        self._ultimo_fuego = 0

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.anunciado and self.btn.clic(e.pos):
                self.app.ir_resumen(self.ctrl)
            elif not self.anunciado and self.btn_saltar.clic(e.pos):
                self.t0 -= PASO_ZONA * (len(self.zonas) + 2)
        elif e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.anunciado:
                self.app.ir_resumen(self.ctrl)
            else:
                self.t0 -= PASO_ZONA * (len(self.zonas) + 2)

    def actualizar(self):
        ahora = pygame.time.get_ticks()
        n = min(len(self.zonas), int((ahora - self.t0 - 900) / PASO_ZONA) + 1) if ahora - self.t0 > 900 else 0
        if n > self.contadas:
            self.contadas = n
            self.app.sonar("votos")
        if self.contadas == len(self.zonas) and not self.anunciado and ahora - self.t0 > 900 + PASO_ZONA * (len(self.zonas) + 0.6):
            self.anunciado = True
            self.t_anuncio = ahora
            self.app.sonar("victoria")
            EFECTOS.confeti(640, 300, 160, 11)
        if self.anunciado and ahora - self._ultimo_fuego > 700 and ahora - self.t_anuncio < 9000:
            self._ultimo_fuego = ahora
            x, y = random.uniform(120, 1160), random.uniform(80, 300)
            EFECTOS.chispas(x, y, random.choice(CONFETI), 26)

    def totales(self):
        tot = {c: 0 for c, _ in CANDIDATOS}
        for z in self.zonas[:self.contadas]:
            for c, v in self.e["zonas"][z]["votos"].items():
                tot[c] += v
        return tot

    def dibujar(self, sup):
        c = TEMA.c
        ahora = pygame.time.get_ticks()
        cielo(sup, noche=1.0)
        if not TEMA.alto_contraste:
            for x, y, r in self.estrellas:
                brillo = 160 + 90 * math.sin(ahora / 400 + x)
                pygame.draw.circle(sup, (255, 255, min(255, round(brillo))), (x, y), r)
            pygame.draw.circle(sup, (255, 244, 200), (1180, 70), 34)
            pygame.draw.circle(sup, (34, 36, 92), (1166, 60), 30)
        blanco = (255, 255, 255) if not TEMA.alto_contraste else c["texto"]
        titulo(sup, "Noche de elecciones", (40, 24), 40, blanco)
        texto(sup, f"Participación {round(self.e['participacion'] * 100)}%: votaron {miles(self.e['votantes'])} "
                   "personas en las 9 zonas de Ciudad Nova.", (42, 76), 16, blanco, peso=800)
        if not self.anunciado:
            self.btn_saltar.dibujar(sup)
        self._zonas(sup)
        self._columnas(sup)
        if self.anunciado:
            self._anuncio(sup)

    def _zonas(self, sup):
        c = TEMA.c
        r = pygame.Rect(36, 118, 300, 584)
        sticker(sup, r, c["papel"], 20, 6, 3)
        texto(sup, "Conteo por zonas", (r.x + 16, r.y + 14), 17, c["texto"], peso=900)
        y = r.y + 46
        for i, z in enumerate(self.zonas):
            fila = pygame.Rect(r.x + 12, y, r.w - 24, 54)
            contada = i < self.contadas
            datos = self.e["zonas"][z]
            if contada:
                gan = datos["ganador"]
                sticker(sup, fila, c["papel2"], 14, 0, 2)
                pygame.draw.rect(sup, COLOR_CANDIDATO[gan], (fila.x + 2, fila.y + 2, 8, fila.h - 4), border_radius=4)
            else:
                pygame.draw.rect(sup, c["papel2"], fila, border_radius=14)
            sup.blit(edificios.edificio(ZONAS[z]["tipo"], 52), (fila.x + 14, fila.y + 4))
            texto(sup, ZONAS[z]["nombre"], (fila.x + 72, fila.y + 8), 14, c["texto"] if contada else c["tenue"], peso=900)
            if contada:
                texto(sup, f"Gana {gan.split()[0]}, {miles(datos['votos'][gan])} votos", (fila.x + 72, fila.y + 28), 12,
                      c["tinta2"], peso=800)
            else:
                texto(sup, "Contando…" if i == self.contadas else "Esperando", (fila.x + 72, fila.y + 28), 12,
                      c["tenue"], peso=800)
            y += 60

    def _columnas(self, sup):
        c = TEMA.c
        tot = self.totales()
        maximo = max(1, max(self.e["totales"].values()))
        base_y = 590
        for i, (nombre, col) in enumerate(CANDIDATOS):
            cx = 450 + i * 210
            alto = round(200 * tot[nombre] / maximo)
            barra = pygame.Rect(cx - 50, base_y - alto, 100, alto)
            if alto > 0:
                sticker(sup, barra, col, 12, 0, 3)
            pygame.draw.line(sup, (255, 255, 255), (cx - 90, base_y), (cx + 90, base_y), 4)
            ganador = self.anunciado and nombre == self.e["ganador"]
            esc = 1.0
            img = afiche(nombre, 136 if not ganador else 150, 0, "feliz" if (ganador or not self.anunciado) else "neutral")
            sup.blit(img, img.get_rect(midbottom=(cx, base_y - alto - 6)))
            r = chip(sup, miles(tot[nombre]), (cx, base_y + 26), c["papel"], c["texto"], "vote", 15, ancla="c", alto=32)
            perdidos = self.e["perdidos"].get(nombre, 0)
            if self.anunciado and perdidos > 0:
                chip(sup, f"-{miles(perdidos)} por rumores", (cx, base_y + 64), c["malo"], c["sobre_color"], "cloud-fog",
                     12, ancla="c", alto=26)

    def _anuncio(self, sup):
        c = TEMA.c
        e = min(1, (pygame.time.get_ticks() - self.t_anuncio) / 600)
        gan = self.e["ganador"]
        cargo = "la nueva alcaldesa" if gan in FEMENINO else "el nuevo alcalde"
        r = pygame.Rect(370, 104, 870, 66)
        if not TEMA.op["menos_movimiento"]:
            r.y -= round((1 - rebote(e)) * 40)
        sticker(sup, r, c["mango"], 22, 6, 3)
        sup.blit(recursos.icono("crown", 34, c["texto"], 2.6), (r.x + 20, r.y + 18))
        titulo(sup, f"¡{gan} es {cargo} de Ciudad Nova!", (r.x + 66, r.centery), 25, c["texto"], ancla="ml")
        cand_jugador = next((j for j in self.p.jugadores if j.candidato == gan), None)
        if self.e["cambio"]:
            leccion = (f"La desinformación cambió la elección: sin rumores habría ganado "
                       f"{self.e['ganador_sin_rumores']}.")
            col = c["malo"]
        else:
            peor = max(self.e["perdidos"], key=self.e["perdidos"].get)
            perdidos = self.e["perdidos"][peor]
            leccion = (f"Los rumores le quitaron {miles(perdidos)} votos a {peor}, pero no cambiaron el resultado."
                       if perdidos > 0 else "Ciudad Nova votó informada: los rumores no le quitaron votos a nadie.")
            col = c["texto"]
        if cand_jugador:
            leccion += f" {cand_jugador.nombre} jugó como su candidato."
        caja = pygame.Rect(370, 640, 600, 62)
        sticker(sup, caja, c["papel"], 18, 4, 3)
        parrafo(sup, leccion, caja.x + 16, caja.y + 10, caja.w - 32, 14, col, peso=800, max_lineas=2)
        self.btn.dibujar(sup)
