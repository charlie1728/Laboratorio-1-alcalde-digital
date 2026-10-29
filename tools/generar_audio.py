"""Genera los efectos de sonido y la música del juego (síntesis, sin grabaciones).

Uso:  python tools/generar_audio.py
Escribe archivos WAV (22 050 Hz, 16 bits, mono) en assets/sonidos/.
"""
import math
import random
import struct
import wave
from pathlib import Path

RATE = 22050
DESTINO = Path(__file__).resolve().parents[1] / "assets" / "sonidos"
rng = random.Random(7)


def nota(n: str) -> float:
    nombres = {"C": 0, "C#": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8,
               "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
    tono, octava = n[:-1], int(n[-1])
    semis = nombres[tono] + 12 * (octava + 1) - 69
    return 440.0 * 2 ** (semis / 12)


def lienzo(seg: float) -> list:
    return [0.0] * int(RATE * seg)


def env(i, n, ataque=0.005, caida=8.0):
    t = i / RATE
    a = min(1.0, t / ataque) if ataque > 0 else 1.0
    return a * math.exp(-caida * t)


def marimba(buf, inicio, f, dur=0.5, vol=0.4, caida=7.0):
    i0 = int(inicio * RATE)
    n = int(dur * RATE)
    for i in range(n):
        if i0 + i >= len(buf):
            break
        t = i / RATE
        e = env(i, n, 0.002, caida)
        v = math.sin(2 * math.pi * f * t) + 0.25 * math.sin(2 * math.pi * f * 4 * t) * math.exp(-40 * t)
        buf[i0 + i] += v * e * vol


def campana(buf, inicio, f, dur=1.0, vol=0.3):
    i0 = int(inicio * RATE)
    for i in range(int(dur * RATE)):
        if i0 + i >= len(buf):
            break
        t = i / RATE
        v = (math.sin(2 * math.pi * f * t) + 0.5 * math.sin(2 * math.pi * f * 2.76 * t) * math.exp(-6 * t)
             + 0.25 * math.sin(2 * math.pi * f * 5.4 * t) * math.exp(-10 * t))
        buf[i0 + i] += v * min(1, t / 0.003) * math.exp(-3.5 * t) * vol


def metal(buf, inicio, f, dur=0.6, vol=0.25):
    """Tono tipo trompeta suave: armónicos que se abren al inicio."""
    i0 = int(inicio * RATE)
    n = int(dur * RATE)
    for i in range(n):
        if i0 + i >= len(buf):
            break
        t = i / RATE
        brillo = min(1, t / 0.05)
        v = sum(math.sin(2 * math.pi * f * k * t) / k * (brillo if k > 1 else 1) for k in range(1, 6))
        e = min(1, t / 0.02) * (1 if t < dur - 0.12 else max(0, (dur - t) / 0.12))
        buf[i0 + i] += v * e * vol * 0.6


def bajo(buf, inicio, f, dur=0.35, vol=0.35):
    i0 = int(inicio * RATE)
    for i in range(int(dur * RATE)):
        if i0 + i >= len(buf):
            break
        t = i / RATE
        v = math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * f * 2 * t)
        buf[i0 + i] += v * min(1, t / 0.006) * math.exp(-5 * t) * vol


def ruido(buf, inicio, dur, vol=0.2, brillo=0.5, caida=30.0):
    i0 = int(inicio * RATE)
    y = 0.0
    for i in range(int(dur * RATE)):
        if i0 + i >= len(buf):
            break
        t = i / RATE
        x = rng.uniform(-1, 1)
        y = y + brillo * (x - y)
        buf[i0 + i] += (x - y if brillo < 0.6 else y) * math.exp(-caida * t) * vol


def barrido(buf, inicio, f0, f1, dur, vol=0.3, onda="sin"):
    i0 = int(inicio * RATE)
    n = int(dur * RATE)
    fase = 0.0
    for i in range(n):
        if i0 + i >= len(buf):
            break
        k = i / n
        f = f0 + (f1 - f0) * k
        fase += 2 * math.pi * f / RATE
        v = math.sin(fase)
        if onda == "cuadrada":
            v = math.tanh(3 * v)
        buf[i0 + i] += v * min(1, i / 60) * (1 - k) ** 1.2 * vol


