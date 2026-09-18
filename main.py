"""Alcalde Digital — El árbol de mutaciones.
Ejecutar:  python main.py
"""
import sys

from alcalde.ui.app import App

if __name__ == "__main__":
    semilla = int(sys.argv[1]) if len(sys.argv) > 1 else None
    App(semilla=semilla).ejecutar()
