"""Tests de la fenêtre QML (src/gui/qml/Tamponne/Fenetre.qml) et de son
point d'entrée (src/gui/application.py)."""

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QAccessible, QAccessibleInterface, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from src.donnees import parametres_affichage
from src.gui import application
from src.gui.pont import Pont


@pytest.fixture
def moteur(qapp: QApplication) -> Iterator[QQmlApplicationEngine]:
    """Moteur avec la fenêtre chargée ; échoue sur tout avertissement QML."""
    avertissements: list[str] = []
    pont = Pont(qapp)
    moteur = application.creer_moteur(pont)
    moteur.warnings.connect(
        lambda erreurs: avertissements.extend(e.toString() for e in erreurs)
    )
    moteur.load(
        QUrl.fromLocalFile(str(application.DOSSIER_QML / "Tamponne" / "Fenetre.qml"))
    )
    assert moteur.rootObjects(), avertissements
    assert avertissements == []
    yield moteur
    for racine in moteur.rootObjects():
        racine.deleteLater()


def _racine(moteur: QQmlApplicationEngine) -> QObject:
    return moteur.rootObjects()[0]


def test_fenetre_ouvre_sur_onglet_profils(moteur: QQmlApplicationEngine) -> None:
    assert _racine(moteur).property("ongletCourant") == 0


def test_creer_moteur_applique_mode_de_theme_enregistre(qapp: QApplication) -> None:
    parametres_affichage.sauvegarder_mode_theme("clair")
    moteur = application.creer_moteur(Pont(qapp))
    theme = moteur.singletonInstance("Tamponne", "Theme")
    assert isinstance(theme, QObject)
    assert theme.property("mode") == "clair"
    assert theme.property("nuit") is False


def test_pont_enregistrer_mode_theme_ignore_valeur_inconnue(qapp: QApplication) -> None:
    pont = Pont(qapp)
    pont.enregistrer_mode_theme("sombre")
    assert parametres_affichage.charger_mode_theme() == "sombre"
    pont.enregistrer_mode_theme("fluo")
    assert parametres_affichage.charger_mode_theme() == "sombre"


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


def test_onglets_et_menus_exposes_aux_lecteurs_d_ecran(
    moteur: QQmlApplicationEngine,
) -> None:
    noms = _noms_accessibles(_racine(moteur))
    for attendu in ("Profils", "Recherche", "Suivi", "Aide", "Réglages"):
        assert attendu in noms
    assert "Bureau de jour" in noms or "Bureau de nuit" in noms
    assert "Tamponné" in noms


def test_bouton_lampe_annonce_le_bureau_vise(moteur: QQmlApplicationEngine) -> None:
    theme = moteur.singletonInstance("Tamponne", "Theme")
    assert isinstance(theme, QObject)
    theme.setProperty("mode", "sombre")
    assert "Bureau de jour" in _noms_accessibles(_racine(moteur))
    theme.setProperty("mode", "clair")
    assert "Bureau de nuit" in _noms_accessibles(_racine(moteur))


def test_adapter_a_l_ecran_agrandit_si_l_ecran_est_trop_petit(
    qapp: QApplication,
) -> None:
    """L'écran hors écran des tests fait 800 × 800 : 1280 × 900 n'y tient pas."""
    fenetre = QWindow()
    fenetre.resize(1280, 900)
    fenetre.show()
    application.adapter_a_l_ecran(fenetre)
    assert fenetre.windowState() & Qt.WindowState.WindowMaximized
    fenetre.close()


def test_adapter_a_l_ecran_garde_la_taille_si_elle_tient(qapp: QApplication) -> None:
    fenetre = QWindow()
    fenetre.resize(600, 500)
    fenetre.show()
    application.adapter_a_l_ecran(fenetre)
    assert not fenetre.windowState() & Qt.WindowState.WindowMaximized
    fenetre.close()


def test_seul_l_ecran_courant_est_cree_au_demarrage(
    moteur: QQmlApplicationEngine,
) -> None:
    racine = _racine(moteur)
    assert racine.findChild(QObject, "ecranProfils") is not None
    for nom in ("ecranRecherche", "ecranSuivi", "ecranReglages"):
        assert racine.findChild(QObject, nom) is None


def test_les_autres_ecrans_sont_crees_apres_la_premiere_image(
    moteur: QQmlApplicationEngine, qtbot: QtBot
) -> None:
    racine = _racine(moteur)
    qtbot.waitUntil(
        lambda: racine.findChild(QObject, "ecranReglages") is not None, timeout=3000
    )
    for nom in ("ecranRecherche", "ecranSuivi", "ecranAide"):
        assert racine.findChild(QObject, nom) is not None


def test_un_onglet_non_encore_cree_s_ouvre_a_la_demande(
    moteur: QQmlApplicationEngine, qapp: QApplication
) -> None:
    racine = _racine(moteur)
    racine.setProperty("ongletCourant", 4)
    qapp.processEvents()
    assert racine.findChild(QObject, "ecranReglages") is not None


def test_la_question_du_raccourci_est_posee_avant_la_creation_des_ecrans(
    moteur: QQmlApplicationEngine, qapp: QApplication
) -> None:
    racine = _racine(moteur)
    pont = racine.property("pont")
    pont.reglages_controleur.question_raccourci.emit("ajout")
    qapp.processEvents()
    dialogue = racine.findChild(QObject, "dialogueRaccourci")
    assert dialogue is not None and dialogue.property("opened") is True
