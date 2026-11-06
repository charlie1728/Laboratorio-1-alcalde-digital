"""Sonidos y música sintetizados al vuelo con numpy (no hace falta ningún archivo de audio).

Cada sonido tiene un subtítulo para el modo de subtítulos (componente inclusivo para quien
no oye bien o juega sin volumen en la feria).
"""

import pygame

try:
    import numpy as np
except ImportError:          # sin numpy el juego funciona igual, solo que sin sonido
    np = None

FR = 22050
SUBTITULOS = {
    "pito": "¡PIII!", "explosion": "¡BUUUM!", "alarma": "¡ALARMA!", "contagio": "¡oh no!",
    "pop": "¡pop!", "cadena": "¡pop-pop-pop!", "antena": "bzzz...", "pelea": "¡grrr!", "paz": "¡paz!",
    "reenvio": "zuum", "golpe": "¡clang!", "viral_mal": "¡se regó!", "victoria": "¡bien!",
}


def _env(n, ataque=0.01, caida=0.2):
    t = np.arange(n) / FR
    a = np.clip(t / max(ataque, 1e-4), 0, 1)
    d = np.exp(-t / max(caida, 1e-4))
    return a * d


def _tono(f, dur, forma="sq", vol=0.4, caida=0.2, desliz=0.0):
    n = int(FR * dur)
    t = np.arange(n) / FR
    frec = f * (1 + desliz * t / max(dur, 1e-4))
    fase = 2 * np.pi * np.cumsum(frec) / FR
    if forma == "sq":
        w = np.sign(np.sin(fase)) * 0.6
    elif forma == "tri":
        w = 2 / np.pi * np.arcsin(np.sin(fase))
    elif forma == "ruido":
        w = np.random.RandomState(int(f)).uniform(-1, 1, n)
    else:
        w = np.sin(fase)
    return w * _env(n, 0.004, caida) * vol


def _junta(*partes, separacion=0.0):
    out = []
    for p in partes:
        out.append(p)
        if separacion:
            out.append(np.zeros(int(FR * separacion)))
    return np.concatenate(out)


def _mezcla(*ondas):
    n = max(len(o) for o in ondas)
    out = np.zeros(n)
    for o in ondas:
        out[:len(o)] += o
    return out


def _crear():
    s = {}
    s["lanzar"] = _tono(500, 0.12, "tri", 0.25, 0.06, desliz=1.2)
    s["pop"] = _mezcla(_tono(900, 0.09, "sq", 0.25, 0.04, desliz=-0.5), _tono(1400, 0.06, "sin", 0.2, 0.03))
    s["cadena"] = _junta(*[_tono(700 + 160 * k, 0.07, "sq", 0.22, 0.05) for k in range(5)])
    s["recoger"] = _junta(_tono(880, 0.06, "sq", 0.2, 0.05), _tono(1320, 0.1, "sq", 0.2, 0.08))
    s["compartir"] = _junta(*[_tono(f, 0.08, "sq", 0.2, 0.08) for f in (523, 659, 784, 1046)])
    s["mal"] = _junta(_tono(300, 0.15, "sq", 0.3, 0.12), _tono(200, 0.3, "sq", 0.3, 0.25))
    s["contagio"] = _tono(420, 0.35, "tri", 0.3, 0.2, desliz=-0.5)
    s["reenvio"] = _tono(300, 0.25, "sin", 0.18, 0.2, desliz=1.5)
    s["antena"] = _mezcla(_tono(120, 0.3, "sq", 0.12, 0.25), _tono(60, 0.3, "ruido", 0.06, 0.2))
    s["golpe"] = _mezcla(_tono(200, 0.12, "sq", 0.3, 0.08), _tono(80, 0.1, "ruido", 0.2, 0.05))
    s["explosion"] = _mezcla(_tono(100, 0.8, "ruido", 0.5, 0.35), _tono(70, 0.6, "sq", 0.25, 0.3, desliz=-0.5))
    s["pito"] = _mezcla(_tono(440, 0.35, "sq", 0.12, 0.5), _tono(554, 0.35, "sq", 0.12, 0.5))
    s["tic"] = _tono(1000, 0.05, "sq", 0.15, 0.03)
    s["cuenta"] = _tono(660, 0.15, "sq", 0.25, 0.1)
    s["ya"] = _junta(_tono(880, 0.1, "sq", 0.25), _tono(1320, 0.3, "sq", 0.25, 0.2))
    s["listo"] = _junta(*[_tono(f, 0.06, "tri", 0.3, 0.06) for f in (784, 988, 1175, 1568)])
    s["poder"] = _mezcla(_tono(200, 0.6, "sq", 0.2, 0.4, desliz=3.0), _tono(400, 0.5, "tri", 0.2, 0.3, desliz=2.0))
    s["paz"] = _junta(*[_tono(f, 0.12, "sin", 0.3, 0.15) for f in (659, 784, 988)])
    s["pelea"] = _mezcla(_tono(150, 0.3, "sq", 0.2, 0.2), _tono(160, 0.3, "sq", 0.2, 0.2))
    s["alarma"] = _junta(*[_tono(f, 0.15, "sq", 0.22, 0.2) for f in (880, 660, 880, 660)])
    s["viral_mal"] = _junta(*[_tono(f, 0.1, "sq", 0.22, 0.1) for f in (600, 500, 400, 300, 200)])
    s["victoria"] = _junta(*[_tono(f, 0.1, "sq", 0.22, 0.1) for f in (523, 659, 784)], _tono(1046, 0.4, "sq", 0.22, 0.3))
    s["fin"] = _junta(_tono(784, 0.15, "sq", 0.25), _tono(523, 0.4, "sq", 0.25, 0.3))
    s["click"] = _tono(700, 0.04, "sq", 0.15, 0.02)
    s["mover"] = _tono(500, 0.03, "tri", 0.15, 0.02)
    s["fanfarria"] = _junta(*[_tono(f, 0.14, "sq", 0.25, 0.12) for f in (523, 523, 784, 659, 784, 1046)])
    return s


