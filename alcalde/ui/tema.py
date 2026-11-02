"""Opciones del jugador (se guardan en la carpeta del usuario para la próxima vez)."""
import json
from pathlib import Path

OPCIONES_DEFECTO = dict(sonido=True, musica=True, tranquilo=False, menos_movimiento=False, subtitulos=True,
                        contraste=False, simbolos=False)

_ARCHIVO = Path.home() / ".alcalde_digital.json"


class Tema:
    def __init__(self):
        self.op = dict(OPCIONES_DEFECTO)
        try:
            guardadas = json.loads(_ARCHIVO.read_text(encoding="utf-8"))
            self.op.update({k: bool(v) for k, v in guardadas.items() if k in OPCIONES_DEFECTO})
        except (OSError, ValueError, AttributeError):
            pass

    def cambiar(self, clave, valor):
        self.op[clave] = valor
        try:
            _ARCHIVO.write_text(json.dumps(self.op), encoding="utf-8")
        except OSError:
            pass


TEMA = Tema()
