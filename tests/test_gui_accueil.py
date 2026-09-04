"""Tests de l'écran Accueil (src/gui/vues/accueil.py).

Isolé de `data/profils.json` réel (fixture autouse, même pattern que
`test_cache.py`/l'ancien `test_tui_accueil.py`).
"""

import pytest
from PySide6.QtWidgets import QLabel, QWidget

from src import profils
from src.gui.vues.accueil import VueAccueil


def _texte_complet(widget: QWidget) -> str:
    """Concatène le texte de tous les QLabel d'une rangée composée
    (`_LigneProfil`), pour vérifier son contenu sans dépendre de sa
    disposition interne exacte."""
    return " ".join(label.text() for label in widget.findChildren(QLabel))


@pytest.fixture(autouse=True)
def _rediriger_profils_vers_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(profils, "CHEMIN_PROFILS", tmp_path / "profils.json")


_PROFIL_TEST: dict = {
    "label": "DGFiP Hérault — IDIV",
    "categories": ["A"],
    "domaines": [],
    "localisations": ["Hérault"],
    "organisations": [],
    "versant": "etat",
    "types_poste": None,
    "experience": "",
    "date_publication": "",
    "management": False,
    "teletravail": False,
    "query": "IDIV",
    "cree_le": "2026-08-01",
    "nb_nouvelles": 2,
}


def test_accueil_sans_profil_affiche_un_message(qtbot):
    vue = VueAccueil()
    qtbot.addWidget(vue)
    assert vue.liste_profils.count() == 1
    assert "Aucun profil" in vue.liste_profils.item(0).text()


def test_accueil_liste_les_profils_sauvegardes(qtbot):
    profils.ajouter_profil("test-idiv", dict(_PROFIL_TEST))
    vue = VueAccueil()
    qtbot.addWidget(vue)
    assert vue.liste_profils.count() == 1
    ligne = vue.liste_profils.itemWidget(vue.liste_profils.item(0))
    assert "DGFiP Hérault" in _texte_complet(ligne)
    assert "★ 2 nouvelle(s)" in _texte_complet(ligne)


def test_action_lancer_emet_le_signal_avec_le_profil(qtbot):
    profils.ajouter_profil("test-idiv", dict(_PROFIL_TEST))
    vue = VueAccueil()
    qtbot.addWidget(vue)

    with qtbot.waitSignal(vue.demande_lancer_profil, timeout=1000) as bloqueur:
        vue._traiter_action("lancer", "test-idiv", vue._profils["test-idiv"])
    assert bloqueur.args[0] == "test-idiv"


def test_double_clic_sur_un_profil_emet_demande_lancer_profil(qtbot):
    profils.ajouter_profil("test-idiv", dict(_PROFIL_TEST))
    vue = VueAccueil()
    qtbot.addWidget(vue)

    with qtbot.waitSignal(vue.demande_lancer_profil, timeout=1000) as bloqueur:
        vue._on_double_clic(vue.liste_profils.item(0))
    assert bloqueur.args[0] == "test-idiv"


def test_action_modifier_emet_le_signal(qtbot):
    profils.ajouter_profil("test-idiv", dict(_PROFIL_TEST))
    vue = VueAccueil()
    qtbot.addWidget(vue)

    with qtbot.waitSignal(vue.demande_modifier_profil, timeout=1000) as bloqueur:
        vue._traiter_action("modifier", "test-idiv", vue._profils["test-idiv"])
    assert bloqueur.args[0] == "test-idiv"


def test_action_dupliquer_avec_nom_duplique_le_profil(qtbot, monkeypatch):
    profils.ajouter_profil("test-idiv", dict(_PROFIL_TEST))
    vue = VueAccueil()
    qtbot.addWidget(vue)

    monkeypatch.setattr(
        "src.gui.vues.accueil.QInputDialog.getText",
        lambda *a, **k: ("test-idiv-copie", True),
    )
    vue._traiter_action("dupliquer", "test-idiv", vue._profils["test-idiv"])
    assert "test-idiv-copie" in profils.charger_profils()


def test_action_supprimer_avec_confirmation_supprime(qtbot, monkeypatch):
    profils.ajouter_profil("test-idiv", dict(_PROFIL_TEST))
    vue = VueAccueil()
    qtbot.addWidget(vue)

    monkeypatch.setattr("src.gui.vues.accueil.question_oui_non", lambda *a, **k: True)
    vue._traiter_action("supprimer", "test-idiv", vue._profils["test-idiv"])
    assert "test-idiv" not in profils.charger_profils()


def test_action_supprimer_sans_confirmation_ne_supprime_pas(qtbot, monkeypatch):
    profils.ajouter_profil("test-idiv", dict(_PROFIL_TEST))
    vue = VueAccueil()
    qtbot.addWidget(vue)

    monkeypatch.setattr("src.gui.vues.accueil.question_oui_non", lambda *a, **k: False)
    vue._traiter_action("supprimer", "test-idiv", vue._profils["test-idiv"])
    assert "test-idiv" in profils.charger_profils()