def _musica():
    """Un loop alegre de 16 compases (bajo + melodía + percusión)."""
    bpm = 132
    negra = 60 / bpm
    total = int(FR * negra * 4 * 16)
    out = np.zeros(total)
    acordes = [(262, 330, 392), (220, 262, 330), (175, 220, 262), (196, 247, 294)] * 4
    melodia = [523, 0, 659, 587, 523, 0, 440, 0, 523, 587, 659, 0, 784, 659, 587, 0,
               440, 0, 523, 494, 440, 0, 392, 0, 440, 523, 587, 0, 659, 587, 523, 0] * 2
    for c, ac in enumerate(acordes):
        base = int(FR * negra * 4 * c)
        for k in range(8):
            f = ac[0] / 2 if k % 2 == 0 else ac[2] / 2
            o = _tono(f, negra / 2, "tri", 0.18, 0.15)
            i = base + int(FR * negra / 2 * k)
            out[i:i + len(o)] += o[:max(0, total - i)]
        for k in range(4):
            o = _tono(60, 0.05, "ruido", 0.06 if k % 2 else 0.1, 0.03)
            i = base + int(FR * negra * k)
            out[i:i + len(o)] += o[:max(0, total - i)]
    paso = negra / 2
    for k, f in enumerate(melodia):
        if not f:
            continue
        o = _tono(f, paso * 0.95, "sq", 0.07, 0.18)
        i = int(FR * paso * k)
        out[i:i + len(o)] += o[:max(0, total - i)]
    return out


class Sonido:
    def __init__(self):
        self.ok = False
        self.efectos = {}
        self.vol_efectos = 0.8
        self.vol_musica = 0.45
        self.musica = None
        self.canal_musica = None
        if np is None:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(FR, -16, 1, 512)
            self.ok = True
        except pygame.error:
            return
        try:
            for k, onda in _crear().items():
                self.efectos[k] = self._a_sonido(onda)
            self.musica = self._a_sonido(_musica() * 0.9)
        except Exception:
            self.ok = False

    def _a_sonido(self, onda):
        datos = np.clip(onda * 32767, -32767, 32767).astype(np.int16)
        canales = pygame.mixer.get_init()[2]
        if canales == 2:
            datos = np.column_stack([datos, datos])
        return pygame.sndarray.make_sound(np.ascontiguousarray(datos))

    def tocar(self, nombre):
        if not self.ok or nombre not in self.efectos:
            return
        snd = self.efectos[nombre]
        snd.set_volume(self.vol_efectos)
        snd.play()

    def musica_on(self):
        if not self.ok or self.musica is None:
            return
        if self.canal_musica is None or not self.canal_musica.get_busy():
            self.canal_musica = self.musica.play(loops=-1)
        if self.canal_musica:
            self.canal_musica.set_volume(self.vol_musica)

    def musica_off(self):
        if self.canal_musica:
            self.canal_musica.stop()
            self.canal_musica = None

    def volumen_musica(self, v):
        self.vol_musica = v
        if self.canal_musica:
            self.canal_musica.set_volume(v)
