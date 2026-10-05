"""Compare un écran de la maquette et son équivalent QML, en jour et en nuit.

Usage : uv run python -m outils.comparer_maquette suivi [--sortie comparaisons]

Pour chaque thème, produit une image côte à côte « Maquette | QML » à la
même taille de fenêtre. La maquette est rendue par Firefox headless avec
les polices embarquées de l'app (aucune police téléchargée), l'interface
QML hors écran avec les données de démonstration de `outils.donnees_demo`.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QRect, Qt, QUrl  # noqa: E402
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402
from shiboken6 import Shiboken  # noqa: E402

from outils import donnees_demo  # noqa: E402
from src import parametres_affichage, parametres_sources  # noqa: E402

RACINE = Path(__file__).parent.parent
DOSSIER_MAQUETTE = Path(__file__).parent / "maquette"
DOSSIER_POLICES = RACINE / "src" / "gui" / "qml" / "Tamponne" / "polices"
FIREFOX = Path("/Applications/Firefox.app/Contents/MacOS/firefox")
LARGEUR = 1280

ECRANS: dict[str, tuple[str, int, int, str]] = {
    "profils": ("Dossier-Accueil.dc.html", 0, 900, ""),
    "dupliquer": (
        "Dossier-Saisie.dc.html",
        0,
        620,
        "ecranProfils:ouvrirDuplication:attache-paris",
    ),
    "recherche": ("Dossier-Recherche.dc.html", 1, 1200, "registre"),
    "suivi": ("Dossier-Suivi.dc.html", 2, 900, ""),
    "aide": ("Dossier-Aide.dc.html", 3, 1400, ""),
    "reglages": ("Dossier-Parametres.dc.html", 4, 900, "avis"),
    "detail": ("Dossier-Detail.dc.html", 2, 1100, "ecranSuivi:ouvrirDetail:MINT_2026-31544"),
    "evenement": (
        "Dossier-Dialogues.dc.html",
        2,
        900,
        "ecranSuivi:ouvrirEvenement:MINT_2026-31544",
    ),
    "confirmation": (
        "Dossier-Dialogues.dc.html",
        2,
        900,
        "ecranSuivi:demanderSuppression:MINT_2026-31544",
    ),
}
"""Écran → (fichier de maquette, index d'onglet QML, hauteur de fenêtre,
action « objectName:fonction:argument » appelée dans le QML avant la
capture, « registre » pour remplir la recherche de démonstration, « avis »
pour l'avis de mise à jour de démonstration, vide si aucune)."""

_POLICES_LOCALES = f"""<style>
@font-face{{font-family:'Archivo';src:url('{(DOSSIER_POLICES / "Archivo-Variable.ttf").as_uri()}');font-weight:100 900;font-stretch:62% 125%}}
@font-face{{font-family:'IBM Plex Mono';src:url('{(DOSSIER_POLICES / "IBMPlexMono-Regular.ttf").as_uri()}');font-weight:400}}
@font-face{{font-family:'IBM Plex Mono';src:url('{(DOSSIER_POLICES / "IBMPlexMono-SemiBold.ttf").as_uri()}');font-weight:600}}
html{{scrollbar-width:none}}
</style>"""


def exporter_maquette(fichier: str, nuit: bool) -> str:
    """HTML statique d'un écran de maquette : variables du composant
    résolues, scripts du canvas retirés, polices locales de l'app."""
    source = (DOSSIER_MAQUETTE / fichier).read_text(encoding="utf-8")
    page = (
        source.replace("{{classe}}", "app nuit" if nuit else "app")
        .replace("{{pressee}}", "true" if nuit else "false")
        .replace("{{libelleLampe}}", "Bureau de jour" if nuit else "Bureau de nuit")
    )
    page = page.replace('<script src="./support.js"></script>', "")
    page = re.sub(r'<script type="text/x-dc".*?</script>', "", page, flags=re.S)
    page = re.sub(r"<link[^>]*fonts\.(googleapis|gstatic)\.com[^>]*>", "", page)
    return page.replace("</head>", _POLICES_LOCALES + "</head>", 1)


def capturer_maquette(fichier: str, nuit: bool, hauteur: int, dossier: Path) -> QImage:
    """Capture Firefox headless de l'écran de maquette."""
    page = dossier / f"maquette-{'nuit' if nuit else 'jour'}.html"
    page.write_text(exporter_maquette(fichier, nuit), encoding="utf-8")
    profil = dossier / "profil-firefox"
    profil.mkdir(exist_ok=True)
    capture = dossier / "screenshot.png"
    capture.unlink(missing_ok=True)
    subprocess.run(
        [
            str(FIREFOX),
            "--headless",
            "--no-remote",
            "--profile",
            str(profil),
            "--screenshot",
            f"--window-size={LARGEUR},{hauteur}",
            page.as_uri(),
        ],
        cwd=dossier,
        check=True,
        capture_output=True,
        timeout=120,
    )
    return QImage(str(capture))


def capturer_qml(onglet: int, nuit: bool, hauteur: int, action: str) -> QImage:
    """Capture hors écran de la fenêtre QML sur l'onglet demandé, après
    avoir ouvert une fenêtre de l'écran Suivi si `action` est renseignée."""
    from src.gui import application, controleur_suivi
    from src.gui.pont import Pont

    controleur_suivi.date_du_jour = lambda: date(2026, 10, 4)
    pont = Pont()
    moteur = application.creer_moteur(pont)
    theme = moteur.singletonInstance("Tamponne", "Theme")
    assert theme is not None
    theme.setProperty("mode", "sombre" if nuit else "clair")
    moteur.load(
        QUrl.fromLocalFile(str(application.DOSSIER_QML / "Tamponne" / "Fenetre.qml"))
    )
    fenetre = cast(
        QQuickWindow,
        Shiboken.wrapInstance(
            Shiboken.getCppPointer(moteur.rootObjects()[0])[0], QQuickWindow
        ),
    )
    fenetre.setProperty("ongletCourant", onglet)
    fenetre.resize(LARGEUR, hauteur)
    app = QGuiApplication.instance()
    assert app is not None
    for _ in range(30):
        app.processEvents()
    if action == "registre":
        donnees_demo.remplir_registre(pont.property("recherche"))
        for _ in range(30):
            app.processEvents()
    elif action == "avis":
        donnees_demo.poser_avis(pont.reglages_controleur)
        for _ in range(30):
            app.processEvents()
    elif action:
        nom_objet, fonction, argument = action.split(":")
        ecran = fenetre.findChild(QObject, nom_objet)
        assert ecran is not None
        QMetaObject.invokeMethod(ecran, fonction, Q_ARG(str, argument))
        for _ in range(30):
            app.processEvents()
    image = fenetre.grabWindow()
    fenetre.close()
    del fenetre
    return image


def assembler(maquette: QImage, qml: QImage, destination: Path) -> None:
    """Image côte à côte, avec un bandeau de légende au-dessus de chaque moitié."""
    bandeau = 36
    largeur = maquette.width() + qml.width() + 24
    hauteur = max(maquette.height(), qml.height()) + bandeau
    resultat = QImage(largeur, hauteur, QImage.Format.Format_RGB32)
    resultat.fill(QColor("#808080"))
    peintre = QPainter(resultat)
    peintre.setFont(QFont("Helvetica", 16, QFont.Weight.Bold))
    peintre.setPen(QColor("#000000"))
    peintre.drawText(
        QRect(0, 0, maquette.width(), bandeau), Qt.AlignmentFlag.AlignCenter, "Maquette"
    )
    x_qml = maquette.width() + 24
    peintre.drawText(
        QRect(x_qml, 0, qml.width(), bandeau), Qt.AlignmentFlag.AlignCenter, "QML"
    )
    peintre.drawImage(0, bandeau, maquette)
    peintre.drawImage(x_qml, bandeau, qml)
    peintre.end()
    resultat.save(str(destination))


def main() -> int:
    """Point d'entrée en ligne de commande."""
    parseur = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parseur.add_argument("ecran", choices=sorted(ECRANS))
    parseur.add_argument("--sortie", type=Path, default=RACINE / "comparaisons")
    arguments = parseur.parse_args()
    if not FIREFOX.exists():
        print(
            "Firefox introuvable\u00a0: capture de la maquette impossible.", file=sys.stderr
        )
        return 1

    QGuiApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeMenuBar)
    app = QGuiApplication(sys.argv[:1])
    fichier, onglet, hauteur, action = ECRANS[arguments.ecran]
    arguments.sortie.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tamponne-comparaison-") as temporaire:
        dossier = Path(temporaire)
        donnees_demo.installer(dossier / "donnees")
        # Sources toutes cochées comme la maquette, sans toucher à data/.
        parametres_sources.CHEMIN_SOURCES = dossier / "donnees" / "sources.json"
        parametres_affichage.CHEMIN_AFFICHAGE = dossier / "donnees" / "affichage.json"
        for nuit in (False, True):
            theme = "nuit" if nuit else "jour"
            maquette = capturer_maquette(fichier, nuit, hauteur, dossier)
            qml = capturer_qml(onglet, nuit, hauteur, action)
            destination = arguments.sortie / f"{arguments.ecran}-{theme}.png"
            assembler(maquette, qml, destination)
            print(destination)
        shutil.rmtree(dossier / "profil-firefox", ignore_errors=True)
    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
