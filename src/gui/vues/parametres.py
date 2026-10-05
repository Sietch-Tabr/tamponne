"""Écran Paramètres : sources, apparence, mise à jour, cache organisations.

Pas de bouton retour propre : couvert par le bandeau de navigation
persistant de `FenetrePrincipale` (« Accueil »), pas de double
affordance pour la même action.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.cache import age_cache_organisations, obtenir_organisations
from src.gui.vues.sources import VueSources
from src.maj import version_locale
from src.parametres_affichage import (
    MODES_THEME,
    charger_mode_theme,
    sauvegarder_mode_theme,
)
from src.types import InfoMaj, Organisations


class VueParametres(QWidget):
    """Écran Paramètres — sources, thème, mise à jour disponible, cache
    organisations."""

    cache_rafraichi = Signal(dict)
    demande_maj_immediate = Signal()
    """Émis par le clic sur « Mettre à jour maintenant » — la fenêtre
    principale décide de la fermeture propre (voir `FenetrePrincipale`)."""
    mode_theme_change = Signal(str)
    """Émis avec le nouveau mode (« auto », « sombre », « clair ») une fois
    enregistré — la fenêtre principale l'applique aussitôt."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(28, 24, 28, 24)
        disposition.setSpacing(16)

        titre = QLabel("Paramètres")
        titre.setProperty("role", "titre")
        disposition.addWidget(titre)

        # Défilement comme l'Aide : des notes de version longues ne doivent
        # pas écraser les autres cartes quand la fenêtre est basse.
        contenu = QWidget()
        pile = QVBoxLayout(contenu)
        pile.setContentsMargins(0, 0, 0, 0)
        pile.setSpacing(16)

        self.groupe_sources = QGroupBox("Sources")
        pile_sources = QVBoxLayout(self.groupe_sources)
        self.vue_sources = VueSources(afficher_titre=False)
        pile_sources.addWidget(self.vue_sources)
        pile.addWidget(self.groupe_sources)

        self.carte_apparence = QGroupBox("Apparence")
        formulaire_apparence = QFormLayout(self.carte_apparence)
        self.combo_theme = QComboBox()
        for mode, libelle in MODES_THEME.items():
            self.combo_theme.addItem(libelle, mode)
        self.combo_theme.setCurrentIndex(
            self.combo_theme.findData(charger_mode_theme())
        )
        self.combo_theme.currentIndexChanged.connect(self._on_theme_choisi)
        formulaire_apparence.addRow("Thème", self.combo_theme)
        pile.addWidget(self.carte_apparence)

        self.carte_maj = QGroupBox("Mise à jour")
        pile_maj = QVBoxLayout(self.carte_maj)
        self.label_maj_version = QLabel()
        self.label_maj_version.setProperty("role", "nom")
        pile_maj.addWidget(self.label_maj_version)
        self.label_maj_notes = QLabel()
        self.label_maj_notes.setProperty("role", "sousTexte")
        self.label_maj_notes.setWordWrap(True)
        # Notes des releases Codeberg rédigées en Markdown (titres, listes) :
        # en AutoText, Qt ne le détecte pas et affiche « ### » et « - » bruts.
        self.label_maj_notes.setTextFormat(Qt.TextFormat.MarkdownText)
        pile_maj.addWidget(self.label_maj_notes)
        self.bouton_maj = QPushButton("Mettre à jour maintenant")
        self.bouton_maj.setToolTip(
            "Ferme l'application et applique la mise à jour immédiatement "
            "— sinon elle s'applique automatiquement au prochain lancement."
        )
        self.bouton_maj.clicked.connect(self.demande_maj_immediate.emit)
        pile_maj.addWidget(self.bouton_maj)
        pile.addWidget(self.carte_maj)

        self.label_cache = QLabel()
        self.label_cache.setProperty("role", "sousTexte")
        pile.addWidget(self.label_cache)

        self.bouton_rafraichir = QPushButton("Rafraîchir le cache des organisations")
        self.bouton_rafraichir.clicked.connect(self._rafraichir_cache)
        pile.addWidget(self.bouton_rafraichir)
        pile.addStretch()

        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        defilement.setWidget(contenu)
        disposition.addWidget(defilement, 1)

        self.rafraichir()
        self.afficher_maj(None)

    def afficher_maj(self, info: InfoMaj | None) -> None:
        """Peuple la carte mise à jour — toujours visible, bouton actif
        seulement si une mise à jour est disponible."""
        if info is None:
            self.label_maj_version.setText(f"Version {version_locale()} (à jour)")
            self.label_maj_notes.setText("Aucune mise à jour disponible.")
            self.bouton_maj.setEnabled(False)
            return
        self.label_maj_version.setText(f"Version {info['version']} disponible")
        self.label_maj_notes.setText(info["notes"] or "Pas de notes de version.")
        self.bouton_maj.setEnabled(True)

    def _on_theme_choisi(self, _index: int) -> None:
        mode = self.combo_theme.currentData()
        sauvegarder_mode_theme(mode)
        self.mode_theme_change.emit(mode)

    def rafraichir(self) -> None:
        """Met à jour l'affichage de l'âge du cache (pas de scraping)."""
        age = age_cache_organisations()
        self.label_cache.setText(
            f"Cache organisations\u00a0: mis à jour {age}"
            if age
            else "Cache organisations\u00a0: jamais chargé"
        )

    def _rafraichir_cache(self) -> None:
        """Force le rafraîchissement (scraping synchrone — rare, pas besoin
        d'un `QThread` dédié pour cette action manuelle et occasionnelle)."""
        try:
            orgas_cache: Organisations = obtenir_organisations(forcer=True)
        except RuntimeError:
            QMessageBox.warning(
                self,
                "Rafraîchissement impossible",
                "Le site choisirleservicepublic.gouv.fr est actuellement "
                "inaccessible. Réessayez plus tard.",
            )
            return
        self.rafraichir()
        self.cache_rafraichi.emit(orgas_cache)
