import math
import random

import pygame

from ..modelo.ciudad import NEGATIVOS, NOMBRES
from . import personajes, recursos
from .ayuda import ICONO_ROL
from .celular import Celular
from .efectos import EFECTOS, acercar
from .escena import cielo
from .guia import Guia
from .juego_comun import cara, color_caso
from .modales import BannerTurno, HojaVerificacion, ModalArchivo, ModalConfirmar, ModalViral, SecuenciaNoche
from .tema import TEMA
from .vista_arbol import VistaArbol
from .vista_mapa import VistaMapa
from .vista_red import VistaRed
from .widgets import Boton, barra, chip, parrafo, recortar, sticker, texto, titulo, tooltip

ICONO_IND = dict(info_verificada="shield-check", confianza="handshake", convivencia="heart-handshake",
                 bienestar="heart-pulse", desinformacion="cloud-fog", conflictos="zap")
FRASES = {
    "bueno": ["¡Bien hecho!", "Eso ayuda a la ciudad.", "¡Así se hace!", "Un rumor menos."],
    "malo": ["Uy… eso no salió bien.", "Debí verificar primero.", "Eso le hizo daño a la ciudad."],
    "logro": ["¡Logro desbloqueado!", "¡Lo logramos!"],
}
CORTOS = dict(info_verificada="Info. verificada", confianza="Confianza", convivencia="Convivencia",
              bienestar="Bienestar", desinformacion="Desinformación", conflictos="Conflictos")


