"""Point d'entrée de l'interface QML (thème « dossier administratif »)."""

import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from src.gui.pont import Pont
from src.parametres_affichage import charger_mode_theme

DOSSIER_QML = Path(__file__).parent / "qml"


def creer_moteur(pont: Pont) -> QQmlApplicationEngine:
    """Moteur QML prêt à charger `Fenetre.qml` : chemin d'import du module
    `Tamponne`, objet `pont` passé en propriété requise de la fenêtre,
    mode de thème enregistré appliqué.

    Args:
        pont: Objet transmis à la propriété `pont` de `Fenetre.qml`.

    Returns:
        Moteur configuré, fenêtre non encore chargée.
    """
    moteur = QQmlApplicationEngine()
    moteur.addImportPath(str(DOSSIER_QML))
    moteur.setInitialProperties({"pont": pont})
    theme = moteur.singletonInstance("Tamponne", "Theme")
    if isinstance(theme, QObject):
        theme.setProperty("mode", charger_mode_theme())
    return moteur


def main() -> int:
    """Lance l'application QML.

    Returns:
        Code de sortie de la boucle Qt.
    """
    # Menus Fichier/Aide dessinés dans la fenêtre (bande bristol) plutôt
    # que dans la barre système de macOS ; à poser avant l'application.
    QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Tamponné")
    app.setApplicationDisplayName("Tamponné")
    app.setOrganizationName("Tamponné")

    pont = Pont()
    app.aboutToQuit.connect(pont.arreter)
    moteur = creer_moteur(pont)
    moteur.load(QUrl.fromLocalFile(str(DOSSIER_QML / "Tamponne" / "Fenetre.qml")))
    if not moteur.rootObjects():
        return 1
    code = app.exec()
    # Moteur détruit avant le pont : ses liaisons liraient sinon un objet disparu.
    del moteur
    return code


if __name__ == "__main__":
    raise SystemExit(main())
