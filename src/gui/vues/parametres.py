"""Écran Paramètres : cache organisations, accessible depuis l'Accueil.

Pas de bouton retour propre : couvert par le bandeau de navigation
persistant de `FenetrePrincipale` (« Accueil »), pas de double
affordance pour la même action.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.cache import age_cache_organisations, obtenir_organisations
from src.maj import version_locale
from src.types import InfoMaj, Organisations


class VueParametres(QWidget):
    """Écran Paramètres — cache organisations, mise à jour disponible."""

    cache_rafraichi = Signal(dict)
    demande_maj_immediate = Signal()
    """Émis par le clic sur « Mettre à jour maintenant » — la fenêtre
    principale décide de la fermeture propre (voir `FenetrePrincipale`)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(28, 24, 28, 24)
        disposition.setSpacing(16)

        titre = QLabel("Paramètres")
        titre.setProperty("role", "titre")
        disposition.addWidget(titre)

        self.carte_maj = QGroupBox("Mise à jour")
        pile_maj = QVBoxLayout(self.carte_maj)
        self.label_maj_version = QLabel()
        self.label_maj_version.setProperty("role", "nom")
        pile_maj.addWidget(self.label_maj_version)
        self.label_maj_notes = QLabel()
        self.label_maj_notes.setProperty("role", "sousTexte")
        self.label_maj_notes.setWordWrap(True)
        pile_maj.addWidget(self.label_maj_notes)
        self.bouton_maj = QPushButton("Mettre à jour maintenant")
        self.bouton_maj.setToolTip(
            "Ferme l'application et applique la mise à jour immédiatement "
            "— sinon elle s'applique automatiquement au prochain lancement."
        )
        self.bouton_maj.clicked.connect(self.demande_maj_immediate.emit)
        pile_maj.addWidget(self.bouton_maj)
        disposition.addWidget(self.carte_maj)

        self.label_cache = QLabel()
        self.label_cache.setProperty("role", "sousTexte")
        disposition.addWidget(self.label_cache)

        self.bouton_rafraichir = QPushButton("Rafraîchir le cache des organisations")
        self.bouton_rafraichir.clicked.connect(self._rafraichir_cache)
        disposition.addWidget(self.bouton_rafraichir)
        disposition.addStretch()

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

    def rafraichir(self) -> None:
        """Met à jour l'affichage de l'âge du cache (pas de scraping)."""
        age = age_cache_organisations()
        self.label_cache.setText(
            f"Cache organisations : mis à jour {age}"
            if age
            else "Cache organisations : jamais chargé"
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
