"""Efectos de sonido y música.

Los sonidos están en assets/sonidos (se generan con tools/generar_audio.py, sin
grabaciones externas). Si faltan, se sintetizan tonos simples al iniciar.
"""
import math
from array import array

import pygame

from .recursos import SONIDOS

_RATE = 22050


def _tono(frecs, dur=0.12, vol=0.35, onda="sin"):
    muestras = array("h")
    for f in frecs:
        n = int(_RATE * dur)
        for i in range(n):
            t = i / _RATE
            env = min(1, i / 200) * (1 - i / n) ** 1.5
            if onda == "sq":
                v = 0.5 if math.sin(2 * math.pi * f * t) > 0 else -0.5
            else:
                v = math.sin(2 * math.pi * f * t)
            muestras.append(int(v * env * vol * 32767))
    return muestras


_RESPALDO = {
    "click": ([880], 0.04, 0.2, "sin"), "bueno": ([660, 880], 0.09, 0.35, "sin"),
    "malo": ([300, 200], 0.14, 0.3, "sq"), "evento": ([988], 0.15, 0.25, "sin"),
    "tick": ([1200], 0.03, 0.15, "sin"), "viral": ([880, 660, 880, 660], 0.08, 0.3, "sq"),
    "logro": ([523, 659, 784, 1046], 0.08, 0.35, "sin"), "rama": ([440, 330, 220], 0.06, 0.25, "sin"),
}
NOMBRES = ["click", "bueno", "malo", "evento", "tick", "viral", "logro", "rama", "noche", "turno",
           "votos", "victoria", "paso", "pop", "sello"]


class Sonidos:
    def __init__(self):
        self.activo = True
        self.s = {}
        self._musica_ok = False
        self._sonando = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(_RATE, -16, 2, 512)
            _, _, canales = pygame.mixer.get_init()
            for nombre in NOMBRES:
                ruta = SONIDOS / f"{nombre}.wav"
                if ruta.exists():
                    self.s[nombre] = pygame.mixer.Sound(str(ruta))
                elif nombre in _RESPALDO:
                    m = _tono(*_RESPALDO[nombre])
                    if canales == 2:
                        st = array("h")
                        for v in m:
                            st.append(v)
                            st.append(v)
                        m = st
                    self.s[nombre] = pygame.mixer.Sound(buffer=m.tobytes())
            for nombre, vol in (("tick", 0.5), ("paso", 0.35), ("click", 0.6), ("pop", 0.5)):
                if nombre in self.s:
                    self.s[nombre].set_volume(vol)
            self._musica_ok = (SONIDOS / "musica.wav").exists()
        except Exception:
            self.s = {}

    def play(self, nombre):
        if self.activo and nombre in self.s:
            self.s[nombre].play()

    def musica(self, encender: bool):
        if not self._musica_ok:
            return
        try:
            if encender and not self._sonando:
                pygame.mixer.music.load(str(SONIDOS / "musica.wav"))
                pygame.mixer.music.set_volume(0.32)
                pygame.mixer.music.play(-1, fade_ms=1200)
                self._sonando = True
            elif not encender and self._sonando:
                pygame.mixer.music.fadeout(500)
                self._sonando = False
        except pygame.error:
            self._musica_ok = False


SONIDOS_GLOBALES = None


def sonidos() -> Sonidos:
    global SONIDOS_GLOBALES
    if SONIDOS_GLOBALES is None:
        SONIDOS_GLOBALES = Sonidos()
    return SONIDOS_GLOBALES