class PantallaJuego:
    toasts_propios = True

    def __init__(self, app, ctrl, guia=True):
        self.app = app
        self.ctrl = ctrl
        self.celular = Celular(self, (12, 74, 322, 636))
        self.r_tabs = pygame.Rect(346, 74, 590, 42)
        self.r_centro = pygame.Rect(346, 124, 590, 584)
        self.r_jugador = pygame.Rect(948, 74, 320, 222)
        self.r_ciudad = pygame.Rect(948, 306, 320, 262)
        self.r_jugadores = pygame.Rect(948, 578, 320, 62)
        self.btn_fin = Boton((948, 650, 320, 58), "Terminar turno", "fin", icono="skip-forward",
                             estilo="primario", tam=19)
        self.mapa = VistaMapa(self, self.r_centro)
        self.red = VistaRed(self, self.r_centro)
        self.arbol = VistaArbol(pygame.Rect(self.r_centro.x + 8, self.r_centro.y + 52, self.r_centro.w - 16,
                                            self.r_centro.h - 128))
        self.vista = "mapa"
        w = (self.r_tabs.w - 16) // 3
        self.tabs = [Boton((self.r_tabs.x + i * (w + 8), self.r_tabs.y, w, 42), nombre, clave, icono=ic, tam=16,
                           estilo="suave", sombra=3)
                     for i, (clave, nombre, ic) in enumerate((("mapa", "Ciudad", "map"), ("red", "Red social", "share-2"),
                                                              ("arbol", "Árbol del rumor", "git-fork")))]
        self.b_ayuda = Boton((1012, 12, 56, 42), "", "ayuda", icono="circle-help", sombra=3)
        self.b_acc = Boton((1076, 12, 56, 42), "", "acc", icono="accessibility", sombra=3)
        self.b_snd = Boton((1140, 12, 56, 42), "", "snd", icono="volume-2", sombra=3)
        self.b_menu = Boton((1204, 12, 56, 42), "", "menu", icono="log-out", sombra=3)
        x = self.r_centro.x + 12
        self.b_rec = []
        for clave, nombre, ic, ancho in (("pre", "Preorden", "list", 112), ("post", "Postorden", "list", 116),
                                         ("bfs", "Por niveles", "waypoints", 124), ("camino", "A la raíz", "footprints", 110),
                                         ("avl", "Archivo", "archive", 96)):
            self.b_rec.append(Boton((x, self.r_centro.bottom - 54, ancho, 42), nombre, clave, icono=ic, tam=14,
                                    estilo="suave", sombra=3))
            x += ancho + 6
        self.chips_arbol = []
        self.arbol_caso = None
        self.sel = None
        self.modal = None
        self.banner = None
        self.expr = ("neutral", 0)
        self.burbuja = None
        p = self.p
        self.msg_vistos = p.total_mensajes()
        self.anim_vistos = p._seq
        self.ind_vista = {k: float(v) for k, v in p.ciudad.v.items()}
        self.deltas = {}
        self.puntos = {j.nombre: j.puntos for j in p.jugadores}
        self.ronda_vista = p.ronda
        self.turno_visto = (p.ronda, p.turno_idx)
        self.fin_mostrado = False
        self._esperando_verif = None
        self._resaltado_visto = None
        self._auto_seleccionar()
        if guia and TEMA.op["guia"]:
            self.modal = Guia(self)
        else:
            self._banner_turno()

    # ------------------------------------------------------------------ acceso
    @property
    def p(self):
        return self.ctrl.partida

    def en_red(self):
        return self.ctrl.en_red

    def yo(self):
        p = self.p
        if self.ctrl.en_red and self.ctrl.indice is not None and 0 <= self.ctrl.indice < len(p.jugadores):
            return p.jugadores[self.ctrl.indice]
        return p.jugador_actual

    def puedo_actuar(self):
        return self.ctrl.es_mi_turno() and self.p.evento_viral is None and not (self.modal and self.modal.bloquea)

    def motivo_espera(self):
        p = self.p
        if p.evento_viral:
            return "Primero hay que atender la publicación viral."
        if getattr(self.ctrl, "esperando", False):
            return "Esperando al servidor…"
        if self.ctrl.en_red and p.turno_idx != self.ctrl.indice:
            return f"Es el turno de {p.jugador_actual.nombre}. Puedes mirar el mapa, la red y el árbol."
        return ""

    def expresion_de(self, j):
        e, t0 = self.expr
        if j is self.p.jugador_actual and pygame.time.get_ticks() - t0 < 2600:
            return e
        return "neutral"

    # ------------------------------------------------------------------ la publicación del turno
    def nodo_sel(self):
        """La publicación que el juego le repartió al jugador de este turno."""
        return self.p.publicacion_turno()[1]

    def caso_sel(self):
        return self.p.publicacion_turno()[0]

    def seleccionar(self, caso_id, nodo_id):
        """Resalta una publicación en el árbol (no cambia la del turno)."""
        self.sel = (caso_id, nodo_id)
        self.arbol.seleccionado = nodo_id
        if self.arbol_caso is not None and self.arbol_caso != caso_id:
            self.arbol_caso = caso_id

    def seleccionar_de_autor(self, nombre, caso_id=None):
        casos = [self.p.caso_por_id(caso_id)] if caso_id else self.p.casos_abiertos()
        for caso in casos:
            if caso is None:
                continue
            for n in caso.arbol.preorden():
                if n.autor == nombre:
                    self.seleccionar(caso.id, n.id)
                    return True
        return False

    def _auto_seleccionar(self):
        caso, n = self.p.publicacion_turno()
        if n is not None:
            self.seleccionar(caso.id, n.id)

    def cambiar_vista(self, v):
        self.vista = v

    # ------------------------------------------------------------------ jugadas
    def accion(self, clave):
        n, caso = self.nodo_sel(), self.caso_sel()
        if n is None or caso is None:
            return
        if not self.puedo_actuar():
            self.app.toasts.agregar(self.motivo_espera() or "Ahora no puedes actuar.", "info")
            return
        self._ejecutar(clave)

    def _ejecutar(self, clave):
        n, caso = self.nodo_sel(), self.caso_sel()
        if n is None or caso is None:
            return
        self.app.sonar("click")
        if clave == "verificar":
            self._esperando_verif = (caso.id, n.id)
        msgs = self.ctrl.accion(caso.id, n.id, clave)
        if msgs and len(msgs) == 1 and msgs[0].tipo == "malo" and not self.ctrl.en_red:
            self.app.toasts.agregar(msgs[0].texto, "malo")
        self._sincronizar()

    def mover(self, zona):
        msgs = self.ctrl.mover(zona)
        if msgs and msgs[0].tipo == "malo" and not self.ctrl.en_red:
            self.app.toasts.agregar(msgs[0].texto, "malo")
        self.app.sonar("paso")
        self._sincronizar()

    def conversar(self):
        if not self.puedo_actuar():
            return
        self.ctrl.conversar()
        self._sincronizar()

    def terminar_turno(self):
        if not self.puedo_actuar():
            if self.ctrl.en_red:
                self.app.toasts.agregar(self.motivo_espera(), "info")
            return
        self.ctrl.terminar_turno()
        self._sincronizar()

    def resolver_viral(self, clave):
        ev = self.p.evento_viral
        if ev is None:
            return
        if clave == "verificar":
            self._esperando_verif = (ev.caso.id, ev.nodo.id)
        self.seleccionar(ev.caso.id, ev.nodo.id)
        self.ctrl.resolver_viral(clave)
        if isinstance(self.modal, ModalViral):
            self.modal = None
        self._sincronizar()

    def cerrar_modal(self):
        self.modal = None
        self._sincronizar()

    def abrir_archivo(self):
        r = self.p.ultimo_resaltado or {}
        self.modal = ModalArchivo(self, r.get("avl_ruta", []), r.get("avl_nuevo"),
                                  volver=self.modal if isinstance(self.modal, HojaVerificacion) else None)

    def terminar_noche(self):
        self.modal = None
        self.vista = "mapa"
        if self.p.terminada:
            self.fin_mostrado = True
            self.app.fin_partida(self.ctrl)
            return
        self._sincronizar()
        if self.modal is None:
            self._banner_turno()

    # ------------------------------------------------------------------ sincronización con el modelo
    def _sincronizar(self):
        p = self.p
        nuevos = p.mensajes_desde(self.msg_vistos)
        self.msg_vistos = p.total_mensajes()
        sonado = False
        hay_noche = (p.ronda != self.ronda_vista or (p.terminada and not self.fin_mostrado))
        for m in nuevos:
            if hay_noche and m.tipo in ("evento", "info"):
                continue
            if m.texto.startswith("Turno de") or m.texto.startswith("Día "):
                continue
            if m.tipo != "info" or "Verific" in m.texto or "compart" in m.texto:
                self.app.toasts.agregar(m.texto, m.tipo)
            if m.tipo in FRASES:
                self.expr = ({"bueno": "feliz", "malo": "preocupado", "logro": "sorprendido"}[m.tipo],
                             pygame.time.get_ticks())
                self.burbuja = (random.choice(FRASES[m.tipo]), pygame.time.get_ticks(), m.tipo)
            if m.tipo == "logro":
                EFECTOS.confeti(self.r_jugador.centerx, self.r_jugador.y + 40, 70)
                self.app.sonar("logro")
                sonado = True
            elif not sonado and m.tipo in ("bueno", "malo"):
                self.app.sonar(m.tipo)
                if m.tipo == "malo":
                    EFECTOS.sacudir()
                sonado = True
        for ev in p.anim:
            if ev["seq"] < self.anim_vistos:
                continue
            self.red.animar(ev)
            self.mapa.animar(ev)
            if ev.get("t") == "vertice_fuera":
                self.red.fantasmas.append((ev["v"], *self.red.pos.get(ev["v"], (0, 0)), pygame.time.get_ticks()))
        self.anim_vistos = p._seq
        r = p.ultimo_resaltado or {}
        clave_r = repr(sorted((k, str(v)) for k, v in r.items()))
        if clave_r != self._resaltado_visto:
            self._resaltado_visto = clave_r
            self.arbol.resaltar(camino=r.get("camino", []), mutacion=r.get("mutacion", []),
                                inmunes=r.get("inmunes", []))
            if "podados" in r:
                self.app.sonar("rama")
        for j in p.jugadores:
            d = j.puntos - self.puntos.get(j.nombre, j.puntos)
            if d:
                self.puntos[j.nombre] = j.puntos
                x, y = (self.r_jugador.right - 60, self.r_jugador.y + 150) if j is p.jugador_actual else \
                    self._pos_mini(p.jugadores.index(j))
                EFECTOS.flotante(x, y, f"{d:+d}", TEMA.c["bueno"] if d > 0 else TEMA.c["malo"], 26)
        if self._esperando_verif and "verificacion" in r:
            caso = p.caso_por_id(self._esperando_verif[0])
            nodo = caso.arbol.buscar(r["verificacion"].get("nodo")) if caso else None
            if nodo is not None and not (self.ctrl.en_red and getattr(self.ctrl, "esperando", False)):
                self._esperando_verif = None
                if not isinstance(self.modal, (SecuenciaNoche, ModalViral)):
                    self.modal = HojaVerificacion(self, caso, nodo, r["verificacion"])
        elif self._esperando_verif and not getattr(self.ctrl, "esperando", False):
            self._esperando_verif = None
        if (p.ronda != self.ronda_vista or (p.terminada and not self.fin_mostrado)) and \
                not isinstance(self.modal, SecuenciaNoche):
            dia = self.ronda_vista
            self.ronda_vista = p.ronda
            noche = [m for m in nuevos]
            self.modal = SecuenciaNoche(self, dia, noche)
            self.vista = "mapa"
            self.red.caso_id = None
            self.banner = None
            self.turno_visto = (p.ronda, p.turno_idx)
            self.sel = None
            self._auto_seleccionar()
            return
        if isinstance(self.modal, SecuenciaNoche):
            return
        if p.evento_viral and not isinstance(self.modal, ModalViral):
            self.modal = ModalViral(self)
            self.seleccionar(p.evento_viral.caso.id, p.evento_viral.nodo.id)
            return
        if (p.ronda, p.turno_idx) != self.turno_visto:
            self.turno_visto = (p.ronda, p.turno_idx)
            self.sel = None
            self._banner_turno()
        self._auto_seleccionar()

    def _banner_turno(self):
        p = self.p
        if p.terminada:
            return
        propio = None
        if self.ctrl.en_red:
            propio = p.turno_idx == self.ctrl.indice
        self.banner = BannerTurno(self, p.jugador_actual, propio)

    # ------------------------------------------------------------------ eventos
    def evento(self, e):
        if self.modal is not None and self.modal.bloquea:
            self.modal.evento(e)
            return
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_TAB:
                orden = ["mapa", "red", "arbol"]
                self.vista = orden[(orden.index(self.vista) + 1) % 3]
                self.app.sonar("click")
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.terminar_turno()
            elif pygame.K_1 <= e.key <= pygame.K_6:
                self.celular.tecla(e.key - pygame.K_1)
            elif e.key == pygame.K_a:
                self.abrir_archivo()
            return
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.banner = None
            for b in self.tabs:
                if b.clic(e.pos):
                    self.vista = b.clave
                    self.app.sonar("click")
                    return
            if self.b_ayuda.clic(e.pos):
                return self.app.abrir(self.app.ayuda)
            if self.b_acc.clic(e.pos):
                return self.app.abrir(self.app.accesibilidad)
            if self.b_snd.clic(e.pos):
                return self.app.alternar_sonido()
            if self.b_menu.clic(e.pos):
                self.modal = ModalConfirmar(self, "Si sales al menú, esta partida se termina para ti.",
                                            "Salir al menú", "Seguir jugando", self.salir, lambda: None)
                self.modal.b_si.icono, self.modal.b_no.icono = "log-out", "play"
                return
            if self.btn_fin.clic(e.pos):
                return self.terminar_turno()
        if self.celular.evento(e):
            return
        if self.vista == "mapa":
            self.mapa.evento(e)
        elif self.vista == "red":
            self.red.evento(e)
        else:
            self._evento_arbol(e)

    def _evento_arbol(self, e):
        caso = self._caso_arbol()
        if e.type == pygame.MOUSEMOTION:
            self.arbol.hover = self.arbol.nodo_en(caso.arbol if caso else None, e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for r, cid in self.chips_arbol:
                if r.collidepoint(e.pos):
                    self.arbol_caso = cid
                    self.app.sonar("click")
                    return
            for b in self.b_rec:
                if b.clic(e.pos):
                    self._recorrido(b.clave, caso)
                    return
            n = self.arbol.nodo_en(caso.arbol if caso else None, e.pos)
            if n is not None:
                self.seleccionar(caso.id, n.id)
                self.app.sonar("pop")

    def _recorrido(self, clave, caso):
        if clave == "avl":
            return self.abrir_archivo()
        if caso is None or caso.arbol.raiz is None:
            return
        a = caso.arbol
        if clave == "pre":
            self.arbol.animar_recorrido("Preorden (raíz, luego hijos): orden en que se leyó el hilo",
                                        [n.id for n in a.preorden()])
        elif clave == "post":
            self.arbol.animar_recorrido("Postorden (hijos, luego raíz): así se suma el alcance de abajo hacia arriba",
                                        [n.id for n in a.postorden()])
        elif clave == "bfs":
            self.arbol.animar_recorrido("Por niveles (con cola): cada nivel es una ola de propagación",
                                        [n.id for nivel in a.por_niveles() for n in nivel])
        elif clave == "camino":
            n = self.nodo_sel()
            if n is None or n.id not in a:
                self.app.toasts.agregar("Elige una publicación de este árbol para ver su camino a la raíz.", "info")
                return
            self.arbol.animar_recorrido("Camino a la raíz: de dónde salió esta versión",
                                        [m.id for m in a.camino_a_raiz(n.id)])
        self.app.sonar("click")

    def _caso_arbol(self):
        p = self.p
        cid = self.arbol_caso if self.arbol_caso is not None else (self.sel[0] if self.sel else None)
        caso = p.caso_por_id(cid) if cid else None
        if caso is None or not caso.abierto:
            abiertos = p.casos_abiertos()
            caso = abiertos[0] if abiertos else None
        return caso

    def salir(self):
        self.ctrl.cerrar()
        self.app.ir_menu()

    def cerrar(self):
        self.ctrl.cerrar()

    # ------------------------------------------------------------------ actualización
    def actualizar(self):
        nuevo, otros = self.ctrl.actualizar()
        for m in otros:
            if m.get("t") == "aviso":
                self.app.toasts.agregar(m.get("texto", ""), m.get("tipo", "info"))
        if nuevo:
            self._sincronizar()
        if self.modal is not None and hasattr(self.modal, "actualizar"):
            self.modal.actualizar()
        if self.banner is not None and not self.banner.vivo():
            self.banner = None
        for k, v in self.p.ciudad.v.items():
            antes = self.ind_vista.get(k, v)
            if round(antes) != v and k not in self.deltas:
                self.deltas[k] = (v - round(antes), pygame.time.get_ticks())
            self.ind_vista[k] = acercar(antes, v, 0.08) if not TEMA.op["menos_movimiento"] else v
        ahora = pygame.time.get_ticks()
        self.deltas = {k: d for k, d in self.deltas.items() if ahora - d[1] < 4000}

    actualizar_red = actualizar

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, sup):
        c = TEMA.c
        dx, dy = EFECTOS.desfase()
        cielo(sup)
        self._barra_superior(sup)
        self.celular.dibujar(sup)
        for b in self.tabs:
            b.seleccionado = b.clave == self.vista
            b.dibujar(sup)
        sticker(sup, self.r_centro, c["papel"], 20, 5, 3)
        if self.vista == "mapa":
            self.mapa.dibujar(sup)
        elif self.vista == "red":
            self.red.dibujar(sup)
        else:
            self._dibujar_arbol(sup)
        self._panel_jugador(sup)
        self._panel_ciudad(sup)
        self._panel_jugadores(sup)
        self.btn_fin.activo = self.puedo_actuar()
        if self.ctrl.en_red and not self.ctrl.es_mi_turno() and not self.p.evento_viral:
            self.btn_fin.etiqueta = f"Turno de {recortar(self.p.jugador_actual.nombre, 18, 160, 600)}"
        else:
            self.btn_fin.etiqueta = "Terminar turno"
        if self.puedo_actuar() and (self.p.turno.get("decidio") or self.nodo_sel() is None):
            pul = 3 + 2 * math.sin(pygame.time.get_ticks() / 160)
            pygame.draw.rect(sup, c["mango"], self.btn_fin.rect.inflate(10 + pul, 10 + pul), 5, border_radius=18)
        self.btn_fin.dibujar(sup)
        alto_toast = 96 if self.vista == "mapa" else 64
        if (self.vista == "red" and self.red.herr) or (self.vista == "arbol" and self.arbol.secuencia):
            alto_toast = 140
        self.app.toasts.dibujar(sup, self.r_centro.x + 18, self.r_centro.bottom - alto_toast, self.r_centro.w - 36,
                                abajo=True)
        if self.banner is not None:
            self.banner.dibujar(sup)
        if self.modal is not None:
            self.modal.dibujar(sup)
        if dx or dy:
            copia = sup.copy()
            sup.fill(c["tinta"])
            sup.blit(copia, (dx, dy))

    def _barra_superior(self, sup):
        c = TEMA.c
        p = self.p
        sup.blit(personajes.civi("feliz", 54), (14, 6))
        titulo(sup, "Alcalde Digital", (56, 8), 24, c["texto"])
        texto(sup, "Ciudad Nova va a elegir alcalde", (58, 38), 13, c["tinta2"], peso=800)
        dia = min(p.ronda, p.rondas_totales)
        x0 = 352
        titulo(sup, f"Día {dia} de {p.rondas_totales}", (x0, 10), 22, c["texto"])
        faltan = p.rondas_totales - dia
        texto(sup, "Mañana es la elección" if faltan == 0 else
              ("Falta 1 día para votar" if faltan == 1 else f"Faltan {faltan} días para votar"),
              (x0 + 2, 40), 13, c["tinta2"], peso=800)
        xp = x0 + 170
        for k in range(1, p.rondas_totales + 1):
            r = pygame.Rect(xp + (k - 1) * 34, 22, 28, 22)
            col = c["acento"] if k < dia else (c["mango"] if k == dia else c["papel"])
            sticker(sup, r, col, 8, 2, 2)
            if k == dia:
                texto(sup, str(k), r.center, 12, c["texto"], peso=900, ancla="c")
        xu = xp + p.rondas_totales * 34
        sticker(sup, (xu, 16, 36, 34), c["papel"], 10, 3, 2)
        sup.blit(recursos.icono("vote", 22, c["acento"], 2.4), (xu + 7, 22))
        if self.ctrl.en_red:
            yo = self.yo()
            chip(sup, f"Eres {yo.nombre}", (xu + 50, 33), yo.color, c["sobre_color"], "user", 13, ancla="ml")
        self.b_snd.icono = "volume-2" if self.app.snd.activo else "volume-x"
        for b in (self.b_ayuda, self.b_acc, self.b_snd, self.b_menu):
            b.dibujar(sup)
        for b, t in ((self.b_ayuda, "Ayuda (H)"), (self.b_acc, "Accesibilidad"), (self.b_snd, "Quitar o poner sonido (M)"),
                     (self.b_menu, "Salir al menú")):
            if b.hover:
                tooltip(sup, t, (b.rect.centerx, b.rect.bottom + 34), 150)

    def _panel_jugador(self, sup):
        c = TEMA.c
        p = self.p
        j = p.jugador_actual
        r = self.r_jugador
        ahora = pygame.time.get_ticks()
        sticker(sup, r, c["papel"], 20, 5, 3)
        foco = pygame.Rect(r.x + 10, r.y + 10, 124, r.h - 20)
        pygame.draw.rect(sup, j.color, foco, border_radius=16)
        pygame.draw.circle(sup, (255, 255, 255), (foco.centerx, foco.y + 70), 48)
        bob = math.sin(ahora / 420) * 2 if not TEMA.op["menos_movimiento"] else 0
        img = personajes.cuerpo(j.look, j.rol, self.expresion_de(j), alto=186, parpadeo=(ahora % 4300) < 130,
                                color_extra=(58, 110, 230))
        sup.blit(img, (foco.centerx - img.get_width() // 2, foco.bottom - 190 + bob))
        x = r.x + 146
        texto(sup, recortar(j.nombre, 21, r.right - x - 12, 700, "titulo"), (x, r.y + 12), 21, c["texto"],
              peso=700, fam="titulo")
        nombre_rol = recortar(j.candidato, 12, r.right - x - 48, 800) if j.candidato else j.info_rol["nombre"]
        chip(sup, nombre_rol, (x, r.y + 44), c["mango2"], c["texto"], ICONO_ROL[j.rol], 12)
        # Los pasos del turno, con su casilla marcada cuando ya se hicieron.
        y = r.y + 78
        t = p.turno
        for hecho, etiqueta in ((t.get("verifico"), "Verificar (si quieres)"),
                                (bool(t.get("decidio")), "Decidir qué hacer"),
                                (t.get("camino"), "Caminar (si quieres)")):
            caja = pygame.Rect(x, y, 18, 18)
            pygame.draw.rect(sup, c["bueno"] if hecho else c["papel"], caja, border_radius=5)
            pygame.draw.rect(sup, c["borde"], caja, 2, border_radius=5)
            if hecho:
                pygame.draw.lines(sup, c["sobre_color"], False, [(caja.x + 4, caja.centery), (caja.x + 8, caja.bottom - 5),
                                                                 (caja.right - 4, caja.y + 4)], 3)
            texto(sup, etiqueta, (x + 26, y + 9), 13, c["tinta2"] if hecho else c["texto"], peso=800, ancla="ml")
            y += 25
        y += 8
        sup.blit(recursos.icono("star", 22, c["logro"], 2.6), (x, y + 2))
        titulo(sup, f"{j.puntos}", (x + 28, y - 2), 26, c["texto"])
        texto(sup, "puntos", (x + 30 + recursos.fuente(26, 700, "titulo").size(str(j.puntos))[0], y + 12), 12,
              c["tinta2"], peso=800)
        y += 36
        texto(sup, "Reputación", (x, y), 12, c["tinta2"], peso=900)
        barra(sup, (x + 70, y + 2, 50, 12), j.reputacion, c["bueno"] if j.reputacion >= 50 else c["malo"])
        texto(sup, str(j.reputacion), (r.right - 12, y), 12, c["texto"], peso=900, ancla="tr")
        if self.burbuja:
            s, t0, tipo = self.burbuja
            e = ahora - t0
            if e > 2600:
                self.burbuja = None
            else:
                caja = pygame.Rect(0, 0, 176, 54)
                caja.topright = (r.x - 8, r.y + 30)
                col = {"bueno": c["bueno2"], "malo": c["malo2"]}.get(tipo, c["mango2"])
                sticker(sup, caja, col, 16, 3, 3)
                pygame.draw.polygon(sup, col, [(caja.right - 3, caja.y + 14), (caja.right + 12, caja.y + 22),
                                               (caja.right - 3, caja.y + 30)])
                pygame.draw.lines(sup, c["tinta"], False, [(caja.right - 1, caja.y + 13), (caja.right + 13, caja.y + 22),
                                                           (caja.right - 1, caja.y + 31)], 3)
                parrafo(sup, s, caja.x + 12, caja.y + 8, caja.w - 22, 14, c["texto"], peso=800, max_lineas=2)

    def _panel_ciudad(self, sup):
        c = TEMA.c
        p = self.p
        r = self.r_ciudad
        sticker(sup, r, c["papel"], 20, 5, 3)
        titulo(sup, "Ciudad Nova", (r.x + 16, r.y + 12), 21, c["texto"])
        texto(sup, "Salud de la ciudad", (r.x + 18, r.y + 40), 12, c["tinta2"], peso=800)
        salud = p.ciudad.salud()
        col = c["bueno"] if salud >= 60 else c["aviso"] if salud >= 45 else c["malo"]
        cara_ic = "smile" if salud >= 60 else "meh" if salud >= 45 else "frown"
        sup.blit(recursos.icono(cara_ic, 34, col, 2.6), (r.right - 104, r.y + 14))
        titulo(sup, str(salud), (r.right - 16, r.y + 10), 34, col, ancla="tr")
        y = r.y + 64
        ahora = pygame.time.get_ticks()
        raton = pygame.mouse.get_pos()
        for k in ("info_verificada", "confianza", "convivencia", "bienestar", "desinformacion", "conflictos"):
            neg = k in NEGATIVOS
            v = self.ind_vista.get(k, p.ciudad.v[k])
            fila = pygame.Rect(r.x + 10, y - 2, r.w - 20, 30)
            sup.blit(recursos.icono(ICONO_IND[k], 18, c["malo"] if neg else c["acento"], 2.4), (r.x + 16, y + 3))
            texto(sup, CORTOS[k], (r.x + 42, y + 1), 13, c["texto"], peso=800)
            barra(sup, (r.x + 154, y + 6, 92, 12), v, c["malo"] if neg else c["acento"], rayas=neg)
            texto(sup, str(p.ciudad.v[k]), (r.right - 12, y + 1), 14, c["texto"], peso=900, ancla="tr")
            if k in self.deltas:
                d, t0 = self.deltas[k]
                bueno = (d < 0) if neg else (d > 0)
                chip(sup, f"{d:+d}", (r.x + 200, y + 12), c["bueno"] if bueno else c["malo"], c["sobre_color"], None,
                     11, ancla="c", alto=20)
            if fila.collidepoint(raton):
                from .ayuda import SECCIONES
                desc = next(b[3] for b in SECCIONES[5][2] if b[0] == "item" and b[2] == NOMBRES[k])
                tooltip(sup, desc, (fila.x + 90, fila.y), 240)
            y += 32

    def _pos_mini(self, i):
        n = len(self.p.jugadores)
        paso = (self.r_jugadores.w - 20) / n
        return self.r_jugadores.x + 10 + paso * i + paso / 2, self.r_jugadores.centery

    def _panel_jugadores(self, sup):
        c = TEMA.c
        p = self.p
        r = self.r_jugadores
        sticker(sup, r, c["papel"], 18, 4, 3)
        for i, j in enumerate(p.jugadores):
            x, y = self._pos_mini(i)
            actual = j is p.jugador_actual
            img = cara(p, j.nombre, 36, borde=c["borde"], grosor=2)
            if i in getattr(self.ctrl, "desconectados", []):
                img = img.copy()
                img.set_alpha(90)
            if actual:
                pygame.draw.circle(sup, j.color, (x - 22, y), 22, 4)
            sup.blit(img, (x - 40, y - 18))
            ancho = (self.r_jugadores.w - 20) / len(p.jugadores) - 50
            texto(sup, recortar(j.nombre, 12, ancho, 900), (x + 4, y - 14), 12, c["texto"], peso=900)
            texto(sup, f"{j.puntos} pts", (x + 4, y + 2), 12, c["tinta2"], peso=800)

    def _dibujar_arbol(self, sup):
        c = TEMA.c
        p = self.p
        caso = self._caso_arbol()
        self.chips_arbol = []
        x, y = self.r_centro.x + 14, self.r_centro.y + 14
        for cs in p.casos_abiertos():
            sel = caso is not None and cs.id == caso.id
            r = chip(sup, recortar(cs.hecho.titulo, 13, 160, 800), (x, y), color_caso(cs.id) if sel else c["papel"],
                     c["sobre_color"] if sel else c["texto"], None, 13, punto=None if sel else color_caso(cs.id))
            self.chips_arbol.append((r, cs.id))
            x = r.right + 8
        if caso is None:
            texto(sup, "No hay historias abiertas.", self.r_centro.center, 16, c["tinta2"], peso=800, ancla="c")
            return
        if self.arbol._arbol_id != caso.id:
            self.arbol.olvidar()
            self.arbol._arbol_id = caso.id
        self.arbol.calcular_layout(caso.arbol)
        n = self.nodo_sel()
        self.arbol.seleccionado = n.id if n is not None and n.id in caso.arbol else None
        self.arbol.dibujar(sup, caso.arbol, p)
        e = caso.arbol.estadisticas()
        texto(sup, f"{e['nodos']} publicaciones, altura {e['altura']}, {e['olas']} olas, le llegó a {e['alcance']} "
                   "personas", (self.r_centro.right - 14, self.r_centro.bottom - 70), 12, c["tinta2"], peso=800,
              ancla="br")
        v = self.arbol
        if v.secuencia:
            paso = v.paso_actual()
            nombres = []
            for nid in v.secuencia[:paso]:
                m = caso.arbol.buscar(nid)
                nombres.append(str(m.autor).split()[0] if m else "?")
            r = pygame.Rect(self.r_centro.x + 12, self.r_centro.bottom - 128, self.r_centro.w - 24, 52)
            sticker(sup, r, c["mango2"], 14, 3, 2)
            texto(sup, v.sec_nombre, (r.x + 12, r.y + 7), 12, c["texto"], peso=900)
            texto(sup, recortar(" › ".join(nombres), 13, r.w - 24, 800), (r.x + 12, r.y + 27), 13, c["tinta2"], peso=800)
        for b in self.b_rec:
            b.activo = not (b.clave == "camino" and (n is None or n.id not in caso.arbol))
            b.dibujar(sup)
