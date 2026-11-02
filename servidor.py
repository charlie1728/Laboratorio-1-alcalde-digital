"""Servidor dedicado del duelo en red (sin ventana).
Ejecutar:  python servidor.py [--puerto 5051]
Los jugadores abren el juego, eligen "Duelo en red", escriben la IP que muestra este servidor y pulsan "Unirme".
El primero que se une es el anfitrión: escoge el barrio y empieza el duelo.
"""
import argparse
import time

from alcalde.red.protocolo import ips_locales
from alcalde.red.sala import PUERTO_DUELO, Servidor

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Servidor del duelo en red de Corta la mentira")
    ap.add_argument("--puerto", type=int, default=PUERTO_DUELO)
    args = ap.parse_args()
    srv = Servidor(args.puerto)
    print(f"Servidor listo en el puerto {args.puerto}. Los jugadores se unen con: {', '.join(ips_locales())}")
    print("Ctrl+C para cerrar.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        srv.cerrar()
