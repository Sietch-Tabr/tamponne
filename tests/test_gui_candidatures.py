"""Tests de l'écran Suivi de candidature (src/gui/vues/candidatures.py)."""

from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt
from pytestqt.qtbot import QtBot

from src import candidatures
from src.gui.vues.candidatures import _DialogueEvenement, VueCandidatures
from src.gui.widgets.delegue_candidature import ROLE_CONTENU
from src.types import DetailOffre


def _texte_ligne(vue: VueCandidatures, ligne: int = 0) -> str:
    """Concatène tous les textes peints pour une ligne du Suivi."""
    return " ".join(vue.modele.index(ligne).data(ROLE_CONTENU).textes())


@pytest.fixture(autouse=True)
def _rediriger_candidatures_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        candidatures, "CHEMIN_CANDIDATURES", tmp_path / "candidatures.json"
    )


def test_sans_candidature_affiche_un_message(qtbot: QtBot) -> None:
    vue = VueCandidatures()
    qtbot.addWidget(vue)
    assert vue.modele.rowCount() == 0
    assert vue._pile.currentWidget() is vue.label_vide
    assert "Aucune candidature" in vue.label_vide.text()


def test_liste_les_candidatures_suivies(qtbot: QtBot) -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = VueCandidatures()
    qtbot.addWidget(vue)
    assert vue.modele.rowCount() == 1
    assert vue._pile.currentWidget() is vue.liste
    texte = _texte_ligne(vue)
    assert "Attaché" in texte
    assert "DGFiP" in texte
    # Pas d'événement préinséré à la création : le statut par défaut
    # reste "Aucun événement" tant que l'utilisateur n'a rien confirmé.
    assert "Aucun événement" in texte


