"""Garde-fous des lanceurs pour la mise à jour depuis la 1.0.x, appliquée
par l'ancien `maj.py` qui réécrit les fichiers sur place pendant que le
lanceur tourne."""

from pathlib import Path

RACINE = Path(__file__).parent.parent

TAILLE_LANCER_SH_1_0_5 = 929
"""bash relit le script à l'ancien décalage une fois sa boucle finie : un
nouveau `lancer.sh` plus long lui ferait exécuter un fragment."""

DEBUT_LANCER_BAT_1_0_5 = (
    "@echo off\n"
    'cd /d "%~dp0"\n'
    "\n"
    ":boucle\n"
    "uv sync --quiet\n"
    "if exist data\\maj_disponible.json (\n"
    "    uv run python -m src.maj --appliquer\n"
    "    if errorlevel 1 echo Mise a jour indisponible, on continue avec la version actuelle. 1>&2\n"
    "    uv sync --quiet\n"
    ")\n"
)
"""cmd reprend la lecture au même décalage après le bloc de mise à jour."""


def test_lancer_sh_pas_plus_long_que_celui_de_la_1_0_5() -> None:
    assert (RACINE / "lancer.sh").stat().st_size <= TAILLE_LANCER_SH_1_0_5


def test_lancer_sh_lu_d_un_bloc_termine_par_exit() -> None:
    lignes = (RACINE / "lancer.sh").read_text(encoding="utf-8").splitlines()
    assert "{" in lignes and lignes[-2:] == ["exit 0", "}"]


def test_lancer_bat_commence_comme_celui_de_la_1_0_5() -> None:
    contenu = (RACINE / "lancer.bat").read_text(encoding="utf-8")
    assert contenu.startswith(DEBUT_LANCER_BAT_1_0_5)
    assert "uv run python -m src.gui.application\n" in contenu


def test_ancien_point_d_entree_conserve() -> None:
    assert "from src.gui.application import main" in (
        RACINE / "src/gui/app.py"
    ).read_text(encoding="utf-8")
