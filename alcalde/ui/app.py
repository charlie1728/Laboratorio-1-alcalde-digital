import os

import pygame

from ..controlador import ControladorLocal
from ..modelo.partida import Partida
from .accesibilidad import PanelAccesibilidad
from .ayuda import Ayuda
from .efectos import EFECTOS
from .pantalla_menu import PantallaMenu
from .personajes import civi
from .sonido import sonidos
from .tema import TEMA
from .widgets import Toasts, sticker, texto

ANCHO, ALTO = 1280, 720

SUBTITULOS = {
    "bueno": "Sonido: acierto", "malo": "Sonido: error", "logro": "Sonido: fanfarria de logro",
    "evento": "Sonido: aviso de evento", "viral": "Sonido: alarma de publicación viral",
    "rama": "Sonido: rama retirada", "noche": "Sonido: llega la noche", "turno": "Sonido: cambio de turno",
    "votos": "Sonido: conteo de votos", "victoria": "Sonido: celebración",
}


class App:
    def __init__(self, semilla=None, rondas=8):
        # Al agrandar la ventana, SDL estira la imagen de 1280x720: con "linear" la suaviza
        # en vez de repetir píxeles (bordes y letras serruchados).
        os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "linear")
        pygame.init()
        pygame.display.set_caption("Alcalde Digital")
        try:
            self.pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        try:
            pygame.display.set_icon(civi("feliz", 64))
        except pygame.error:
            pass
        pygame.key.set_repeat(380, 40)
        self.reloj = pygame.time.Clock()
        self.snd = sonidos()
        self.snd.activo = TEMA.op["sonido"]
        self.toasts = Toasts()
        self.ayuda = Ayuda(self)
        self.accesibilidad = PanelAccesibilidad(self)
        self.overlay = None
        self.semilla = semilla
        self.rondas = rondas
        self.corriendo = True
        self.subtitulo = None
        self._fundido_t0 = -10_000
        self.actual = PantallaMenu(self)
        self.snd.musica(TEMA.op["musica"] and TEMA.op["sonido"])

    # ------------------------------------------------------------------ navegación
    def cambiar(self, pantalla):
        self.toasts.items.clear()
        self.overlay = None
        self.actual = pantalla
        self._fundido_t0 = pygame.time.get_ticks()

    def iniciar_local(self, cfg, rondas=None, guia=True):
        from .pantalla_juego import PantallaJuego
        p = Partida(cfg, rondas=rondas or self.rondas, semilla=self.semilla)
        self.cambiar(PantallaJuego(self, ControladorLocal(p), guia=guia))

    def iniciar_red(self, controlador, guia=False):
        from .pantalla_juego import PantallaJuego
        self.cambiar(PantallaJuego(self, controlador, guia=guia))

    def fin_partida(self, controlador):
        from .pantalla_eleccion import PantallaEleccion
        self.cambiar(PantallaEleccion(self, controlador))

    def ir_resumen(self, controlador):
        from .pantalla_resumen import PantallaResumen
        self.cambiar(PantallaResumen(self, controlador))

    def ir_menu(self):
        self.cambiar(PantallaMenu(self))

    def abrir(self, overlay):
        self.overlay = overlay
        if hasattr(overlay, "abrir"):
            overlay.abrir()

    # ------------------------------------------------------------------ sonido con subtítulos
    def sonar(self, nombre):
        self.snd.play(nombre)
        if self.snd.activo and TEMA.op["subtitulos"] and nombre in SUBTITULOS:
            self.subtitulo = (SUBTITULOS[nombre], pygame.time.get_ticks())

    def alternar_sonido(self):
        TEMA.cambiar("sonido", not TEMA.op["sonido"])
        self.snd.activo = TEMA.op["sonido"]
        self.snd.musica(TEMA.op["musica"] and TEMA.op["sonido"])

    # ------------------------------------------------------------------ bucle
    def escribiendo(self):
        return getattr(self.actual, "escribiendo", lambda: False)()

    def paso(self, eventos):
        for e in eventos:
            if e.type == pygame.QUIT:
                self.corriendo = False
                continue
            if self.overlay is not None:
                if self.overlay.evento(e) == "cerrar" or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    self.overlay = None
                continue
            if e.type == pygame.KEYDOWN and not self.escribiendo():
                if e.key == pygame.K_h or e.key == pygame.K_F1:
                    self.abrir(self.ayuda)
                    continue
                if e.key == pygame.K_c:
                    TEMA.alternar_contraste()
                    continue
                if e.key == pygame.K_m:
                    self.alternar_sonido()
                    continue
                if e.key == pygame.K_F11:
                    try:
                        pygame.display.toggle_fullscreen()
                    except pygame.error:
                        pass
                    continue
            self.actual.evento(e)
        if hasattr(self.actual, "actualizar") and self.overlay is None:
            self.actual.actualizar()
        elif hasattr(self.actual, "actualizar_red"):
            self.actual.actualizar_red()
        self.actual.dibujar(self.pantalla)
        if self.overlay is not None:
            self.overlay.dibujar(self.pantalla)
        EFECTOS.dibujar(self.pantalla)
        if not getattr(self.actual, "toasts_propios", False):
            self.toasts.dibujar(self.pantalla, ANCHO // 2 - 220, ALTO - 16, 440, abajo=True)
        self._dibujar_subtitulo()
        edad = pygame.time.get_ticks() - self._fundido_t0
        if edad < 260 and not TEMA.op["menos_movimiento"]:
            velo = pygame.Surface((ANCHO, ALTO))
            velo.fill(TEMA.c["tinta"])
            velo.set_alpha(int(255 * (1 - edad / 260)))
            self.pantalla.blit(velo, (0, 0))

    def _dibujar_subtitulo(self):
        if not self.subtitulo:
            return
        s, t0 = self.subtitulo
        edad = pygame.time.get_ticks() - t0
        if edad > 2200:
            self.subtitulo = None
            return
        c = TEMA.c
        w = 20 + len(s) * 8
        r = pygame.Rect(0, 0, w, 28)
        r.midtop = (ANCHO // 2, 66)
        fondo = (0, 0, 0) if TEMA.alto_contraste else c["tinta"]
        sticker(self.pantalla, r, fondo, radio=14, sombra=0, borde=2,
                color_borde=c["mango"] if TEMA.alto_contraste else c["papel"],
                alpha=230 if edad < 1800 else int(230 * (2200 - edad) / 400))
        texto(self.pantalla, f"[{s}]", r.center, 13, (255, 255, 255), peso=800, ancla="c")

    def ejecutar(self):
        while self.corriendo:
            self.paso(pygame.event.get())
            pygame.display.flip()
            self.reloj.tick(60)
        cerrar = getattr(self.actual, "cerrar", None)
        if cerrar:
            cerrar()
        pygame.quit()