def test_action_voir_ouvre_le_navigateur(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = VueCandidatures()
    qtbot.addWidget(vue)

    ouvertes = []
    monkeypatch.setattr("webbrowser.open", lambda url: ouvertes.append(url))
    vue._traiter_action("voir", "ref-1", vue._candidatures["ref-1"])
    assert ouvertes == ["https://example.org/1"]


def test_action_detail_ouvre_la_dialogue_avec_le_detail_archive(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    detail_factice: DetailOffre = {
        "description": "Missions du poste",
        "salaire": "",
        "experience_requise": "",
        "formation_requise": "",
        "secteur": "",
        "date_publication": "",
        "a_propos_employeur": "",
        "sections_complementaires": {},
        "page_html": "",
        "lien_postuler": "",
        "date_limite": "",
    }
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1", detail=detail_factice
    )
    vue = VueCandidatures()
    qtbot.addWidget(vue)

    appels: list[tuple[str, str, DetailOffre, str, str]] = []

    class _DialogueFactice:
        def __init__(
            self,
            titre_offre: str,
            employeur: str,
            detail: DetailOffre,
            url: str,
            reference: str,
            parent: object = None,
        ) -> None:
            appels.append((titre_offre, employeur, detail, url, reference))

        def exec(self) -> None:
            return None

    monkeypatch.setattr(
        "src.gui.vues.candidatures.DialogueDetailOffre", _DialogueFactice
    )
    vue._traiter_action("detail", "ref-1", vue._candidatures["ref-1"])

    assert appels == [
        ("Attaché", "DGFiP", detail_factice, "https://example.org/1", "ref-1")
    ]


def test_action_supprimer_avec_confirmation_supprime(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_action_supprimer_sans_confirmation_ne_supprime_pas(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_action_evenement_ajoute_un_evenement_via_le_dialogue(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_action_evenement_annulee_najoute_rien(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_badge_relance_suggeree_affiche_si_ancienne(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    assert "Relance suggérée" in _texte_ligne(vue)


def test_historique_affiche_dans_lordre_chronologique(qtbot: QtBot) -> None:
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
    texte = _texte_ligne(vue)

    assert "Historique" in texte
    # ordre chronologique : envoyée (01/01) avant accusé (10/01) avant
    # entretien (20/01), même si l'entretien a été saisi en premier.
    pos_envoyee = texte.find("01/01/2026")
    pos_accuse = texte.find("10/01/2026")
    pos_entretien = texte.find("20/01/2026")
    assert -1 < pos_envoyee < pos_accuse < pos_entretien
    assert "RDV visio" in texte


def _vue_affichee(qtbot: QtBot) -> VueCandidatures:
    vue = VueCandidatures()
    qtbot.addWidget(vue)
    vue.resize(1000, 600)
    vue.show()
    qtbot.waitExposed(vue)
    return vue


def _centre_bouton(vue: VueCandidatures, action: str) -> QPoint:
    index = vue.modele.index(0)
    rect = vue.liste.visualRect(index)
    return vue.delegue.rectangles_boutons(rect, vue.liste.font())[action].center()


@pytest.mark.parametrize("action", ["voir", "detail", "evenement", "supprimer"])
def test_clic_sur_un_bouton_peint_declenche_son_action(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = _vue_affichee(qtbot)
    appels = []
    monkeypatch.setattr(
        vue, "_traiter_action", lambda a, ref, c: appels.append((a, ref))
    )
    qtbot.mouseClick(
        vue.liste.viewport(), Qt.MouseButton.LeftButton, pos=_centre_bouton(vue, action)
    )
    assert appels == [(action, "ref-1")]


def test_clic_hors_des_boutons_ne_declenche_rien(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = _vue_affichee(qtbot)
    appels = []
    monkeypatch.setattr(
        vue, "_traiter_action", lambda a, ref, c: appels.append((a, ref))
    )
    rect = vue.liste.visualRect(vue.modele.index(0))
    qtbot.mouseClick(
        vue.liste.viewport(),
        Qt.MouseButton.LeftButton,
        pos=rect.topLeft() + QPoint(4, 4),
    )
    assert appels == []


@pytest.mark.parametrize(
    "touche, action",
    [
        (Qt.Key.Key_Return, "detail"),
        (Qt.Key.Key_Delete, "supprimer"),
    ],
)
def test_raccourcis_clavier_sur_la_ligne_courante(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, touche: Qt.Key, action: str
) -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    vue = _vue_affichee(qtbot)
    appels = []
    monkeypatch.setattr(
        vue, "_traiter_action", lambda a, ref, c: appels.append((a, ref))
    )
    vue.liste.setCurrentIndex(vue.modele.index(0))
    vue.liste.setFocus()
    qtbot.keyClick(vue.liste, touche)
    assert appels == [(action, "ref-1")]


def test_menu_contextuel_expose_les_quatre_actions(qtbot: QtBot) -> None:
    vue = VueCandidatures()
    qtbot.addWidget(vue)
    assert vue.liste.contextMenuPolicy() == Qt.ContextMenuPolicy.ActionsContextMenu
    assert [a.text() for a in vue.liste.actions()] == [
        "Voir l'offre",
        "Voir le détail",
        "Ajouter un événement",
        "Supprimer",
    ]


def test_badge_offre_depubliee(qtbot: QtBot) -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    candidatures.marquer_disponibilite("ref-1", False)
    vue = VueCandidatures()
    qtbot.addWidget(vue)
    contenu = vue.modele.index(0).data(ROLE_CONTENU)
    assert ("Offre dépubliée", "neutre") in contenu.badges
    assert contenu.disponible is False


def test_candidatures_triees_de_la_plus_recente_a_la_plus_ancienne(
    qtbot: QtBot,
) -> None:
    for reference, date in [("ancienne", "2026-01-01"), ("recente", "2026-03-01")]:
        candidatures.ajouter_candidature(
            reference,
            reference,
            "DGFiP",
            "https://example.org/1",
            date_candidature=date,
        )
    vue = VueCandidatures()
    qtbot.addWidget(vue)
    assert vue.modele.index(0).data(ROLE_CONTENU).reference == "recente"
    assert vue.modele.index(1).data(ROLE_CONTENU).reference == "ancienne"
