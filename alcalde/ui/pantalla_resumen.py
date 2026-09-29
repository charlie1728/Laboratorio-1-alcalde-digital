import pygame

from ..modelo.ciudad import NEGATIVOS, NOMBRES
from .tema import TEMA
from .widgets import Boton, panel, texto

class PantallaResumen:
    def __init__(self, app, partida):
        self.app = app
        self.p = partida
        self.btn_nueva = Boton((460, 690, 200, 46), "Nueva partida", tam=16)
        self.btn_salir = Boton((680, 690, 140, 46), "Salir", tam=16)
        app.snd.play("logro" if partida.ciudad.salud() >= 55 else "malo")

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.btn_nueva.clic(e.pos):
                self.app.ir_inicio()
            elif self.btn_salir.clic(e.pos):
                self.app.corriendo = False

    def dibujar(self, sup):
        c = TEMA.c
        sup.fill(c["fondo"])
        res = self.p.resumen()
        salud = res["salud"]
        texto(sup, "FIN DE LA CAMPAÑA", (640, 50), 40, c["texto"], True, centro=True)
        msg = ("Ciudad Nova llega a las urnas bien informada." if salud >= 60 else
               "Ciudad Nova llega dividida, pero resistió." if salud >= 45 else
               "La desinformación ganó terreno en Ciudad Nova.")
        texto(sup, msg, (640, 92), 18, c["bueno"] if salud >= 55 else c["malo"], centro=True)

        izq = pygame.Rect(60, 130, 560, 540)
        panel(sup, izq)
        texto(sup, f"Salud de la ciudad: {salud}", (80, 146), 22, c["acento"], True)
        y = 190
        for k, v in res["indicadores"].items():
            texto(sup, NOMBRES[k], (80, y), 15)
            texto(sup, str(v), (600, y), 15, c["texto"], True, derecha=True)
            col = c["malo"] if k in NEGATIVOS else c["acento"]
            pygame.draw.rect(sup, c["panel2"], (80, y + 22, 520, 10), border_radius=5)
            pygame.draw.rect(sup, col, (80, y + 22, int(520 * v / 100), 10), border_radius=5)
            y += 50
                                        
        texto(sup, "Desinformación por ronda", (80, y + 6), 14, c["tenue"], True)
        hist = [h["desinformacion"] for h in self.p.ciudad.historial]
        gx, gy, gw, gh = 80, y + 30, 520, 120
        pygame.draw.rect(sup, c["panel2"], (gx, gy, gw, gh), border_radius=6)
        if len(hist) > 1:
            pts = [(gx + 10 + i * (gw - 20) / (len(hist) - 1), gy + gh - 10 - v * (gh - 20) / 100)
                   for i, v in enumerate(hist)]
            pygame.draw.lines(sup, c["malo"], False, pts, 3)
            for p in pts:
                pygame.draw.circle(sup, c["malo"], p, 4)

        der = pygame.Rect(660, 130, 560, 540)
        panel(sup, der)
        texto(sup, "Ranking de jugadores", (680, 146), 22, c["acento"], True)
        y = 190
        for i, j in enumerate(res["ranking"]):
            pygame.draw.circle(sup, j.color, (700, y + 16), 16)
            texto(sup, j.info_rol["simbolo"], (700, y + 16), 16, (10, 12, 20), True, centro=True)
            texto(sup, f"{i + 1}. {j.nombre}", (726, y), 18, c["texto"], True)
            texto(sup, f"{j.puntos} pts", (1200, y), 18, c["aviso"], True, derecha=True)
            texto(sup, f"{j.info_rol['nombre']} · reputación {j.reputacion}", (726, y + 22), 13, c["tenue"])
            texto(sup, "Logros: " + (", ".join(j.logros) or "ninguno"), (726, y + 40), 13, c["logro"])
            y += 76
        texto(sup, "Elección del alcalde: se habilita en la entrega final.", (680, 632), 14, c["tenue"])
        self.btn_nueva.dibujar(sup)
        self.btn_salir.dibujar(sup)
