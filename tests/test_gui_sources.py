"""Tests de l'écran Sources (src/gui/vues/sources.py)."""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QLabel
from pytestqt.qtbot import QtBot

from src import parametres_sources
from src.gui.vues.sources import VueSources


@pytest.fixture(autouse=True)
def _rediriger_sources_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")


def test_toutes_les_sources_precochees_par_defaut(qtbot: QtBot) -> None:
    vue = VueSources()
    qtbot.addWidget(vue)
    for case in vue._cases.values():
        assert case.isChecked() is True


def test_une_case_par_source_disponible(qtbot: QtBot) -> None:
    vue = VueSources()
    qtbot.addWidget(vue)
    assert set(vue._cases.keys()) == set(parametres_sources.SOURCES_DISPONIBLES.keys())


def test_decocher_sauvegarde_immediatement(qtbot: QtBot) -> None:
    vue = VueSources()
    qtbot.addWidget(vue)
    vue._cases["emploiterritorial"].setChecked(False)
    etats = parametres_sources.charger_sources_actives()
    assert etats["emploiterritorial"] is False
    assert etats["choisirleservicepublic"] is True


def test_etat_sauvegarde_est_relu_a_la_reconstruction(qtbot: QtBot) -> None:
    parametres_sources.sauvegarder_sources_actives({"emploiterritorial": False})
    vue = VueSources()
    qtbot.addWidget(vue)
    assert vue._cases["emploiterritorial"].isChecked() is False
    assert vue._cases["choisirleservicepublic"].isChecked() is True


def test_sans_titre_naffiche_pas_le_label_titre(qtbot: QtBot) -> None:
    """`afficher_titre=False` : usage intégré (Paramètres), pas de titre
    « Sources » en double avec celui de l'écran parent."""
    vue = VueSources(afficher_titre=False)
    qtbot.addWidget(vue)
    titres = [
        label for label in vue.findChildren(QLabel) if label.property("role") == "titre"
    ]
    assert titres == []


def test_avec_titre_par_defaut_affiche_le_label_titre(qtbot: QtBot) -> None:
    vue = VueSources()
    qtbot.addWidget(vue)
    titres = [
        label for label in vue.findChildren(QLabel) if label.property("role") == "titre"
    ]
    assert len(titres) == 1
    assert titres[0].text() == "Sources"
