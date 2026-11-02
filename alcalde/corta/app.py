"""Ventana del juego y paso de una pantalla a otra.

Dibuja al tamaño real de la ventana (sin estirar una imagen pequeña), así se ve nítido en
cualquier pantalla. La ventana arranca maximizada; F11 cambia a pantalla completa.
"""
from __future__ import annotations

import sys

import pygame

from ..ui.dibujo import BLANCO, TINTA, ancho_texto, icono, pildora, texto
from ..ui.personajes import civi
from ..ui.sonido import sonidos
from ..ui.tema import TEMA

# El corte ("pop") no lleva subtítulo: ya se ve en pantalla y llenaría todo de texto.
SUBTITULOS = {
    "malo": "Sonido: error", "logro": "Sonido: premio", "viral": "Sonido: ¡alarma!",
    "rama": "Sonido: el rumor se reenvía", "victoria": "Sonido: celebración", "noche": "Sonido: llega la noche",
    "votos": "Sonido: conteo de votos", "turno": "Sonido: empieza el turno", "evento": "Sonido: aviso",
    "sello": "Sonido: sello de verificado",
}


class AppCorta:
    def __init__(self, semilla=None, duracion=None):
        pygame.init()
        pygame.display.set_caption("Alcalde Digital · Corta la mentira")
        self.completa = False
        self._maximizar = 0
        self.ventana = self._abrir_ventana()
        try:
            pygame.display.set_icon(civi("feliz", 64))
        except pygame.error:
            pass
        self.reloj = pygame.time.Clock()
        self.snd = sonidos()
        self.semilla = semilla
        self.duracion = duracion
        self.corriendo = True
        self.subtitulo = None
        self.logro = None
        self.t = 0.0
        self._fundido = 0.0
        self.aplicar_sonido()
        from .menu import MenuPrincipal
        self.actual = MenuPrincipal(self)

    @property
    def menos_movimiento(self):
        return TEMA.op.get("menos_movimiento", False)

    # -------------------------------------------------------------- ventana
    def _abrir_ventana(self):
        if self.completa:
            try:
                return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except pygame.error:
                self.completa = False
        try:
            escritorio = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, IndexError, AttributeError):
            escritorio = (1280, 720)
        tam = (max(960, escritorio[0] - 40), max(540, escritorio[1] - 110))
        ventana = pygame.display.set_mode(tam, pygame.RESIZABLE)
        if sys.platform == "win32":
            # Maximizar con la API de Windows: ocupa la pantalla sin tapar la barra de tareas.
            try:
                import ctypes
                hwnd = pygame.display.get_wm_info().get("window")
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 1)
                    ctypes.windll.user32.ShowWindow(hwnd, 3)
            except (OSError, AttributeError, pygame.error):
                pass
            self._maximizar = 3
        return pygame.display.get_surface() or ventana

    # -------------------------------------------------------------- sonido
    def aplicar_sonido(self):
        self.snd.activo = TEMA.op["sonido"]
        self.snd.musica(TEMA.op["musica"] and TEMA.op["sonido"])

    def sonar(self, nombre):
        self.snd.play(nombre)
        if self.snd.activo and TEMA.op.get("subtitulos") and nombre in SUBTITULOS:
            self.subtitulo = (SUBTITULOS[nombre], self.t)

    # -------------------------------------------------------------- navegación
    def cambiar(self, pantalla):
        self.actual = pantalla
        self._fundido = 0.25
        pygame.mouse.set_visible(not hasattr(pantalla, "n") or getattr(pantalla, "demo", False))

    def ir_menu(self):
        from .menu import MenuPrincipal
        self.cambiar(MenuPrincipal(self))

    def abrir_mapa(self, campana, resultado=None, cambios=None):
        from .pantalla_mapa import PantallaMapa
        self.cambiar(PantallaMapa(self, campana, resultado, cambios))

    def nueva_campana(self, personaje):
        from .campana import Campana
        from .historia import PantallaHistoria
        c = Campana.nueva(personaje, self.semilla)
        c.guardar()
        # Antes de la primera campaña se cuenta la historia (se puede saltar con Esc).
        self.cambiar(PantallaHistoria(self, personaje, lambda: self.abrir_mapa(c)))

    def jugar_zona(self, campana, zona):
        from .nivel import Nivel
        from .pantalla_nivel import PantallaNivel
        kw = {} if self.duracion is None else dict(duracion=self.duracion)
        n = Nivel(zona, campana.personaje, semilla=campana.semilla * 31 + campana.dia * 7 + len(zona), red=campana.red,
                  mejoras=campana.mejoras, infeccion=campana.infeccion.get(zona, 0), tranquilo=TEMA.op["tranquilo"],
                  mision=campana.mision(zona), **kw)

        def terminar(res):
            if res is None:
                self.abrir_mapa(campana)
                return
            cambios = campana.registrar(res)
            campana.guardar()
            from .contenido import SENALES
            from .logros import REGISTRO
            if len(campana.senales) >= len(SENALES):
                REGISTRO.ganar("coleccion")
            if campana.terminada and (campana.eleccion or {}).get("final") == "oro":
                REGISTRO.ganar("oro")
            self.abrir_mapa(campana, res, cambios)
        self.sonar("turno")
        self.cambiar(PantallaNivel(self, n, terminar))

    def fiesta(self, jugadores):
        from .fiesta import PantallaFiesta
        self.cambiar(PantallaFiesta(self, jugadores))

    def rapido(self, jugador):
        from .rapido import PantallaRapido
        PantallaRapido(self, jugador)

    # -------------------------------------------------------------- bucle
    def paso(self, eventos, dt):
        self.t += dt
        for e in eventos:
            if e.type == pygame.QUIT:
                self.corriendo = False
                continue
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F11:
                    self.completa = not self.completa
                    self.ventana = self._abrir_ventana()
                    continue
                if e.key == pygame.K_m and not getattr(self.actual, "escribiendo", lambda: False)():
                    TEMA.cambiar("sonido", not TEMA.op["sonido"])
                    self.aplicar_sonido()
                    continue
            self.actual.evento(e)
        self.actual.actualizar(dt)
        sup = pygame.display.get_surface()
        self.actual.dibujar(sup)
        self._dibujar_subtitulo(sup)
        self._dibujar_logro(sup)
        if self._fundido > 0:
            v = pygame.Surface(sup.get_size())
            v.fill((30, 20, 80))
            v.set_alpha(round(255 * self._fundido / 0.25))
            sup.blit(v, (0, 0))
            self._fundido = max(0.0, self._fundido - dt)

    def _dibujar_logro(self, sup):
        """Aviso de medalla nueva: baja desde arriba, se queda un rato y se va."""
        from .comunes import estrella
        from .logros import LOGROS, REGISTRO
        if self.logro is None:
            nuevo = REGISTRO.sacar_nuevo()
            if nuevo is None:
                return
            self.logro = (nuevo, self.t)
            self.sonar("logro")
        k, t0 = self.logro
        edad = self.t - t0
        if edad > 3.4:
            self.logro = None
            return
        nombre, ic, desc, _ = LOGROS[k]
        U = sup.get_height() / 720
        baja = min(1.0, edad / 0.35, (3.4 - edad) / 0.35)
        w = max(ancho_texto(desc, 15 * U, 800), ancho_texto(nombre, 24 * U, 700, "titulo")) + 150 * U
        r = pygame.Rect(0, 0, w, 84 * U)
        r.midtop = (sup.get_width() / 2, -90 * U + baja * 196 * U)
        pildora(sup, r, TINTA, round(26 * U))
        pygame.draw.rect(sup, (255, 200, 40), r, max(2, round(4 * U)), border_radius=round(26 * U))
        estrella(sup, (r.x + 46 * U, r.centery), 30 * U, (255, 200, 40), (214, 140, 0))
        icono(sup, ic, (r.x + 46 * U, r.centery + 2 * U), 22 * U, TINTA, 2.8)
        texto(sup, "¡Logro desbloqueado!", (r.x + 88 * U, r.y + 20 * U), 13 * U, (255, 200, 40), 900, ancla="midleft")
        texto(sup, nombre, (r.x + 88 * U, r.y + 44 * U), 24 * U, BLANCO, 700, "titulo", "midleft")
        texto(sup, desc, (r.x + 88 * U, r.y + 66 * U), 15 * U, (220, 214, 250), 800, ancla="midleft")

    def _dibujar_subtitulo(self, sup):
        if not self.subtitulo:
            return
        s, t0 = self.subtitulo
        edad = self.t - t0
        if edad > 1.8:
            self.subtitulo = None
            return
        U = sup.get_height() / 720
        w = len(s) * 9 * U + 30 * U
        r = pygame.Rect(0, 0, w, 30 * U)
        r.midbottom = (sup.get_width() / 2, sup.get_height() - 8 * U)
        pildora(sup, r, TINTA, con_sombra=False, alfa=210)
        texto(sup, f"[{s}]", r.center, 14 * U, BLANCO, 800)

    def ejecutar(self):
        while self.corriendo:
            dt = self.reloj.tick(60) / 1000
            if self._maximizar:
                self._maximizar -= 1
                if self._maximizar == 0 and sys.platform == "win32" and not self.completa:
                    try:
                        import ctypes
                        hwnd = pygame.display.get_wm_info().get("window")
                        if pygame.display.get_surface().get_size() != pygame.display.get_desktop_sizes()[0]:
                            ctypes.windll.user32.ShowWindow(hwnd, 1)
                            ctypes.windll.user32.ShowWindow(hwnd, 3)
                    except (OSError, AttributeError, pygame.error):
                        pass
            self.paso(pygame.event.get(), dt)
            pygame.display.flip()
        cerrar = getattr(self.actual, "cerrar", None)
        if cerrar:
            cerrar()
        pygame.quit()
