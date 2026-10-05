"""Tests de src/gui/controleur_reglages.py : sources, préférences,
avis de mise à jour et rafraîchissement du cache des organisations."""

from datetime import date
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from src import parametres_affichage, parametres_sources
from src.gui import controleur_reglages, travailleurs
from src.gui.controleur_reglages import (
    MESSAGE_CACHE_INDISPONIBLE,
    ControleurReglages,
)
from src.gui.pont import Pont
from src.types import InfoMaj, Organisations

INFO: InfoMaj = {
    "version": "2.0.1",
    "notes": "- Correctifs",
    "url_zip": "https://codeberg.org/archive.zip",
    "url_publication": "https://codeberg.org/release",
}


@pytest.fixture(autouse=True)
def _environnement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    monkeypatch.setattr(controleur_reglages, "version_locale", lambda: "2.0.0")
    monkeypatch.setattr(controleur_reglages, "date_avis", lambda: date(2026, 10, 4))


def test_sources_toutes_actives_par_defaut_dans_l_ordre(qapp: QApplication) -> None:
    reglages = ControleurReglages()
    cles = [s["cle"] for s in reglages.property("sources")]
    assert cles == list(parametres_sources.SOURCES_DISPONIBLES)
    assert all(reglages.property("sources_actives")[cle] for cle in cles)


def test_basculer_source_enregistre_aussitot(qapp: QApplication) -> None:
    reglages = ControleurReglages()
    reglages.basculer_source("fhf")
    assert parametres_sources.charger_sources_actives()["fhf"] is False
    assert reglages.property("sources_actives")["fhf"] is False


def test_basculer_source_inconnue_ignoree(qapp: QApplication) -> None:
    reglages = ControleurReglages()
    reglages.basculer_source("inconnue")
    assert not parametres_sources.CHEMIN_SOURCES.exists()


def test_definir_reduire_animations_persiste(qapp: QApplication) -> None:
    reglages = ControleurReglages()
    reglages.definir_reduire_animations(True)
    assert parametres_affichage.charger_reduire_animations() is True
    assert ControleurReglages().property("reduire_animations") is True


def test_avis_sans_publication_annonce_version_a_jour(qapp: QApplication) -> None:
    reglages = ControleurReglages()
    assert reglages.property("avis") == {
        "disponible": False,
        "objet": "version 2.0.0 installée, rien de plus récent.",
    }
    assert reglages.property("pastille") is False


def test_afficher_avis_reprend_version_date_et_notes(qapp: QApplication) -> None:
    reglages = ControleurReglages()
    reglages.afficher_avis(INFO)
    assert reglages.property("avis") == {
        "disponible": True,
        "numero": "Avis n° 2.0.1",
        "date": "04/10/2026",
        "objet": "version 2.0.1 disponible (installée : 2.0.0).",
        "notes": "- Correctifs",
    }
    assert reglages.property("pastille") is True


def test_afficher_avis_sans_notes_le_signale(qapp: QApplication) -> None:
    reglages = ControleurReglages()
    reglages.afficher_avis({**INFO, "notes": ""})
    assert reglages.property("avis")["notes"] == "Pas de notes de version."


def test_reporter_maj_efface_la_pastille(qapp: QApplication) -> None:
    reglages = ControleurReglages()
    reglages.afficher_avis(INFO)
    reglages.reporter_maj()
    assert reglages.property("pastille") is False
    assert reglages.property("avis")["disponible"] is True


def test_installer_maj_demande_a_quitter(qapp: QApplication, qtbot: QtBot) -> None:
    reglages = ControleurReglages()
    reglages.afficher_avis(INFO)
    with qtbot.waitSignal(reglages.quitter_demande, timeout=1000):
        reglages.installer_maj()
    assert reglages.redemarrage_demande is True


def test_installer_maj_sans_avis_ne_fait_rien(qapp: QApplication, qtbot: QtBot) -> None:
    reglages = ControleurReglages()
    with qtbot.assertNotEmitted(reglages.quitter_demande):
        reglages.installer_maj()
    assert reglages.redemarrage_demande is False


def test_verifier_mise_a_jour_affiche_l_avis_trouve(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(travailleurs, "verifier_derniere_publication", lambda: INFO)
    monkeypatch.setattr(travailleurs, "ecrire_maj_disponible", lambda _info: None)
    reglages = ControleurReglages()
    with qtbot.waitSignal(reglages.etat_change, timeout=5000):
        reglages.verifier_mise_a_jour()
    reglages.arreter()
    assert reglages.property("avis")["disponible"] is True


def test_rafraichir_cache_transmet_les_organisations(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    orgas: Organisations = {"Ministère": {"Direction": 12}}
    monkeypatch.setattr(
        controleur_reglages, "obtenir_organisations", lambda forcer=False: orgas
    )
    reglages = ControleurReglages()
    with qtbot.waitSignal(reglages.organisations_rafraichies, timeout=5000) as signal:
        reglages.rafraichir_cache()
        assert reglages.property("cache_en_cours") is True
    reglages.arreter()
    assert signal.args == [orgas]
    assert reglages.property("cache_en_cours") is False
    assert reglages.property("message_cache") == ""


def test_rafraichir_cache_en_echec_affiche_un_message(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    def echouer(forcer: bool = False) -> Organisations:
        raise RuntimeError("site inaccessible")

    monkeypatch.setattr(controleur_reglages, "obtenir_organisations", echouer)
    reglages = ControleurReglages()
    with qtbot.waitSignal(reglages.etat_change, timeout=5000):
        reglages.rafraichir_cache()
    qtbot.waitUntil(lambda: not reglages.property("cache_en_cours"), timeout=5000)
    reglages.arreter()
    assert reglages.property("message_cache") == MESSAGE_CACHE_INDISPONIBLE


def test_pont_transmet_le_cache_rafraichi_a_la_recherche(qapp: QApplication) -> None:
    pont = Pont()
    orgas: Organisations = {"Ministère": {"Direction": 12}}
    pont.reglages_controleur.organisations_rafraichies.emit(orgas)
    groupes = pont.property("recherche").groupes_selection("organisations")
    assert groupes[0]["elements"][0]["valeur"] == "Ministère - Direction"


def test_pont_pastille_suit_l_avis(qapp: QApplication) -> None:
    pont = Pont()
    assert pont.property("mise_a_jour_disponible") is False
    pont.reglages_controleur.afficher_avis(INFO)
    assert pont.property("mise_a_jour_disponible") is True
    pont.reglages_controleur.reporter_maj()
    assert pont.property("mise_a_jour_disponible") is False
