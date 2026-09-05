"""Tests du thème QSS (src/gui/theme.py).

Validation visuelle réelle faite hors suite de tests (capture PNG,
voir REFONTE.md §8) — ces tests vérifient que la feuille de style
s'applique sans erreur et que le mécanisme de variante par propriété
Qt fonctionne, pas le rendu pixel par pixel.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton

from src.gui.theme import construire_feuille_style


def test_construire_feuille_style_sapplique_sans_erreur(qtbot):
    app = QApplication.instance()
    feuille = construire_feuille_style(13.0)
    app.setStyleSheet(feuille)
    bouton = QPushButton("Test")
    qtbot.addWidget(bouton)
    bouton.show()
    assert app.styleSheet() == feuille


def test_construire_feuille_style_utilise_pt_pas_px():
    feuille = construire_feuille_style(13.0)
    assert "font-size: 13.0pt;" in feuille
    tailles_police = [ligne for ligne in feuille.splitlines() if "font-size" in ligne]
    assert tailles_police  # au moins une règle trouvée
    assert all("px" not in ligne for ligne in tailles_police)


def test_bouton_a_variante_est_cochable_et_garde_son_etat(qtbot):
    bouton = QPushButton("A")
    bouton.setProperty("variant", "nav")
    bouton.setCheckable(True)
    qtbot.addWidget(bouton)

    assert bouton.isChecked() is False
    qtbot.mouseClick(bouton, Qt.MouseButton.LeftButton)
    assert bouton.isChecked() is True
