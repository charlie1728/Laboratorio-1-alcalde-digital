@echo off
rem Abre Alcalde Digital con el Python que esta en el PATH (el mismo de "python main.py").
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python. Instalalo desde https://www.python.org/downloads/ marcando "Add Python to PATH".
    pause
    exit /b 1
)
python main.py %*
if errorlevel 1 pause
