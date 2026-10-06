@echo off
chcp 65001 >nul
rem Lanceur Windows : double-clic. Bloc entre parenthèses lu en entier avant
rem exécution : une mise à jour peut réécrire ce fichier pendant qu'il tourne.
(
cd /d "%~dp0"
rem Variables posées ici (proxy, premier lancement) : pas dans la console appelante.
setlocal
set "TAMPONNE_PREMIER_LANCEMENT="
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
rem uv ignore le proxy de Windows (réglages Internet, script PAC) : il le reçoit
rem par HTTPS_PROXY, hérité aussi par l'application. Rien en connexion directe.
if not defined HTTPS_PROXY for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$u = [uri]'https://github.com'; $p = [System.Net.WebRequest]::GetSystemWebProxy().GetProxy($u); if ($p -ne $u) { $p.Scheme + '://' + $p.Authority }" 2^>nul`) do (
    set "HTTPS_PROXY=%%P"
    set "HTTP_PROXY=%%P"
)
rem Hors clone git, pas d'outils de développement (mypy, pytest) : uv les
rem retire, ici comme dans src.lanceur qui hérite de la variable.
if not exist .git set "UV_NO_DEV=1"
if not exist .venv (
    set "TAMPONNE_PREMIER_LANCEMENT=1"
    echo Premier lancement : téléchargement de Python et des composants ^(quelques minutes^)…
    uv sync
) else (
    uv sync --quiet
)
if errorlevel 1 (
    powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [void][System.Windows.MessageBox]::Show('Impossible de préparer Tamponné : vérifiez la connexion internet puis relancez.', 'Tamponné', 'OK', 'Error')"
    exit /b 1
)
rem Le lanceur se relance sans console puis rend la main : cette fenêtre se ferme,
rem après un délai au premier lancement, où l'ouverture est plus longue.
.venv\Scripts\python.exe -m src.lanceur
if defined TAMPONNE_PREMIER_LANCEMENT (
    echo Installation terminée. Tamponné s'ouvre dans quelques instants ^(jusqu'à une minute la première fois^)…
    timeout /t 15 /nobreak >nul 2>&1
)
exit /b
)
