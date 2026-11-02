"""La pantalla de juego en vivo: controles, dibujo de la ciudad que se mueve, efectos y barra de información."""
from __future__ import annotations

import math
import random

import pygame

from ..modelo.mapa import ZONAS, nombre_zona
from ..modelo.roles import ROLES
from ..ui import personajes
from . import geometria as geo
from .dibujo import (AZUL, BLANCO, COLOR_TIPO, GRIS, LILA, LILA2, MANGO, ROJO, TINTA, TINTA2, VERDE, anillo,
                     ancho_texto, bezier, circulo, curva, icono, mezclar, oscuro, pildora, rebote, sombra, suave,
                     tecla, texto)
from .escenario import Escenario
from .mundo import PODERES, Mundo

# ------------------------------------------------------------------ controles
K = pygame
PERFILES = [
    dict(nombre="Teclado izquierdo", arriba=[K.K_w], abajo=[K.K_s], izq=[K.K_a], der=[K.K_d],
         escanear=[K.K_e], reportar=[K.K_r], compartir=[K.K_f], poder=[K.K_q],
         etiquetas=dict(mover="WASD", escanear="E", reportar="R", compartir="F", poder="Q")),
    dict(nombre="Teclado derecho", arriba=[K.K_UP], abajo=[K.K_DOWN], izq=[K.K_LEFT], der=[K.K_RIGHT],
         escanear=[K.K_COMMA, K.K_KP1, K.K_k], reportar=[K.K_PERIOD, K.K_KP2, K.K_l],
         compartir=[K.K_MINUS, K.K_SLASH, K.K_KP3, K.K_j], poder=[K.K_RSHIFT, K.K_KP0, K.K_i],
         etiquetas=dict(mover="Flechas", escanear=",", reportar=".", compartir="-", poder="Shift")),
]
MANDO = dict(etiquetas=dict(mover="Palanca", escanear="A", reportar="B", compartir="X", poder="Y"))

COLORES_JUGADOR = [(255, 194, 61), (96, 190, 255), (255, 120, 170), (120, 220, 140)]
ICONO_EVENTO = {"falsa": "message-square-warning", "candidato": "megaphone", "verdad": "badge-check",
                "viral": "flame", "discusion": "angry", "campana": "heart-handshake", "reporte": "flag",
                "bot": "bot"}
COLOR_EVENTO = {"falsa": ROJO, "candidato": (196, 64, 150), "verdad": AZUL, "viral": (255, 90, 40),
                "discusion": (214, 120, 0), "campana": VERDE, "reporte": VERDE, "bot": (90, 96, 130)}
SONIDO_EVENTO = {"viral": "viral", "bot": "malo"}
ICONO_IND = [("info_verificada", "badge-check", "Info verificada", True), ("confianza", "handshake", "Confianza", True),
             ("convivencia", "heart-handshake", "Convivencia", True), ("bienestar", "smile", "Bienestar", True),
             ("desinformacion", "message-square-warning", "Desinformación", False),
             ("conflictos", "angry", "Conflictos", False)]


