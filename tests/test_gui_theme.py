"""Tests du thème QSS (src/gui/theme.py).

Validation visuelle réelle faite hors suite de tests (capture PNG,
voir REFONTE.md §8) — ces tests vérifient que la feuille de style
s'applique sans erreur et que le mécanisme de variante par propriété
Qt fonctionne, pas le rendu pixel par pixel.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QPushButton

from src.gui import theme
from src.gui.theme import (
    PALETTE_CLAIRE,
    PALETTE_SOMBRE,
    appliquer_theme,
    construire_feuille_style,
    palette_active,
    palette_systeme,
)


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


def _luminance(couleur: str) -> float:
    canaux = [int(couleur[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineaires = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux
    ]
    return 0.2126 * lineaires[0] + 0.7152 * lineaires[1] + 0.0722 * lineaires[2]


def _contraste(texte: str, fond: str) -> float:
    clair, sombre = sorted([_luminance(texte), _luminance(fond)], reverse=True)
    return (clair + 0.05) / (sombre + 0.05)


# Paires (texte, fond) réellement utilisées par la QSS.
_PAIRES_TEXTE_FOND = [
    ("texte", "bg"),
    ("texte", "surface"),
    ("texte", "panel"),
    ("texte", "accent_soft"),
    ("texte_dim", "bg"),
    ("texte_dim", "surface"),
    ("texte_dim", "panel"),
    ("accent_clair", "bg"),
    ("accent_clair", "accent_soft"),
    ("sur_accent", "accent"),
    ("sur_accent", "accent_clair"),
    ("sur_accent", "attention"),
    ("sur_accent", "danger"),
    ("danger", "panel"),
]


@pytest.mark.parametrize("palette", [PALETTE_SOMBRE, PALETTE_CLAIRE])
@pytest.mark.parametrize("texte, fond", _PAIRES_TEXTE_FOND)
def test_palette_contraste_wcag_aa(palette, texte, fond):
    rapport = _contraste(getattr(palette, texte), getattr(palette, fond))
    assert rapport >= 4.5, f"{texte}/{fond} : {rapport:.2f}:1"


@pytest.mark.parametrize("palette", [PALETTE_SOMBRE, PALETTE_CLAIRE])
def test_construire_feuille_style_utilise_les_couleurs_de_la_palette(palette):
    feuille = construire_feuille_style(13.0, palette)
    assert f"background-color: {palette.bg};" in feuille
    assert f"color: {palette.sur_accent};" in feuille


class _StyleHintsFactices:
    def __init__(self, schema: Qt.ColorScheme) -> None:
        self._schema = schema

    def colorScheme(self) -> Qt.ColorScheme:
        return self._schema


@pytest.mark.parametrize(
    "schema, attendue",
    [
        (Qt.ColorScheme.Light, PALETTE_CLAIRE),
        (Qt.ColorScheme.Dark, PALETTE_SOMBRE),
        (Qt.ColorScheme.Unknown, PALETTE_SOMBRE),
    ],
)
def test_palette_systeme_suit_le_reglage_clair_sombre(monkeypatch, schema, attendue):
    monkeypatch.setattr(
        theme.QGuiApplication,
        "styleHints",
        staticmethod(lambda: _StyleHintsFactices(schema)),
    )
    assert palette_systeme() is attendue


def test_appliquer_theme_memorise_la_taille_pour_la_reapplication(
    qtbot, monkeypatch
):
    monkeypatch.setattr(theme, "_palette_active", PALETTE_SOMBRE)
    monkeypatch.setattr(theme, "_taille_base_pt", 13.0)
    monkeypatch.setattr(theme, "palette_systeme", lambda: PALETTE_CLAIRE)
    app = QApplication.instance()
    feuille_origine = app.styleSheet()
    try:
        appliquer_theme(app, 20.0)
        appliquer_theme(app)  # réapplication à chaud, sans taille
        assert palette_active() is PALETTE_CLAIRE
        assert "font-size: 20.0pt;" in app.styleSheet()
        assert app.palette().color(QPalette.ColorRole.Window) == QColor(
            PALETTE_CLAIRE.bg
        )
    finally:
        app.setStyleSheet(feuille_origine)
        app.setPalette(QPalette())
