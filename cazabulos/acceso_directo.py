"""Crea el acceso directo "Cazabulos" con el ícono del juego (solo Windows).

Abre el juego con pythonw, así no queda una consola negra detrás de la ventana.
    python -m cazabulos.acceso_directo               -> lo crea junto a main.py
    python -m cazabulos.acceso_directo --escritorio  -> también en el Escritorio
jugar.bat lo crea solo la primera vez.
"""
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent          # la carpeta del proyecto (donde está main.py)
ICONO = Path(__file__).resolve().parent / "assets" / "icono.ico"


def _pythonw():
    candidato = Path(sys.executable).with_name("pythonw.exe")
    if candidato.exists():
        return candidato
    otro = shutil.which("pythonw")
    return Path(otro) if otro else Path(sys.executable)


def crear(destino: Path) -> None:
    ps = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
        "$s.TargetPath = '{exe}';"
        "$s.Arguments = '\"{main}\"';"
        "$s.WorkingDirectory = '{dir}';"
        "$s.IconLocation = '{ico},0';"
        "$s.Description = 'Cazabulos - Alcalde Digital';"
        "$s.Save()"
    ).format(lnk=destino, exe=_pythonw(), main=AQUI / "main.py", dir=AQUI, ico=ICONO)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                   check=True, capture_output=True)


def escritorio() -> Path:
    salida = subprocess.run(["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                            capture_output=True, text=True, check=True).stdout.strip()
    return Path(salida)


if __name__ == "__main__":
    if not sys.platform.startswith("win"):
        print("El acceso directo es para Windows. En otros sistemas: python main.py")
        sys.exit(0)
    destinos = [AQUI / "Cazabulos.lnk"]
    if "--escritorio" in sys.argv:
        destinos.append(escritorio() / "Cazabulos.lnk")
    for d in destinos:
        crear(d)
        print(f"Acceso directo creado: {d}")
