@echo off
chcp 65001 >nul
rem Lanceur Windows : double-clic. Bloc entre parenthèses lu en entier avant
rem exécution : une mise à jour peut réécrire ce fichier pendant qu'il tourne.
(
cd /d "%~dp0"
rem Depuis un raccourci ou juste après l'installation, uv n'est pas encore dans le PATH.
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>&1 || (
    echo Installation de uv, le gestionnaire de Python de Tamponné…
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
where uv >nul 2>&1 || (
    powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [void][System.Windows.MessageBox]::Show('Impossible d''installer uv : vérifiez la connexion internet puis relancez Tamponné.', 'Tamponné', 'OK', 'Error')"
    exit /b 1
)
if not exist .venv (
    echo Premier lancement : téléchargement de Python et des composants ^(quelques minutes^)…
    uv sync
) else (
    uv sync --quiet
)
if errorlevel 1 (
    powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [void][System.Windows.MessageBox]::Show('Impossible de préparer Tamponné : vérifiez la connexion internet puis relancez.', 'Tamponné', 'OK', 'Error')"
    exit /b 1
)
rem Le lanceur se relance sans console puis rend la main : cette fenêtre se ferme.
.venv\Scripts\python.exe -m src.lanceur
exit /b
)
