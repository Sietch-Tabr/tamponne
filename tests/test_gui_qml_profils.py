"""Tests de l'écran Profils QML (EcranProfils.qml, FicheBristol.qml) avec
les fiches de démonstration de la maquette."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QUrl
from PySide6.QtGui import QAccessible, QAccessibleInterface
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from outils import donnees_demo
from src import parametres_sources, profils
from src.gui import application
from src.gui.pont import Pont


@pytest.fixture(autouse=True)
def _sans_sources_reseau(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """« Lancer » démarre une vraie recherche : aucune source réseau active
    (CLAUDE.md), la recherche échoue alors immédiatement sans appel."""
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    parametres_sources.sauvegarder_sources_actives(
        {cle: False for cle in parametres_sources.SOURCES_DISPONIBLES}
    )


def _charger(qapp: QApplication) -> tuple[QQmlApplicationEngine, list[str]]:
    avertissements: list[str] = []
    moteur = application.creer_moteur(Pont(qapp))
    moteur.warnings.connect(
        lambda erreurs: avertissements.extend(e.toString() for e in erreurs)
    )
    moteur.load(
        QUrl.fromLocalFile(str(application.DOSSIER_QML / "Tamponne" / "Fenetre.qml"))
    )
    qapp.processEvents()
    return moteur, avertissements


@pytest.fixture
def ecran_avec_fiches(
    qapp: QApplication, tmp_path: Path
) -> Iterator[tuple[QQmlApplicationEngine, list[str]]]:
    donnees_demo.installer(tmp_path / "donnees")
    moteur, avertissements = _charger(qapp)
    yield moteur, avertissements
    del moteur


def _noms_accessibles(objet: QObject) -> list[str]:
    noms: list[str] = []

    def parcourir(interface: QAccessibleInterface | None) -> None:
        if interface is None:
            return
        nom = interface.text(QAccessible.Text.Name)
        if nom:
            noms.append(nom)
        for rang in range(interface.childCount()):
            parcourir(interface.child(rang))

    QAccessible.setActive(True)
    parcourir(QAccessible.queryAccessibleInterface(objet))
    return noms


def _fenetre_et_ecran(moteur: QQmlApplicationEngine) -> tuple[QObject, QObject]:
    """(fenêtre racine, écran Profils) : la racine doit rester référencée."""
    racine = moteur.rootObjects()[0]
    ecran = racine.findChild(QObject, "ecranProfils")
    assert ecran is not None
    return racine, ecran


def test_ecran_profils_expose_fiches_et_actions(
    ecran_avec_fiches: tuple[QQmlApplicationEngine, list[str]],
) -> None:
    moteur, avertissements = ecran_avec_fiches
    racine, _ = _fenetre_et_ecran(moteur)
    noms = _noms_accessibles(racine)
    assert avertissements == []
    assert "Mes fiches de recherche" in noms
    assert "2 fiches classées" in noms
    assert "Attaché, Paris et petite couronne" in noms
    assert not any("nouvelle" in nom for nom in noms)
    assert "Lancer la fiche «\u00a0Hospitalier, achats\u00a0»" in noms
    assert "Nouvelle fiche" in noms


def test_lancer_une_fiche_ouvre_l_onglet_recherche(
    ecran_avec_fiches: tuple[QQmlApplicationEngine, list[str]],
    qapp: QApplication,
    qtbot: QtBot,
) -> None:
    moteur, _ = ecran_avec_fiches
    racine, _ = _fenetre_et_ecran(moteur)
    pont = racine.property("pont")
    assert isinstance(pont, Pont)
    pont.property("profils").lancer("attache-paris")
    qapp.processEvents()
    assert racine.property("ongletCourant") == 1
    recherche = pont.property("recherche")
    qtbot.waitUntil(lambda: recherche.property("phase") == "erreur", timeout=5000)
    qtbot.waitUntil(lambda: recherche.property("texte_bouton") == "Lancer la recherche")


def test_dupliquer_cree_la_copie_et_refuse_un_doublon(
    ecran_avec_fiches: tuple[QQmlApplicationEngine, list[str]], qapp: QApplication
) -> None:
    moteur, _ = ecran_avec_fiches
    racine, ecran = _fenetre_et_ecran(moteur)
    QMetaObject.invokeMethod(ecran, "ouvrirDuplication", Q_ARG(str, "attache-paris"))
    qapp.processEvents()
    dialogue = next(
        e
        for e in ecran.children()
        if e.metaObject().className().startswith("DialogueDupliquer")
    )
    assert dialogue.property("opened") is True
    dialogue.duplique.emit("attache-paris", "hospitalier-achats", "")  # type: ignore[attr-defined]
    assert dialogue.property("erreur") == "Une fiche porte déjà ce nom."
    assert dialogue.property("opened") is True
    dialogue.duplique.emit("attache-paris", "attache-paris-copie", "Copie de test")  # type: ignore[attr-defined]
    qapp.processEvents()
    assert profils.charger_profils()["attache-paris-copie"].get("label") == "Copie de test"
    assert racine is not None


def test_ecran_profils_vide_affiche_le_message(qapp: QApplication) -> None:
    moteur, avertissements = _charger(qapp)
    noms = _noms_accessibles(moteur.rootObjects()[0])
    assert avertissements == []
    assert any(n.startswith("Aucune fiche classée.") for n in noms)
    del moteur
