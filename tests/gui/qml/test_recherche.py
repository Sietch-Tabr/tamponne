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
    moteur.rootObjects()[0].setProperty("ecransEnAvance", 5)
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


def _fenetre_detail(
    moteur: QQmlApplicationEngine,
) -> tuple[QObject, Any, QObject]:
    """(racine, contrôleur, fenêtre de détail) : la racine doit rester
    référencée pendant le test, sa libération détruirait la fenêtre."""
    racine = moteur.rootObjects()[0]
    dialogue = racine.findChild(QObject, "dialogueDetail")
    assert dialogue is not None
    return racine, racine.property("pont").recherche, dialogue


def test_detail_s_ouvre_des_l_attente_puis_se_remplit(
    moteur: QQmlApplicationEngine, qapp: QApplication
) -> None:
    racine, recherche, dialogue = _fenetre_detail(moteur)
    recherche.detail_attendu.emit(
        {"reference": "R1", "titre": "Chargé de mission", "sousTitre": "Paris"}
    )
    qapp.processEvents()
    assert dialogue.property("opened") is True
    assert dialogue.property("chargement") is True

    recherche.detail_pret.emit(
        {"reference": "R1", "titre": "Chargé de mission", "description": "Missions."}
    )
    qapp.processEvents()
    assert dialogue.property("chargement") is False
    assert dialogue.property("fiche")["description"] == "Missions."


def test_detail_ignore_une_fiche_d_une_autre_offre_ou_arrivee_apres_la_fermeture(
    moteur: QQmlApplicationEngine, qapp: QApplication
) -> None:
    racine, recherche, dialogue = _fenetre_detail(moteur)
    recherche.detail_attendu.emit({"reference": "R1", "titre": "A", "sousTitre": ""})
    qapp.processEvents()

    recherche.detail_pret.emit({"reference": "R2", "titre": "B"})
    qapp.processEvents()
    assert dialogue.property("chargement") is True
    assert dialogue.property("fiche")["reference"] == "R1"

    QMetaObject.invokeMethod(dialogue, "close")
    qapp.processEvents()
    recherche.detail_pret.emit({"reference": "R1", "titre": "A"})
    qapp.processEvents()
    assert dialogue.property("opened") is False


def test_detail_se_ferme_si_le_telechargement_echoue(
    moteur: QQmlApplicationEngine, qapp: QApplication
) -> None:
    racine, recherche, dialogue = _fenetre_detail(moteur)
    recherche.detail_attendu.emit({"reference": "R1", "titre": "A", "sousTitre": ""})
    qapp.processEvents()

    recherche.action_echouee.emit("Opération impossible")
    qapp.processEvents()
    assert dialogue.property("opened") is False
    del racine


def _boutons_visibles(item: Any) -> dict[str, bool]:
    """Texte → actif, pour les boutons du pied de la fenêtre de détail."""
    trouves: dict[str, bool] = {}

    def parcourir(element: Any) -> None:
        for enfant in element.childItems():
            texte = enfant.property("text")
            if (
                texte in ("Postuler", "Consulter en ligne", "Postuler sur le site")
                or texte in ("Tamponner pour suivi", "Dossier ouvert")
            ) and enfant.metaObject().indexOfMethod("clicked()") >= 0:
                if enfant.isVisible():
                    trouves[texte] = bool(enfant.property("enabled"))
            parcourir(enfant)

    parcourir(item)
    return trouves


def _ouvrir_fiche(
    moteur: QQmlApplicationEngine, qapp: QApplication, fiche: dict[str, Any]
) -> tuple[Any, QObject]:
    racine, recherche, dialogue = _fenetre_detail(moteur)
    recherche.detail_attendu.emit({"reference": "R1", "titre": "A", "sousTitre": ""})
    qapp.processEvents()
    recherche.detail_pret.emit({"reference": "R1", "titre": "A", **fiche})
    qapp.processEvents()
    return racine, dialogue


@pytest.mark.parametrize(
    ("fiche", "attendus"),
    [
        (
            {"peutPostuler": True, "enLigne": True},
            {"Postuler": True, "Consulter en ligne": True},
        ),
        ({"peutPostuler": False, "enLigne": True}, {"Postuler sur le site": True}),
        ({"peutPostuler": False, "enLigne": False}, {}),
    ],
)
def test_detail_ne_propose_pas_deux_boutons_vers_la_meme_page(
    moteur: QQmlApplicationEngine,
    qapp: QApplication,
    fiche: dict[str, Any],
    attendus: dict[str, bool],
) -> None:
    racine, dialogue = _ouvrir_fiche(moteur, qapp, fiche)
    assert _boutons_visibles(dialogue.property("contentItem")) == attendus


@pytest.mark.parametrize(
    ("fiche", "attendus"),
    [
        ({"suivable": True, "dejaSuivie": False}, {"Tamponner pour suivi": True}),
        ({"suivable": True, "dejaSuivie": True}, {"Dossier ouvert": False}),
        ({}, {}),
    ],
)
def test_detail_propose_le_suivi_depuis_la_recherche(
    moteur: QQmlApplicationEngine,
    qapp: QApplication,
    fiche: dict[str, Any],
    attendus: dict[str, bool],
) -> None:
    racine, dialogue = _ouvrir_fiche(moteur, qapp, fiche)
    assert _boutons_visibles(dialogue.property("contentItem")) == attendus
