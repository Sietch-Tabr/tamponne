@echo off
cd /d "%~dp0"

:boucle
uv sync --quiet
if exist data\maj_disponible.json (
    uv run python -m src.maj --appliquer
    if errorlevel 1 echo Mise a jour indisponible, on continue avec la version actuelle. 1>&2
    uv sync --quiet
)
uv run python -m src.gui.app
if %ERRORLEVEL%==42 goto boucle
