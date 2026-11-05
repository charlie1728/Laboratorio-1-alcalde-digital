@echo off
rem Abre Cazabulos (Alcalde Digital) sin dejar una consola abierta detras del juego.
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python. Instalalo desde https://www.python.org/downloads/ marcando "Add Python to PATH".
    pause
    exit /b 1
)
rem Si falta Pygame, main.py lo explica y ofrece instalarlo: eso necesita la consola.
python -c "import pygame" >nul 2>nul
if errorlevel 1 (
    python main.py %*
    if errorlevel 1 pause
    exit /b
)
rem La primera vez se crea el acceso directo "Cazabulos" con el icono del juego.
if not exist "Cazabulos.lnk" python crear_acceso_directo.py >nul 2>nul
where pythonw >nul 2>nul
if errorlevel 1 (
    python main.py %*
) else (
    start "" pythonw main.py %*
)
