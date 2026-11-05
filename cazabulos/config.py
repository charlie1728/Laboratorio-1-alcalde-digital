"""Constantes del juego Cazabulos."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ASSETS = RAIZ / "assets"
DATOS = RAIZ.parent / "datos"          # récords, opciones y logros guardados

ANCHO, ALTO = 1280, 720
FPS = 60
TILE = 16          # tamaño de un tile en la hoja (pixeles nativos)
ESC = 3            # cada pixel nativo se dibuja de 3x3 en pantalla
TS = TILE * ESC    # tamaño de un tile en pantalla (48)

TITULO = "Cazabulos · Alcalde Digital"

# Colores de interfaz
TINTA = (28, 20, 48)
TINTA_SUAVE = (60, 50, 92)
BLANCO = (255, 255, 255)
CREMA = (255, 248, 230)
AMARILLO = (255, 205, 50)
NARANJA = (255, 140, 50)
ROJO = (236, 70, 80)
VERDE = (70, 200, 110)
AZUL = (70, 140, 255)
ROSA = (255, 96, 170)
MORADO = (130, 70, 230)
MORADO_OSCURO = (52, 22, 96)
CIELO = (120, 200, 255)

# Ronda
DURACION_RONDA = 120        # segundos por turno (se puede cambiar en el menú)
VELOCIDAD_JUGADOR = 78      # pixeles nativos por segundo
VELOCIDAD_BULO = 34
