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
