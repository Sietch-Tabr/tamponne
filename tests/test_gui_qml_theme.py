"""Tests du thème QML (src/gui/qml/Tamponne/Theme.qml) : chargement,
modes jour/nuit et contraste WCAG AA de chaque paire texte/fond utilisée
par l'interface, lus directement dans le QML."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

DOSSIER_QML = Path(__file__).parent.parent / "src" / "gui" / "qml"

PAIRES_TEXTE: list[tuple[str, str]] = [
    ("encre", "papier"),
    ("encre2", "papier"),
    ("encre", "papier2"),
    ("encre2", "papier2"),
    ("encre", "papierGrise"),
    ("encre2", "papierGrise"),
    ("encre", "bristol"),
    ("encre2", "bristol"),
    ("tampon", "papier"),
    ("tampon", "papier2"),
    ("tampon", "bristol"),
    ("surTampon", "tampon"),
    ("rouge", "papier"),
    ("rouge", "papierGrise"),
    ("rouge", "bristol"),
    ("vert", "papier"),
    ("encre", "etiquette"),
    ("encre", "etiquetteSurvol"),
    ("rougeEtiquette", "etiquette"),
    ("rougeEtiquette", "etiquetteSurvol"),
    ("vert", "papierGrise"),
    ("encre", "onglet"),
    ("encre", "ongletSurvol"),
    ("encre", "kraft"),
    ("texteKraft", "kraft"),
    ("texteKraft", "ongletSurvol"),
    ("surligneTexte", "surligneur"),
    ("postitTexte", "postit"),
    ("logo", "bureau"),
    ("sousLogo", "bureau"),
    ("bureau", "logo"),
]
"""(texte, fond) : seuil 4.5:1 (WCAG AA, texte normal)."""

PAIRES_ELEMENTS: list[tuple[str, str]] = [
    ("encre2", "papier"),
    ("encre2", "kraft"),
    ("pointille", "kraft"),
    ("tampon", "papier"),
    ("tampon", "kraft"),
    ("encre", "papier"),
]
"""(élément graphique, fond) : seuil 3:1 (WCAG 1.4.11) — bordures
d'étiquettes, pointillés, cadres de focus."""


@pytest.fixture
def theme(qapp: QApplication) -> Iterator[QObject]:
    """Singleton `Theme` chargé par un moteur QML réel."""
    moteur = QQmlEngine(qapp)
    moteur.addImportPath(str(DOSSIER_QML))
    composant = QQmlComponent(moteur)
    composant.setData(
        b"import QtQuick\nimport Tamponne\nQtObject { property var t: Theme }",
        QUrl.fromLocalFile(str(DOSSIER_QML / "essai.qml")),
    )
    hote = composant.create()
    assert hote is not None, [e.toString() for e in composant.errors()]
    valeur = hote.property("t")
    assert isinstance(valeur, QObject)
    yield valeur
    hote.deleteLater()


def _luminance(couleur: QColor) -> float:
    canaux = (couleur.redF(), couleur.greenF(), couleur.blueF())
    lineaires = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux
    ]
    return 0.2126 * lineaires[0] + 0.7152 * lineaires[1] + 0.0722 * lineaires[2]


def _contraste(premier: QColor, second: QColor) -> float:
    clair, sombre = sorted([_luminance(premier), _luminance(second)], reverse=True)
    return (clair + 0.05) / (sombre + 0.05)


def _couleur(theme: QObject, jeton: str) -> QColor:
    valeur = theme.property(jeton)
    assert isinstance(valeur, QColor), f"jeton inconnu ou non couleur : {jeton}"
    return valeur


@pytest.mark.parametrize("mode", ["clair", "sombre"])
@pytest.mark.parametrize(("texte", "fond"), PAIRES_TEXTE)
def test_paires_texte_respectent_wcag_aa(
    theme: QObject, mode: str, texte: str, fond: str
) -> None:
    theme.setProperty("mode", mode)
    ratio = _contraste(_couleur(theme, texte), _couleur(theme, fond))
    assert ratio >= 4.5, f"{texte}/{fond} en mode {mode} : {ratio:.2f}"


@pytest.mark.parametrize("mode", ["clair", "sombre"])
@pytest.mark.parametrize(("element", "fond"), PAIRES_ELEMENTS)
def test_elements_graphiques_respectent_seuil_non_textuel(
    theme: QObject, mode: str, element: str, fond: str
) -> None:
    theme.setProperty("mode", mode)
    ratio = _contraste(_couleur(theme, element), _couleur(theme, fond))
    assert ratio >= 3.0, f"{element}/{fond} en mode {mode} : {ratio:.2f}"


@pytest.mark.parametrize(
    ("mode", "nuit_attendue"), [("clair", False), ("sombre", True)]
)
def test_mode_force_le_bureau(theme: QObject, mode: str, nuit_attendue: bool) -> None:
    theme.setProperty("mode", mode)
    assert theme.property("nuit") is nuit_attendue
    assert theme.property("fusionEcran") is nuit_attendue


def test_encre_de_tampon_violette_le_jour_orange_la_nuit(theme: QObject) -> None:
    theme.setProperty("mode", "clair")
    assert _couleur(theme, "tampon").name() == "#4b2c9e"
    theme.setProperty("mode", "sombre")
    assert _couleur(theme, "tampon").name() == "#ffb672"


def test_polices_embarquees_chargees(theme: QObject, qtbot: QtBot) -> None:
    qtbot.waitUntil(lambda: theme.property("policeTexte") == "Archivo")
    assert theme.property("policeMono") == "IBM Plex Mono"


def test_licences_des_polices_presentes() -> None:
    dossier = DOSSIER_QML / "Tamponne" / "polices"
    assert (
        (dossier / "OFL-Archivo.txt")
        .read_text(encoding="utf-8")
        .count("SIL Open Font License, Version 1.1")
    )
    assert (
        (dossier / "OFL-IBMPlexMono.txt")
        .read_text(encoding="utf-8")
        .count("SIL Open Font License, Version 1.1")
    )
