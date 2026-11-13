@echo off
chcp 65001 >nul
rem Lanceur Windows : double-clic. Bloc entre parenthèses lu en entier avant
rem exécution : une mise à jour peut réécrire ce fichier pendant qu'il tourne.
(
cd /d "%~dp0"
rem Variables posées ici (proxy, premier lancement) : pas dans la console appelante.
setlocal
set "TAMPONNE_PREMIER_LANCEMENT="
rem Un seul Tamponné à la fois (double-clic répété) : la console garde le fichier
rem ouvert en écriture jusqu'à sa sortie ; un second lancement ne peut pas
rem l'ouvrir et passe à la branche du bas. Windows le libère à la mort du
rem processus : jamais de verrou périmé. Le lanceur Python prend ensuite le relais.
if not exist data mkdir data
2>nul (
9>"data\.lancement.verrou" (
rem Depuis un raccourci ou juste après l'installation, uv n'est pas encore dans le PATH.
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>&1 || (
    set "TAMPONNE_ANNONCE=Installation de uv, le gestionnaire de Python de Tamponné…" & powershell -NoProfile -Command "try { $l = [Console]::WindowWidth - 1 } catch { $l = 79 }; $e = ' ' * $l; Write-Host ''; Write-Host $e -ForegroundColor White -BackgroundColor DarkBlue; Write-Host ('  ' + $env:TAMPONNE_ANNONCE).PadRight($l) -ForegroundColor White -BackgroundColor DarkBlue; Write-Host $e -ForegroundColor White -BackgroundColor DarkBlue; Write-Host ''"
    powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
where uv >nul 2>&1 || (
    powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [void][System.Windows.MessageBox]::Show('Tamponné n''a pas pu installer uv, l''outil qui télécharge Python et ses composants.' + [char]10 + [char]10 + 'Vérifiez que l''ordinateur est connecté à internet (et le proxy éventuel), puis relancez Tamponné.' + [char]10 + [char]10 + 'Détail : l''installeur de uv (astral.sh) a échoué ; son message exact est affiché dans la fenêtre noire. ' + 'Proxy utilisé : ' + $(if ($env:HTTPS_PROXY) { try { $p = [uri]$env:HTTPS_PROXY; $p.Scheme + '://' + $p.Host + ':' + $p.Port } catch { 'illisible' } } else { 'aucun' }), 'Tamponné', 'OK', 'Error')"
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
    set "TAMPONNE_ANNONCE=Premier lancement : téléchargement de Python et des composants (quelques minutes)…" & powershell -NoProfile -Command "try { $l = [Console]::WindowWidth - 1 } catch { $l = 79 }; $e = ' ' * $l; Write-Host ''; Write-Host $e -ForegroundColor White -BackgroundColor DarkBlue; Write-Host ('  ' + $env:TAMPONNE_ANNONCE).PadRight($l) -ForegroundColor White -BackgroundColor DarkBlue; Write-Host $e -ForegroundColor White -BackgroundColor DarkBlue; Write-Host ''"
    uv sync
) else (
    uv sync
)
rem Un uv trop ancien ne connaît pas la version de Python demandée
rem (required-version) : mis à jour, par l'installeur si l'API GitHub refuse.
if errorlevel 1 (
    set "TAMPONNE_ANNONCE=Mise à jour de uv, le gestionnaire de Python de Tamponné…" & powershell -NoProfile -Command "try { $l = [Console]::WindowWidth - 1 } catch { $l = 79 }; $e = ' ' * $l; Write-Host ''; Write-Host $e -ForegroundColor White -BackgroundColor DarkBlue; Write-Host ('  ' + $env:TAMPONNE_ANNONCE).PadRight($l) -ForegroundColor White -BackgroundColor DarkBlue; Write-Host $e -ForegroundColor White -BackgroundColor DarkBlue; Write-Host ''"
    uv self update || powershell -NoProfile -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    uv sync
)
if errorlevel 1 (
    powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [void][System.Windows.MessageBox]::Show('Tamponné n''a pas pu télécharger Python ou ses composants, même après la mise à jour de uv.' + [char]10 + [char]10 + 'Vérifiez que l''ordinateur est connecté à internet (et le proxy éventuel), puis relancez Tamponné. Si le problème continue, signalez-le sur GitHub avec une capture de la fenêtre noire restée ouverte.' + [char]10 + [char]10 + 'Détail : « uv sync » a échoué ; son message exact est affiché dans la fenêtre noire. ' + 'Proxy utilisé : ' + $(if ($env:HTTPS_PROXY) { try { $p = [uri]$env:HTTPS_PROXY; $p.Scheme + '://' + $p.Host + ':' + $p.Port } catch { 'illisible' } } else { 'aucun' }), 'Tamponné', 'OK', 'Error')"
    exit /b 1
)
rem Le lanceur se relance sans console puis rend la main : cette fenêtre se ferme,
rem après un délai au premier lancement, où l'ouverture est plus longue.
.venv\Scripts\python.exe -m src.lanceur
if defined TAMPONNE_PREMIER_LANCEMENT (
    set "TAMPONNE_ANNONCE=Installation terminée. Tamponné s'ouvre dans quelques instants (jusqu'à une minute la première fois)…" & powershell -NoProfile -Command "try { $l = [Console]::WindowWidth - 1 } catch { $l = 79 }; $e = ' ' * $l; Write-Host ''; Write-Host $e -ForegroundColor White -BackgroundColor DarkBlue; Write-Host ('  ' + $env:TAMPONNE_ANNONCE).PadRight($l) -ForegroundColor White -BackgroundColor DarkBlue; Write-Host $e -ForegroundColor White -BackgroundColor DarkBlue; Write-Host ''"
    timeout /t 15 /nobreak >nul 2>&1
)
exit /b
)
) || (
    set "TAMPONNE_ANNONCE=Tamponné est déjà ouvert, ou en cours d'ouverture. Patientez quelques instants (jusqu'à une minute la première fois), ou cherchez sa fenêtre dans la barre des tâches." & powershell -NoProfile -Command "try { $l = [Console]::WindowWidth - 1 } catch { $l = 79 }; $e = ' ' * $l; Write-Host ''; Write-Host $e -ForegroundColor White -BackgroundColor DarkBlue; Write-Host ('  ' + $env:TAMPONNE_ANNONCE).PadRight($l) -ForegroundColor White -BackgroundColor DarkBlue; Write-Host $e -ForegroundColor White -BackgroundColor DarkBlue; Write-Host ''"
    timeout /t 6 /nobreak >nul 2>&1
    exit /b 0
)
exit /b
)
