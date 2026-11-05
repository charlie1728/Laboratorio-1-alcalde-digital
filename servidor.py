"""Servidor dedicado de Cazabulos en línea (sin ventana).
Ejecutar:  python servidor.py [--puerto 5070]
Los jugadores abren el juego, eligen "En línea" > "Unirme a una sala" y escriben la dirección
que muestra este servidor. El primero que se une es el anfitrión y es quien empieza la partida.
"""
import argparse
import time

from cazabulos.red.protocolo import PUERTO, ips_locales
from cazabulos.red.servidor import Servidor

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Servidor de Cazabulos en línea")
    ap.add_argument("--puerto", type=int, default=PUERTO)
    args = ap.parse_args()
    srv = Servidor(args.puerto)
    print(f"Sala lista en el puerto {args.puerto}. Los jugadores se unen con: {', '.join(ips_locales())}")
    print("Ctrl+C para cerrar.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        srv.cerrar()
