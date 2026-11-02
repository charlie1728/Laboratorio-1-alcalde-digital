"""El final de la campaña: la portada del Diario Nova con el resultado de la elección.

Cuenta quién ganó, cómo votó la ciudad y lo que hizo el jugador en toda la campaña (lo que aprendió).
"""
from __future__ import annotations

import math
import random

import pygame

from ..ui import personajes
from ..ui.dibujo import LILA, MANGO, ROJO, TINTA, TINTA2, VERDE, icono, mezclar, rebote, sombra, texto
from .comunes import Boton, Escala, parrafo
from .pantalla_mapa import LOOK_CANDIDATO

PAPEL = (250, 246, 236)


def leccion(stats: dict, final: str) -> str:
    """Lo que Civi le dice al jugador al final, según cómo jugó."""
    if stats.get("mentiras_compartidas", 0) > stats.get("frenadas", 0):
        return ("Compartiste más mentiras de las que frenaste. La próxima vez, antes de compartir: ¡verifica! "
                "Una sola publicación puede llegarles a decenas de vecinos.")
    if final == "derrota":
        return ("Ganaron los bots porque muchos barrios se quedaron con rumores. Libera más barrios antes del jefe: "
                "una ciudad informada vota mejor.")
    if stats.get("verificadas", 0) == 0:
        return "Lo hiciste bien cortando mentiras. Ahora prueba VERIFICAR en la alerta viral: vale más puntos."
    return ("¡Así se cuida una ciudad! Verificaste antes de compartir, frenaste rumores y dejaste llegar las "
            "noticias reales. Eso mismo sirve en las redes de verdad.")


