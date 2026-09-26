"""Tests des dialogues modaux de sélection (src/gui/widgets/dialogue_selection.py)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QTreeWidget, QTreeWidgetItem
from pytestqt.qtbot import QtBot

from src.gui.widgets.dialogue_selection import (
    DialogueSelectionGrades,
    DialogueSelectionListe,
    DialogueSelectionOrganisations,
)


def _racine(arbre: QTreeWidget, index: int) -> QTreeWidgetItem:
    element = arbre.topLevelItem(index)
    assert element is not None
    return element


def _enfant(parent: QTreeWidgetItem, index: int) -> QTreeWidgetItem:
    element = parent.child(index)
    assert element is not None
    return element


def test_selection_liste_preremplie_avec_deja_selectionnes(qtbot: QtBot) -> None:
    dialogue = DialogueSelectionListe(
        "Domaine(s)", ["Achat", "Numérique", "Santé"], ["Numérique"]
    )
    qtbot.addWidget(dialogue)
    assert dialogue.selection() == ["Numérique"]


def test_selection_liste_recherche_cache_les_non_correspondants(qtbot: QtBot) -> None:
    dialogue = DialogueSelectionListe("Domaine(s)", ["Achat", "Numérique", "Santé"], [])
    qtbot.addWidget(dialogue)

    dialogue._recherche.setText("num")
    assert dialogue._liste.item(0).isHidden() is True  # Achat
    assert dialogue._liste.item(1).isHidden() is False  # Numérique
    assert dialogue._liste.item(2).isHidden() is True  # Santé

    dialogue._recherche.setText("")
    for i in range(dialogue._liste.count()):
        assert dialogue._liste.item(i).isHidden() is False


def test_selection_liste_cocher_un_item_apparait_dans_selection(qtbot: QtBot) -> None:
    dialogue = DialogueSelectionListe("Domaine(s)", ["Achat", "Numérique"], [])
    qtbot.addWidget(dialogue)
    dialogue._liste.item(1).setCheckState(Qt.CheckState.Checked)
    assert dialogue.selection() == ["Numérique"]


def test_boutons_ok_annuler_traduits_en_francais(qtbot: QtBot) -> None:
    dialogue = DialogueSelectionListe("Domaine(s)", ["Achat"], [])
    qtbot.addWidget(dialogue)
    labels = {b.text() for b in dialogue.findChildren(QPushButton)}
    assert "Annuler" in labels
    assert "Cancel" not in labels


_ORGAS_TEST = {
    "Ministère Alpha": {"Sous-org 1": 1, "Sous-org 2": 2},
    "Ministère Beta": {"Sous-org 3": 3},
}


def test_selection_organisations_preremplie(qtbot: QtBot) -> None:
    dialogue = DialogueSelectionOrganisations(
        _ORGAS_TEST, ["Ministère Alpha - Sous-org 1"]
    )
    qtbot.addWidget(dialogue)
    assert dialogue.selection() == ["Ministère Alpha - Sous-org 1"]


def test_selection_organisations_recherche_cache_ministere_sans_correspondance(
    qtbot: QtBot,
) -> None:
    dialogue = DialogueSelectionOrganisations(_ORGAS_TEST, [])
    qtbot.addWidget(dialogue)

    dialogue._recherche.setText("sous-org 3")
    racine_alpha = _racine(dialogue._arbre, 0)
    racine_beta = _racine(dialogue._arbre, 1)
    assert racine_alpha.isHidden() is True
    assert racine_beta.isHidden() is False
    assert racine_beta.isExpanded() is True


def test_selection_organisations_cocher_une_sous_org(qtbot: QtBot) -> None:
    dialogue = DialogueSelectionOrganisations(_ORGAS_TEST, [])
    qtbot.addWidget(dialogue)
    racine = _racine(dialogue._arbre, 0)
    enfant = _enfant(racine, 0)
    enfant.setCheckState(0, Qt.CheckState.Checked)
    assert dialogue.selection() == ["Ministère Alpha - Sous-org 1"]


_CORPS_GRADES_TEST = {
    "Attaché": ["Attaché", "Attaché principal", "Attaché hors classe"],
    "Adjoint administratif": [
        "Adjoint administratif",
        "Adjoint administratif principal",
    ],
}


def test_selection_grades_preremplie(qtbot: QtBot) -> None:
    dialogue = DialogueSelectionGrades(_CORPS_GRADES_TEST, ["Attaché principal"])
    qtbot.addWidget(dialogue)
    assert dialogue.selection() == ["Attaché principal"]


def test_selection_grades_corps_toujours_deplies_par_defaut(qtbot: QtBot) -> None:
    """Peu de corps/grades : tout visible d'emblée, pas besoin de déplier."""
    dialogue = DialogueSelectionGrades(_CORPS_GRADES_TEST, [])
    qtbot.addWidget(dialogue)
    for i in range(dialogue._arbre.topLevelItemCount()):
        assert _racine(dialogue._arbre, i).isExpanded() is True


def test_selection_grades_recherche_cache_corps_sans_correspondance(
    qtbot: QtBot,
) -> None:
    dialogue = DialogueSelectionGrades(_CORPS_GRADES_TEST, [])
    qtbot.addWidget(dialogue)

    dialogue._recherche.setText("hors classe")
    racine_attache = _racine(dialogue._arbre, 0)
    racine_adjoint = _racine(dialogue._arbre, 1)
    assert racine_attache.isHidden() is False
    assert racine_adjoint.isHidden() is True

    dialogue._recherche.setText("")
    assert racine_attache.isHidden() is False
    assert racine_adjoint.isHidden() is False


def test_selection_grades_cocher_un_grade(qtbot: QtBot) -> None:
    dialogue = DialogueSelectionGrades(_CORPS_GRADES_TEST, [])
    qtbot.addWidget(dialogue)
    racine = _racine(dialogue._arbre, 0)
    enfant = _enfant(racine, 1)  # Attaché principal
    enfant.setCheckState(0, Qt.CheckState.Checked)
    assert dialogue.selection() == ["Attaché principal"]
