"""Tests des écrans Réglages et Aide QML : chargement sans avertissement,
exposition aux lecteurs d'écran et branchements vers `ControleurReglages`."""

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QUrl
from PySide6.QtGui import QAccessible, QAccessibleInterface
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from src import export, parametres_affichage, parametres_sources, raccourci
from src.gui import application, controleur_reglages
from src.gui.pont import Pont


@pytest.fixture(autouse=True)
def _sans_sources_reseau(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Aucune source réseau active (CLAUDE.md)."""
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    parametres_sources.sauvegarder_sources_actives(
        {cle: False for cle in parametres_sources.SOURCES_DISPONIBLES}
    )


@pytest.fixture
def chargement(
    qapp: QApplication,
) -> Iterator[tuple[QQmlApplicationEngine, Pont, list[str]]]:
    avertissements: list[str] = []
    pont = Pont(qapp)
    moteur = application.creer_moteur(pont)
    moteur.warnings.connect(
        lambda erreurs: avertissements.extend(e.toString() for e in erreurs)
    )
    moteur.load(
        QUrl.fromLocalFile(str(application.DOSSIER_QML / "Tamponne" / "Fenetre.qml"))
    )
    qapp.processEvents()
    yield moteur, pont, avertissements
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


def _element(racine: QObject, nom: str) -> QQuickItem:
    """Élément visuel nommé, y compris un délégué de `Repeater` (sans
    parent `QObject`, donc introuvable par `findChild`)."""
    ecran = racine.findChild(QQuickItem, "ecranReglages")
    assert ecran is not None
    a_visiter = [ecran]
    while a_visiter:
        element = a_visiter.pop()
        if element.objectName() == nom:
            return element
        a_visiter.extend(element.childItems())
    raise AssertionError(f"élément {nom} introuvable")


def _afficher(
    moteur: QQmlApplicationEngine, onglet: int, qapp: QApplication
) -> QObject:
    racine = moteur.rootObjects()[0]
    racine.setProperty("ongletCourant", onglet)
    qapp.processEvents()
    return racine


def test_ecran_aide_expose_ses_rubriques(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]], qapp: QApplication
) -> None:
    moteur, _, avertissements = chargement
    noms = _noms_accessibles(_afficher(moteur, 3, qapp))
    assert avertissements == []
    for rubrique in (
        "Notice d'utilisation",
        "Les cases du formulaire",
        "Exemples de demande",
        "Grades supérieurs (IDIV / IP / AFIP)",
        "Les fiches de recherche",
        "Les dossiers de suivi",
        "Tampons",
    ):
        assert rubrique in noms


def test_ecran_reglages_expose_sources_et_classement(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]], qapp: QApplication
) -> None:
    moteur, _, avertissements = chargement
    racine = _afficher(moteur, 4, qapp)
    noms = _noms_accessibles(racine)
    assert avertissements == []
    for nom in (
        "Avis de mise à jour",
        "Sources consultées",
        *parametres_sources.SOURCES_DISPONIBLES.values(),
        "Thème\u00a0: Suivre le système",
        "Réduire les animations",
        "Liste des organisations\u00a0: Rafraîchir le cache",
        "Sauvegarde",
        "Exporter…",
        "Importer…",
    ):
        assert nom in noms
    assert _element(racine, "boutonInstaller").isVisible() is False


def test_avis_disponible_affiche_les_boutons_d_installation(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]], qapp: QApplication
) -> None:
    moteur, pont, _ = chargement
    pont.reglages_controleur.afficher_avis(
        {"version": "9.9.9", "notes": "", "url_zip": "", "url_publication": ""}
    )
    racine = _afficher(moteur, 4, qapp)
    assert _element(racine, "boutonInstaller").isVisible() is True
    assert _element(racine, "boutonReporter").isVisible() is True


def test_date_cache_affichee_apres_rafraichissement(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]],
    qapp: QApplication,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    moteur, pont, _ = chargement
    racine = _afficher(moteur, 4, qapp)
    assert _element(racine, "dateCache").isVisible() is False
    monkeypatch.setattr(
        controleur_reglages, "obtenir_organisations", lambda forcer=False: {}
    )
    monkeypatch.setattr(
        controleur_reglages,
        "date_cache_organisations",
        lambda: datetime(2026, 10, 12, 14, 5).astimezone(),
    )
    reglages = pont.reglages_controleur
    with qtbot.waitSignal(reglages.organisations_rafraichies, timeout=5000):
        reglages.rafraichir_cache()
    reglages.arreter()
    qapp.processEvents()
    date = _element(racine, "dateCache")
    assert date.isVisible() is True
    assert date.property("text") == (
        "En cache depuis le 12\u00a0octobre\u00a02026 à\u00a014\u00a0h\u00a005"
    )


def test_exports_sans_fichier_masque_les_boutons(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]], qapp: QApplication
) -> None:
    moteur, _, _ = chargement
    racine = _afficher(moteur, 4, qapp)
    assert _element(racine, "etatExports").property("text") == (
        "Aucun export de recherche."
    )
    assert _element(racine, "boutonSupprimerExports").isVisible() is False


def test_supprimer_exports_apres_confirmation(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]], qapp: QApplication
) -> None:
    moteur, _, avertissements = chargement
    racine = _afficher(moteur, 0, qapp)
    export.DOSSIER_EXPORTS.mkdir(parents=True)
    (export.DOSSIER_EXPORTS / "a.html").write_text("x", encoding="utf-8")
    racine.setProperty("ongletCourant", 4)
    qapp.processEvents()
    bouton = _element(racine, "boutonSupprimerExports")
    assert bouton.isVisible() is True
    QMetaObject.invokeMethod(bouton, "clicked")
    qapp.processEvents()
    confirmation = racine.findChild(QObject, "confirmationExports")
    assert confirmation is not None and confirmation.property("opened") is True
    QMetaObject.invokeMethod(confirmation, "confirme")
    qapp.processEvents()
    assert export.etat_exports() == (0, 0)
    assert _element(racine, "etatExports").property("text") == (
        "Aucun export de recherche."
    )
    assert avertissements == []


def test_case_source_enregistre_le_choix(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]], qapp: QApplication
) -> None:
    moteur, _, _ = chargement
    racine = _afficher(moteur, 4, qapp)
    case = _element(racine, "source_fhf")
    assert case.property("coche") is False
    QMetaObject.invokeMethod(case, "clicked")
    qapp.processEvents()
    assert parametres_sources.charger_sources_actives()["fhf"] is True
    assert case.property("coche") is True


def test_case_animations_applique_et_enregistre(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]], qapp: QApplication
) -> None:
    moteur, _, _ = chargement
    racine = _afficher(moteur, 4, qapp)
    theme = moteur.singletonInstance("Tamponne", "Theme")
    case = racine.findChild(QObject, "caseAnimations")
    assert isinstance(theme, QObject) and case is not None
    QMetaObject.invokeMethod(case, "clicked")
    qapp.processEvents()
    assert theme.property("reduireAnimations") is True
    assert parametres_affichage.charger_reduire_animations() is True


def test_liste_theme_suit_le_bouton_lampe(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]], qapp: QApplication
) -> None:
    moteur, _, _ = chargement
    racine = _afficher(moteur, 4, qapp)
    theme = moteur.singletonInstance("Tamponne", "Theme")
    liste = racine.findChild(QObject, "listeTheme")
    assert isinstance(theme, QObject) and liste is not None
    theme.setProperty("mode", "sombre")
    qapp.processEvents()
    assert liste.property("displayText") == "Bureau de nuit"


def test_question_du_raccourci_ouvre_le_dialogue_et_ajoute(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]],
    qapp: QApplication,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(raccourci, "systeme_courant", lambda: "linux")
    moteur, pont, avertissements = chargement
    racine = _afficher(moteur, 0, qapp)
    pont.reglages_controleur.verifier_raccourci()
    qapp.processEvents()
    dialogue = racine.findChild(QObject, "dialogueRaccourci")
    assert dialogue is not None and dialogue.property("opened") is True
    assert dialogue.property("titre") == "Raccourci"
    QMetaObject.invokeMethod(dialogue, "ajoutDemande")
    qtbot.waitUntil(lambda: raccourci.etat() == "a_jour")
    pont.reglages_controleur.arreter()
    assert avertissements == []


def test_confirmation_import_demande_avant_de_remplacer(
    chargement: tuple[QQmlApplicationEngine, Pont, list[str]], qapp: QApplication
) -> None:
    moteur, _, avertissements = chargement
    racine = _afficher(moteur, 4, qapp)
    ecran = racine.findChild(QObject, "ecranReglages")
    assert ecran is not None
    QMetaObject.invokeMethod(
        ecran, "confirmerImport", Q_ARG(str, "file:///tmp/Tamponne-donnees.zip")
    )
    qapp.processEvents()
    confirmation = racine.findChild(QObject, "confirmationImport")
    assert confirmation is not None and confirmation.property("opened") is True
    assert "Tamponne\u2011donnees.zip" in confirmation.property("message")
    assert avertissements == []