class PantallaPeriodico:
    def __init__(self, app, campana):
        self.app = app
        self.c = campana
        self.el = campana.eleccion or campana.votar()
        self.t = 0.0
        self.confeti = []
        self._hoja = None             # (tamaño, superficie): la portada se dibuja una sola vez
        self.btn = Boton("Volver al menú", "menu", MANGO, "chevron-right", tecla=[pygame.K_RETURN, pygame.K_ESCAPE])
        app.sonar("victoria" if self.el["final"] != "derrota" else "malo")

    def evento(self, e):
        if self.t > 1.0 and self.btn.toca(e):
            self.app.ir_menu()

    def actualizar(self, dt):
        self.t += dt
        if self.el["final"] != "derrota" and not self.app.menos_movimiento and random.random() < 0.5:
            self.confeti.append(dict(x=random.random(), y=-0.05, v=random.uniform(0.15, 0.35), r=random.uniform(0, 6.3),
                                     c=random.choice([MANGO, ROJO, LILA, VERDE, (96, 190, 255)])))
        for c in self.confeti:
            c["y"] += c["v"] * dt
            c["r"] += dt * 5
        self.confeti = [c for c in self.confeti if c["y"] < 1.1][-200:]

    def dibujar(self, sup):
        E = Escala(sup)
        U = E.U
        for y in range(0, E.H, 4):
            pygame.draw.rect(sup, mezclar((60, 44, 140), (120, 90, 230), y / E.H), (0, y, E.W, 4))
        k = rebote(min(1, self.t / 0.6))
        if self._hoja is None or self._hoja[0] != (E.W, E.H):
            self._hoja = ((E.W, E.H), self._portada(U))
        hoja = self._hoja[1]
        # la hoja entra girando, como un periódico que cae en la mesa
        img = pygame.transform.rotozoom(hoja, (1 - k) * 12, 0.6 + 0.4 * k) if k < 1 else hoja
        rect = img.get_rect(center=(E.W / 2, E.y(340)))
        sombra(sup, rect.inflate(-40 * U, -40 * U), round(10 * U), 90)
        sup.blit(img, rect)
        for c in self.confeti:
            px, py = c["x"] * E.W, c["y"] * E.H
            pygame.draw.polygon(sup, c["c"], [(px + math.cos(c["r"] + a) * 8 * U, py + math.sin(c["r"] + a) * 5 * U)
                                              for a in (0, 2, 3.5, 5)])
        if self.t > 1.0:
            self.btn.dibujar(sup, E.r(640 - 160, 660, 320, 56), self.t)

    def _portada(self, U):
        el = self.el
        candidatos = self.c.candidatos()
        ganador = next((c for c in candidatos if c["id"] == el.get("ganador")), candidatos[0])
        bots = ganador.get("bot", False)
        hoja = pygame.Surface((round(1120 * U), round(660 * U)), pygame.SRCALPHA)
        hoja.fill((0, 0, 0, 0))
        r = hoja.get_rect()
        pygame.draw.rect(hoja, PAPEL, r, border_radius=round(10 * U))
        # cabecera
        texto(hoja, "DIARIO NOVA", (r.centerx, 46 * U), 54 * U, TINTA, 700, "titulo")
        texto(hoja, f"Edición especial · Elecciones de Ciudad Nova · día {min(self.c.dia, 12)}", (r.centerx, 88 * U),
              15 * U, TINTA2, 900)
        for y in (104, 110):
            pygame.draw.line(hoja, TINTA, (36 * U, y * U), (r.w - 36 * U, y * U), max(1, round(2 * U)))
        titular = f"¡{ganador['nombre']} gana con cadenas y bots!" if bots else f"¡{ganador['nombre']} gana la Alcaldía!"
        texto(hoja, titular, (r.centerx, 150 * U), 46 * U, ROJO if bots else TINTA, 700, "titulo")
        sub = {"oro": "La ciudad votó informada: las mentiras no pudieron con Ciudad Nova",
               "plata": "Buena elección: la mayoría de los barrios votó con información verdadera",
               "bronce": "Una ciudad dividida: muchos votaron sin saber qué era verdad",
               "derrota": "Las cadenas y los bots confundieron a la mayoría de los votantes"}[el["final"]]
        texto(hoja, sub, (r.centerx, 192 * U), 18 * U, TINTA2, 900)
        # la foto del ganador
        foto = pygame.Rect(40 * U, 224 * U, 400 * U, 300 * U)
        pygame.draw.rect(hoja, (226, 222, 210), foto)
        pygame.draw.rect(hoja, TINTA, foto, max(1, round(2 * U)))
        if bots:
            # Emilio celebra y detrás asoma el Bot Supremo, que le hizo la campaña.
            bot = personajes.cuerpo({}, "npc", "feliz", round(200 * U), bot=True)
            hoja.blit(bot, (foto.right - bot.get_width() - 10 * U, foto.y + 10 * U))
            img = personajes.cuerpo(LOOK_CANDIDATO["emilio"], "candidato", "feliz", round(270 * U))
        elif ganador.get("jugador"):
            img = personajes.cuerpo(self.c.personaje.get("look") or {}, self.c.personaje.get("rol", "candidato"),
                                    "feliz", round(270 * U))
        else:
            img = personajes.cuerpo(LOOK_CANDIDATO.get(ganador["id"], {}), "candidato", "feliz", round(270 * U))
        hoja.blit(img, (foto.centerx - img.get_width() / 2, foto.bottom - img.get_height() - 4 * U))
        texto(hoja, f"{ganador['nombre']} · {ganador['lema']}", (foto.centerx, foto.bottom + 18 * U), 14 * U, TINTA2, 900)
        # columnas
        x = 470 * U
        texto(hoja, "Cómo votó la ciudad", (x, 240 * U), 22 * U, TINTA, 700, "titulo", "midleft")
        lineas = [f"{el['porcentaje']}% votó con información verdadera",
                  f"{el['liberadas']} barrios liberados de los rumores",
                  f"{el['hechos']} noticias reales en el Archivo",
                  f"Emilio, el de los bots: {round(el.get('votos', {}).get('emilio', 0))}% de los votos"]
        for i, l in enumerate(lineas):
            icono(hoja, ("vote", "flag", "archive", "bot")[i], (x + 10 * U, 274 * U + i * 28 * U), 18 * U, LILA, 2.6)
            texto(hoja, l, (x + 30 * U, 274 * U + i * 28 * U), 15 * U, TINTA, 800, ancla="midleft")
        s = self.c.stats
        nombre = self.c.personaje.get("nombre", "Tú")
        texto(hoja, f"Lo que hizo {nombre}", (x, 410 * U), 22 * U, TINTA, 700, "titulo", "midleft")
        datos = [("scissors", s.get("cortadas", 0), "mentiras cortadas"),
                 ("search", s.get("verificadas", 0), "alertas verificadas"),
                 ("shield-check", s.get("frenadas", 0), "rumores frenados"),
                 ("hand-heart", s.get("calmadas", 0), "peleas calmadas"),
                 ("flag", s.get("misiones", 0), "misiones cumplidas")]
        for i, (ic, v, et) in enumerate(datos):
            cx = x + 60 * U + i * 118 * U
            icono(hoja, ic, (cx, 452 * U), 24 * U, LILA, 2.6)
            texto(hoja, str(v), (cx, 484 * U), 26 * U, TINTA, 700, "titulo")
            texto(hoja, et, (cx, 508 * U), 11 * U, TINTA2, 900)
        # la lección de Civi
        caja = pygame.Rect(40 * U, 556 * U, r.w - 80 * U, 84 * U)
        pygame.draw.rect(hoja, (236, 231, 255), caja, border_radius=round(18 * U))
        civi = personajes.civi("feliz", round(88 * U))
        hoja.blit(civi, (caja.x + 10 * U, caja.y - 14 * U))
        parrafo(hoja, leccion(s, el["final"]), caja.x + 80 * U, caja.y + 14 * U, caja.w - 100 * U, 16 * U, TINTA)
        return hoja
