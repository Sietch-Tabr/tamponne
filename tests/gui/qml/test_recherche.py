"""Tests de l'écran Recherche QML : branchements du formulaire vers
`ControleurRecherche`, en passant par le QML (les valeurs JavaScript y
arrivent sous une autre forme que depuis Python)."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtWidgets import QApplication

from src.donnees import parametres_sources
from src.gui import application
from src.gui.pont import Pont


@pytest.fixture(autouse=True)
def _sans_sources_reseau(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aucune source réseau active (CLAUDE.md)."""
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    parametres_sources.sauvegarder_sources_actives(
        {cle: False for cle in parametres_sources.SOURCES_DISPONIBLES}
    )


@pytest.fixture
def moteur(qapp: QApplication) -> Iterator[QQmlApplicationEngine]:
    orgas = {"Ministère de l'Intérieur": {"Préfecture de police": 123}}
    moteur = application.creer_moteur(Pont(qapp, orgas_cache=orgas))
    moteur.load(
        QUrl.fromLocalFile(str(application.DOSSIER_QML / "Tamponne" / "Fenetre.qml"))
    )
    qapp.processEvents()
    yield moteur
    del moteur


def _recherche(moteur: QQmlApplicationEngine) -> QObject:
    racine = moteur.rootObjects()[0]
    recherche = racine.property("pont").property("recherche")
    assert isinstance(recherche, QObject)
    return recherche


def _etat(moteur: QQmlApplicationEngine) -> dict[str, Any]:
    etat = _recherche(moteur).property("etat")
    assert isinstance(etat, dict)
    return etat


@pytest.mark.parametrize(
    "liste", ["domaines", "localisations", "organisations", "grades"]
)
def test_valider_une_selection_l_enregistre_dans_le_formulaire(
    moteur: QQmlApplicationEngine, qapp: QApplication, liste: str
) -> None:
    racine = moteur.rootObjects()[0]
    ecran = racine.findChild(QObject, "ecranRecherche")
    dialogue = racine.findChild(QObject, "dialogueSelection")
    assert ecran is not None and dialogue is not None
    QMetaObject.invokeMethod(
        ecran, "ouvrirSelection", Q_ARG(str, liste), Q_ARG(str, liste)
    )
    qapp.processEvents()
    groupes = dialogue.property("groupes")
    valeur = groupes[-1]["elements"][0]["valeur"]
    dialogue.setProperty("choisis", {valeur: True})
    valider = dialogue.findChild(QObject, "boutonValiderSelection")
    assert valider is not None
    QMetaObject.invokeMethod(valider, "clicked")
    qapp.processEvents()

    etat = _etat(moteur)
    assert etat[liste] == [valeur]
    assert etat[f"libelle_{liste}"] == valeur.split(" - ")[-1]


@pytest.mark.parametrize(
    ("appel", "champ", "attendu"),
    [
        ('r.definir("type_poste", 2)', "type_poste", 2),
        ('r.definir("mot_cle", "chef de projet")', "mot_cle", "chef de projet"),
        ('r.definir("management", true)', "management", True),
        ('r.basculer("categories", "A", true)', "categories", ["A"]),
        ('r.basculer("versants", "etat", false)', "versants", []),
        ('r.definir("domaines", [])', "domaines", []),
    ],
)
def test_appels_du_formulaire_depuis_javascript(
    moteur: QQmlApplicationEngine, appel: str, champ: str, attendu: object
) -> None:
    composant = QQmlComponent(moteur)
    composant.setData(
        (
            "import QtQuick\nQtObject { required property var r\n"
            f"Component.onCompleted: {appel} }}"
        ).encode(),
        QUrl(),
    )
    objet = composant.createWithInitialProperties({"r": _recherche(moteur)})
    assert objet is not None, composant.errorString()

    assert _etat(moteur)[champ] == attendu
