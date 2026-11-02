"""Pantallas del duelo en red: crear o unirse a una sala, esperar, jugar todos a la vez y ver el marcador."""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.mapa import ZONAS, crear_mapa, nombre_zona
from ..modelo.red_social import generar_red
from ..red.protocolo import ips_locales
from ..red.sala import PUERTO_DUELO, Cliente, Servidor
from ..ui import personajes
from ..ui.dibujo import BLANCO, LILA, MANGO, ROJO, TINTA, TINTA2, VERDE, icono, mezclar, pildora, texto
from ..ui.tema import TEMA
from .comunes import Boton, Escala, panel, parrafo, titulo_grande
from .contenido import BARRIOS_JUEGO
from .menu import PERSONAJES
from .nivel import Nivel
from .pantalla_nivel import PantallaNivel

ZONAS_DUELO = ["ESTADIO", "COLEGIO", "PARQUE", "TERMINAL", "NORTE", "PRADO", "HOSPITAL", "PLAZA", "ALCALDIA"]


class PantallaDuelo:
    def __init__(self, app):
        self.app = app
        self.t = 0.0
        self.estado = "inicio"
        self.personaje = 0
        self.ip = ""
        self.escribiendo_ip = False
        self.error = ""
        self.servidor = None
        self.cliente = None
        self.sala = []
        self.anfitrion = None
        self.marcador = []
        self.zona_i = 0
        self.juego = None
        self.terminado = False
        self._envio = 0.0
        self._rects = {}
        self.avisos = []
        self.btn_crear = Boton("Crear sala", "crear", MANGO, "server")
        self.btn_unirse = Boton("Unirme", "unirse", (214, 240, 255), "log-in")
        self.btn_empezar = Boton("¡Empezar duelo!", "empezar", MANGO, "play", tecla=pygame.K_RETURN)
        self.btn_volver = Boton("Volver a la sala", "volver", MANGO, "chevron-left", tecla=pygame.K_RETURN)
        self.btn_salir = Boton("Salir", "salir", (236, 238, 248), "log-out")

    # -------------------------------------------------------------- red
    def _conectar(self, ip, crear=False):
        try:
            if crear:
                self.servidor = Servidor()
            self.cliente = Cliente(ip)
        except OSError as e:
            self.error = "No se pudo conectar. Revisa la IP y que estén en la misma red." if not crear else \
                f"No se pudo crear la sala ({e.__class__.__name__})."
            if self.servidor:
                self.servidor.cerrar()
                self.servidor = None
            return
        p = PERSONAJES[self.personaje]
        self.cliente.enviar({"t": "hola", "nombre": p["nombre"], "rol": p["rol"], "look": p["look"],
                             "color": list(p["color"])})
        self.estado = "sala"
        self.error = ""
        self.app.sonar("turno")

    def _mensajes(self):
        if not self.cliente:
            return
        for m in self.cliente.mensajes():
            t = m.get("t")
            if t == "sala":
                self.sala, self.anfitrion = m["jugadores"], m["anfitrion"]
            elif t == "marcador":
                self.marcador = m["jugadores"]
            elif t == "empezar":
                self._empezar(m["zona"], m["semilla"])
            elif t == "ataque" and self.juego and self.juego.n.estado == "jugando":
                self.juego.n.recibir_ataque(m["de"])
            elif t == "aviso":
                self.avisos.append((m["texto"], self.t))
            elif t == "desconectado":
                self.error = "Se perdió la conexión con la sala."
                self.estado = "inicio"
                self.juego = None
                pygame.mouse.set_visible(True)

    def _empezar(self, zona, semilla):
        p = PERSONAJES[self.personaje]
        red = generar_red(random.Random(semilla), crear_mapa(), set())
        n = Nivel(zona, p, semilla=semilla, red=red, infeccion=1, tranquilo=TEMA.op["tranquilo"],
                  **({} if self.app.duracion is None else dict(duracion=self.app.duracion)))
        self.juego = PantallaNivel(self.app, n, self._fin_local, titulo=f"Duelo · {nombre_zona(zona)}")
        self.juego.al_evento = self._evento_juego
        self.terminado = False
        self.estado = "jugando"
        pygame.mouse.set_visible(False)
        self.app.sonar("turno")

    def _evento_juego(self, ev):
        if ev["t_"] == "ataque" and self.cliente:
            self.cliente.enviar({"t": "ataque"})

    def _fin_local(self, res):
        self.terminado = True
        n = self.juego.n
        if self.cliente:
            self.cliente.enviar({"t": "puntos", "puntos": n.puntos, "salud": round(100 * n.salud / n.salud_max),
                                 "estado": n.estado if res is not None else "salio"})
        self.estado = "resultado"
        pygame.mouse.set_visible(True)

    def cerrar(self):
        if self.cliente:
            self.cliente.cerrar()
        if self.servidor:
            self.servidor.cerrar()

    def escribiendo(self):
        return self.escribiendo_ip

    # -------------------------------------------------------------- entrada
    def evento(self, e):
        if self.estado == "jugando" and self.juego:
            self.juego.evento(e)
            return
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and not self.escribiendo_ip:
            self.cerrar()
            self.app.ir_menu()
            return
        if self.btn_salir.toca(e):
            self.cerrar()
            self.app.ir_menu()
            return
        if self.estado == "inicio":
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for (tipo, v), r in self._rects.items():
                    if r.collidepoint(e.pos):
                        if tipo == "personaje":
                            self.personaje = v
                            self.app.sonar("pop")
                        elif tipo == "ip":
                            self.escribiendo_ip = True
                        return
                self.escribiendo_ip = False
            if self.btn_crear.toca(e):
                self._conectar("127.0.0.1", crear=True)
            elif self.btn_unirse.toca(e):
                if self.ip.strip():
                    self._conectar(self.ip.strip())
                else:
                    self.escribiendo_ip = True
                    self.error = "Escribe la IP que aparece en el computador que creó la sala."
            elif e.type == pygame.KEYDOWN and self.escribiendo_ip:
                if e.key == pygame.K_BACKSPACE:
                    self.ip = self.ip[:-1]
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._conectar(self.ip.strip())
                elif e.unicode and (e.unicode.isdigit() or e.unicode == ".") and len(self.ip) < 15:
                    self.ip += e.unicode
        elif self.estado == "sala":
            soy_anfitrion = self.cliente and self.cliente.id == self.anfitrion
            if soy_anfitrion:
                if self.btn_empezar.toca(e) and self.sala:
                    self.cliente.enviar({"t": "empezar", "zona": ZONAS_DUELO[self.zona_i]})
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    for (tipo, v), r in self._rects.items():
                        if r.collidepoint(e.pos) and tipo == "zona":
                            self.zona_i = (self.zona_i + v) % len(ZONAS_DUELO)
                            self.app.sonar("click")
        elif self.estado == "resultado":
            todos = self.marcador and all(j["estado"] != "jugando" for j in self.marcador)
            if todos and self.btn_volver.toca(e):
                if self.cliente and self.cliente.id == self.anfitrion:
                    self.cliente.enviar({"t": "volver"})
                self.estado = "sala"

    def actualizar(self, dt):
        self.t += dt
        self._mensajes()
        if self.estado == "jugando" and self.juego:
            self.juego.actualizar(dt)
            self._envio -= dt
            if self._envio <= 0 and self.cliente and not self.terminado:
                n = self.juego.n
                self.cliente.enviar({"t": "puntos", "puntos": n.puntos, "salud": round(100 * n.salud / n.salud_max),
                                     "estado": "jugando"})
                self._envio = 0.5
        self.avisos = [a for a in self.avisos if self.t - a[1] < 4]

    # -------------------------------------------------------------- dibujo
    def dibujar(self, sup):
        E = Escala(sup)
        U = E.U
        self._rects = {}
        if self.estado == "jugando" and self.juego:
            self.juego.dibujar(sup)
            self._marcador(sup, E, U, en_juego=True)
            return
        for y in range(0, E.H, 4):
            pygame.draw.rect(sup, mezclar((40, 110, 220), (120, 90, 230), y / E.H), (0, y, E.W, 4))
        titulo_grande(sup, "Duelo en red", (E.W / 2, 70 * U), 56 * U)
        getattr(self, "_" + self.estado)(sup, E, U)
        self.btn_salir.dibujar(sup, E.r(1280 - 200, 24, 170, 54), self.t)
        for i, (txt, _) in enumerate(self.avisos):
            texto(sup, txt, (E.W / 2, E.H - 60 * U - i * 26 * U), 16 * U, BLANCO, 900)

    def _inicio(self, sup, E, U):
        texto(sup, "Cada uno en su computador, conectados a la misma red (el mismo wifi).", (E.W / 2, 124 * U), 18 * U,
              BLANCO, 800)
        w = 200
        x0 = 640 - (4 * w + 3 * 18) / 2
        for i, p in enumerate(PERSONAJES):
            r = E.r(x0 + i * (w + 18), 160, w, 240)
            sel = i == self.personaje
            panel(sup, r, BLANCO if sel else (230, 232, 246), round(22 * U), borde=p["color"] if sel else None, grosor=6)
            img = personajes.cuerpo(p["look"], p["rol"], "feliz" if sel else "neutral", round(150 * U))
            sup.blit(img, (r.centerx - img.get_width() / 2, r.y + 14 * U + (math.sin(self.t * 4) * 4 * U if sel else 0)))
            texto(sup, p["nombre"], (r.centerx, r.bottom - 50 * U), 22 * U, TINTA, 700, "titulo")
            texto(sup, p["titulo"], (r.centerx, r.bottom - 24 * U), 14 * U, TINTA2, 900)
            self._rects[("personaje", i)] = r
        r = panel(sup, E.r(160, 430, 440, 210), BLANCO, round(26 * U))
        texto(sup, "¿Eres el anfitrión?", (r.centerx, r.y + 40 * U), 22 * U, TINTA, 700, "titulo")
        parrafo(sup, "Crea la sala en este computador. Los demás se unen con tu IP.", r.x + 30 * U, r.y + 60 * U,
                r.w - 60 * U, 15 * U, TINTA2, centrado=True)
        self.btn_crear.dibujar(sup, pygame.Rect(r.x + 70 * U, r.bottom - 84 * U, r.w - 140 * U, 64 * U), self.t)
        r = panel(sup, E.r(680, 430, 440, 210), BLANCO, round(26 * U))
        texto(sup, "¿Te vas a unir?", (r.centerx, r.y + 40 * U), 22 * U, TINTA, 700, "titulo")
        caja = pygame.Rect(r.x + 40 * U, r.y + 66 * U, r.w - 80 * U, 50 * U)
        pygame.draw.rect(sup, (246, 247, 255), caja, border_radius=round(14 * U))
        pygame.draw.rect(sup, LILA if self.escribiendo_ip else (210, 212, 228), caja, max(2, round(3 * U)),
                         border_radius=round(14 * U))
        txt = self.ip + ("|" if self.escribiendo_ip and int(self.t * 2) % 2 == 0 else "")
        texto(sup, txt or "IP del anfitrión (ej. 192.168.1.20)", (caja.x + 16 * U, caja.centery), 18 * U,
              TINTA if self.ip else TINTA2, 800, ancla="midleft")
        self._rects[("ip", 0)] = caja
        self.btn_unirse.dibujar(sup, pygame.Rect(r.x + 70 * U, r.bottom - 84 * U, r.w - 140 * U, 64 * U), self.t)
        if self.error:
            texto(sup, self.error, (E.W / 2, 670 * U), 17 * U, (255, 220, 220), 900)

    def _sala(self, sup, E, U):
        soy_anfitrion = self.cliente and self.cliente.id == self.anfitrion
        if self.servidor:
            ip = " o ".join(ips_locales()[:2])
            r = panel(sup, E.r(340, 110, 600, 70), MANGO, round(22 * U))
            texto(sup, f"Los demás se unen con la IP:  {ip}", r.center, 22 * U, TINTA, 700, "titulo")
        y = 200
        texto(sup, f"En la sala ({len(self.sala)})", (E.x(340), E.y(y)), 22 * U, BLANCO, 700, "titulo", "midleft")
        for i, j in enumerate(self.sala):
            r = panel(sup, E.r(340, y + 24 + i * 76, 600, 66), BLANCO, round(20 * U), borde=tuple(j["color"]))
            av = personajes.avatar(j["look"], round(50 * U), tuple(j["color"]), j["rol"], "feliz")
            sup.blit(av, (r.x + 10 * U, r.y + 8 * U))
            texto(sup, j["nombre"], (r.x + 74 * U, r.centery), 22 * U, TINTA, 700, "titulo", "midleft")
            if j["id"] == self.anfitrion:
                texto(sup, "anfitrión", (r.right - 30 * U, r.centery), 15 * U, LILA, 900, ancla="midright")
        z = ZONAS_DUELO[self.zona_i]
        r = panel(sup, E.r(340, 540, 600, 80), BLANCO, round(22 * U))
        icono(sup, BARRIOS_JUEGO[z]["icono"], (r.x + 40 * U, r.centery), 34 * U, LILA, 2.6)
        texto(sup, f"Barrio: {nombre_zona(z)}", (r.x + 74 * U, r.y + 28 * U), 22 * U, TINTA, 700, "titulo", "midleft")
        texto(sup, BARRIOS_JUEGO[z]["titulo"], (r.x + 74 * U, r.y + 56 * U), 15 * U, TINTA2, 900, ancla="midleft")
        if soy_anfitrion:
            for v, x in ((-1, r.right - 110 * U), (1, r.right - 50 * U)):
                b = pygame.Rect(0, 0, 46 * U, 46 * U)
                b.center = (x, r.centery)
                pygame.draw.rect(sup, (236, 231, 255), b, border_radius=round(14 * U))
                icono(sup, "chevron-left" if v < 0 else "chevron-right", b.center, 26 * U, LILA, 3)
                self._rects[("zona", v)] = b
            self.btn_empezar.latir = len(self.sala) >= 1
            self.btn_empezar.dibujar(sup, E.r(440, 640, 400, 66), self.t)
        else:
            texto(sup, "Esperando a que el anfitrión empiece…", (E.W / 2, 670 * U), 20 * U, BLANCO, 900)

    def _resultado(self, sup, E, U):
        self._marcador(sup, E, U, en_juego=False)
        todos = self.marcador and all(j["estado"] != "jugando" for j in self.marcador)
        if todos:
            self.btn_volver.dibujar(sup, E.r(640 - 180, 640, 360, 64), self.t)
        else:
            texto(sup, "Esperando a que terminen los demás…", (E.W / 2, 670 * U), 20 * U, BLANCO, 900)

    def _marcador(self, sup, E, U, en_juego):
        lista = self.marcador or []
        if en_juego:
            x, y, w = E.W - 250 * U, 110 * U, 232 * U
            r = pygame.Rect(x, y, w, (46 + 50 * len(lista)) * U)
            pildora(sup, r, BLANCO, round(20 * U), alfa=225)
            texto(sup, "Marcador", (r.centerx, r.y + 22 * U), 17 * U, TINTA, 700, "titulo")
            for i, j in enumerate(lista):
                yy = r.y + 56 * U + i * 50 * U
                av = personajes.avatar(j["look"], round(36 * U), tuple(j["color"]), j["rol"], "feliz")
                sup.blit(av, (r.x + 10 * U, yy - 18 * U))
                texto(sup, f"{i + 1}. {j['nombre']}", (r.x + 54 * U, yy - 6 * U), 15 * U, TINTA, 900, ancla="midleft")
                texto(sup, f"{j['puntos']} pts", (r.x + 54 * U, yy + 12 * U), 13 * U, TINTA2, 800, ancla="midleft")
                if j["estado"] not in ("jugando", "sala"):
                    icono(sup, "flag", (r.right - 22 * U, yy), 18 * U, VERDE if j["estado"] == "ganado" else ROJO, 2.6)
            return
        texto(sup, "Resultado del duelo", (E.W / 2, 140 * U), 34 * U, BLANCO, 700, "titulo")
        for i, j in enumerate(lista):
            r = panel(sup, E.r(340, 180 + i * 96, 600, 84), BLANCO if i else (255, 244, 200), round(24 * U),
                      borde=tuple(j["color"]))
            texto(sup, f"{i + 1}°", (r.x + 40 * U, r.centery), 34 * U, LILA, 700, "titulo")
            av = personajes.avatar(j["look"], round(60 * U), tuple(j["color"]), j["rol"], "feliz" if i == 0 else "neutral")
            sup.blit(av, (r.x + 80 * U, r.y + 12 * U))
            texto(sup, j["nombre"], (r.x + 156 * U, r.y + 30 * U), 24 * U, TINTA, 700, "titulo", "midleft")
            estado = {"ganado": "salvó su barrio", "perdido": "perdió su barrio", "jugando": "todavía jugando…",
                      "salio": "se salió"}.get(j["estado"], "")
            texto(sup, estado, (r.x + 156 * U, r.y + 58 * U), 15 * U, TINTA2, 900, ancla="midleft")
            texto(sup, f"{j['puntos']:,}".replace(",", "."), (r.right - 30 * U, r.centery), 30 * U, TINTA, 700, "titulo",
                  "midright")
