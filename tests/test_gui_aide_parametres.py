"""Tests des écrans Aide et Paramètres (src/gui/vues/aide.py, parametres.py).

Pas de bouton retour propre à ces écrans — couvert par le bandeau de
navigation de `FenetrePrincipale`, testé dans `test_gui_app.py`.
"""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QGroupBox, QLabel, QWidget
from pytestqt.qtbot import QtBot

from src import cache, parametres_affichage, parametres_sources
from src.gui.vues.aide import VueAide
from src.gui.vues.parametres import VueParametres
from src.types import InfoMaj


@pytest.fixture(autouse=True)
def _rediriger_cache_vers_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cache, "CHEMIN_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(cache, "CHEMIN_OFFRES", tmp_path / "offres.json")


@pytest.fixture(autouse=True)
def _rediriger_sources_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VueParametres intègre désormais VueSources (lecture/écriture de
    parametres_sources.json) — jamais le vrai fichier de config pendant
    les tests, même pattern que _rediriger_cache_vers_tmp."""
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")


def _texte_complet(widget: QWidget) -> str:
    """Concatène le texte de tous les QLabel et titres de QGroupBox —
    l'Aide est construite en widgets natifs (QGroupBox/QLabel), pas en
    HTML brut, même pattern que les tuiles composées (_LigneProfil)."""
    labels = " ".join(label.text() for label in widget.findChildren(QLabel))
    titres = " ".join(g.title() for g in widget.findChildren(QGroupBox))
    return f"{labels} {titres}"


def test_aide_affiche_le_vocabulaire_cle(qtbot: QtBot) -> None:
    vue = VueAide()
    qtbot.addWidget(vue)
    texte = _texte_complet(vue)
    assert "IDIV" in texte
    assert "grades supérieurs" in texte
    assert "Suivi de candidature" in texte
    assert "Offre dépubliée" in texte
    assert "Attaché principal territorial" in texte
    assert "Chef de projet informatique" in texte


def test_parametres_sans_cache_indique_jamais_charge(qtbot: QtBot) -> None:
    vue = VueParametres()
    qtbot.addWidget(vue)
    assert "jamais chargé" in vue.label_cache.text()


def test_parametres_carte_maj_visible_par_defaut_bouton_desactive(qtbot: QtBot) -> None:
    vue = VueParametres()
    qtbot.addWidget(vue)
    vue.show()
    assert vue.carte_maj.isVisible() is True
    assert vue.bouton_maj.isEnabled() is False
    assert "à jour" in vue.label_maj_notes.text()


def test_parametres_afficher_maj_montre_et_peuple_la_carte(qtbot: QtBot) -> None:
    vue = VueParametres()
    qtbot.addWidget(vue)
    vue.show()
    info: InfoMaj = {
        "version": "1.2.0",
        "notes": "Corrige un bug.",
        "url_zip": "https://codeberg.org/x.zip",
        "url_publication": "https://codeberg.org/x",
    }

    vue.afficher_maj(info)

    assert vue.carte_maj.isVisible() is True
    assert vue.bouton_maj.isEnabled() is True
    assert "1.2.0" in vue.label_maj_version.text()
    assert "Corrige un bug." in vue.label_maj_notes.text()


def test_parametres_afficher_maj_none_desactive_le_bouton_sans_cacher_la_carte(
    qtbot: QtBot,
) -> None:
    vue = VueParametres()
    qtbot.addWidget(vue)
    vue.show()
    vue.afficher_maj(
        {"version": "1.2.0", "notes": "", "url_zip": "", "url_publication": ""}
    )

    vue.afficher_maj(None)

    assert vue.carte_maj.isVisible() is True
    assert vue.bouton_maj.isEnabled() is False


def test_parametres_rafraichir_cache_erreur_reseau_affiche_avertissement(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _obtenir_organisations_factice(forcer: bool = False) -> None:
        raise RuntimeError("Erreur HTTP 500 lors du chargement de ...")

    monkeypatch.setattr(
        "src.gui.vues.parametres.obtenir_organisations",
        _obtenir_organisations_factice,
    )
    avertissements = []
    monkeypatch.setattr(
        "src.gui.vues.parametres.QMessageBox.warning",
        lambda *a, **k: avertissements.append(True),
    )
    vue = VueParametres()
    qtbot.addWidget(vue)

    vue._rafraichir_cache()

    assert avertissements == [True]


def test_parametres_bouton_maj_emet_demande_maj_immediate(qtbot: QtBot) -> None:
    vue = VueParametres()
    qtbot.addWidget(vue)
    vue.afficher_maj(
        {"version": "1.2.0", "notes": "", "url_zip": "", "url_publication": ""}
    )
    recus = []
    vue.demande_maj_immediate.connect(lambda: recus.append(True))

    vue.bouton_maj.click()

    assert recus == [True]


def test_parametres_theme_preselectionne_le_mode_enregistre(qtbot: QtBot) -> None:
    parametres_affichage.sauvegarder_mode_theme("clair")
    vue = VueParametres()
    qtbot.addWidget(vue)
    assert vue.combo_theme.currentData() == "clair"


def test_parametres_changer_de_theme_enregistre_et_emet(qtbot: QtBot) -> None:
    vue = VueParametres()
    qtbot.addWidget(vue)
    assert vue.combo_theme.currentData() == "auto"

    with qtbot.waitSignal(vue.mode_theme_change) as signal:
        vue.combo_theme.setCurrentIndex(vue.combo_theme.findData("sombre"))

    assert signal.args == ["sombre"]
    assert parametres_affichage.charger_mode_theme() == "sombre"
