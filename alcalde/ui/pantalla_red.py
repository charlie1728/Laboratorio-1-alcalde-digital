"""Jugar en red: crear una partida (servidor en este computador) o unirse a una."""
import random

import pygame

from ..controlador import ControladorRed
from ..modelo.apariencia import COLORES_JUGADOR, look_aleatorio
from ..modelo.roles import ROLES
from ..red.cliente import Cliente
from ..red.protocolo import PUERTO, ips_locales
from ..red.servidor import Servidor
from . import personajes, recursos
from .ayuda import ICONO_ROL
from .escena import Escena
from .pantalla_seleccion import DURACIONES
from .tarjeta_jugador import TarjetaJugador
from .tema import TEMA
from .widgets import Boton, chip, parrafo, recortar, sticker, texto, titulo


class PantallaRed:
    def __init__(self, app):
        self.app = app
        self.escena = Escena(semilla=9, gente=0, y_suelo=760)
        self.tarjeta = TarjetaJugador((36, 100, 290, 522), 0, COLORES_JUGADOR[0], "", "periodista",
                                      look_aleatorio(random.Random(), True))
        self.estado = "inicio"
        self.cliente = None
        self.servidor = None
        self.puerto = PUERTO
        self.ip = ""
        self.editando_ip = False
        self.error = ""
        self.lobby = []
        self.anfitrion = None
        self.duracion = 1
        self.btn_volver = Boton((36, 26, 52, 48), "", "volver", icono="arrow-left", sombra=3)
        self.btn_crear = Boton((380, 300, 380, 60), "Crear partida", "crear", icono="server", estilo="primario", tam=19)
        self.r_ip = pygame.Rect(820, 300, 230, 60)
        self.btn_unirse = Boton((1062, 300, 182, 60), "Unirse", "unirse", icono="link", estilo="primario", tam=19)
        self.btn_comenzar = Boton((900, 640, 344, 60), "Comenzar partida", "comenzar", icono="play",
                                  estilo="primario", tam=20)
        self.b_dur = [Boton((380 + i * 112, 648, 104, 46), n, i, tam=16, estilo="suave", sombra=3)
                      for i, (n, _) in enumerate(DURACIONES)]

    def escribiendo(self):
        return self.editando_ip or self.tarjeta.editando

    # ------------------------------------------------------------------ red
    def _perfil(self):
        d = self.tarjeta.perfil()
        d["nombre"] = self.tarjeta.nombre.strip()
        d["mas_tiempo"] = TEMA.op["mas_tiempo"]
        return d

    def _crear(self):
        self.error = ""
        for k in range(6):
            try:
                self.servidor = Servidor("0.0.0.0", PUERTO + k, registro=lambda *_: None).iniciar()
                self.puerto = PUERTO + k
                break
            except OSError:
                self.servidor = None
        if self.servidor is None:
            self.error = "No se pudo abrir el servidor en este computador (puertos 5050 a 5055 ocupados)."
            return
        self._conectar("127.0.0.1", self.puerto)

    def _conectar(self, host, puerto):
        try:
            self.cliente = Cliente(host, puerto)
        except OSError:
            self.error = (f"No se encontró una partida en {host}. Revisa la dirección y que estén en la misma red.")
            if self.servidor:
                self.servidor.detener()
                self.servidor = None
            return
        self.cliente.enviar(dict(t="hola", **self._perfil()))
        self.estado = "lobby"
        self.app.sonar("bueno")

    def _unirse(self):
        texto_ip = self.ip.strip() or "127.0.0.1"
        host, _, puerto = texto_ip.partition(":")
        try:
            puerto = int(puerto) if puerto else PUERTO
        except ValueError:
            self.error = "El puerto debe ser un número (por ejemplo 192.168.1.20:5050)."
            return
        self.error = ""
        self._conectar(host, puerto)

    def actualizar(self):
        if not self.cliente:
            return
        for m in self.cliente.recibir():
            t = m.get("t")
            if t == "lobby":
                self.lobby = m["jugadores"]
                self.anfitrion = m.get("anfitrion")
            elif t == "estado":
                ctrl = ControladorRed(self.cliente, m, self.servidor)
                self.cliente = None
                self.app.iniciar_red(ctrl, guia=TEMA.op["guia"])
                return
            elif t == "aviso":
                self.error = m.get("texto", "")
            elif t == "_cerrado":
                self.error = "Se cerró la conexión con la partida."
                self.estado = "inicio"
                self.cliente = None

    def cerrar(self):
        if self.cliente:
            self.cliente.cerrar()
        if self.servidor:
            self.servidor.detener()

    # ------------------------------------------------------------------ eventos
    def evento(self, e):
        if self.tarjeta.evento(e, self.app.sonar):
            if self.tarjeta.cambio and self.cliente:
                self.cliente.enviar(dict(t="perfil", **self._perfil()))
            self.editando_ip = False
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.editando_ip = False
            if self.btn_volver.clic(e.pos):
                self.cerrar()
                self.app.ir_menu()
            elif self.estado == "inicio":
                if self.btn_crear.clic(e.pos):
                    self._crear()
                elif self.r_ip.collidepoint(e.pos):
                    self.editando_ip = True
                elif self.btn_unirse.clic(e.pos):
                    self._unirse()
            elif self.estado == "lobby":
                if self.btn_comenzar.clic(e.pos):
                    self.cliente.enviar(dict(t="iniciar", rondas=DURACIONES[self.duracion][1]))
                    self.app.sonar("logro")
                for b in self.b_dur:
                    if b.clic(e.pos):
                        self.duracion = b.clave
        elif e.type == pygame.KEYDOWN and self.editando_ip:
            if e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.editando_ip = False
                self._unirse()
            elif e.key == pygame.K_ESCAPE:
                self.editando_ip = False
            elif e.key == pygame.K_BACKSPACE:
                self.ip = self.ip[:-1]
            elif e.unicode and (e.unicode.isalnum() or e.unicode in ".:-") and len(self.ip) < 30:
                self.ip += e.unicode
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.cerrar()
            self.app.ir_menu()

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, sup):
        c = TEMA.c
        self.escena.dibujar(sup, sol=False)
        self.btn_volver.dibujar(sup)
        titulo(sup, "Jugar en red", (106, 22), 38, c["texto"])
        texto(sup, "Cada jugador en su computador, conectados a la misma red wifi. Arma tu personaje a la izquierda.",
              (108, 70), 16, c["tinta2"], peso=700)
        self.tarjeta.dibujar(sup, etiqueta="Tu personaje")
        if self.estado == "inicio":
            self._inicio(sup)
        else:
            self._lobby(sup)
        if self.error:
            r = pygame.Rect(346, 588, 898, 44)
            sticker(sup, r, c["malo2"], 14, 3, 2)
            sup.blit(recursos.icono("triangle-alert", 20, c["malo"], 2.6), (r.x + 14, r.y + 12))
            texto(sup, recortar(self.error, 14, r.w - 60, 800), (r.x + 44, r.centery), 14, c["texto"], peso=800, ancla="ml")

    def _inicio(self, sup):
        c = TEMA.c
        izq = pygame.Rect(346, 110, 440, 460)
        der = pygame.Rect(804, 110, 440, 460)
        for r, ic, tit, desc in ((izq, "server", "Crear partida",
                                  "Este computador será el servidor: guarda la partida y le envía cada jugada a los demás. "
                                  "Tú también juegas desde aquí."),
                                 (der, "link", "Unirse a una partida",
                                  "Escribe la dirección que aparece en la pantalla de quien creó la partida.")):
            sticker(sup, r, c["papel"], 22, 6, 3)
            pygame.draw.circle(sup, c["acento2"], (r.x + 52, r.y + 56), 32)
            sup.blit(recursos.icono(ic, 32, c["acento"], 2.4), (r.x + 36, r.y + 40))
            titulo(sup, tit, (r.x + 100, r.y + 36), 26, c["texto"])
            parrafo(sup, desc, r.x + 30, r.y + 110, r.w - 60, 15, c["tinta2"], peso=700)
        self.btn_crear.rect.topleft = (izq.x + 30, izq.y + 200)
        self.btn_crear.dibujar(sup)
        parrafo(sup, "Se abre en el puerto 5050. Si Windows pregunta por el firewall, permite el acceso en redes "
                     "privadas.", izq.x + 30, izq.y + 280, izq.w - 60, 13, c["tenue"], peso=700)
        self.r_ip.topleft = (der.x + 30, der.y + 200)
        self.r_ip.w = 220
        sticker(sup, self.r_ip, c["acento2"] if self.editando_ip else c["papel2"], 14, 0, 3 if self.editando_ip else 2,
                color_borde=c["acento"] if self.editando_ip else c["borde"])
        cursor = "|" if self.editando_ip and (pygame.time.get_ticks() // 450) % 2 else ""
        if self.ip or self.editando_ip:
            texto(sup, self.ip + cursor, (self.r_ip.x + 14, self.r_ip.centery), 19, c["texto"], peso=800, ancla="ml")
        else:
            texto(sup, "192.168.1.20", (self.r_ip.x + 14, self.r_ip.centery), 18, c["tenue"], peso=700, ancla="ml")
        self.btn_unirse.rect.topleft = (self.r_ip.right + 12, der.y + 200)
        self.btn_unirse.rect.w = der.right - 30 - self.btn_unirse.rect.x
        self.btn_unirse.dibujar(sup)
        parrafo(sup, "Para probar en un solo computador, deja el campo vacío: se conecta a 127.0.0.1.",
                der.x + 30, der.y + 280, der.w - 60, 13, c["tenue"], peso=700)

    def _lobby(self, sup):
        c = TEMA.c
        r = pygame.Rect(346, 110, 898, 470)
        sticker(sup, r, c["papel"], 22, 6, 3)
        soy_anfitrion = self.cliente is not None and self.cliente.id == self.anfitrion
        titulo(sup, "Sala de espera", (r.x + 24, r.y + 18), 26, c["texto"])
        if self.servidor:
            ips = ", ".join(ips_locales())
            chip(sup, f"Los demás se unen con: {ips}" + (f":{self.puerto}" if self.puerto != PUERTO else ""),
                 (r.right - 20, r.y + 34), c["mango"], c["texto"], "wifi", 15, ancla="mr", alto=36)
        y = r.y + 76
        for i in range(4):
            fila = pygame.Rect(r.x + 20, y, r.w - 40, 86)
            if i < len(self.lobby):
                jj = self.lobby[i]
                sticker(sup, fila, c["papel2"], 18, 0, 2)
                col = tuple(jj["color"])
                pygame.draw.rect(sup, col, (fila.x + 2, fila.y + 2, 12, fila.h - 4), border_radius=6)
                img = personajes.avatar(jj.get("look") or {}, 66, col, jj["rol"], "feliz", borde=c["borde"])
                sup.blit(img, (fila.x + 26, fila.y + 10))
                yo = self.cliente is not None and jj["id"] == self.cliente.id
                texto(sup, jj["nombre"] + ("  (tú)" if yo else ""), (fila.x + 108, fila.y + 16), 20, c["texto"], peso=900)
                info = ROLES[jj["rol"]]
                chip(sup, info["nombre"], (fila.x + 108, fila.y + 48), c["mango2"], c["texto"], ICONO_ROL[jj["rol"]], 13)
                if jj["id"] == self.anfitrion:
                    chip(sup, "Anfitrión", (fila.right - 16, fila.centery), c["acento"], c["sobre_color"], "crown", 13,
                         ancla="mr")
            else:
                pygame.draw.rect(sup, c["papel2"], fila, border_radius=18)
                texto(sup, "Puesto libre: esperando a que alguien se una…", (fila.x + 26, fila.centery), 15,
                      c["tenue"], peso=800, ancla="ml")
            y += 96
        if soy_anfitrion:
            texto(sup, "Duración", (346, 671), 16, c["texto"], peso=800, ancla="ml")
            for b in self.b_dur:
                b.rect.x = 430 + b.clave * 112
                b.seleccionado = b.clave == self.duracion
                b.dibujar(sup)
            self.btn_comenzar.activo = 2 <= len(self.lobby) <= 4
            self.btn_comenzar.dibujar(sup)
            if len(self.lobby) < 2:
                texto(sup, "Se necesitan al menos 2 jugadores.", (self.btn_comenzar.rect.centerx, 626), 13, c["tinta2"],
                      peso=800, ancla="c")
        else:
            r2 = pygame.Rect(346, 640, 898, 60)
            sticker(sup, r2, c["papel"], 18, 4, 3)
            sup.blit(recursos.icono("hourglass", 24, c["acento"], 2.4), (r2.x + 18, r2.y + 18))
            texto(sup, "Esperando a que el anfitrión comience la partida…", (r2.x + 54, r2.centery), 17, c["texto"],
                  peso=800, ancla="ml")
