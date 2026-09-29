import math
import random

import pygame

from ..modelo.roles import ORDEN_ROLES, ROLES
from .tema import TEMA
from .widgets import Boton, panel, parrafo, texto

COLORES_JUGADOR = [(86, 180, 233), (230, 159, 0), (0, 158, 115), (204, 121, 167)]
NOMBRES = ["Jugador 1", "Jugador 2", "Jugador 3", "Jugador 4"]

class PantallaInicio:
    def __init__(self, app):
        self.app = app
        self.slots = [dict(activo=i < 2, nombre=NOMBRES[i], rol=ORDEN_ROLES[i]) for i in range(4)]
        self.editando = None
        rnd = random.Random(7)
        self.particulas = [[rnd.uniform(0, 1280), rnd.uniform(0, 760),
                            rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3)] for _ in range(46)]
        self.btn_jugar = Boton((490, 668, 300, 50), "Comenzar campaña", tam=19)
        self.btn_ayuda = Boton((810, 668, 130, 50), "Ayuda (H)", tam=15)
        self.tarjetas = []
        for i in range(4):
            x = 70 + i * 290
            self.tarjetas.append(dict(
                rect=pygame.Rect(x, 300, 270, 330),
                toggle=Boton((x + 16, 316, 238, 32), "", tam=14),
                nombre=pygame.Rect(x + 16, 360, 238, 34),
                izq=Boton((x + 16, 408, 36, 36), "<", tam=18),
                der=Boton((x + 218, 408, 36, 36), ">", tam=18),
            ))

    def activos(self):
        return [s for s in self.slots if s["activo"]]

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.editando = None
            for i, t in enumerate(self.tarjetas):
                s = self.slots[i]
                if t["toggle"].clic(e.pos):
                    if s["activo"] and len(self.activos()) <= 2:
                        self.app.toasts.agregar("Se necesitan al menos 2 jugadores.", "malo")
                    else:
                        s["activo"] = not s["activo"]
                    self.app.snd.play("click")
                elif s["activo"] and t["nombre"].collidepoint(e.pos):
                    self.editando = i
                elif s["activo"] and (t["izq"].clic(e.pos) or t["der"].clic(e.pos)):
                    paso = -1 if t["izq"].rect.collidepoint(e.pos) else 1
                    k = (ORDEN_ROLES.index(s["rol"]) + paso) % len(ORDEN_ROLES)
                    s["rol"] = ORDEN_ROLES[k]
                    self.app.snd.play("click")
            if self.btn_jugar.clic(e.pos):
                self._comenzar()
            if self.btn_ayuda.clic(e.pos):
                self.app.mostrar_ayuda = True
        elif e.type == pygame.KEYDOWN and self.editando is not None:
            s = self.slots[self.editando]
            if e.key in (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_TAB):
                self.editando = None
            elif e.key == pygame.K_BACKSPACE:
                s["nombre"] = s["nombre"][:-1]
            elif e.unicode and e.unicode.isprintable() and len(s["nombre"]) < 14:
                s["nombre"] += e.unicode
            return True                                            
        return False

    def _comenzar(self):
        cfg = []
        for i, s in enumerate(self.slots):
            if s["activo"]:
                cfg.append((s["nombre"].strip() or NOMBRES[i], s["rol"], COLORES_JUGADOR[i]))
        candidatos = sum(1 for _, r, _ in cfg if r == "candidato")
        if candidatos > 4:
            return
        self.app.snd.play("logro")
        self.app.iniciar_partida(cfg)

    def dibujar(self, sup):
        c = TEMA.c
        sup.fill(c["fondo"])
                                                                
        for p in self.particulas:
            p[0] = (p[0] + p[2]) % 1280
            p[1] = (p[1] + p[3]) % 760
        for i, a in enumerate(self.particulas):
            for b in self.particulas[i + 1:]:
                d = math.hypot(a[0] - b[0], a[1] - b[1])
                if d < 120:
                    pygame.draw.line(sup, c["panel2"], a[:2], b[:2], 1)
        for p in self.particulas:
            pygame.draw.circle(sup, c["borde"], p[:2], 3)

        t = pygame.time.get_ticks() / 1000
        texto(sup, "ALCALDE DIGITAL", (640, 92), 64, c["texto"], True, centro=True)
        texto(sup, "El árbol de mutaciones de Ciudad Nova", (640, 150), 22, c["acento"], centro=True)
        parrafo(sup, "Cada reenvío puede torcer la historia. Encuentra dónde mutó la verdad antes "
                     "de que la campaña termine.", 330, 190, 640, 17, c["tenue"])
        pygame.draw.circle(sup, c["aviso"], (640, 262), 5 + 2 * math.sin(t * 3))
        texto(sup, "Configura de 2 a 4 jugadores (modo local por turnos)", (640, 280), 15, c["tenue"], centro=True)

        for i, t_ in enumerate(self.tarjetas):
            s = self.slots[i]
            col = COLORES_JUGADOR[i]
            panel(sup, t_["rect"], c["panel"] if s["activo"] else c["fondo"])
            pygame.draw.rect(sup, col if s["activo"] else c["borde"],
                             (t_["rect"].x, t_["rect"].y, t_["rect"].w, 5), border_radius=3)
            t_["toggle"].etiqueta = "Participa  [sí]" if s["activo"] else "Participa  [no]"
            t_["toggle"].seleccionado = s["activo"]
            t_["toggle"].color = col
            t_["toggle"].dibujar(sup)
            if not s["activo"]:
                texto(sup, "Puesto libre", t_["rect"].center, 16, c["tenue"], centro=True)
                continue
            r = t_["nombre"]
            pygame.draw.rect(sup, c["panel2"], r, border_radius=6)
            pygame.draw.rect(sup, c["acento"] if self.editando == i else c["borde"], r, 1, border_radius=6)
            cursor = "|" if self.editando == i and (pygame.time.get_ticks() // 400) % 2 else ""
            texto(sup, s["nombre"] + cursor, (r.x + 10, r.y + 7), 16)
            info = ROLES[s["rol"]]
            t_["izq"].dibujar(sup)
            t_["der"].dibujar(sup)
            cx = t_["rect"].centerx
            pygame.draw.circle(sup, col, (cx, 426), 18)
            texto(sup, info["simbolo"], (cx, 426), 18, (10, 12, 20), True, centro=True)
            texto(sup, info["nombre"], (cx, 458), 18, c["texto"], True, centro=True)
            y = parrafo(sup, "Especial: " + info["especial"][1], t_["rect"].x + 16, 486, 238, 13, c["aviso"])
            y = parrafo(sup, info["descripcion"], t_["rect"].x + 16, y + 4, 238, 13, c["tenue"])
            parrafo(sup, info["pasivo"], t_["rect"].x + 16, y + 4, 238, 13, c["tenue"])

        self.btn_jugar.activo = 2 <= len(self.activos()) <= 4
        self.btn_jugar.dibujar(sup)
        self.btn_ayuda.dibujar(sup)
        texto(sup, "Haz clic en el nombre para editarlo · flechas para cambiar de personaje",
              (640, 734), 13, c["tenue"], centro=True)
