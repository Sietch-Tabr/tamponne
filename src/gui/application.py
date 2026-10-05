"""Point d'entrée de l'interface QML (thème « dossier administratif »)."""

import json
import sys
import urllib.error
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from src.cache import obtenir_organisations
from src.gui.pont import Pont
from src.parametres_affichage import charger_mode_theme, charger_reduire_animations

DOSSIER_QML = Path(__file__).parent / "qml"
CODE_RETOUR_MAJ = 42
"""Code de sortie qui demande au lanceur d'appliquer la mise à jour et de relancer."""


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


def main() -> int:
    """Lance l'application QML.

    Returns:
        `CODE_RETOUR_MAJ` si l'utilisateur a choisi « Installer et
        redémarrer » (`lancer.sh`/`lancer.bat` appliquent alors la mise à
        jour et relancent), sinon le code de sortie de la boucle Qt.
    """
    # Menus Fichier/Aide dessinés dans la fenêtre (bande bristol) plutôt
    # que dans la barre système de macOS ; à poser avant l'application.
    QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Tamponné")
    app.setApplicationDisplayName("Tamponné")
    app.setOrganizationName("Tamponné")

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
    pont.reglages_controleur.verifier_mise_a_jour()
    code = app.exec()
    return CODE_RETOUR_MAJ if pont.reglages_controleur.redemarrage_demande else code


if __name__ == "__main__":
    raise SystemExit(main())
