"""Garde-fous des scripts de lancement `Tamponne.command` et `Tamponne.bat`."""

import os
from pathlib import Path

RACINE = Path(__file__).parent.parent


def test_tamponne_command_executable_et_lu_d_un_bloc() -> None:
    """Le bloc `{ … exit 0 }` est lu en entier avant exécution : une mise à
    jour qui réécrit le script pendant qu'il tourne ne change rien."""
    chemin = RACINE / "Tamponne.command"
    assert os.access(chemin, os.X_OK)
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    assert lignes[0] == "#!/bin/bash"
    assert "{" in lignes and lignes[-2:] == ["exit 0", "}"]
    assert "uv run --quiet python -m src.lanceur \\" in lignes


def test_tamponne_command_se_relance_dans_un_terminal_sous_linux() -> None:
    """Double-cliqué sous KDE ou GNOME, le script n'a pas de terminal :
    il s'y relance pour montrer l'installation, une seule fois."""
    contenu = (RACINE / "Tamponne.command").read_text(encoding="utf-8")
    assert 'TAMPONNE_TERMINAL=1 exec "$terminal" "$option" /bin/bash' in contenu
    assert '[ -z "${TAMPONNE_TERMINAL:-}" ]' in contenu


def test_tamponne_bat_lu_d_un_bloc() -> None:
    """cmd relit un `.bat` ligne par ligne, sauf un bloc entre parenthèses,
    analysé en entier : tout le script y tient, sans `goto` ni `%ERRORLEVEL%`
    (développé à l'analyse du bloc)."""
    contenu = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    assert "\r\n" in contenu and "\n" not in contenu.replace("\r\n", "")
    lignes = contenu.splitlines()
    debut = lignes.index("(")
    assert lignes[-1] == ")"
    bloc = "\n".join(lignes[debut:])
    assert "goto" not in bloc.lower() and "%ERRORLEVEL%" not in bloc.upper()
    assert ".venv\\Scripts\\python.exe -m src.lanceur" in bloc


def test_tamponne_bat_transmet_le_proxy_de_windows_a_uv() -> None:
    """uv ne lit pas le proxy de Windows : le lanceur le lui passe par
    `HTTPS_PROXY` avant `uv sync`, sans écraser une valeur déjà définie."""
    contenu = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    lignes = contenu.splitlines()
    detection = next(
        i for i, ligne in enumerate(lignes) if "GetSystemWebProxy()" in ligne
    )
    assert lignes[detection].startswith("if not defined HTTPS_PROXY for /f ")
    assert lignes[detection + 1 : detection + 3] == [
        '    set "HTTPS_PROXY=%%P"',
        '    set "HTTP_PROXY=%%P"',
    ]
    assert detection > lignes.index("(")
    assert detection < next(i for i, ligne in enumerate(lignes) if "uv sync" in ligne)


def test_lanceurs_sans_outils_de_developpement_hors_clone_git() -> None:
    """Une installation n'a pas besoin de mypy ni de pytest : `UV_NO_DEV`,
    posé avant le premier `uv`, vaut aussi pour `src.lanceur`."""
    commande = (RACINE / "Tamponne.command").read_text(encoding="utf-8")
    bat = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    for contenu, garde in (
        (commande, "[ -e .git ] || export UV_NO_DEV=1"),
        (bat, 'if not exist .git set "UV_NO_DEV=1"'),
    ):
        lignes = contenu.splitlines()
        assert garde in lignes
        assert lignes.index(garde) < next(
            i for i, ligne in enumerate(lignes) if ligne.strip().startswith("uv sync")
        )


def test_lanceurs_demandent_de_patienter_au_premier_lancement() -> None:
    """La première ouverture est longue (Qt chargé pour la première fois) :
    la console le dit, et celle de Windows reste ouverte le temps de lire."""
    message = "Installation terminée. Tamponné s'ouvre dans quelques instants"
    commande = (RACINE / "Tamponne.command").read_text(encoding="utf-8")
    assert message in commande
    assert commande.index(message) < commande.index("uv run --quiet python")
    bat = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    lignes = bat.splitlines()
    lancement = lignes.index(".venv\\Scripts\\python.exe -m src.lanceur")
    assert lignes[lancement + 1] == "if defined TAMPONNE_PREMIER_LANCEMENT ("
    assert message in lignes[lancement + 2]
    assert lignes.index("setlocal") < lignes.index('set "TAMPONNE_PREMIER_LANCEMENT="')
