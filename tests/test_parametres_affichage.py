"""Tests des préférences d'affichage (src/parametres_affichage.py).

`CHEMIN_AFFICHAGE` est redirigé vers un dossier temporaire par la
fixture automatique de `conftest.py`.
"""

import json

import pytest

from src import parametres_affichage
from src.parametres_affichage import charger_mode_theme, sauvegarder_mode_theme


def test_charger_mode_theme_sans_fichier_retourne_auto():
    assert charger_mode_theme() == "auto"


@pytest.mark.parametrize("mode", ["auto", "sombre", "clair"])
def test_sauvegarder_puis_charger_mode_theme_restitue_le_choix(mode):
    sauvegarder_mode_theme(mode)
    assert charger_mode_theme() == mode


def test_charger_mode_theme_valeur_inconnue_retourne_auto():
    parametres_affichage.CHEMIN_AFFICHAGE.write_text(
        json.dumps({"theme": "fluo"}), encoding="utf-8"
    )
    assert charger_mode_theme() == "auto"


def test_charger_mode_theme_fichier_corrompu_retourne_auto(capsys):
    parametres_affichage.CHEMIN_AFFICHAGE.write_text("{pas du json", encoding="utf-8")
    assert charger_mode_theme() == "auto"
    assert "affichage.json" in capsys.readouterr().err
