"""Point d'entrée de l'interface graphique PySide6 « Tamponné ».

Remplace le TUI Textual retiré (voir REFONTE.md §5bis pour la
chronologie du revirement TUI → GUI).
"""

import json
import urllib.error
from collections.abc import Callable
from typing import cast

from PySide6.QtCore import QThread
from PySide6.QtGui import QCloseEvent, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.cache import obtenir_organisations
from src.gui.theme import appliquer_theme
from src.gui.travailleurs import VerificateurMiseAJour
from src.gui.vues.accueil import VueAccueil
from src.gui.vues.aide import VueAide
from src.gui.vues.candidatures import VueCandidatures
from src.gui.vues.parametres import VueParametres
from src.gui.vues.recherche_resultats import VueRechercheResultats
from src.gui.widgets.point_statut import PointStatut
from src.parametres_affichage import ModeTheme, charger_mode_theme
from src.types import FiltresRecherche, InfoMaj, Organisations, Profil

CODE_RETOUR_MAJ = 42
"""Code de sortie signalant à lancer.sh/lancer.bat d'appliquer la mise à
jour en attente puis de relancer immédiatement, plutôt qu'attendre le
prochain lancement naturel (voir `_demander_maj_immediate`)."""


class FenetrePrincipale(QMainWindow):
    """Fenêtre principale : bandeau de navigation persistant au-dessus
    d'un `QStackedWidget`.

    Chaque section a une entrée dans le bandeau — y compris
    « Recherche », qui ouvre une recherche vierge (l'écran a son propre
    bouton RAZ pour repartir de zéro sans changer d'écran), et « Suivi »,
    qui liste les candidatures suivies (lot Suivi de candidature,
    REFONTE.md §7).
    """

    def __init__(self, orgas_cache: Organisations | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Tamponné")
        self._orgas_cache = orgas_cache or {}
        self._vue_recherche: VueRechercheResultats | None = None
        self._redemarrage_demande = False
        self._thread_maj: QThread | None = None
        self._verificateur_maj: VerificateurMiseAJour | None = None

        self._pile = QStackedWidget()

        conteneur = QWidget()
        disposition = QVBoxLayout(conteneur)
        disposition.setContentsMargins(0, 0, 0, 0)
        disposition.setSpacing(0)
        disposition.addWidget(self._construire_barre_navigation())
        disposition.addWidget(self._pile, 1)
        self.setCentralWidget(conteneur)
        self._construire_menu_natif()

        self._vue_accueil = VueAccueil()
        self._vue_accueil.demande_lancer_profil.connect(self._ouvrir_recherche_profil)
        self._vue_accueil.demande_modifier_profil.connect(self._ouvrir_edition_profil)
        self._pile.addWidget(self._vue_accueil)

        self._vue_candidatures = VueCandidatures()
        self._pile.addWidget(self._vue_candidatures)

        self._vue_aide = VueAide()
        self._pile.addWidget(self._vue_aide)

        self._vue_parametres = VueParametres()
        self._vue_parametres.cache_rafraichi.connect(self._on_cache_rafraichi)
        self._vue_parametres.demande_maj_immediate.connect(self._demander_maj_immediate)
        self._vue_parametres.mode_theme_change.connect(self._on_mode_theme_change)
        self._pile.addWidget(self._vue_parametres)

        self._pile.setCurrentWidget(self._vue_accueil)
        self.setMinimumSize(
            720, 480
        )  # garde-fou : en dessous, formulaires/tableau illisibles
        self.resize(1100, 750)

        QGuiApplication.styleHints().colorSchemeChanged.connect(
            self._on_schema_couleurs_change
        )

    def _on_schema_couleurs_change(self) -> None:
        """Réapplique le thème quand le système bascule entre clair et
        sombre, sans redémarrer l'application (sans effet visible si un
        thème sombre ou clair est imposé dans les Paramètres)."""
        app = QApplication.instance()
        if isinstance(app, QApplication):
            appliquer_theme(app)

    def _on_mode_theme_change(self, mode: str) -> None:
        """Applique aussitôt le thème choisi dans les Paramètres."""
        app = QApplication.instance()
        if isinstance(app, QApplication):
            appliquer_theme(app, mode=cast(ModeTheme, mode))

    def _construire_barre_navigation(self) -> QWidget:
        barre = QWidget()
        barre.setObjectName("barreNavigation")
        barre.setMinimumHeight(40)  # garde-fou : jamais écrasé au redimensionnement
        disposition = QHBoxLayout(barre)
        disposition.setContentsMargins(16, 0, 16, 0)
        disposition.setSpacing(4)

        self._groupe_nav = QButtonGroup(self)
        self._groupe_nav.setExclusive(True)

        self.bouton_nav_accueil = self._ajouter_bouton_nav(
            disposition, "Accueil", self._revenir_accueil
        )
        self.bouton_nav_recherche = self._ajouter_bouton_nav(
            disposition, "Recherche", self._ouvrir_recherche_vierge
        )
        self.bouton_nav_candidatures = self._ajouter_bouton_nav(
            disposition, "Suivi", self._ouvrir_candidatures
        )
        self.bouton_nav_parametres = self._ajouter_bouton_nav(
            disposition, "Paramètres", self._ouvrir_parametres
        )
        # Badge sur « Paramètres » : c'est là qu'est la carte Mise à jour.
        self.point_maj = PointStatut()
        self.point_maj.setToolTip("Mise à jour disponible")
        self.point_maj.ancrer_sur(self.bouton_nav_parametres)
        self.bouton_nav_aide = self._ajouter_bouton_nav(
            disposition, "Aide", self._ouvrir_aide
        )
        self.bouton_nav_accueil.setChecked(True)

        disposition.addStretch()
        return barre

    def _ajouter_bouton_nav(
        self, disposition: QHBoxLayout, texte: str, action: Callable[[], None]
    ) -> QPushButton:
        bouton = QPushButton(texte)
        bouton.setProperty("variant", "nav")
        bouton.setCheckable(True)
        bouton.clicked.connect(action)
        self._groupe_nav.addButton(bouton)
        disposition.addWidget(bouton)
        return bouton

    def _construire_menu_natif(self) -> None:
        """Barre de menus native du système (menu Application sous macOS,
        barre de menus sous Windows/Linux) — un `QMenuBar` posé sur un
        `QMainWindow` s'y intègre automatiquement, sans empaquetage
        supplémentaire."""
        menu_fichier = self.menuBar().addMenu("&Fichier")
        action_recherche = menu_fichier.addAction("&Nouvelle recherche")
        action_recherche.setShortcut(QKeySequence("Ctrl+N"))
        action_recherche.triggered.connect(self._ouvrir_recherche_vierge)
        action_candidatures = menu_fichier.addAction("&Suivi de candidature")
        action_candidatures.triggered.connect(self._ouvrir_candidatures)
        menu_fichier.addSeparator()
        action_quitter = menu_fichier.addAction("&Quitter")
        action_quitter.setShortcut(QKeySequence.StandardKey.Quit)
        action_quitter.triggered.connect(self.close)

        menu_aide = self.menuBar().addMenu("&Aide")
        action_aide = menu_aide.addAction("&Aide de Tamponné")
        action_aide.triggered.connect(self._ouvrir_aide)

    def _ouvrir_recherche_vierge(self) -> None:
        self._ouvrir_recherche()

    def _ouvrir_recherche_profil(self, nom: str, profil: Profil) -> None:
        self._ouvrir_recherche(
            filtres_existants=profil, nom_profil=nom, lancer_immediatement=True
        )

    def _ouvrir_edition_profil(self, nom: str, profil: Profil) -> None:
        self._ouvrir_recherche(
            filtres_existants=profil, nom_profil=nom, mode_edition=True
        )

    def _ouvrir_recherche(
        self,
        filtres_existants: FiltresRecherche | None = None,
        nom_profil: str | None = None,
        mode_edition: bool = False,
        lancer_immediatement: bool = False,
    ) -> None:
        if self._vue_recherche is not None:
            self._vue_recherche.arreter_recherche_en_cours()
            self._pile.removeWidget(self._vue_recherche)
            self._vue_recherche.deleteLater()
        self._vue_recherche = VueRechercheResultats(
            self._orgas_cache,
            filtres_existants=filtres_existants,
            nom_profil=nom_profil,
            mode_edition=mode_edition,
        )
        self._vue_recherche.demande_retour.connect(self._revenir_accueil)
        self._pile.addWidget(self._vue_recherche)
        self._pile.setCurrentWidget(self._vue_recherche)
        self.bouton_nav_recherche.setChecked(True)
        if lancer_immediatement:
            self._vue_recherche.lancer_recherche_immediatement()

    def _revenir_accueil(self) -> None:
        self._pile.setCurrentWidget(self._vue_accueil)
        self._vue_accueil.rafraichir()
        self.bouton_nav_accueil.setChecked(True)

    def _ouvrir_aide(self) -> None:
        self._pile.setCurrentWidget(self._vue_aide)
        self.bouton_nav_aide.setChecked(True)

    def _ouvrir_parametres(self) -> None:
        self._vue_parametres.rafraichir()
        self._pile.setCurrentWidget(self._vue_parametres)
        self.bouton_nav_parametres.setChecked(True)

    def _ouvrir_candidatures(self) -> None:
        self._vue_candidatures.rafraichir()
        self._pile.setCurrentWidget(self._vue_candidatures)
        self.bouton_nav_candidatures.setChecked(True)

    def _on_cache_rafraichi(self, orgas_cache: Organisations) -> None:
        self._orgas_cache = orgas_cache

    def closeEvent(self, event: QCloseEvent) -> None:
        """Qt plante si un `QThread` est détruit pendant qu'il tourne
        encore — même garde que `VueRechercheResultats.arreter_recherche_en_cours`.
        Borné par le timeout HTTP de `verifier_derniere_publication`."""
        if self._thread_maj is not None and self._thread_maj.isRunning():
            self._thread_maj.quit()
            self._thread_maj.wait()
        super().closeEvent(event)

    def _lancer_verification_maj(self) -> None:
        """Vérification en arrière-plan, une fois au démarrage — jamais
        de dialogue en cas d'échec, l'indicateur reste simplement caché.

        Volontairement pas appelée depuis `__init__` : appelée par `main()`
        après `show()` à la place. Les tests construisent `FenetrePrincipale`
        directement sans passer par `main()` ni faire tourner la boucle
        d'événements Qt (`app.exec()`) — un thread démarré dans `__init__`
        pourrait ne pas avoir fini avant le teardown de `qtbot.addWidget`
        et planter le processus (destruction d'un `QThread` encore actif).
        """
        self._thread_maj = QThread()
        self._verificateur_maj = VerificateurMiseAJour()
        self._verificateur_maj.moveToThread(self._thread_maj)
        self._thread_maj.started.connect(self._verificateur_maj.executer)
        self._verificateur_maj.resultat.connect(self._on_maj_verifiee)
        self._verificateur_maj.resultat.connect(self._thread_maj.quit)
        self._thread_maj.start()

    def _on_maj_verifiee(self, info: InfoMaj | None) -> None:
        self.point_maj.setVisible(info is not None)
        self._vue_parametres.afficher_maj(info)

    def _demander_maj_immediate(self) -> None:
        """Clic sur « Mettre à jour maintenant » — le marqueur est déjà
        posé par `VerificateurMiseAJour.executer`. Ferme l'app avec un code
        de sortie dédié pour que lancer.sh/lancer.bat l'applique et
        relance immédiatement plutôt qu'attendre le prochain lancement."""
        self._redemarrage_demande = True
        self.close()


def main() -> int:
    """Lance l'application (entry point `pyproject.toml`).

    `setApplicationName`/`setOrganizationName` couvrent l'identité Qt
    (À propos, emplacement de `QSettings`) — pas le nom affiché dans le
    menu Application de macOS : celui-ci vient du bundle `.app`
    (`CFBundleName`), inexistant tant que l'app tourne comme simple
    script Python. Corrigible seulement par un vrai empaquetage macOS
    (py2app/briefcase), pas depuis le code Qt (lot d'empaquetage,
    REFONTE.md §6).

    Returns:
        `CODE_RETOUR_MAJ` si l'utilisateur a demandé une mise à jour
        immédiate (voir `FenetrePrincipale._demander_maj_immediate`) —
        lancer.sh/lancer.bat l'interprètent pour relancer aussitôt après
        avoir appliqué la mise à jour ; ``0`` sinon.
    """
    app = QApplication([])
    app.setApplicationName("Tamponné")
    app.setApplicationDisplayName("Tamponné")
    app.setOrganizationName("Tamponné")
    # Police système (dont les préférences d'accessibilité, ex. KDE) capturée
    # avant la QSS, pour en dériver les tailles au lieu de les imposer.
    taille_base_pt = app.font().pointSizeF()
    # Base Fusion : rendu identique sur toutes les plateformes, là où la QSS
    # posée sur le style natif (macOS, Windows) donne des résultats inégaux.
    app.setStyle("Fusion")
    appliquer_theme(app, taille_base_pt, charger_mode_theme())

    try:
        orgas_cache = obtenir_organisations()
    except OSError, json.JSONDecodeError, urllib.error.URLError, RuntimeError:
        orgas_cache = {}

    fenetre = FenetrePrincipale(orgas_cache)
    fenetre.show()
    fenetre._lancer_verification_maj()
    app.exec()

    return CODE_RETOUR_MAJ if fenetre._redemarrage_demande else 0


if __name__ == "__main__":
    raise SystemExit(main())
