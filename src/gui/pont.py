"""Objets Python exposés à l'interface QML : actions et états, jamais de
couleur (les jetons visuels vivent uniquement dans `Theme.qml`)."""

from typing import cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.donnees.parametres_affichage import (
    MODES_THEME,
    ModeTheme,
    sauvegarder_mode_theme,
)
from src.gui.controleurs.profils import ControleurProfils
from src.gui.controleurs.recherche import ControleurRecherche
from src.gui.controleurs.reglages import ControleurReglages
from src.gui.controleurs.suivi import ControleurSuivi
from src.types import Organisations


class Pont(QObject):
    """Point d'entrée unique du QML vers le code métier (propriété requise
    `pont` de `Fenetre.qml`)."""

    mise_a_jour_disponible_changee = Signal()

    def __init__(
        self, parent: QObject | None = None, orgas_cache: Organisations | None = None
    ) -> None:
        super().__init__(parent)
        self._suivi = ControleurSuivi(self)
        self._profils = ControleurProfils(self)
        self._recherche = ControleurRecherche(orgas_cache or {}, self)
        self._reglages = ControleurReglages(self)
        self._reglages.etat_change.connect(self.mise_a_jour_disponible_changee)
        self._reglages.organisations_rafraichies.connect(
            self._recherche.remplacer_organisations
        )
        self._reglages.etat_change.connect(self._relayer_chargement_organisations)

    def _relayer_chargement_organisations(self) -> None:
        """La recherche affiche « chargement… » tant que Réglages recharge
        la liste des organisations."""
        self._recherche.definir_chargement_organisations(
            bool(self._reglages.property("cache_en_cours"))
        )

    def _lire_suivi(self) -> QObject:
        return self._suivi

    suivi = Property(QObject, _lire_suivi, constant=True)
    """Contrôleur de l'écran Suivi (`ControleurSuivi`)."""

    def _lire_profils(self) -> QObject:
        return self._profils

    profils = Property(QObject, _lire_profils, constant=True)
    """Contrôleur de l'écran Profils (`ControleurProfils`)."""

    def _lire_recherche(self) -> QObject:
        return self._recherche

    recherche = Property(QObject, _lire_recherche, constant=True)
    """Contrôleur de l'écran Recherche (`ControleurRecherche`)."""

    def _lire_reglages(self) -> QObject:
        return self._reglages

    reglages = Property(QObject, _lire_reglages, constant=True)
    """Contrôleur de l'écran Réglages (`ControleurReglages`)."""

    @property
    def reglages_controleur(self) -> ControleurReglages:
        """Contrôleur des Réglages typé, pour `main()` (vérification, sortie)."""
        return self._reglages

    def arreter(self) -> None:
        """Attend la fin des traitements en arrière-plan avant de quitter."""
        self._suivi.arreter()
        self._recherche.arreter()
        self._reglages.arreter()

    def _lire_mise_a_jour_disponible(self) -> bool:
        return bool(self._reglages.pastille)

    mise_a_jour_disponible = Property(
        bool, _lire_mise_a_jour_disponible, notify=mise_a_jour_disponible_changee
    )
    """Vrai si une publication plus récente attend : pastille de l'onglet Réglages."""

    @Slot(str)
    def enregistrer_mode_theme(self, mode: str) -> None:
        """Persiste le mode de thème choisi depuis l'interface ; ignore une
        valeur inconnue plutôt que d'écrire un réglage invalide."""
        if mode in MODES_THEME:
            sauvegarder_mode_theme(cast(ModeTheme, mode))
