"""Écran d'accueil : liste des profils sauvegardés, point d'entrée de l'app."""

from collections.abc import Callable
from functools import partial

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.gui.widgets.dialogue_selection import question_oui_non
from src.profils import (
    charger_profils,
    dupliquer_profil,
    resume_profil,
    supprimer_profil,
)
from src.types import Profil


class _LigneProfil(QWidget):
    """Une rangée composée (titre + résumé + badge + actions), pas un bloc
    de texte brut avec menu contextuel — les actions sont des boutons
    cliquables directement dans la tuile, comme dans une vraie app."""

    def __init__(
        self,
        nom: str,
        profil: Profil,
        on_action: Callable[[str, str, Profil], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(14, 12, 14, 12)
        disposition.setSpacing(6)

        entete = QHBoxLayout()
        entete.setSpacing(12)
        nom_label = QLabel(profil.get("label", nom))
        nom_label.setProperty("role", "nom")
        entete.addWidget(nom_label, 1)
        nb_nouv = profil.get("nb_nouvelles", 0)
        if nb_nouv:
            badge = QLabel(f"★ {nb_nouv} nouvelle(s)")
            badge.setProperty("role", "badge")
            entete.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        disposition.addLayout(entete)

        resume = QLabel(resume_profil(profil))
        resume.setProperty("role", "sousTexte")
        disposition.addWidget(resume)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        for texte, action, variant in [
            ("Lancer", "lancer", "ligneAction"),
            ("Modifier", "modifier", "ligneAction"),
            ("Dupliquer", "dupliquer", "ligneAction"),
            ("Supprimer", "supprimer", "ligneActionDanger"),
        ]:
            bouton = QPushButton(texte)
            bouton.setProperty("variant", variant)
            bouton.clicked.connect(partial(on_action, action, nom, profil))
            actions.addWidget(bouton)
        actions.addStretch()
        disposition.addLayout(actions)


class VueAccueil(QWidget):
    """Premier écran affiché : liste des profils sauvegardés.

    Pas de bouton « nouvelle recherche » propre : couvert par l'entrée
    « Recherche » du bandeau de navigation persistant de
    `FenetrePrincipale`, pas de double affordance pour la même action.
    """

    demande_lancer_profil = Signal(str, dict)
    demande_modifier_profil = Signal(str, dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profils: dict[str, Profil] = {}
        self._construire_ui()
        self.rafraichir()

    def _construire_ui(self) -> None:
        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(28, 24, 28, 24)
        disposition.setSpacing(16)

        titre = QLabel("Tamponné")
        titre.setProperty("role", "titre")
        disposition.addWidget(titre)

        sous_titre = QLabel("Recherche d'offres — Choisir le Service Public")
        sous_titre.setProperty("role", "sousTexte")
        disposition.addWidget(sous_titre)

        self.liste_profils = QListWidget()
        self.liste_profils.setSpacing(0)
        self.liste_profils.itemDoubleClicked.connect(self._on_double_clic)
        disposition.addWidget(self.liste_profils, 1)

    def rafraichir(self) -> None:
        """Recharge la liste des profils depuis le disque."""
        self._profils = charger_profils()
        self.liste_profils.clear()
        if not self._profils:
            item = QListWidgetItem(
                "Aucun profil sauvegardé — lance une nouvelle recherche"
            )
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.liste_profils.addItem(item)
            return
        for nom, profil in self._profils.items():
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, nom)
            ligne = _LigneProfil(nom, profil, self._traiter_action)
            item.setSizeHint(ligne.sizeHint())
            self.liste_profils.addItem(item)
            self.liste_profils.setItemWidget(item, ligne)

    def _on_double_clic(self, item: QListWidgetItem) -> None:
        """Double-clic sur un profil = lancer sa recherche directement,
        en plus du bouton « Lancer » déjà présent dans la tuile."""
        nom = item.data(Qt.ItemDataRole.UserRole)
        if nom is None:
            return
        self._traiter_action("lancer", nom, self._profils[nom])

    def _traiter_action(self, action: str, nom: str, profil: Profil) -> None:
        """Résolution de l'action choisie, appelée par les boutons de la
        tuile — reste testable sans piloter de clic réel."""
        if action == "lancer":
            self.demande_lancer_profil.emit(nom, profil)
        elif action == "modifier":
            self.demande_modifier_profil.emit(nom, profil)
        elif action == "dupliquer":
            self._dupliquer(nom)
        elif action == "supprimer":
            self._supprimer(nom, profil)

    def _dupliquer(self, nom: str) -> None:
        nouveau_nom, ok = QInputDialog.getText(
            self,
            "Dupliquer le profil",
            "Nom du nouveau profil :",
            text=f"{nom}-copie",
        )
        if ok and nouveau_nom.strip():
            dupliquer_profil(nom, nouveau_nom.strip())
            self.rafraichir()

    def _supprimer(self, nom: str, profil: Profil) -> None:
        if question_oui_non(
            self,
            "Supprimer le profil",
            f"Supprimer le profil « {profil.get('label', nom)} » ?",
        ):
            supprimer_profil(nom)
            self.rafraichir()
