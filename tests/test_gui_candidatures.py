"""Tests de l'écran Suivi de candidature (src/gui/vues/candidatures.py)."""

import pytest
from PySide6.QtWidgets import QLabel, QWidget

from src import candidatures
from src.gui.vues.candidatures import VueCandidatures, _DialogueEvenement


def _texte_complet(widget: QWidget) -> str:
    """Concatène le texte de tous les QLabel d'une rangée composée
    (`_LigneCandidature`), même pattern que `test_gui_accueil.py`."""
    return " ".join(label.text() for label in widget.findChildren(QLabel))


@pytest.fixture(autouse=True)
def _rediriger_candidatures_vers_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(
        candidatures, "CHEMIN_CANDIDATURES", tmp_path / "candidatures.json"
    )


def test_sans_candidature_affiche_un_message(qtbot):
    vue = VueCandidatures()
    qtbot.addWidget(vue)
    assert vue.liste.count() == 1
    assert "Aucune candidature" in vue.liste.item(0).text()


def test_liste_les_candidatures_suivies(qtbot):
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = VueCandidatures()
    qtbot.addWidget(vue)
    assert vue.liste.count() == 1
    ligne = vue.liste.itemWidget(vue.liste.item(0))
    texte = _texte_complet(ligne)
    assert "Attaché" in texte
    assert "DGFiP" in texte
    # Pas d'événement préinséré à la création : le statut par défaut
    # reste "Aucun événement" tant que l'utilisateur n'a rien confirmé.
    assert "Aucun événement" in texte


def test_action_voir_ouvre_le_navigateur(qtbot, monkeypatch):
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = VueCandidatures()
    qtbot.addWidget(vue)

    ouvertes = []
    monkeypatch.setattr("webbrowser.open", lambda url: ouvertes.append(url))
    vue._traiter_action("voir", "ref-1", vue._candidatures["ref-1"])
    assert ouvertes == ["https://example.org/1"]


def test_action_detail_ouvre_la_dialogue_avec_le_detail_archive(qtbot, monkeypatch):
    detail_factice = {
        "description": "Missions du poste",
        "salaire": "",
        "experience_requise": "",
        "formation_requise": "",
        "secteur": "",
        "date_publication": "",
        "a_propos_employeur": "",
        "sections_complementaires": {},
        "page_html": "",
    }
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1", detail=detail_factice
    )
    vue = VueCandidatures()
    qtbot.addWidget(vue)

    appels = []

    class _DialogueFactice:
        def __init__(self, titre_offre, employeur, detail, url, reference, parent=None):
            appels.append((titre_offre, employeur, detail, url, reference))

        def exec(self):
            return None

    monkeypatch.setattr(
        "src.gui.vues.candidatures.DialogueDetailOffre", _DialogueFactice
    )
    vue._traiter_action("detail", "ref-1", vue._candidatures["ref-1"])

    assert appels == [
        ("Attaché", "DGFiP", detail_factice, "https://example.org/1", "ref-1")
    ]


def test_action_supprimer_avec_confirmation_supprime(qtbot, monkeypatch):
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = VueCandidatures()
    qtbot.addWidget(vue)

    monkeypatch.setattr(
        "src.gui.vues.candidatures.question_oui_non", lambda *a, **k: True
    )
    vue._traiter_action("supprimer", "ref-1", vue._candidatures["ref-1"])
    assert "ref-1" not in candidatures.charger_candidatures()


def test_action_supprimer_sans_confirmation_ne_supprime_pas(qtbot, monkeypatch):
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = VueCandidatures()
    qtbot.addWidget(vue)

    monkeypatch.setattr(
        "src.gui.vues.candidatures.question_oui_non", lambda *a, **k: False
    )
    vue._traiter_action("supprimer", "ref-1", vue._candidatures["ref-1"])
    assert "ref-1" in candidatures.charger_candidatures()


def test_action_evenement_ajoute_un_evenement_via_le_dialogue(qtbot, monkeypatch):
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = VueCandidatures()
    qtbot.addWidget(vue)

    from PySide6.QtWidgets import QDialog

    monkeypatch.setattr(
        _DialogueEvenement, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    monkeypatch.setattr(
        _DialogueEvenement, "type_choisi", lambda self: "entretien_planifie"
    )
    monkeypatch.setattr(_DialogueEvenement, "date_choisie", lambda self: "2026-02-01")
    monkeypatch.setattr(_DialogueEvenement, "note_saisie", lambda self: "RDV visio")

    vue._traiter_action("evenement", "ref-1", vue._candidatures["ref-1"])

    historique = candidatures.charger_candidatures()["ref-1"]["historique"]
    assert len(historique) == 1
    assert historique[0] == {
        "date": "2026-02-01",
        "type": "entretien_planifie",
        "note": "RDV visio",
    }


def test_action_evenement_annulee_najoute_rien(qtbot, monkeypatch):
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = VueCandidatures()
    qtbot.addWidget(vue)

    from PySide6.QtWidgets import QDialog

    monkeypatch.setattr(
        _DialogueEvenement, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    vue._traiter_action("evenement", "ref-1", vue._candidatures["ref-1"])

    historique = candidatures.charger_candidatures()["ref-1"]["historique"]
    assert len(historique) == 0


def test_badge_relance_suggeree_affiche_si_ancienne(qtbot, monkeypatch):
    monkeypatch.setattr(candidatures, "SEUIL_RELANCE_JOURS", 0)
    candidatures.ajouter_candidature(
        "ref-1",
        "Attaché",
        "DGFiP",
        "https://example.org/1",
        date_candidature="2020-01-01",
    )
    candidatures.ajouter_evenement("ref-1", "candidature_envoyee", "2020-01-01")
    vue = VueCandidatures()
    qtbot.addWidget(vue)
    ligne = vue.liste.itemWidget(vue.liste.item(0))
    assert "Relance suggérée" in _texte_complet(ligne)


def test_historique_affiche_dans_lordre_chronologique(qtbot):
    candidatures.ajouter_candidature(
        "ref-1",
        "Attaché",
        "DGFiP",
        "https://example.org/1",
        date_candidature="2026-01-01",
    )
    candidatures.ajouter_evenement("ref-1", "candidature_envoyee", "2026-01-01")
    candidatures.ajouter_evenement(
        "ref-1", "entretien_planifie", "2026-01-20", "RDV visio"
    )
    candidatures.ajouter_evenement("ref-1", "accuse_reception", "2026-01-10")

    vue = VueCandidatures()
    qtbot.addWidget(vue)
    ligne = vue.liste.itemWidget(vue.liste.item(0))
    texte = _texte_complet(ligne)

    assert "Historique" in texte
    # ordre chronologique : envoyée (01/01) avant accusé (10/01) avant
    # entretien (20/01), même si l'entretien a été saisi en premier.
    pos_envoyee = texte.find("01/01/2026")
    pos_accuse = texte.find("10/01/2026")
    pos_entretien = texte.find("20/01/2026")
    assert -1 < pos_envoyee < pos_accuse < pos_entretien
    assert "RDV visio" in texte
