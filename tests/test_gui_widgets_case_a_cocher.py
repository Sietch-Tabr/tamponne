"""Tests du widget CaseACocher (src/gui/widgets/case_a_cocher.py)."""

from PySide6.QtGui import QColor

from src.gui.theme import BG
from src.gui.widgets.case_a_cocher import CaseACocher

_COULEUR_COCHE = QColor(BG)


def _rendu(case: CaseACocher, qtbot) -> bool:
    """Rend la case dans un QPixmap réel et retourne True si un pixel
    de la couleur du trait de coche est présent."""
    qtbot.addWidget(case)
    case.resize(case.sizeHint())
    pixmap = case.grab()
    image = pixmap.toImage()
    for x in range(image.width()):
        for y in range(image.height()):
            if image.pixelColor(x, y) == _COULEUR_COCHE:
                return True
    return False


def test_case_non_cochee_naffiche_aucune_coche(qtbot):
    case = CaseACocher("Test")
    assert _rendu(case, qtbot) is False


def test_case_cochee_affiche_une_coche(qtbot):
    case = CaseACocher("Test")
    case.setChecked(True)
    assert _rendu(case, qtbot) is True


def test_case_a_cocher_reste_utilisable_comme_un_checkbox(qtbot):
    case = CaseACocher("Test")
    qtbot.addWidget(case)
    etats = []
    case.toggled.connect(etats.append)
    case.setChecked(True)
    assert case.isChecked() is True
    assert etats == [True]
    case.setChecked(False)
    assert case.isChecked() is False
