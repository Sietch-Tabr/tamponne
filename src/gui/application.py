"""Point d'entrée de l'interface QML (thème « dossier administratif »)."""

import json
import sys
import urllib.error
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QIcon, QWindow
from PySide6.QtQml import QQmlApplicationEngine

from src.cache import obtenir_organisations
from src.gui.pont import Pont
from src.lanceur import CODE_REDEMARRAGE
from src.nettoyage import nettoyer_fichiers_obsoletes
from src.parametres_affichage import charger_mode_theme, charger_reduire_animations

DOSSIER_QML = Path(__file__).parent / "qml"
ICONE = Path(__file__).parent / "icones" / "tamponne.png"


def creer_moteur(pont: Pont) -> QQmlApplicationEngine:
    """Moteur QML prêt à charger `Fenetre.qml` : chemin d'import du module
    `Tamponne`, objet `pont` passé en propriété requise de la fenêtre,
    mode de thème enregistré appliqué.

    Args:
        pont: Objet transmis à la propriété `pont` de `Fenetre.qml` ; le
            moteur en devient le parent (détruit après l'interface).

    Returns:
        Moteur configuré, fenêtre non encore chargée.
    """
    moteur = QQmlApplicationEngine()
    # Le moteur devient parent du pont : Qt détruit toujours l'interface
    # avant lui, quel que soit l'ordre de libération côté Python.
    pont.setParent(moteur)
    moteur.addImportPath(str(DOSSIER_QML))
    moteur.setInitialProperties({"pont": pont})
    theme = moteur.singletonInstance("Tamponne", "Theme")
    if isinstance(theme, QObject):
        theme.setProperty("mode", charger_mode_theme())
        theme.setProperty("reduireAnimations", charger_reduire_animations())
    return moteur


def adapter_a_l_ecran(fenetre: QWindow) -> None:
    """Agrandit la fenêtre si sa taille d'ouverture (1280 × 900, barre de
    titre comprise) dépasse la zone utile de son écran, sans la barre de
    menus ni le Dock ou la barre des tâches : petit écran de portable."""
    ecran = fenetre.screen()
    if ecran is None:
        return
    zone = ecran.availableGeometry()
    cadre = fenetre.frameGeometry()
    if cadre.width() > zone.width() or cadre.height() > zone.height():
        fenetre.showMaximized()


def main() -> int:
    """Lance l'application QML, après avoir retiré les fichiers obsolètes
    laissés par les mises à jour (`src.nettoyage`).

    Returns:
        `CODE_REDEMARRAGE` si l'utilisateur a choisi « Installer et
        redémarrer » ou importé des données (`src.lanceur` applique alors
        la mise à jour en attente et relance), sinon le code de sortie de
        la boucle Qt.
    """
    nettoyer_fichiers_obsoletes()
    # Menus Fichier/Aide dessinés dans la fenêtre (bande bristol) plutôt
    # que dans la barre système de macOS ; à poser avant l'application.
    QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Tamponné")
    app.setApplicationDisplayName("Tamponné")
    app.setOrganizationName("Tamponné")
    # Icône du Dock (macOS) et de la barre des tâches ; le nom relie la
    # fenêtre au raccourci `tamponne.desktop` sous Linux (Wayland).
    app.setWindowIcon(QIcon(str(ICONE)))
    app.setDesktopFileName("tamponne")

    try:
        orgas_cache = obtenir_organisations()
    except OSError, json.JSONDecodeError, urllib.error.URLError, RuntimeError:
        orgas_cache = {}

    pont = Pont(orgas_cache=orgas_cache)
    app.aboutToQuit.connect(pont.arreter)
    pont.reglages_controleur.quitter_demande.connect(app.quit)
    moteur = creer_moteur(pont)
    moteur.load(QUrl.fromLocalFile(str(DOSSIER_QML / "Tamponne" / "Fenetre.qml")))
    if not moteur.rootObjects():
        return 1
    fenetre = moteur.rootObjects()[0]
    if isinstance(fenetre, QWindow):
        adapter_a_l_ecran(fenetre)
    pont.reglages_controleur.verifier_mise_a_jour()
    pont.reglages_controleur.verifier_raccourci()
    code = app.exec()
    return CODE_REDEMARRAGE if pont.reglages_controleur.redemarrage_demande else code


if __name__ == "__main__":
    raise SystemExit(main())
