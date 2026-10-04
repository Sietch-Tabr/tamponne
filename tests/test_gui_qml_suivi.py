"""Tests de l'écran Suivi QML (EcranSuivi.qml, DossierSuivi.qml) avec les
données de démonstration de la maquette."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QAccessible, QAccessibleInterface
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

from outils import donnees_demo
from src.gui import application, controleur_suivi
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
    assert "Statut : entretien planifié le 01/10/2026 (visio, 14 h)" in noms
    assert "Entretien 01/10/26" in noms
    assert "Relance suggérée, sans nouvelles depuis 23 jours" in noms
    assert "archive PDF" in noms


def test_ecran_suivi_vide_affiche_le_message(qapp: QApplication) -> None:
    moteur, pont, avertissements = _charger(qapp)
    noms = _noms_accessibles(moteur.rootObjects()[0])
    assert avertissements == []
    assert any(n.startswith("Aucun dossier en cours.") for n in noms)
    del moteur, pont
