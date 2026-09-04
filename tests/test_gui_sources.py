"""Tests de l'écran Sources (src/gui/vues/sources.py)."""

import pytest

from src import parametres_sources
from src.gui.vues.sources import VueSources


@pytest.fixture(autouse=True)
def _rediriger_sources_vers_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")


def test_toutes_les_sources_precochees_par_defaut(qtbot):
    vue = VueSources()
    qtbot.addWidget(vue)
    for case in vue._cases.values():
        assert case.isChecked() is True


def test_une_case_par_source_disponible(qtbot):
    vue = VueSources()
    qtbot.addWidget(vue)
    assert set(vue._cases.keys()) == set(parametres_sources.SOURCES_DISPONIBLES.keys())


def test_decocher_sauvegarde_immediatement(qtbot):
    vue = VueSources()
    qtbot.addWidget(vue)
    vue._cases["emploiterritorial"].setChecked(False)
    etats = parametres_sources.charger_sources_actives()
    assert etats["emploiterritorial"] is False
    assert etats["choisirleservicepublic"] is True


def test_etat_sauvegarde_est_relu_a_la_reconstruction(qtbot):
    parametres_sources.sauvegarder_sources_actives({"emploiterritorial": False})
    vue = VueSources()
    qtbot.addWidget(vue)
    assert vue._cases["emploiterritorial"].isChecked() is False
    assert vue._cases["choisirleservicepublic"].isChecked() is True
