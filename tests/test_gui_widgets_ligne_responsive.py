"""Tests de LigneResponsive (src/gui/widgets/ligne_responsive.py).

Couvre le bug corrigé pendant la conception : `_reconstruire()` détruisait
les enfants (RuntimeError sur objet C++ déjà supprimé) si l'ancien layout
n'était pas d'abord vidé, et `minimumSizeHint()` mal calculé empêchait la
bascule vers l'affichage vertical (le parent n'offrait jamais une largeur
assez étroite)."""

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget
from pytestqt.qtbot import QtBot

from src.gui.widgets.ligne_responsive import LigneResponsive


def _construire_ligne(
    qtbot: QtBot,
) -> tuple[QWidget, LigneResponsive, QPushButton, QPushButton]:
    b1 = QPushButton("Localisation(s)\nTous")
    b2 = QPushButton("Organisation(s)\nTous")
    b1.setMinimumWidth(130)
    b2.setMinimumWidth(130)
    ligne = LigneResponsive(b1, b2)

    parent = QWidget()
    QVBoxLayout(parent).addWidget(ligne)
    qtbot.addWidget(parent)
    parent.show()
    return parent, ligne, b1, b2


def test_large_reste_horizontal(qtbot: QtBot) -> None:
    parent, ligne, b1, b2 = _construire_ligne(qtbot)
    parent.resize(400, 100)
    qtbot.wait(10)
    assert isinstance(ligne.layout(), QHBoxLayout)
    assert b1.isVisible() and b2.isVisible()


def test_etroit_repasse_en_vertical_sans_detruire_les_enfants(qtbot: QtBot) -> None:
    parent, ligne, b1, b2 = _construire_ligne(qtbot)
    parent.resize(150, 150)
    qtbot.wait(10)
    assert isinstance(ligne.layout(), QVBoxLayout)
    assert b1.isVisible() and b2.isVisible()
    assert b1.parent() is ligne
    assert b2.parent() is ligne


def test_plusieurs_allers_retours_ne_plantent_pas(qtbot: QtBot) -> None:
    parent, _ligne, b1, b2 = _construire_ligne(qtbot)
    for largeur in [400, 150, 100, 500, 200, 90, 600, 130, 1000]:
        parent.resize(largeur, 150)
        qtbot.wait(5)
    # Ne doit pas lever RuntimeError (objet C++ détruit) et les boutons
    # doivent rester utilisables.
    assert b1.text() == "Localisation(s)\nTous"
    assert b2.text() == "Organisation(s)\nTous"
