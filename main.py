"""Alcalde Digital.
Ejecutar:  python main.py           (partida aleatoria)
           python main.py 42        (semilla fija: la partida se repite igual)
"""
import sys

from alcalde.ui.app import App

if __name__ == "__main__":
    semilla = int(sys.argv[1]) if len(sys.argv) > 1 else None
    App(semilla=semilla).ejecutar()
