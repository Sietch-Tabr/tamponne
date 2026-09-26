"""Tests de la persistance des sources actives (src/parametres_sources.py)."""

from pathlib import Path

import pytest

from src import parametres_sources


@pytest.fixture(autouse=True)
def _rediriger_sources_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")


def test_charger_sources_actives_absent_retourne_tout_actif() -> None:
    etats = parametres_sources.charger_sources_actives()
    assert etats == {cle: True for cle in parametres_sources.SOURCES_DISPONIBLES}


def test_charger_sources_actives_corrompu_retourne_tout_actif(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chemin = tmp_path / "sources.json"
    chemin.write_text("{ceci n'est pas du json", encoding="utf-8")
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", chemin)
    etats = parametres_sources.charger_sources_actives()
    assert etats == {cle: True for cle in parametres_sources.SOURCES_DISPONIBLES}


def test_sauvegarder_puis_charger_conserve_les_etats() -> None:
    parametres_sources.sauvegarder_sources_actives({"emploiterritorial": False})
    etats = parametres_sources.charger_sources_actives()
    assert etats["emploiterritorial"] is False
    assert etats["choisirleservicepublic"] is True


def test_charger_sources_actives_nouvelle_cle_absente_du_fichier_est_active() -> None:
    # Simule un fichier écrit avant l'ajout d'une nouvelle source connue.
    parametres_sources.sauvegarder_sources_actives({"choisirleservicepublic": False})
    etats = parametres_sources.charger_sources_actives()
    assert etats["emploiterritorial"] is True
    assert etats["choisirleservicepublic"] is False
