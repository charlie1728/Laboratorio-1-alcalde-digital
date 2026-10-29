"""Resultados finales: cómo quedó la ciudad, el podio de jugadores y lo que pasó en la campaña."""
import math

import pygame

from ..modelo.ciudad import NEGATIVOS, NOMBRES
from . import personajes, recursos
from .efectos import EFECTOS
from .escena import Escena
from .tema import TEMA
from .widgets import Boton, barra, parrafo, recortar, sticker, texto, titulo

ICONO_IND = dict(info_verificada="shield-check", confianza="handshake", convivencia="heart-handshake",
                 bienestar="heart-pulse", desinformacion="cloud-fog", conflictos="zap")


class PantallaResumen:
    def __init__(self, app, ctrl):
        self.app = app
        self.ctrl = ctrl
        self.p = ctrl.partida
        self.escena = Escena(semilla=8, gente=5, y_suelo=760)
        self.btn_otra = Boton((830, 650, 210, 56), "Jugar otra vez", "otra", icono="rotate-ccw", estilo="primario", tam=18)
        self.btn_menu = Boton((1052, 650, 196, 56), "Menú principal", "menu", icono="house", tam=17)
        self.t0 = pygame.time.get_ticks()
        salud = self.p.ciudad.salud()
        app.sonar("logro" if salud >= 55 else "malo")
        if salud >= 55:
            EFECTOS.confeti(640, 200, 120, 9)
        ctrl.cerrar()

    def evento(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.btn_otra.clic(e.pos):
                if self.ctrl.en_red:
                    from .pantalla_red import PantallaRed
                    self.app.cambiar(PantallaRed(self.app))
                else:
                    from .pantalla_seleccion import PantallaSeleccion
                    self.app.cambiar(PantallaSeleccion(self.app))
            elif self.btn_menu.clic(e.pos):
                self.app.ir_menu()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.app.ir_menu()

    def dibujar(self, sup):
        c = TEMA.c
        p = self.p
        self.escena.dibujar(sup, sol=False)
        salud = p.ciudad.salud()
        if salud >= 65:
            frase = "Ciudad Nova llegó a las urnas bien informada."
        elif salud >= 50:
            frase = "Ciudad Nova resistió, aunque algunos rumores dejaron huella."
        else:
            frase = "La desinformación ganó terreno en Ciudad Nova."
        titulo(sup, "Fin de la campaña", (36, 18), 38, c["texto"])
        texto(sup, frase, (38, 66), 17, c["tinta2"], peso=800)
        self._ciudad(sup)
        self._podio(sup)
        self._campana(sup)
        self.btn_otra.dibujar(sup)
        self.btn_menu.dibujar(sup)

    def _ciudad(self, sup):
        c = TEMA.c
        p = self.p
        r = pygame.Rect(30, 104, 380, 600)
        sticker(sup, r, c["papel"], 22, 6, 3)
        salud = p.ciudad.salud()
        col = c["bueno"] if salud >= 60 else c["aviso"] if salud >= 45 else c["malo"]
        titulo(sup, "Así quedó la ciudad", (r.x + 18, r.y + 14), 21, c["texto"])
        sup.blit(recursos.icono("smile" if salud >= 60 else "meh" if salud >= 45 else "frown", 54, col, 2.4),
                 (r.x + 18, r.y + 52))
        titulo(sup, str(salud), (r.x + 84, r.y + 46), 52, col)
        texto(sup, "de salud", (r.x + 88, r.y + 106), 13, c["tinta2"], peso=800)
        y = r.y + 136
        for k in ("info_verificada", "confianza", "convivencia", "bienestar", "desinformacion", "conflictos"):
            neg = k in NEGATIVOS
            v = p.ciudad.v[k]
            sup.blit(recursos.icono(ICONO_IND[k], 18, c["malo"] if neg else c["acento"], 2.4), (r.x + 18, y + 2))
            texto(sup, NOMBRES[k], (r.x + 44, y), 14, c["texto"], peso=800)
            texto(sup, str(v), (r.right - 18, y), 14, c["texto"], peso=900, ancla="tr")
            barra(sup, (r.x + 44, y + 22, r.w - 66, 10), v, c["malo"] if neg else c["acento"], rayas=neg)
            y += 44
        texto(sup, "Desinformación día a día", (r.x + 18, y + 6), 14, c["texto"], peso=900)
        g = pygame.Rect(r.x + 18, y + 30, r.w - 36, r.bottom - y - 50)
        pygame.draw.rect(sup, c["papel2"], g, border_radius=12)
        hist = [h["desinformacion"] for h in p.ciudad.historial]
        if len(hist) > 1:
            pts = [(g.x + 16 + i * (g.w - 32) / (len(hist) - 1), g.bottom - 14 - v * (g.h - 28) / 100)
                   for i, v in enumerate(hist)]
            pygame.draw.lines(sup, c["malo"], False, pts, 4)
            for i, q in enumerate(pts):
                pygame.draw.circle(sup, c["papel"], q, 6)
                pygame.draw.circle(sup, c["malo"], q, 6, 3)
            texto(sup, "inicio", (g.x + 8, g.bottom + 2), 11, c["tinta2"], peso=800)
            texto(sup, "elección", (g.right - 8, g.bottom + 2), 11, c["tinta2"], peso=800, ancla="tr")

    def _podio(self, sup):
        c = TEMA.c
        p = self.p
        r = pygame.Rect(426, 104, 440, 530)
        sticker(sup, r, c["papel"], 22, 6, 3)
        titulo(sup, "Jugadores", (r.x + 18, r.y + 14), 21, c["texto"])
        ranking = sorted(p.jugadores, key=lambda j: -j.puntos)
        posiciones = {0: (r.centerx, 150), 1: (r.x + 86, 110), 2: (r.right - 86, 80), 3: (r.right - 40, 50)}
        ahora = pygame.time.get_ticks()
        suelo = r.y + 400
        for i, j in enumerate(ranking[:3]):
            cx, alto_podio = posiciones[i]
            podio = pygame.Rect(cx - 62, suelo - alto_podio, 124, alto_podio)
            sticker(sup, podio, (c["mango"], c["papel3"], c["mango2"])[i], 12, 4, 3)
            titulo(sup, str(i + 1), podio.center, 40, c["texto"], ancla="c")
            bob = math.sin(ahora / 300 + i) * 3 if not TEMA.op["menos_movimiento"] else 0
            img = personajes.cuerpo(j.look, j.rol, "feliz" if i == 0 else "neutral", alto=150 if i == 0 else 128,
                                    parpadeo=(ahora + i * 900) % 3600 < 120, color_extra=(58, 110, 230))
            sup.blit(img, (cx - img.get_width() // 2, podio.y - img.get_height() + 8 + bob))
            if i == 0:
                sup.blit(recursos.icono("crown", 30, c["logro"], 2.8), (cx - 15, podio.y - img.get_height() - 22))
        y = suelo + 14
        for i, j in enumerate(ranking):
            fila = pygame.Rect(r.x + 14, y, r.w - 28, 26)
            pygame.draw.circle(sup, j.color, (fila.x + 10, fila.centery), 8)
            texto(sup, f"{i + 1}. {recortar(j.nombre, 14, 130, 900)}", (fila.x + 24, fila.centery), 14, c["texto"],
                  peso=900, ancla="ml")
            texto(sup, j.info_rol["nombre"], (fila.x + 186, fila.centery), 12, c["tinta2"], peso=800, ancla="ml")
            texto(sup, f"{j.puntos} pts", (fila.right - 6, fila.centery), 14, c["texto"], peso=900, ancla="mr")
            x = fila.x + 270
            for k, lg in enumerate(j.logros[:5]):
                pygame.draw.circle(sup, c["mango"], (x + k * 18, fila.centery), 8)
                sup.blit(recursos.icono("award", 11, c["texto"], 2.6), (x + k * 18 - 6, fila.centery - 6))
            y += 28

    def _campana(self, sup):
        c = TEMA.c
        p = self.p
        r = pygame.Rect(882, 104, 368, 530)
        sticker(sup, r, c["papel"], 22, 6, 3)
        titulo(sup, "Lo que pasó", (r.x + 18, r.y + 14), 21, c["texto"])
        st = {k: sum(j.stats[k] for j in p.jugadores) for k in p.jugadores[0].stats}
        bots = sum(1 for m in p.mensajes if "suspendió la cuenta bot" in m.texto)
        mayor = max(p.casos, key=lambda cs: len(cs.arbol)) if p.casos else None
        e = p.eleccion or {}
        filas = [("search", f"{st['verificados']} publicaciones verificadas"),
                 ("message-circle", f"{st['corregidos']} personas dejaron de creer algo falso"),
                 ("flag", f"{st['reportes']} reportes aceptados"),
                 ("share-2", f"{st['falsos_compartidos']} veces se compartió algo falso"),
                 ("bot", f"{bots} cuentas bot suspendidas"),
                 ("footprints", f"{st['km']} minutos caminando por la ciudad")]
        if mayor:
            filas.append(("git-fork", f"La historia más grande: {mayor.hecho.titulo} ({len(mayor.arbol)} publicaciones)"))
        if e:
            filas.append(("vote", f"Ganó {e['ganador']}"))
        y = r.y + 54
        for ic, s in filas:
            pygame.draw.circle(sup, c["acento2"], (r.x + 32, y + 12), 15)
            sup.blit(recursos.icono(ic, 16, c["acento"], 2.4), (r.x + 24, y + 4))
            y = parrafo(sup, s, r.x + 56, y + 2, r.w - 74, 14, c["texto"], peso=800, max_lineas=2) + 12
        y += 4
        caja = pygame.Rect(r.x + 14, max(y, r.bottom - 136), r.w - 28, 122)
        sticker(sup, caja, c["mango2"], 16, 0, 2)
        texto(sup, "Para la vida real", (caja.x + 14, caja.y + 10), 15, c["texto"], peso=900)
        parrafo(sup, "Antes de compartir, verifica. Una noticia puede ser cierta en su origen y torcerse en el "
                     "camino, y borrar no deshace lo que ya circuló. Hablar con la gente también desmiente.",
                caja.x + 14, caja.y + 34, caja.w - 28, 13, c["tinta2"], peso=700, max_lineas=5)