def guardar(nombre: str, buf: list, normalizar: float = 0.85) -> None:
    pico = max(1e-6, max(abs(v) for v in buf))
    k = normalizar / pico if pico > normalizar else 1.0
    DESTINO.mkdir(parents=True, exist_ok=True)
    with wave.open(str(DESTINO / f"{nombre}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v * k)) * 32767)) for v in buf))
    print(f"  {nombre}.wav  {len(buf) / RATE:.2f} s")


def efectos() -> None:
    b = lienzo(0.06); barrido(b, 0, 1500, 900, 0.05, 0.35); guardar("click", b)
    b = lienzo(0.09); barrido(b, 0, 500, 1300, 0.08, 0.4); guardar("pop", b)
    b = lienzo(0.45); marimba(b, 0, nota("E5"), 0.3, 0.45); marimba(b, 0.09, nota("A5"), 0.35, 0.45)
    marimba(b, 0.18, nota("C#6"), 0.3, 0.35); guardar("bueno", b)
    b = lienzo(0.5); barrido(b, 0, 330, 250, 0.22, 0.32, "cuadrada"); barrido(b, 0.2, 260, 170, 0.28, 0.32, "cuadrada")
    guardar("malo", b)
    b = lienzo(0.9); campana(b, 0, nota("E6"), 0.9, 0.35); guardar("evento", b)
    b = lienzo(0.05); ruido(b, 0, 0.04, 0.4, 0.9, 80); marimba(b, 0, 1800, 0.04, 0.25, 60); guardar("tick", b)
    b = lienzo(0.8)
    for k in range(4):
        barrido(b, k * 0.18, 880 if k % 2 == 0 else 660, 870 if k % 2 == 0 else 650, 0.16, 0.3, "cuadrada")
    guardar("viral", b)
    b = lienzo(1.1)
    for k, n in enumerate(("C5", "E5", "G5", "C6")):
        marimba(b, k * 0.08, nota(n), 0.6, 0.4)
    campana(b, 0.32, nota("G6"), 0.8, 0.18); campana(b, 0.38, nota("C7"), 0.7, 0.12)
    guardar("logro", b)
    b = lienzo(0.4); ruido(b, 0, 0.3, 0.35, 0.3, 10); barrido(b, 0.05, 220, 90, 0.3, 0.4); guardar("rama", b)
    b = lienzo(2.0)
    for k, n in enumerate(("C6", "A5", "G5", "E5", "D5")):
        campana(b, k * 0.22, nota(n), 1.1, 0.22)
    guardar("noche", b)
    b = lienzo(0.7); marimba(b, 0, nota("G5"), 0.5, 0.4); marimba(b, 0.12, nota("C6"), 0.6, 0.45); guardar("turno", b)
    b = lienzo(0.25); marimba(b, 0, nota("A5"), 0.2, 0.35); ruido(b, 0, 0.05, 0.2, 0.9, 60); guardar("votos", b)
    b = lienzo(2.2)
    metal(b, 0.0, nota("G4"), 0.16, 0.3); metal(b, 0.16, nota("G4"), 0.16, 0.3); metal(b, 0.32, nota("C5"), 0.32, 0.32)
    metal(b, 0.64, nota("E5"), 0.2, 0.3); metal(b, 0.84, nota("G5"), 1.2, 0.32)
    metal(b, 0.84, nota("C5"), 1.2, 0.2); metal(b, 0.84, nota("E5"), 1.2, 0.16)
    for t in (0.0, 0.32, 0.84):
        ruido(b, t, 0.3, 0.25, 0.9, 12)
    guardar("victoria", b)
    b = lienzo(0.1); ruido(b, 0, 0.08, 0.35, 0.15, 40); guardar("paso", b)
    b = lienzo(0.3); barrido(b, 0, 180, 70, 0.2, 0.5); ruido(b, 0, 0.1, 0.3, 0.5, 35); guardar("sello", b)


def musica() -> None:
    """Bucle tropical suave: I-vi-IV-V en Do mayor, marimba, bajo y shaker (8 compases)."""
    bpm = 100
    negra = 60 / bpm
    compases = 8
    buf = lienzo(compases * 4 * negra + 0.01)
    acordes = [("C", ["C4", "E4", "G4"], "C2"), ("A", ["A3", "C4", "E4"], "A1"),
               ("F", ["F3", "A3", "C4"], "F1"), ("G", ["G3", "B3", "D4"], "G1")]
    melodia = ["E5", None, "G5", "E5", "D5", None, "C5", None, "A4", None, "C5", "D5", "E5", None, None, None,
               "F5", None, "E5", "C5", "D5", None, "C5", "A4", "G4", None, "B4", "D5", "C5", None, None, None]
    for comp in range(compases):
        _, notas, raiz = acordes[(comp // 2) % 4]
        t0 = comp * 4 * negra
        bajo(buf, t0, nota(raiz), 0.45, 0.32)
        bajo(buf, t0 + 1.5 * negra, nota(raiz[:-1] + str(int(raiz[-1]) + 1)), 0.25, 0.22)
        bajo(buf, t0 + 2 * negra, nota(raiz), 0.45, 0.28)
        patron = [0, 1, 2, 1, 0, 2, 1, 2]
        for k, idx in enumerate(patron):
            marimba(buf, t0 + k * negra / 2, nota(notas[idx]), 0.32, 0.11, 9)
        for k in range(8):
            ruido(buf, t0 + k * negra / 2 + negra / 4, 0.05, 0.05 if k % 2 else 0.035, 0.95, 70)
        barrido(buf, t0, 120, 50, 0.12, 0.25)
        barrido(buf, t0 + 2 * negra, 120, 50, 0.12, 0.18)
    for vuelta in range(compases // 4):
        for k, n in enumerate(melodia):
            if n:
                marimba(buf, vuelta * 16 * negra + k * negra / 2, nota(n), 0.5, 0.16, 5)
    cola = int(0.02 * RATE)
    for i in range(cola):
        buf[-1 - i] *= i / cola
    guardar("musica", buf, 0.6)


if __name__ == "__main__":
    print("Generando sonidos en", DESTINO)
    efectos()
    musica()