class PantallaJuego:
    def __init__(self, app, config, semilla=None, dia_seg=None, demo=False):
        self.app = app
        self.demo = demo
        self.config = config
        kw = {} if dia_seg is None else dict(dia_seg=dia_seg)
        self.m = Mundo(config, semilla=semilla, **kw)
        for i, j in enumerate(self.m.jugadores):
            j.color = COLORES_JUGADOR[i % 4]
        self.t = 0.0
        self.esc = None
        self.tam = None
        self.efectos = []
        self.banners = []
        self.avisos = []           # mensajes cortos que se van apagando
        self.temblor = 0.0
        self.ver_red = False
        self.pausa = False
        self.mandos = {}
        self._lpx = 0
        self._sprites = {}
        self.estado_previo = self.m.estado
        self._noche_t = 0.0
        self.consejos = []                  # globos de ayuda sobre la cabeza de un jugador
        self.dichos = set()                 # (jugador, consejo) ya mostrados
        self._joy_init()

    # -------------------------------------------------------------- utilidades
    def _joy_init(self):
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                js = pygame.joystick.Joystick(i)
                js.init()
                self.mandos[js.get_instance_id()] = js
        except pygame.error:
            pass

    def perfil(self, idx):
        """Qué controla a cada jugador: los dos primeros, el teclado; el resto, mandos."""
        if idx < len(PERFILES):
            return PERFILES[idx]
        return MANDO

    def mando_de(self, idx):
        lista = list(self.mandos.values())
        k = idx - len(PERFILES)
        return lista[k] if 0 <= k < len(lista) else None

    def _preparar(self, sup):
        tam = sup.get_size()
        if tam != self.tam:
            self.tam = tam
            self.U = tam[1] / 720
            self.esc = Escenario(tam[0], tam[1], round(86 * self.U), round(18 * self.U))
            self._sprites.clear()

    def a_pantalla(self, x, y, z=0.0):
        sx, sy = self.esc.pr.p(x, y, z)
        return sx + self._sx, sy + self._sy

    def alto_persona(self, jugador=False):
        return self.esc.pr.tw * (0.74 if jugador else 0.6)

    def sprite(self, look, rol, expresion, alto, voltear, bot=False):
        clave = (repr(sorted(look.items())) if look else "bot", rol, expresion, round(alto), voltear, bot)
        img = self._sprites.get(clave)
        if img is None:
            img = personajes.cuerpo(look or {}, rol, expresion, round(alto), bot=bot)
            if voltear:
                img = pygame.transform.flip(img, True, False)
            if len(self._sprites) > 600:
                self._sprites.clear()
            self._sprites[clave] = img
        return img

    def cabeza(self, nombre):
        pos = self.m.pos(nombre)
        if pos is None:
            return None
        sx, sy = self.a_pantalla(*pos)
        es_j = self.m.jugador(nombre) is not None
        return sx, sy - self.alto_persona(es_j) * 0.92

    # -------------------------------------------------------------- entrada
    def evento(self, e):
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.pausa = not self.pausa
                return
            if self.pausa:
                if e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.pausa = False
                elif e.key == pygame.K_x:
                    self.app.ir_menu()
                return
            if e.key == pygame.K_TAB:
                self.ver_red = not self.ver_red
                return
            if self.m.estado == "noche" and self._noche_t > 1.2 and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.m.siguiente_dia()
                return
            if self.m.estado == "eleccion" and self._noche_t > 2.0 and e.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.app.ir_menu()
                return
            for idx in range(len(self.m.jugadores)):
                p = self.perfil(idx)
                for que in ("reportar", "compartir", "poder"):
                    if e.key in p.get(que, []):
                        self._accion(idx, que)
                        return
                if self.m.estado == "noche" and self._noche_t > 1.2 and any(
                        e.key in p.get(q, []) for q in ("escanear", "reportar", "compartir", "poder")):
                    self.m.siguiente_dia()
                    return
        elif e.type == pygame.JOYDEVICEADDED:
            js = pygame.joystick.Joystick(e.device_index)
            js.init()
            self.mandos[js.get_instance_id()] = js
        elif e.type == pygame.JOYDEVICEREMOVED:
            self.mandos.pop(e.instance_id, None)
        elif e.type == pygame.JOYBUTTONDOWN:
            lista = list(self.mandos)
            if e.instance_id in lista:
                idx = len(PERFILES) + lista.index(e.instance_id)
                if self.m.estado == "noche" and self._noche_t > 1.2:
                    self.m.siguiente_dia()
                    return
                que = {1: "reportar", 2: "compartir", 3: "poder"}.get(e.button)
                if que and idx < len(self.m.jugadores):
                    self._accion(idx, que)
                if e.button == 7:
                    self.pausa = not self.pausa

    def _accion(self, idx, que):
        if self.m.estado == "jugando" and not self.pausa:
            self.m.accion(idx, que)

    def _leer_entrada(self):
        teclas = pygame.key.get_pressed()
        for idx, j in enumerate(self.m.jugadores):
            p = self.perfil(idx)
            dx = dy = 0.0
            esc = False
            if idx < len(PERFILES):
                sx = sum(teclas[k] for k in p["der"]) - sum(teclas[k] for k in p["izq"])
                sy = sum(teclas[k] for k in p["abajo"]) - sum(teclas[k] for k in p["arriba"])
                esc = any(teclas[k] for k in p["escanear"])
            else:
                js = self.mando_de(idx)
                sx = sy = 0.0
                if js is not None:
                    ax, ay = js.get_axis(0), js.get_axis(1)
                    sx = ax if abs(ax) > 0.3 else 0.0
                    sy = ay if abs(ay) > 0.3 else 0.0
                    if js.get_numhats():
                        hx, hy = js.get_hat(0)
                        sx, sy = sx or hx, sy or -hy
                    esc = bool(js.get_numbuttons() and js.get_button(0))
            # De la pantalla al mundo isométrico: derecha = (1, -1), abajo = (1, 1).
            dx, dy = (sx + sy) / math.sqrt(2), (sy - sx) / math.sqrt(2)
            j.entrada = dict(dx=dx, dy=dy, escanear=esc)

    # -------------------------------------------------------------- bucle
    def actualizar(self, dt):
        self.t += dt
        if self.pausa:
            return
        if self.m.estado == "jugando":
            self._leer_entrada()
            if self.demo:
                self.m.reloj = 0.0
            self.m.actualizar(dt)
        else:
            self._noche_t += dt
        if self.m.estado != self.estado_previo:
            self._noche_t = 0.0
            if self.m.estado in ("noche", "eleccion"):
                self.app.sonar("noche" if self.m.estado == "noche" else "victoria")
            self.estado_previo = self.m.estado
        if self.m.estado == "jugando":
            self._consejos_por_estado()
        for fx in self.m.fx:
            self._efecto(fx)
        self.m.fx.clear()
        while self._lpx < len(self.m.log_items):
            self.avisos.append(dict(self.m.log_items[self._lpx], t0=self.t))
            self._lpx += 1
        if len(self.m.log_items) >= 30:
            self._lpx = len(self.m.log_items)
        self.avisos = [a for a in self.avisos if self.t - a["t0"] < 6.5][-4:]
        self.temblor = max(0.0, self.temblor - dt * 2.5)

    def consejo(self, idx, clave, txt, dur=4.5):
        if self.demo or (idx, clave) in self.dichos:
            return
        self.dichos.add((idx, clave))
        self.consejos = [c for c in self.consejos if c["jugador"] != idx]
        self.consejos.append(dict(jugador=idx, texto=txt, t0=self.t, dur=dur))

    def _consejos_por_estado(self):
        for j in self.m.jugadores:
            et = self.perfil(j.idx)["etiquetas"]
            if self.m.tiempo > 1.0:
                self.consejo(j.idx, "correr", "¡Corre hasta una burbuja con ?!", 5)
            if j.objetivo:
                p = self.m.portadores.get(j.objetivo)
                n = self.m.nodo(p.caso, p.nodo) if p else None
                if n is not None and not n.verificado:
                    self.consejo(j.idx, "escanear", f"Mantén {et['escanear']} para escanearla")
            if j.recarga <= 0 and self.m.tiempo > 25:
                self.consejo(j.idx, "poder", f"¡Tu poder está listo! Pulsa {et['poder']}")

    def _efecto(self, fx):
        tipo = fx["t_"]
        if tipo == "escaneo" and fx.get("jugador") is not None:
            et = self.perfil(fx["jugador"])["etiquetas"]
            if fx["falso"]:
                self.consejo(fx["jugador"], "reportar", f"¡Es mentira! Repórtala con {et['reportar']}")
            else:
                self.consejo(fx["jugador"], "compartir", f"Es verdad: compártela con {et['compartir']}")
        e = dict(fx, t0=self.t)
        sonido = {"escaneo": "sello", "poda": "rama", "logro": "logro", "rechazo": "malo", "estallido": "malo",
                  "bot_fuera": "pop", "ondas": "bueno", "alerta": "bueno", "discurso": "votos",
                  "discusion": "evento", "rastreo": "rama", "recargando": "tick", "nada": "tick"}.get(tipo)
        if tipo == "compartir":
            sonido = "malo" if fx.get("falso") else "bueno"
        if tipo == "evento":
            sonido = SONIDO_EVENTO.get(fx["tipo"], "evento")
            self.banners.append(e)
            self.banners = self.banners[-2:]
        elif tipo == "logro":
            self.banners.append(dict(e, tipo="logro", titulo="¡Logro!", texto=fx["nombre"]))
        elif tipo == "estallido":
            self.temblor = 1.0
        if sonido and not self.demo:
            self.app.sonar(sonido)
        if tipo != "evento":
            self.efectos.append(e)

    # -------------------------------------------------------------- dibujo
    def dibujar(self, sup):
        self._preparar(sup)
        U = self.U
        self._sx = self._sy = 0.0
        if self.temblor > 0 and not self.app.menos_movimiento:
            self._sx = random.uniform(-1, 1) * 9 * U * self.temblor
            self._sy = random.uniform(-1, 1) * 6 * U * self.temblor
        sup.blit(self.esc.suelo, (round(self._sx), round(self._sy)))
        self._sombras_nubes(sup)
        if self.ver_red:
            self._red(sup)
        self._objetivos(sup)
        self._flechas(sup)
        self._entidades(sup)
        self._paquetes(sup)
        self._burbujas(sup)
        self._efectos(sup)
        self._globos_consejo(sup)
        if self.demo:
            return
        self._tinte(sup)
        self._hud(sup)
        self._banners(sup)
        if self.m.estado == "noche":
            self._noche(sup)
        elif self.m.estado == "eleccion":
            self._eleccion(sup)
        if self.pausa:
            self._pausa(sup)

    def _sombras_nubes(self, sup):
        """Sombras de nubes que pasan despacio por encima de la isla."""
        if self.app.menos_movimiento:
            return
        w, h = sup.get_size()
        for k, (vel, y0, tam) in enumerate(((0.012, 0.35, 1.0), (0.008, 0.62, 0.8), (0.015, 0.2, 0.7))):
            x = ((self.t * vel + k * 0.37) % 1.4 - 0.2) * w
            y = y0 * h
            s = self._sombra_nube(round(260 * self.U * tam))
            sup.blit(s, (round(x - s.get_width() / 2), round(y - s.get_height() / 2)))

    def _sombra_nube(self, ancho):
        clave = ("nube", ancho)
        if clave not in self._sprites:
            s = pygame.Surface((ancho, ancho // 2), pygame.SRCALPHA)
            for dx, dy, r in ((0.3, 0.55, 0.18), (0.5, 0.45, 0.24), (0.7, 0.55, 0.17)):
                pygame.draw.circle(s, (20, 40, 60, 40), (round(dx * ancho), round(dy * ancho / 2)), round(r * ancho))
            w, h = s.get_size()
            s = pygame.transform.smoothscale(pygame.transform.smoothscale(s, (w // 8, h // 8)), (w, h))
            self._sprites[clave] = s
        return self._sprites[clave]

    def _red(self, sup):
        """Tab: se ve la red social completa (cada línea es alguien que sigue a alguien)."""
        U = self.U
        for u, v, a in self.m.red.aristas():
            pa, pb = self.cabeza(u), self.cabeza(v)
            if pa is None or pb is None:
                continue
            col = (255, 255, 255)
            curva(sup, pa, pb, 26 * U, col, max(1, round(1.5 * U * (0.5 + a["peso"]))), alfa=round(60 + 110 * a["peso"]))

    def _objetivos(self, sup):
        """Debajo del vecino al que apunta cada jugador: un aro de su color y las líneas a sus seguidores."""
        U = self.U
        for j in self.m.jugadores:
            v = j.objetivo
            if not v or v not in self.m.vecinos:
                continue
            x, y = self.a_pantalla(self.m.vecinos[v].x, self.m.vecinos[v].y)
            r = pygame.Rect(0, 0, 70 * U, 30 * U)
            r.center = (round(x), round(y))
            pygame.draw.ellipse(sup, j.color, r, max(2, round(4 * U)))
            cab = self.cabeza(v)
            for w in self.m.red.vecinos(v):
                pb = self.cabeza(w)
                if pb is not None:
                    curva(sup, cab, pb, 40 * U, BLANCO, max(1, round(2 * U)), alfa=110)

    def _flechas(self, sup):
        """Si un jugador no está junto a nadie, una flecha en el piso le señala la burbuja más cercana."""
        U = self.U
        for j in self.m.jugadores:
            if j.objetivo or not self.m.portadores:
                continue
            cerca = [v for v in self.m.portadores if v in self.m.vecinos]
            if not cerca:
                continue
            v = min(cerca, key=lambda v: math.hypot(self.m.vecinos[v].x - j.x, self.m.vecinos[v].y - j.y))
            x, y = self.a_pantalla(j.x, j.y)
            tx, ty = self.a_pantalla(self.m.vecinos[v].x, self.m.vecinos[v].y)
            ang = math.atan2(ty - y, tx - x)
            r = 48 * U
            px, py = x + math.cos(ang) * r, y + math.sin(ang) * r * 0.55
            a1, a2 = ang + 2.5, ang - 2.5
            pts = [(px + math.cos(ang) * 16 * U, py + math.sin(ang) * 9 * U),
                   (px + math.cos(a1) * 12 * U, py + math.sin(a1) * 7 * U),
                   (px + math.cos(a2) * 12 * U, py + math.sin(a2) * 7 * U)]
            pygame.draw.polygon(sup, j.color, pts)
            pygame.draw.polygon(sup, oscuro(j.color, 0.7), pts, max(1, round(2 * U)))

    def _globos_consejo(self, sup):
        U = self.U
        vivos = []
        for c in self.consejos:
            edad = self.t - c["t0"]
            if edad > c["dur"] or c["jugador"] >= len(self.m.jugadores):
                continue
            vivos.append(c)
            j = self.m.jugadores[c["jugador"]]
            x, y = self.a_pantalla(j.x, j.y)
            y -= self.alto_persona(True) + 72 * U + math.sin(self.t * 4) * 3 * U
            k = rebote(min(1, edad / 0.3))
            alfa = round(255 * min(1, (c["dur"] - edad) / 0.4))
            w = (ancho_texto(c["texto"], 16 * U, 900) + 34 * U) * k
            h = 40 * U * k
            r = pygame.Rect(0, 0, w, h)
            r.center = (round(x), round(y))
            sombra(sup, r, round(h / 2))
            pygame.draw.polygon(sup, BLANCO, [(x - 9 * U, r.bottom - 2), (x + 9 * U, r.bottom - 2), (x, r.bottom + 12 * U * k)])
            pygame.draw.rect(sup, BLANCO, r, border_radius=round(h / 2))
            pygame.draw.rect(sup, j.color, r, max(2, round(3 * U)), border_radius=round(h / 2))
            if k > 0.7:
                texto(sup, c["texto"], r.center, 16 * U, TINTA, 900, alfa=alfa)
        self.consejos = vivos

    def _estado_visible(self, v):
        """Qué se le nota a un vecino. Lo falso solo se ve como falso cuando alguien ya lo descubrió."""
        ve = self.m.vecinos.get(v)
        if ve and ve.enojo > 0:
            return "pelea"
        hay = None
        for c in self.m.casos:
            e = c.creencia.get(v)
            if e == "falso":
                return "falso" if c.revelado else "oculto"
            if e in ("corregido", "veraz") and hay is None:
                hay = e
            elif e == "duda" and hay is None:
                hay = "duda"
        return hay or "nada"

    def _entidades(self, sup):
        U = self.U
        cosas = [(p.clave, 0, p) for p in self.esc.piezas]
        for v, ve in self.m.vecinos.items():
            cosas.append((self.esc.clave_personaje(ve.x, ve.y), 1, ve))
        for j in self.m.jugadores:
            cosas.append((self.esc.clave_personaje(j.x, j.y), 2, j))
        cosas.sort(key=lambda c: c[0])
        for _, tipo, obj in cosas:
            if tipo == 0:
                sup.blit(obj.img, (obj.pos[0] + round(self._sx), obj.pos[1] + round(self._sy)))
            elif tipo == 1:
                self._vecino(sup, obj)
            else:
                self._jugador(sup, obj)

    def _sombra_pies(self, sup, x, y, ancho):
        clave = ("pies", round(ancho))
        if clave not in self._sprites:
            w = round(ancho)
            s = pygame.Surface((w * 2, w), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (20, 30, 40, 90), (w * 0.5, w * 0.3, w, w * 0.4))
            s = pygame.transform.smoothscale(pygame.transform.smoothscale(s, (max(1, w // 3), max(1, w // 6))), (w * 2, w))
            self._sprites[clave] = s
        s = self._sprites[clave]
        sup.blit(s, (round(x - s.get_width() / 2), round(y - s.get_height() / 2)))

    def _vecino(self, sup, ve):
        U = self.U
        d = self.m.red.dato(ve.nombre) if ve.nombre in self.m.red else None
        if d is None:
            return
        x, y = self.a_pantalla(ve.x, ve.y)
        alto = self.alto_persona()
        estado = self._estado_visible(ve.nombre)
        exp = {"falso": "enojado", "pelea": "enojado", "oculto": "sorprendido", "duda": "confundido",
               "corregido": "feliz", "veraz": "feliz"}.get(estado, "neutral")
        if ve.destello and ve.destello[0] in ("cree", "duda"):
            exp = "sorprendido"
        self._sombra_pies(sup, x, y, alto * 0.55)
        aro = {"falso": ROJO, "pelea": ROJO, "corregido": VERDE, "veraz": AZUL, "oculto": LILA}.get(estado)
        if aro:
            r = pygame.Rect(0, 0, alto * 0.62, alto * 0.24)
            r.center = (round(x), round(y))
            pygame.draw.ellipse(sup, aro, r, max(2, round(3 * U)))
        if ve.nombre in self.m.prevenidos:
            r = pygame.Rect(0, 0, alto * 0.8, alto * 0.3)
            r.center = (round(x), round(y))
            pygame.draw.ellipse(sup, (120, 220, 200), r, max(1, round(2 * U)))
        bote = abs(math.sin(ve.paso)) * alto * 0.06 if ve.moviendo else math.sin(self.t * 2 + hash(ve.nombre) % 7) * alto * 0.012
        img = self.sprite(d.look, "npc", exp, alto, ve.dir < 0, bot=d.bot)
        sup.blit(img, (round(x - img.get_width() / 2), round(y - img.get_height() - bote + 3 * U)))
        if ve.enojo > 0:
            cx, cy = x + alto * 0.3, y - alto * 1.05
            pildora(sup, (cx - 22 * U, cy - 12 * U, 44 * U, 24 * U), BLANCO, con_sombra=False)
            texto(sup, "#@!", (cx, cy), 14 * U, ROJO, 900)
        if d.bot:
            texto(sup, ve.nombre, (x, y + 12 * U), 12 * U, TINTA, 900)
        if ve.destello:
            tipo, resto = ve.destello
            k = 1 - resto / 0.8
            col = {"corrige": VERDE, "escudo": (120, 220, 200), "veraz": AZUL, "cree": ROJO, "duda": GRIS}[tipo]
            anillo(sup, (x, y - alto * 0.45), alto * (0.35 + 0.5 * k), col, 4 * U, alfa=round(255 * (1 - k)))
            if tipo in ("corrige", "escudo"):
                icono(sup, "check" if tipo == "corrige" else "shield", (x, y - alto * 1.25 - 10 * U * k), 22 * U, col, 3)

    def _jugador(self, sup, j):
        U = self.U
        x, y = self.a_pantalla(j.x, j.y)
        alto = self.alto_persona(True)
        self._sombra_pies(sup, x, y, alto * 0.6)
        r = pygame.Rect(0, 0, alto * 0.78, alto * 0.3)
        r.center = (round(x), round(y))
        pygame.draw.ellipse(sup, j.color, r, max(3, round(5 * U)))
        bote = abs(math.sin(j.paso)) * alto * 0.07 if j.moviendo else math.sin(self.t * 2.5 + j.idx) * alto * 0.012
        exp = "feliz" if j.recarga > PODERES[j.rol]["recarga"] - 1.5 else "neutral"
        img = self.sprite(j.look, j.rol, exp, alto, j.dir < 0)
        sup.blit(img, (round(x - img.get_width() / 2), round(y - img.get_height() - bote + 3 * U)))
        # nombre
        ty = y - alto - 26 * U
        w = ancho_texto(j.nombre, 15 * U, 900, "titulo") + 22 * U
        pildora(sup, (x - w / 2, ty - 13 * U, w, 26 * U), j.color, con_sombra=False)
        texto(sup, j.nombre, (x, ty), 15 * U, TINTA, 700, "titulo")
        pygame.draw.polygon(sup, j.color, [(x - 7 * U, ty + 12 * U), (x + 7 * U, ty + 12 * U), (x, ty + 20 * U)])

    def _paquetes(self, sup):
        """Publicaciones viajando por la red social: un punto que salta de una cabeza a otra."""
        U = self.U
        for pq in self.m.paquetes:
            a, b = self.cabeza(pq.de), self.cabeza(pq.a)
            if a is None or b is None:
                continue
            nodo = self.m.nodo(pq.caso, pq.nodo)
            if nodo is None:
                continue
            tipo = "correccion" if nodo.es_correccion else ("veraz" if nodo.es_veraz else "falso") \
                if nodo.verificado or pq.jugador is not None else "oculto"
            col = COLOR_TIPO[tipo]
            alto = 50 * U
            k = suave(pq.t / pq.dur)
            curva(sup, a, b, alto, col, 2 * U, alfa=90)
            for i in range(4, 0, -1):
                px, py = bezier(a, b, alto, max(0.0, k - i * 0.05))
                circulo(sup, (px, py), (7 - i) * U, col, alfa=round(200 - i * 40))
            px, py = bezier(a, b, alto, k)
            circulo(sup, (px, py), 9 * U, BLANCO)
            circulo(sup, (px, py), 7 * U, col)

    def _burbujas(self, sup):
        """Encima de quien tiene una publicación: una burbuja que late y un reloj de cuándo la va a mandar."""
        U = self.U
        for v, p in self.m.portadores.items():
            cab = self.cabeza(v)
            nodo = self.m.nodo(p.caso, p.nodo)
            if cab is None or nodo is None:
                continue
            x, y = cab
            alcance = self.m.red.grado_salida(v) if v in self.m.red else 0
            tam = (17 + min(12, alcance * 1.2)) * U * (1.7 if p.viral else 1.0)
            urg = 1 - p.falta / p.total
            lat = 1 + math.sin(self.t * (6 + urg * 14)) * 0.06 * (0.5 + urg)
            r = tam * lat
            cy = y - r - 16 * U
            if nodo.verificado:
                tipo = "correccion" if nodo.es_correccion else ("veraz" if nodo.es_veraz else "falso")
            else:
                tipo = "oculto"
            col = (255, 90, 40) if p.viral else COLOR_TIPO[tipo]
            if p.viral:
                circulo(sup, (x, cy), r * (1.6 + 0.2 * math.sin(self.t * 10)), col, alfa=70)
            pygame.draw.polygon(sup, col, [(x - 8 * U, cy + r - 5 * U), (x + 8 * U, cy + r - 5 * U), (x, cy + r + 12 * U)])
            circulo(sup, (x, cy), r + 3 * U, BLANCO)
            circulo(sup, (x, cy), r, col)
            anillo(sup, (x, cy), r + 7 * U, oscuro(col, 0.8), 4 * U, 1 - urg)
            signo = {"oculto": "?", "falso": "!", "veraz": "i", "correccion": "✓"}[tipo]
            if p.viral:
                texto(sup, str(max(0, math.ceil(p.falta))), (x, cy + 2 * U), r * 1.1, BLANCO, 700, "titulo")
                icono(sup, "flame", (x, cy - r - 14 * U), 26 * U, (255, 90, 40), 3)
            elif signo == "✓":
                icono(sup, "check", (x, cy), r * 1.1, BLANCO, 3.5)
            else:
                texto(sup, signo, (x, cy + 2 * U), r * 1.25, BLANCO, 700, "titulo")
            if alcance and not p.viral:
                pildora(sup, (x + r * 0.5, cy - r - 6 * U, 34 * U, 20 * U), BLANCO, con_sombra=False)
                icono(sup, "users", (x + r * 0.5 + 10 * U, cy - r + 4 * U), 13 * U, TINTA2, 2.4)
                texto(sup, alcance, (x + r * 0.5 + 24 * U, cy - r + 4 * U), 12 * U, TINTA, 900)
        # Barras de escaneo y teclas de ayuda sobre cada jugador.
        for j in self.m.jugadores:
            if not j.objetivo or j.objetivo not in self.m.portadores:
                continue
            cab = self.cabeza(j.objetivo)
            if cab is None:
                continue
            if j.escaneo > 0:
                x, y = cab
                anillo(sup, (x, y - 30 * U), 34 * U, j.color, 7 * U, j.escaneo)
                icono(sup, "search", (x + 30 * U, y - 60 * U), 28 * U, j.color, 3.2)
            self._ayuda_teclas(sup, j)

    def _ayuda_teclas(self, sup, j):
        U = self.U
        p = self.perfil(j.idx)["etiquetas"]
        port = self.m.portadores.get(j.objetivo)
        nodo = self.m.nodo(port.caso, port.nodo) if port else None
        x, y = self.a_pantalla(j.x, j.y)
        y += 18 * U
        items = []
        if nodo is not None and not nodo.verificado:
            items.append((p["escanear"], "Escanear"))
        items += [(p["reportar"], "Reportar"), (p["compartir"], "Compartir")]
        ancho = sum(ancho_texto(t, 12 * U, 900) + 38 * U for _, t in items) + 8 * U
        r = pildora(sup, (x - ancho / 2, y, ancho, 28 * U), j.color, alfa=235, con_sombra=False)
        cx = r.x + 8 * U
        for k, t in items:
            kr = tecla(sup, k, (cx + 11 * U, r.centery), 20 * U)
            texto(sup, t, (kr.right + 4 * U, r.centery), 12 * U, TINTA, 900, ancla="midleft")
            cx += ancho_texto(t, 12 * U, 900) + 38 * U

    # -------------------------------------------------------------- efectos
    def _efectos(self, sup):
        U = self.U
        vivos = []
        for e in self.efectos:
            edad = self.t - e["t0"]
            dur = {"escaneo": 3.0, "poda": 1.6, "rastreo": 2.6, "ondas": 1.6, "alerta": 1.4, "discurso": 1.8,
                   "discusion": 2.0, "estallido": 1.2, "bot_fuera": 1.0, "compartir": 1.0, "rechazo": 1.4,
                   "recargando": 0.6, "nada": 0.5, "nuevo": 0.8, "logro": 0.1}.get(e["t_"], 1.0)
            if edad > dur:
                continue
            vivos.append(e)
            k = edad / dur
            getattr(self, "_fx_" + e["t_"], lambda *a: None)(sup, e, edad, k)
        self.efectos = vivos

    def _jpos(self, idx):
        j = self.m.jugadores[idx]
        return self.a_pantalla(j.x, j.y)

    def _fx_escaneo(self, sup, e, edad, k):
        cab = self.cabeza(e["quien"])
        if cab is None:
            return
        U = self.U
        x, y = cab
        s = rebote(min(1, edad / 0.35)) * (1 - max(0, k - 0.8) * 5)
        if s <= 0:
            return
        falso = e["falso"]
        col = ROJO if falso else AZUL
        txt = "¡FALSO!" if falso else "¡VERDAD!"
        w, h = (ancho_texto(txt, 26 * U, 700, "titulo") + 30 * U) * s, 46 * U * s
        r = pygame.Rect(0, 0, w, h)
        r.center = (round(x), round(y - 90 * U))
        pygame.draw.rect(sup, BLANCO, r.inflate(8 * U, 8 * U), border_radius=round(12 * U))
        pygame.draw.rect(sup, col, r, border_radius=round(10 * U))
        if s > 0.6:
            texto(sup, txt, r.center, 26 * U * s, BLANCO, 700, "titulo")
        trucos = e.get("trucos") or []
        if trucos and s > 0.9:
            linea = "Truco: " + " · ".join(trucos)
            w2 = ancho_texto(linea, 14 * U, 900) + 26 * U
            r2 = pygame.Rect(0, 0, w2, 28 * U)
            r2.midtop = (r.centerx, r.bottom + 8 * U)
            pygame.draw.rect(sup, BLANCO, r2, border_radius=round(14 * U))
            pygame.draw.rect(sup, ROJO, r2, max(1, round(2 * U)), border_radius=round(14 * U))
            texto(sup, linea, r2.center, 14 * U, ROJO, 900)

    def _fx_poda(self, sup, e, edad, k):
        U = self.U
        autores = e.get("autores") or []
        for i, a in enumerate(autores):
            t = edad - i * 0.08
            if t < 0 or t > 0.9:
                continue
            cab = self.cabeza(a)
            if cab is None:
                continue
            kk = t / 0.9
            anillo(sup, cab, (20 + 50 * kk) * U, VERDE, 6 * U * (1 - kk) + 1, alfa=round(255 * (1 - kk)))
            icono(sup, "check", (cab[0], cab[1] - 30 * U - 20 * U * kk), 30 * U, VERDE, 3.5)
        cab = self.cabeza(e["quien"]) if e.get("quien") else None
        if cab and edad < 0.8:
            texto(sup, f"−{len(autores)}", (cab[0], cab[1] - 70 * U - 30 * U * k), 30 * U, VERDE, 700, "titulo")

    def _fx_rastreo(self, sup, e, edad, k):
        U = self.U
        ruta = [self.cabeza(n) for n in e["ruta"]]
        ruta = [p for p in ruta if p is not None]
        if len(ruta) < 2:
            return
        prog = min(1.0, edad / 1.2) * (len(ruta) - 1)
        col = ROJO if e.get("falso") else AZUL
        for i in range(len(ruta) - 1):
            if prog <= i:
                break
            a, b = ruta[-1 - i], ruta[-2 - i]          # del jugador hacia el origen
            t = min(1.0, prog - i)
            pts = [bezier(a, b, 40 * U, s / 12 * t) for s in range(13)]
            pygame.draw.lines(sup, col, False, pts, max(2, round(5 * U)))
        if prog >= len(ruta) - 1:
            x, y = ruta[0]
            kk = min(1.0, (edad - 1.2) / 0.5)
            anillo(sup, (x, y), (30 + 40 * kk) * U, col, 6 * U)
            w = ancho_texto("Paciente cero", 15 * U, 900) + 24 * U
            pildora(sup, (x - w / 2, y - 120 * U, w, 30 * U), col)
            texto(sup, "Paciente cero" if e.get("falso") else "Origen", (x, y - 105 * U), 15 * U, BLANCO, 900)
            if e.get("falso") and edad > 1.2:
                self._fx_poda(sup, dict(e, quien=None), edad - 1.2, k)

    def _fx_ondas(self, sup, e, edad, k):
        x, y = self._jpos(e["jugador"])
        for i in range(3):
            kk = (k * 1.4 - i * 0.2)
            if 0 < kk < 1:
                r = pygame.Rect(0, 0, 900 * self.U * kk, 450 * self.U * kk)
                r.center = (round(x), round(y))
                s = pygame.Surface(r.size, pygame.SRCALPHA)
                pygame.draw.ellipse(s, (*AZUL, round(200 * (1 - kk))), (0, 0, r.w, r.h), max(2, round(8 * self.U)))
                sup.blit(s, r)
        icono(sup, "megaphone", (x, y - self.alto_persona(True) - 60 * self.U), 40 * self.U, AZUL, 3)

    def _fx_alerta(self, sup, e, edad, k):
        x, y = self._jpos(e["jugador"])
        cab = (x, y - self.alto_persona(True) * 0.9)
        for a in e.get("a", []):
            pb = self.cabeza(a)
            if pb:
                curva(sup, cab, pb, 50 * self.U, (120, 220, 200), 4 * self.U, alfa=round(230 * (1 - k)))
        icono(sup, "bell-ring", (x, y - self.alto_persona(True) - 60 * self.U), 40 * self.U, (40, 170, 140), 3)

    def _fx_discurso(self, sup, e, edad, k):
        U = self.U
        x, y = self._jpos(e["jugador"])
        for i in range(8):
            ang = i / 8 * math.tau + edad
            px, py = x + math.cos(ang) * 80 * U * k, y - 60 * U - 120 * U * k + math.sin(ang) * 30 * U
            icono(sup, "heart", (px, py), 24 * U, (240, 90, 140), 3)
        for v, ruta in (e.get("rutas") or {}).items():
            pts = [self.cabeza(n) for n in ruta]
            pts = [p for p in pts if p]
            if len(pts) >= 2:
                pygame.draw.lines(sup, (240, 90, 140), False, pts, max(1, round(3 * U)))

    def _fx_discusion(self, sup, e, edad, k):
        a, b = self.cabeza(e["a"]), self.cabeza(e["b"])
        if not a or not b:
            return
        U = self.U
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 30 * U
        pts = [a, (mx - 10 * U, my), (mx + 10 * U, my + 12 * U), b]
        if int(edad * 12) % 2 == 0:
            pygame.draw.lines(sup, MANGO, False, pts, max(2, round(5 * U)))
        icono(sup, "zap", (mx, my - 20 * U), 34 * U, (214, 120, 0), 3)

    def _fx_estallido(self, sup, e, edad, k):
        cab = self.cabeza(e["quien"])
        if not cab:
            return
        for i, col in enumerate(((255, 90, 40), ROJO, MANGO)):
            kk = min(1, k * (1.3 - i * 0.2))
            circulo(sup, cab, (40 + 260 * kk) * self.U, col, alfa=round(160 * (1 - kk)))

    def _fx_bot_fuera(self, sup, e, edad, k):
        if not e.get("mundo"):
            return
        pos = self.a_pantalla(*e["mundo"])
        for i in range(6):
            ang = i / 6 * math.tau
            circulo(sup, (pos[0] + math.cos(ang) * 40 * self.U * k, pos[1] + math.sin(ang) * 20 * self.U * k),
                    18 * self.U * (1 - k), (230, 232, 244))

    def _fx_compartir(self, sup, e, edad, k):
        x, y = self._jpos(e["jugador"])
        col = ROJO if e.get("falso") else AZUL
        r = pygame.Rect(0, 0, 300 * self.U * k, 140 * self.U * k)
        r.center = (round(x), round(y))
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.ellipse(s, (*col, round(220 * (1 - k))), (0, 0, r.w, r.h), max(2, round(6 * self.U)))
        sup.blit(s, r)

    def _fx_rechazo(self, sup, e, edad, k):
        cab = self.cabeza(e["quien"])
        if cab:
            icono(sup, "circle-x", (cab[0], cab[1] - 80 * self.U), 54 * self.U * rebote(min(1, edad / 0.3)), ROJO, 3)

    def _fx_recargando(self, sup, e, edad, k):
        x, y = self._jpos(e["jugador"])
        j = self.m.jugadores[e["jugador"]]
        texto(sup, f"Poder listo en {math.ceil(j.recarga)} s", (x, y + 50 * self.U), 15 * self.U, TINTA, 900)

    def _fx_nada(self, sup, e, edad, k):
        x, y = self._jpos(e["jugador"])
        texto(sup, "Acércate a alguien con una burbuja", (x, y + 50 * self.U), 15 * self.U, TINTA, 900)

    def _fx_nuevo(self, sup, e, edad, k):
        cab = self.cabeza(e["quien"])
        if cab:
            anillo(sup, cab, (20 + 60 * k) * self.U, LILA, 5 * self.U, alfa=round(255 * (1 - k)))

    def _tinte(self, sup):
        """Atardecer al final del día."""
        falta = self.m.dia_seg - self.m.reloj
        if self.m.estado == "jugando" and falta < 15:
            a = round(70 * (1 - falta / 15))
            s = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
            s.fill((255, 120, 60, a // 2))
            sup.blit(s, (0, 0))
        if self.m.viral and int(self.t * 3) % 2 == 0:
            w, h = sup.get_size()
            pygame.draw.rect(sup, (255, 90, 40), (0, 0, w, h), max(4, round(10 * self.U)))

    # -------------------------------------------------------------- barra de información
    def _hud(self, sup):
        U = self.U
        W, H = sup.get_size()
        m = self.m
        # reloj del día (arriba al centro)
        w = 360 * U
        r = pildora(sup, (W / 2 - w / 2, 14 * U, w, 60 * U), BLANCO, round(20 * U))
        falta = max(0, m.dia_seg - m.reloj)
        icono(sup, "sun" if falta > 15 else "sunset", (r.x + 34 * U, r.centery), 34 * U, MANGO, 2.8)
        texto(sup, f"Día {m.dia} de {m.dias}", (r.x + 62 * U, r.y + 20 * U), 21 * U, TINTA, 700, "titulo", "midleft")
        barra = pygame.Rect(r.x + 62 * U, r.y + 38 * U, r.w - 140 * U, 10 * U)
        pygame.draw.rect(sup, (232, 234, 246), barra, border_radius=round(5 * U))
        relleno = barra.copy()
        relleno.w = round(barra.w * falta / m.dia_seg)
        pygame.draw.rect(sup, MANGO if falta > 15 else ROJO, relleno, border_radius=round(5 * U))
        texto(sup, f"{int(falta) // 60}:{int(falta) % 60:02d}", (r.right - 38 * U, r.centery), 22 * U,
              TINTA if falta > 15 else ROJO, 700, "titulo")
        # ciudad (arriba a la izquierda)
        salud = m.salud()
        r = pildora(sup, (16 * U, 14 * U, 424 * U, 60 * U), BLANCO, round(20 * U))
        col = VERDE if salud >= 60 else MANGO if salud >= 40 else ROJO
        circulo(sup, (r.x + 32 * U, r.centery), 22 * U, mezclar(col, BLANCO, 0.82))
        anillo(sup, (r.x + 32 * U, r.centery), 24 * U, col, 5 * U, salud / 100)
        icono(sup, "smile" if salud >= 60 else "meh" if salud >= 40 else "frown", (r.x + 32 * U, r.centery), 24 * U, col, 2.6)
        texto(sup, "Ciudad Nova", (r.x + 64 * U, r.y + 18 * U), 13 * U, TINTA2, 900, ancla="midleft")
        texto(sup, f"{salud}", (r.x + 64 * U, r.y + 40 * U), 24 * U, TINTA, 700, "titulo", "midleft")
        x0 = r.x + 160 * U
        pygame.draw.line(sup, (232, 234, 246), (x0 - 12 * U, r.y + 10 * U), (x0 - 12 * U, r.bottom - 10 * U), max(1, round(2 * U)))
        for i, (clave, ic, nombre, bueno) in enumerate(ICONO_IND):
            cx = x0 + (i % 3) * 86 * U
            cy = r.y + (18 if i < 3 else 42) * U
            v = m.indicadores[clave]
            ok = v >= 50 if bueno else v < 35
            c2 = VERDE if ok else ROJO
            icono(sup, ic, (cx + 8 * U, cy), 15 * U, c2, 2.4)
            b = pygame.Rect(cx + 20 * U, cy - 3 * U, 56 * U, 7 * U)
            pygame.draw.rect(sup, (232, 234, 246), b, border_radius=round(3 * U))
            b2 = b.copy()
            b2.w = round(b.w * v / 100)
            pygame.draw.rect(sup, c2, b2, border_radius=round(3 * U))
        # botones (arriba a la derecha)
        x = W - 16 * U
        for etiqueta, k in (("Pausa", "Esc"), ("Red social", "Tab")):
            w = ancho_texto(etiqueta, 14 * U, 900) + ancho_texto(k, 12 * U, 900) + 50 * U
            r = pildora(sup, (x - w, 22 * U, w, 44 * U), BLANCO, round(16 * U))
            kr = tecla(sup, k, (r.x + 14 * U + ancho_texto(k, 12 * U, 900) / 2 + 6 * U, r.centery), 26 * U,
                       LILA2 if not (k == "Tab" and self.ver_red) else MANGO)
            texto(sup, etiqueta, (kr.right + 8 * U, r.centery), 14 * U, TINTA, 900, ancla="midleft")
            x = r.x - 10 * U
        # jugadores (abajo, en las esquinas)
        for j in m.jugadores:
            self._tarjeta(sup, j)
        # mensajes
        y = H - 20 * U
        maximo = W - 2 * (316 * U + 24 * U)
        for a in reversed(self.avisos[-3:]):
            edad = self.t - a["t0"]
            alfa = round(255 * min(1, (6.5 - edad) / 1.0))
            col = {"bueno": VERDE, "malo": ROJO, "logro": (200, 140, 0), "evento": LILA}.get(a["tipo"], TINTA2)
            txt = a["texto"]
            while ancho_texto(txt, 14 * U, 800) > maximo - 44 * U and len(txt) > 12:
                txt = txt[:-4] + "…"
            w = ancho_texto(txt, 14 * U, 800) + 40 * U
            r = pildora(sup, (W / 2 - w / 2, y - 34 * U, w, 30 * U), BLANCO, alfa=min(235, alfa), con_sombra=False)
            circulo(sup, (r.x + 14 * U, r.centery), 6 * U, col)
            texto(sup, txt, (r.x + 26 * U, r.centery), 14 * U, TINTA, 800, ancla="midleft", alfa=alfa)
            y -= 36 * U

    def _tarjeta(self, sup, j):
        U = self.U
        W, H = sup.get_size()
        w, h = 300 * U, 92 * U
        orden = [0, 1, 2, 3]
        lado = j.idx % 2
        fila = j.idx // 2
        x = 16 * U if lado == 0 else W - 16 * U - w
        y = H - 16 * U - h - fila * (h + 10 * U)
        r = pildora(sup, (x, y, w, h), BLANCO, round(22 * U))
        pygame.draw.rect(sup, j.color, r, max(3, round(4 * U)), border_radius=round(22 * U))
        av = personajes.avatar(j.look, round(64 * U), j.color, j.rol, "feliz")
        sup.blit(av, (r.x + 12 * U, r.y + 14 * U))
        texto(sup, j.nombre, (r.x + 88 * U, r.y + 24 * U), 19 * U, TINTA, 700, "titulo", "midleft")
        texto(sup, ROLES[j.rol]["nombre"], (r.x + 88 * U, r.y + 46 * U), 12 * U, TINTA2, 900, ancla="midleft")
        icono(sup, "star", (r.x + 98 * U, r.y + 70 * U), 18 * U, (230, 159, 0), 2.6)
        texto(sup, f"{j.puntos}", (r.x + 112 * U, r.y + 70 * U), 20 * U, TINTA, 700, "titulo", "midleft")
        # poder con su recarga
        cx, cy = r.right - 50 * U, r.centery - 4 * U
        listo = j.recarga <= 0
        circulo(sup, (cx, cy), 30 * U, MANGO if listo else (232, 234, 246))
        if not listo:
            anillo(sup, (cx, cy), 30 * U, MANGO, 6 * U, 1 - j.recarga / PODERES[j.rol]["recarga"])
        icono(sup, {"periodista": "git-branch", "influencer": "megaphone", "ciudadano": "bell-ring",
                    "candidato": "mic"}.get(j.rol, "sparkles"), (cx, cy), 28 * U, TINTA if listo else GRIS, 2.6)
        etq = self.perfil(j.idx)["etiquetas"]["poder"]
        tecla(sup, etq, (cx, r.bottom - 10 * U), 22 * U, MANGO if listo else (232, 234, 246))

    def _banners(self, sup):
        U = self.U
        W, H = sup.get_size()
        vivos = []
        y = 90 * U
        for b in self.banners:
            edad = self.t - b["t0"]
            dur = 4.2 if b.get("tipo") != "logro" else 2.8
            if edad > dur:
                continue
            vivos.append(b)
            entra = suave(min(1, edad / 0.35))
            sale = suave(min(1, max(0, edad - dur + 0.4) / 0.4))
            tipo = b.get("tipo")
            col = COLOR_EVENTO.get(tipo, (230, 159, 0))
            ic = ICONO_EVENTO.get(tipo, "trophy")
            w = max(ancho_texto(b["titulo"], 24 * U, 700, "titulo"), ancho_texto(b["texto"], 14 * U, 800)) + 110 * U
            w = min(w, W * 0.7)
            h = 70 * U
            yy = y - (1 - entra) * 120 * U - sale * 120 * U
            r = pildora(sup, (W / 2 - w / 2, yy, w, h), BLANCO, round(22 * U))
            pygame.draw.rect(sup, col, r, max(3, round(4 * U)), border_radius=round(22 * U))
            circulo(sup, (r.x + 38 * U, r.centery), 26 * U, col)
            icono(sup, ic, (r.x + 38 * U, r.centery), 28 * U, BLANCO, 2.8)
            texto(sup, b["titulo"], (r.x + 76 * U, r.y + 24 * U), 24 * U, col, 700, "titulo", "midleft")
            t2 = b["texto"]
            while ancho_texto(t2, 14 * U, 800) > w - 100 * U and len(t2) > 10:
                t2 = t2[:-2]
            if t2 != b["texto"]:
                t2 = t2[:-1] + "…"
            texto(sup, t2, (r.x + 76 * U, r.y + 50 * U), 14 * U, TINTA, 800, ancla="midleft")
            y += h + 10 * U
        self.banners = vivos

    # -------------------------------------------------------------- pantallas encima
    def _velo(self, sup, color=(24, 20, 70), alfa=170):
        s = pygame.Surface(sup.get_size(), pygame.SRCALPHA)
        s.fill((*color, alfa))
        sup.blit(s, (0, 0))

    def _noche(self, sup):
        U = self.U
        W, H = sup.get_size()
        k = suave(min(1, self._noche_t / 0.8))
        self._velo(sup, (20, 18, 64), round(185 * k))
        res = self.m.resumen_dia
        if not res:
            return
        w, h = 640 * U, (430 + 50 * len(self.m.jugadores)) * U
        r = pildora(sup, (W / 2 - w / 2, H / 2 - h / 2 + (1 - k) * 60 * U, w, h), BLANCO, round(30 * U))
        icono(sup, "moon", (r.centerx, r.y + 46 * U), 46 * U, LILA, 2.6)
        texto(sup, f"Termina el día {res['dia']}", (r.centerx, r.y + 98 * U), 34 * U, TINTA, 700, "titulo")
        antes = self.m.historial[-2]["salud"] if len(self.m.historial) > 1 else None
        salud = res["salud"]
        delta = "" if antes is None else (f"  (+{salud - antes})" if salud >= antes else f"  ({salud - antes})")
        texto(sup, f"Salud de Ciudad Nova: {salud}{delta}", (r.centerx, r.y + 140 * U), 20 * U,
              VERDE if salud >= 60 else ROJO, 900)
        hoy = res.get("hoy", {})
        datos = [("search", f"{hoy.get('escaneos', 0)} escaneos", LILA),
                 ("flag", f"{hoy.get('retiradas', 0)} publicaciones falsas retiradas", VERDE),
                 ("check", f"{hoy.get('corregidos', 0)} vecinos dejaron de creer mentiras", VERDE),
                 ("flame", f"{hoy.get('estallidos', 0)} rumores virales estallaron", ROJO),
                 ("frown", f"{res.get('creen', 0)} vecinos todavía creen algo falso", ROJO)]
        y = r.y + 178 * U
        for ic, t, col in datos:
            icono(sup, ic, (r.x + 70 * U, y), 20 * U, col, 2.6)
            texto(sup, t, (r.x + 92 * U, y), 15 * U, TINTA, 800, ancla="midleft")
            y += 28 * U
        y += 14 * U
        for j in sorted(self.m.jugadores, key=lambda j: -j.puntos):
            av = personajes.avatar(j.look, round(44 * U), j.color, j.rol, "feliz")
            sup.blit(av, (r.x + 66 * U, y - 22 * U))
            texto(sup, j.nombre, (r.x + 122 * U, y), 19 * U, TINTA, 700, "titulo", "midleft")
            g = res.get("ganados", {}).get(j.nombre, 0)
            texto(sup, (f"+{g}" if g >= 0 else str(g)) + " hoy", (r.right - 200 * U, y), 16 * U,
                  VERDE if g >= 0 else ROJO, 900, ancla="midright")
            texto(sup, f"{j.puntos} pts", (r.right - 66 * U, y), 21 * U, TINTA, 700, "titulo", "midright")
            y += 50 * U
        if self._noche_t > 1.2:
            texto(sup, "Pulsa Enter (o cualquier botón) para empezar el siguiente día", (r.centerx, r.bottom - 34 * U),
                  15 * U, LILA, 900)

    def _eleccion(self, sup):
        U = self.U
        W, H = sup.get_size()
        k = suave(min(1, self._noche_t / 0.8))
        self._velo(sup, (20, 18, 64), round(195 * k))
        el = self.m.eleccion
        w, h = 760 * U, 520 * U
        r = pildora(sup, (W / 2 - w / 2, H / 2 - h / 2, w, h), BLANCO, round(30 * U))
        texto(sup, "Elección de alcalde", (r.centerx, r.y + 50 * U), 36 * U, TINTA, 700, "titulo")
        tot = el["totales"]
        maximo = max(tot.values()) or 1
        y = r.y + 110 * U
        from ..modelo.hechos import CANDIDATOS
        for nombre, col in CANDIDATOS:
            v = tot[nombre]
            prog = min(1, max(0, (self._noche_t - 0.6) / 2.5))
            texto(sup, nombre, (r.x + 40 * U, y), 18 * U, TINTA, 900, ancla="midleft")
            b = pygame.Rect(r.x + 260 * U, y - 14 * U, (w - 380 * U) * v / maximo * prog, 28 * U)
            pygame.draw.rect(sup, col, b, border_radius=round(10 * U))
            texto(sup, f"{round(v * prog):,}".replace(",", "."), (b.right + 10 * U, y), 16 * U, TINTA, 900, ancla="midleft")
            y += 50 * U
        if self._noche_t > 3.2:
            texto(sup, f"¡Gana {el['ganador']}!", (r.centerx, y + 20 * U), 30 * U, VERDE, 700, "titulo")
            y += 70 * U
            mejor = max(self.m.jugadores, key=lambda j: j.puntos)
            texto(sup, f"Mejor jugador: {mejor.nombre} con {mejor.puntos} puntos · Salud final {self.m.salud()}",
                  (r.centerx, y), 17 * U, TINTA2, 900)
            texto(sup, "Pulsa Enter para volver al menú", (r.centerx, r.bottom - 30 * U), 15 * U, LILA, 900)

    def _pausa(self, sup):
        U = self.U
        W, H = sup.get_size()
        self._velo(sup, alfa=150)
        w, h = 760 * U, 470 * U
        r = pildora(sup, (W / 2 - w / 2, H / 2 - h / 2, w, h), BLANCO, round(30 * U))
        texto(sup, "Pausa", (r.centerx, r.y + 44 * U), 34 * U, TINTA, 700, "titulo")
        filas = [("Moverse", "mover"), ("Escanear: ¿es verdad o mentira? (mantener)", "escanear"),
                 ("Reportar a Civitas (si es falso)", "reportar"), ("Compartir con tus seguidores (si es verdad)", "compartir"),
                 ("Poder especial", "poder")]
        y = r.y + 100 * U
        for i, j in enumerate(self.m.jugadores[:2]):
            texto(sup, j.nombre, (r.x + 470 * U + i * 140 * U, y), 16 * U, TINTA, 700, "titulo")
        y += 36 * U
        for etiqueta, clave in filas:
            texto(sup, etiqueta, (r.x + 40 * U, y), 15 * U, TINTA, 800, ancla="midleft")
            for i, j in enumerate(self.m.jugadores[:2]):
                tecla(sup, self.perfil(i)["etiquetas"][clave], (r.x + 470 * U + i * 140 * U, y), 30 * U, LILA2)
            y += 46 * U
        texto(sup, "Esc / Enter: seguir jugando     X: salir al menú", (r.centerx, r.bottom - 36 * U), 15 * U, LILA, 900)
