"""Tests de l'écran Suivi QML (EcranSuivi.qml, DossierSuivi.qml) avec les
données de démonstration de la maquette."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QUrl
from PySide6.QtGui import QAccessible, QAccessibleInterface
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from outils import donnees_demo
from src.donnees import candidatures
from src.gui import application
from src.gui.controleurs import suivi as controleur_suivi
from src.gui.pont import Pont

ONGLET_SUIVI = 2


def _charger(qapp: QApplication) -> tuple[QQmlApplicationEngine, Pont, list[str]]:
    avertissements: list[str] = []
    pont = Pont(qapp)
    moteur = application.creer_moteur(pont)
    moteur.warnings.connect(
        lambda erreurs: avertissements.extend(e.toString() for e in erreurs)
    )
    moteur.load(
        QUrl.fromLocalFile(str(application.DOSSIER_QML / "Tamponne" / "Fenetre.qml"))
    )
    moteur.rootObjects()[0].setProperty("ecransEnAvance", 5)
    moteur.rootObjects()[0].setProperty("ongletCourant", ONGLET_SUIVI)
    qapp.processEvents()
    return moteur, pont, avertissements


@pytest.fixture
def ecran_avec_dossiers(
    qapp: QApplication, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[QQmlApplicationEngine, list[str]]]:
    donnees_demo.installer(tmp_path / "donnees")
    monkeypatch.setattr(controleur_suivi, "date_du_jour", lambda: date(2026, 10, 4))
    moteur, pont, avertissements = _charger(qapp)
    yield moteur, avertissements
    del moteur, pont


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


def test_ecran_suivi_se_charge_sans_avertissement(
    ecran_avec_dossiers: tuple[QQmlApplicationEngine, list[str]],
) -> None:
    _, avertissements = ecran_avec_dossiers
    assert avertissements == []


def test_ecran_suivi_expose_dossiers_statuts_et_tampons(
    ecran_avec_dossiers: tuple[QQmlApplicationEngine, list[str]],
) -> None:
    moteur, _ = ecran_avec_dossiers
    noms = _noms_accessibles(moteur.rootObjects()[0])
    assert "Dossiers en cours" in noms
    assert "3 candidatures suivies" in noms
    assert "Réf. MINT_2026-31544" in noms
    assert "Attaché(e) d'administration RH" in noms
    assert "Statut\u00a0: entretien planifié le 01/10/2026 (visio, 14 h)" in noms
    assert "Modifier l'événement Entretien du 01/10/26" in noms
    assert "Relance suggérée, sans nouvelles depuis 23 jours" in noms
    assert "archive PDF" in noms


def test_ecran_suivi_vide_affiche_le_message(qapp: QApplication) -> None:
    moteur, pont, avertissements = _charger(qapp)
    noms = _noms_accessibles(moteur.rootObjects()[0])
    assert avertissements == []
    assert any(n.startswith("Aucun dossier en cours.") for n in noms)
    del moteur, pont


def _ecran(moteur: QQmlApplicationEngine) -> tuple[QObject, QObject]:
    """(fenêtre racine, écran Suivi) : la racine doit rester référencée
    pendant le test, sa libération côté Python détruirait la fenêtre."""
    racine = moteur.rootObjects()[0]
    ecran = racine.findChild(QObject, "ecranSuivi")
    assert ecran is not None
    return racine, ecran


def _dialogue(ecran: QObject, nom_type: str) -> QObject:
    """Fenêtre de l'écran par son type QML (DialogueDetail, DialogueEvenement…)."""
    for enfant in ecran.children():
        if enfant.metaObject().className().startswith(nom_type):
            return enfant
    raise AssertionError(f"{nom_type} introuvable")


def test_detail_s_ouvre_sur_la_fiche_archivee(
    ecran_avec_dossiers: tuple[QQmlApplicationEngine, list[str]], qapp: QApplication
) -> None:
    moteur, avertissements = ecran_avec_dossiers
    _racine, ecran = _ecran(moteur)
    QMetaObject.invokeMethod(ecran, "ouvrirDetail", Q_ARG(str, "MINT_2026-31544"))
    qapp.processEvents()
    detail = _dialogue(ecran, "DialogueDetail")
    assert detail.property("opened") is True
    assert detail.property("fiche")["titre"] == "Attaché(e) d'administration RH"
    assert avertissements == []


def test_evenement_tamponne_met_a_jour_le_dossier(
    ecran_avec_dossiers: tuple[QQmlApplicationEngine, list[str]], qapp: QApplication
) -> None:
    moteur, _ = ecran_avec_dossiers
    _racine, ecran = _ecran(moteur)
    QMetaObject.invokeMethod(ecran, "ouvrirEvenement", Q_ARG(str, "MINT_2026-31544"))
    qapp.processEvents()
    dialogue = _dialogue(ecran, "DialogueEvenement")
    assert dialogue.property("opened") is True
    dialogue.tamponne.emit(  # type: ignore[attr-defined]
        "MINT_2026-31544", "relance", "2026-10-04", "par courriel"
    )
    historique = candidatures.charger_candidatures()["MINT_2026-31544"]["historique"]
    assert historique[-1] == {
        "date": "2026-10-04",
        "type": "relance",
        "note": "par courriel",
    }


def test_suppr_demande_confirmation_puis_oui_supprime(
    ecran_avec_dossiers: tuple[QQmlApplicationEngine, list[str]], qapp: QApplication
) -> None:
    moteur, _ = ecran_avec_dossiers
    _racine, ecran = _ecran(moteur)
    QMetaObject.invokeMethod(
        ecran, "demanderSuppression", Q_ARG(str, "MINT_2026-31544")
    )
    qapp.processEvents()
    confirmation = _dialogue(ecran, "DialogueConfirmation")
    assert confirmation.property("opened") is True
    assert "Attaché(e) d'administration RH" in confirmation.property("message")
    confirmation.confirme.emit()  # type: ignore[attr-defined]
    assert "MINT_2026-31544" not in candidatures.charger_candidatures()
