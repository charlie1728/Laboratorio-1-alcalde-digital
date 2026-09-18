"""Efectos de sonido sintetizados (no se necesitan archivos de audio).
Cada sonido tiene además un aviso visual (toast), para jugadores sordos o
con el sonido apagado."""
import math
from array import array

import pygame

_RATE = 22050


def _tono(frecs, dur=0.12, vol=0.35, onda="sin"):
    muestras = array("h")
    for f in frecs:
        n = int(_RATE * dur)
        for i in range(n):
            t = i / _RATE
            env = min(1, i / 200) * (1 - i / n) ** 1.5
            if onda == "sq":
                v = 1 if math.sin(2 * math.pi * f * t) > 0 else -1
                v *= 0.5
            else:
                v = math.sin(2 * math.pi * f * t)
            muestras.append(int(v * env * vol * 32767))
    return muestras


class Sonidos:
    def __init__(self):
        self.activo = True
        self.s = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(_RATE, -16, 1, 512)
            freq, fmt, canales = pygame.mixer.get_init()
            defs = {
                "click": _tono([880], 0.04, 0.2),
                "bueno": _tono([660, 880], 0.09),
                "malo": _tono([300, 200], 0.14, 0.3, "sq"),
                "evento": _tono([988], 0.15, 0.25),
                "tick": _tono([1200], 0.03, 0.15),
                "viral": _tono([880, 660, 880, 660], 0.08, 0.3, "sq"),
                "logro": _tono([523, 659, 784, 1046], 0.08),
                "rama": _tono([440, 330, 220], 0.06, 0.25),
            }
            for k, m in defs.items():
                if canales == 2:
                    st = array("h")
                    for v in m:
                        st.append(v)
                        st.append(v)
                    m = st
                self.s[k] = pygame.mixer.Sound(buffer=m.tobytes())
        except Exception:
            self.s = {}

    def play(self, nombre):
        if self.activo and nombre in self.s:
            self.s[nombre].play()


SONIDOS = None


def sonidos() -> Sonidos:
    global SONIDOS
    if SONIDOS is None:
        SONIDOS = Sonidos()
    return SONIDOS
