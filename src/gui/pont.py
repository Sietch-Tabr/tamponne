"""Objets Python exposés à l'interface QML : actions et états, jamais de
couleur (les jetons visuels vivent uniquement dans `Theme.qml`)."""

from typing import cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.gui.controleur_profils import ControleurProfils
from src.gui.controleur_suivi import ControleurSuivi
from src.parametres_affichage import MODES_THEME, ModeTheme, sauvegarder_mode_theme


class Pont(QObject):
    """Point d'entrée unique du QML vers le code métier (propriété requise
    `pont` de `Fenetre.qml`)."""

    mise_a_jour_disponible_changee = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._mise_a_jour_disponible = False
        self._suivi = ControleurSuivi(self)
        self._profils = ControleurProfils(self)

    def _lire_suivi(self) -> QObject:
        return self._suivi

    suivi = Property(QObject, _lire_suivi, constant=True)
    """Contrôleur de l'écran Suivi (`ControleurSuivi`)."""

    def _lire_profils(self) -> QObject:
        return self._profils

    profils = Property(QObject, _lire_profils, constant=True)
    """Contrôleur de l'écran Profils (`ControleurProfils`)."""

    def arreter(self) -> None:
        """Attend la fin des traitements en arrière-plan avant de quitter."""
        self._suivi.arreter()

    def _lire_mise_a_jour_disponible(self) -> bool:
        return self._mise_a_jour_disponible

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
