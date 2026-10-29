"""Alcalde Digital.
Ejecutar:  python main.py           (partida aleatoria)
           python main.py 42        (semilla fija: la partida se repite igual)
En Windows también se puede abrir con doble clic en jugar.bat.
"""
import subprocess
import sys
import traceback
from pathlib import Path


def _esperar():
    # Con doble clic la consola se cerraría antes de poder leer el mensaje.
    try:
        input("\nPresiona Enter para cerrar...")
    except (EOFError, KeyboardInterrupt):
        pass


def _hay_pygame() -> bool:
    try:
        import pygame  # noqa: F401
        return True
    except ImportError:
        return False


def _otro_python():
    """Otro Python instalado que sí tenga Pygame (con doble clic Windows puede escoger uno sin él)."""
    import shutil
    candidatos = [shutil.which("python"), shutil.which("python3")]
    ejecutable = Path(sys.executable)
    candidatos.append(str(ejecutable.with_name("python.exe")))
    try:
        listado = subprocess.run(["py", "-0p"], capture_output=True, text=True, timeout=10).stdout
        candidatos += [linea.split()[-1] for linea in listado.splitlines() if linea.strip().endswith(".exe")]
    except (OSError, subprocess.SubprocessError):
        pass
    vistos = {str(ejecutable).lower()}
    for c in candidatos:
        if not c or c.lower() in vistos or "windowsapps" in c.lower() or not Path(c).exists():
            continue
        vistos.add(c.lower())
        try:
            if subprocess.run([c, "-c", "import pygame"], capture_output=True, timeout=20).returncode == 0:
                return c
        except (OSError, subprocess.SubprocessError):
            continue
    return None


def _instalar_pygame() -> bool:
    print(f"Este Python no tiene Pygame:\n  {sys.executable}\n")
    try:
        respuesta = input("¿Instalarlo ahora? (S/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        respuesta = "n"
    if respuesta not in ("", "s", "si", "sí", "y", "yes"):
        print(f"\nPara instalarlo a mano:\n  \"{sys.executable}\" -m pip install pygame")
        return False
    ok = subprocess.call([sys.executable, "-m", "pip", "install", "pygame"]) == 0
    if not ok:
        print("\nNo se pudo instalar Pygame en este Python. Abre el juego con jugar.bat o desde una terminal con:"
              "\n  python main.py")
    return ok and _hay_pygame()


if __name__ == "__main__":
    if not _hay_pygame():
        otro = _otro_python()
        if otro:
            sys.exit(subprocess.call([otro, str(Path(__file__).resolve())] + sys.argv[1:]))
        if not _instalar_pygame():
            _esperar()
            sys.exit(1)
    try:
        from alcalde.ui.app import App
        semilla = int(sys.argv[1]) if len(sys.argv) > 1 else None
        App(semilla=semilla).ejecutar()
    except Exception:
        registro = Path(__file__).resolve().parent / "alcalde_error.log"
        registro.write_text(traceback.format_exc(), encoding="utf-8")
        traceback.print_exc()
        print(f"\nEl juego se cerró por un error. Quedó guardado en {registro}")
        _esperar()
        sys.exit(1)
