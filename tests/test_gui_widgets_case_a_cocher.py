"""Tests du widget CaseACocher (src/gui/widgets/case_a_cocher.py)."""

from dataclasses import replace

import pytest
from PySide6.QtGui import QColor
from pytestqt.qtbot import QtBot

from src.gui import theme
from src.gui.theme import palette_active
from src.gui.widgets.case_a_cocher import CaseACocher

_COULEUR_COCHE = QColor(palette_active().sur_accent)


def _rendu(case: CaseACocher, qtbot: QtBot, couleur: QColor = _COULEUR_COCHE) -> bool:
    """Rend la case dans un QPixmap réel et retourne True si un pixel
    de la couleur `couleur` (trait de coche) est présent."""
    qtbot.addWidget(case)
    case.resize(case.sizeHint())
    pixmap = case.grab()
    image = pixmap.toImage()
    for x in range(image.width()):
        for y in range(image.height()):
            if image.pixelColor(x, y) == couleur:
                return True
    return False


def test_case_non_cochee_naffiche_aucune_coche(qtbot: QtBot) -> None:
    case = CaseACocher("Test")
    assert _rendu(case, qtbot) is False


def test_case_cochee_affiche_une_coche(qtbot: QtBot) -> None:
    case = CaseACocher("Test")
    case.setChecked(True)
    assert _rendu(case, qtbot) is True


def test_case_cochee_dessine_la_coche_dans_la_couleur_de_la_palette_active(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Couleur volontairement absente du rendu par défaut, pour ne détecter
    # que le trait de coche.
    palette_test = replace(theme.PALETTE_CLAIRE, sur_accent="#12AB34")
    monkeypatch.setattr(theme, "_palette_active", palette_test)
    case = CaseACocher("Test")
    case.setChecked(True)
    assert _rendu(case, qtbot, QColor("#12AB34")) is True


def test_case_a_cocher_reste_utilisable_comme_un_checkbox(qtbot: QtBot) -> None:
    case = CaseACocher("Test")
    qtbot.addWidget(case)
    etats: list[bool] = []
    case.toggled.connect(etats.append)
    case.setChecked(True)
    assert case.isChecked() is True
    assert etats == [True]
    case.setChecked(False)
    assert case.isChecked() is False
