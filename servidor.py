"""Servidor dedicado de Alcalde Digital (sin ventana).
Ejecutar:  python servidor.py [--puerto 5050] [--semilla 42]
Los jugadores abren el juego, eligen "Jugar en red" y "Unirse" con la dirección que se muestra.
"""
from alcalde.red.servidor import main

if __name__ == "__main__":
    main()
