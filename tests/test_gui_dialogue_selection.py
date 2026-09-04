"""Tests des dialogues modaux de sélection (src/gui/widgets/dialogue_selection.py)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from src.gui.widgets.dialogue_selection import (
    DialogueSelectionListe,
    DialogueSelectionOrganisations,
)


def test_selection_liste_preremplie_avec_deja_selectionnes(qtbot):
    dialogue = DialogueSelectionListe(
        "Domaine(s)", ["Achat", "Numérique", "Santé"], ["Numérique"]
    )
    qtbot.addWidget(dialogue)
    assert dialogue.selection() == ["Numérique"]


def test_selection_liste_recherche_cache_les_non_correspondants(qtbot):
    dialogue = DialogueSelectionListe("Domaine(s)", ["Achat", "Numérique", "Santé"], [])
    qtbot.addWidget(dialogue)

    dialogue._recherche.setText("num")
    assert dialogue._liste.item(0).isHidden() is True  # Achat
    assert dialogue._liste.item(1).isHidden() is False  # Numérique
    assert dialogue._liste.item(2).isHidden() is True  # Santé

    dialogue._recherche.setText("")
    for i in range(dialogue._liste.count()):
        assert dialogue._liste.item(i).isHidden() is False


def test_selection_liste_cocher_un_item_apparait_dans_selection(qtbot):
    dialogue = DialogueSelectionListe("Domaine(s)", ["Achat", "Numérique"], [])
    qtbot.addWidget(dialogue)
    dialogue._liste.item(1).setCheckState(Qt.CheckState.Checked)
    assert dialogue.selection() == ["Numérique"]


def test_boutons_ok_annuler_traduits_en_francais(qtbot):
    dialogue = DialogueSelectionListe("Domaine(s)", ["Achat"], [])
    qtbot.addWidget(dialogue)
    labels = {b.text() for b in dialogue.findChildren(QPushButton)}
    assert "Annuler" in labels
    assert "Cancel" not in labels


_ORGAS_TEST = {
    "Ministère Alpha": {"Sous-org 1": 1, "Sous-org 2": 2},
    "Ministère Beta": {"Sous-org 3": 3},
}


def test_selection_organisations_preremplie(qtbot):
    dialogue = DialogueSelectionOrganisations(
        _ORGAS_TEST, ["Ministère Alpha - Sous-org 1"]
    )
    qtbot.addWidget(dialogue)
    assert dialogue.selection() == ["Ministère Alpha - Sous-org 1"]


def test_selection_organisations_recherche_cache_ministere_sans_correspondance(qtbot):
    dialogue = DialogueSelectionOrganisations(_ORGAS_TEST, [])
    qtbot.addWidget(dialogue)

    dialogue._recherche.setText("sous-org 3")
    racine_alpha = dialogue._arbre.topLevelItem(0)
    racine_beta = dialogue._arbre.topLevelItem(1)
    assert racine_alpha.isHidden() is True
    assert racine_beta.isHidden() is False
    assert racine_beta.isExpanded() is True


def test_selection_organisations_cocher_une_sous_org(qtbot):
    dialogue = DialogueSelectionOrganisations(_ORGAS_TEST, [])
    qtbot.addWidget(dialogue)
    racine = dialogue._arbre.topLevelItem(0)
    enfant = racine.child(0)
    enfant.setCheckState(0, Qt.CheckState.Checked)
    assert dialogue.selection() == ["Ministère Alpha - Sous-org 1"]
