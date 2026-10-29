import sys

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
        pygame.init()
        pygame.display.set_caption("Alcalde Digital")
        # La ventana arranca maximizada. El juego se dibuja en un lienzo de 720 de alto con la
        # misma forma de la ventana: la pantalla de 1280x720 va centrada y los fondos (cielo,
        # pasto, calle, gente) se dibujan de borde a borde, así que no quedan franjas.
        self.completa = False
        self._maximizar = 0
        self.ventana = self._abrir_ventana()
        self.lienzo = None
        self._escala = (1.0, 0, 0, 0)
        self._ajustar_lienzo()
        self._instalar_raton()
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

    def _abrir_ventana(self):
        if self.completa:
            try:
                return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            except pygame.error:
                self.completa = False
        try:
            escritorio = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, IndexError, AttributeError):
            escritorio = (ANCHO, ALTO)
        tam = (max(640, escritorio[0] - 40), max(360, escritorio[1] - 110))
        ventana = pygame.display.set_mode(tam, pygame.RESIZABLE)
        if sys.platform == "win32":
            # Maximizar con la API de Windows: ocupa la pantalla sin tapar la barra de tareas.
            # (pygame._sdl2.Window.from_display_module() no sirve: al liberarse destruye la ventana.)
            try:
                import ctypes
                hwnd = pygame.display.get_wm_info().get("window")
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 1)   # restaurar (si venía de pantalla completa)
                    ctypes.windll.user32.ShowWindow(hwnd, 3)   # maximizar
            except (OSError, AttributeError, pygame.error):
                pass
            self._maximizar = 3          # al volver de F11 Windows a veces ignora el primer intento
        return pygame.display.get_surface() or ventana

    def alternar_pantalla_completa(self):
        """F11: pantalla completa de verdad, o volver a la ventana maximizada."""
        self.completa = not self.completa
        self.ventana = self._abrir_ventana()

    def _instalar_raton(self):
        """El ratón llega en coordenadas de la ventana; el juego trabaja en las del lienzo."""
        real = pygame.mouse.get_pos
        self._raton_real = real

        def en_lienzo():
            return self.a_lienzo(real())
        pygame.mouse.get_pos = en_lienzo

    def _ajustar_lienzo(self):
        ventana = pygame.display.get_surface()
        w, h = ventana.get_size() if ventana else (ANCHO, ALTO)
        ancho = max(ANCHO, min(round(ALTO * w / max(1, h)), ALTO * 3))
        if self.lienzo is None or self.lienzo.get_width() != ancho:
            self.lienzo = pygame.Surface((ancho, ALTO)).convert()
            self.pantalla = self.lienzo.subsurface(((ancho - ANCHO) // 2, 0, ANCHO, ALTO))

    def a_lienzo(self, pos):
        """Coordenadas de la ventana a coordenadas de la pantalla de 1280x720."""
        k, ox, oy, recorte = self._escala
        return (round((pos[0] - ox) / k) - recorte, round((pos[1] - oy) / k))

    def _convertir(self, e):
        if hasattr(e, "pos") and e.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            datos = dict(e.__dict__)
            datos["pos"] = self.a_lienzo(e.pos)
            return pygame.event.Event(e.type, datos)
        return e

    def _presentar(self):
        ventana = pygame.display.get_surface()
        w, h = ventana.get_size()
        lw, lh = self.lienzo.get_size()
        k = min(w / lw, h / lh)
        dw, dh = round(lw * k), round(lh * k)
        ox, oy = (w - dw) // 2, (h - dh) // 2
        self._escala = (k, ox, oy, (lw - ANCHO) // 2)
        if ox > 0 or oy > 0:
            # Solo en ventanas más altas que anchas: se repite la fila de arriba y la de abajo.
            ventana.blit(pygame.transform.scale(self.lienzo.subsurface((0, 0, lw, 1)), (w, oy + 1)), (0, 0))
            ventana.blit(pygame.transform.scale(self.lienzo.subsurface((0, lh - 1, lw, 1)), (w, h - oy - dh + 1)),
                         (0, oy + dh - 1))
        if (dw, dh) == (lw, lh):
            ventana.blit(self.lienzo, (ox, oy))
        else:
            ventana.blit(pygame.transform.smoothscale(self.lienzo, (dw, dh)), (ox, oy))

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
                    self.alternar_pantalla_completa()
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
            destino = self.pantalla.get_parent() or self.pantalla
            velo = pygame.Surface(destino.get_size())
            velo.fill(TEMA.c["tinta"])
            velo.set_alpha(int(255 * (1 - edad / 260)))
            destino.blit(velo, (0, 0))

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
            if getattr(self, "_maximizar", 0):
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
            self._ajustar_lienzo()
            self.paso([self._convertir(e) for e in pygame.event.get()])
            self._presentar()
            pygame.display.flip()
            self.reloj.tick(60)
        cerrar = getattr(self.actual, "cerrar", None)
        if cerrar:
            cerrar()
        pygame.quit()
