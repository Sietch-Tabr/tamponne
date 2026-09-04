"""Écran Sources : active ou désactive les sources d'offres interrogées."""

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.gui.widgets.case_a_cocher import CaseACocher
from src.parametres_sources import (
    SOURCES_DISPONIBLES,
    charger_sources_actives,
    sauvegarder_sources_actives,
)


class VueSources(QWidget):
    """Une case à cocher par source connue, toutes pré-cochées,
    sauvegarde immédiate au changement d'état (pas de bouton dédié)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(28, 24, 28, 24)
        disposition.setSpacing(16)

        titre = QLabel("Sources")
        titre.setProperty("role", "titre")
        disposition.addWidget(titre)

        sous_titre = QLabel(
            "Sources interrogées à chaque recherche — décoche celles que "
            "tu ne veux pas utiliser."
        )
        sous_titre.setProperty("role", "sousTexte")
        sous_titre.setWordWrap(True)
        disposition.addWidget(sous_titre)

        self._cases: dict[str, CaseACocher] = {}
        etats = charger_sources_actives()
        for cle, libelle in SOURCES_DISPONIBLES.items():
            case = CaseACocher(libelle)
            case.setChecked(etats.get(cle, True))
            case.toggled.connect(self._on_toggle)
            self._cases[cle] = case
            disposition.addWidget(case)

        disposition.addStretch()

    def _on_toggle(self) -> None:
        etats = {cle: case.isChecked() for cle, case in self._cases.items()}
        sauvegarder_sources_actives(etats)
