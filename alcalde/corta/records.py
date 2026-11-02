"""Récords del Juego rápido (la tabla de la feria). Se guardan en la carpeta del usuario."""
from __future__ import annotations

import json
import time
from pathlib import Path

ARCHIVO = Path.home() / ".alcalde_digital_records.json"
MAXIMO = 50


def cargar(ruta: Path = ARCHIVO) -> list[dict]:
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        return [d for d in datos if isinstance(d, dict) and "nombre" in d and "puntos" in d]
    except (OSError, ValueError, TypeError):
        return []


def agregar(nombre: str, puntos: int, rol: str, zona: str, estrellas: int = 0, ruta: Path = ARCHIVO) -> int:
    """Guarda un puntaje y devuelve el puesto que ocupó (1 = el mejor). Con empate, el más antiguo va primero."""
    lista = cargar(ruta)
    nuevo = dict(nombre=nombre.strip()[:14] or "Jugador", puntos=int(puntos), rol=rol, zona=zona,
                 estrellas=int(estrellas), fecha=time.strftime("%Y-%m-%d %H:%M"))
    lista.append(nuevo)
    lista.sort(key=lambda d: -d["puntos"])          # sort es estable: con empate se respeta la llegada
    puesto = next(i for i, d in enumerate(lista) if d is nuevo) + 1
    try:
        ruta.write_text(json.dumps(lista[:MAXIMO], ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return puesto


def mejores(n: int = 8, ruta: Path = ARCHIVO) -> list[dict]:
    return cargar(ruta)[:n]
