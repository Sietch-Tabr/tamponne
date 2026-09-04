"""Écran Suivi de candidature : liste des candidatures suivies."""

import webbrowser
from collections.abc import Callable
from datetime import date as date_cls
from functools import partial

from PySide6.QtCore import QDate, QThread, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.candidatures import (
    TYPES_EVENEMENT,
    ajouter_evenement,
    charger_candidatures,
    marquer_disponibilite,
    relance_suggeree,
    statut_libelle,
    supprimer_candidature,
)
from src.gui.travailleurs import VerificateurDisponibilite
from src.gui.widgets.dialogue_detail_offre import DialogueDetailOffre
from src.gui.widgets.dialogue_selection import boutons_ok_annuler, question_oui_non
from src.types import Candidature


class _DialogueEvenement(QDialog):
    """Formulaire d'ajout d'un événement à l'historique d'une candidature."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajouter un événement")
        disposition = QFormLayout(self)

        self.type_combo = QComboBox()
        for cle, libelle in TYPES_EVENEMENT.items():
            self.type_combo.addItem(libelle, cle)
        disposition.addRow("Type", self.type_combo)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        disposition.addRow("Date", self.date_edit)

        self.note_champ = QLineEdit()
        disposition.addRow("Note (optionnel)", self.note_champ)

        boutons = boutons_ok_annuler()
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        disposition.addRow(boutons)

    def type_choisi(self) -> str:
        return str(self.type_combo.currentData())

    def date_choisie(self) -> str:
        return self.date_edit.date().toString("yyyy-MM-dd")

    def note_saisie(self) -> str:
        return self.note_champ.text().strip()


def _reformater_date_iso(date_iso: str) -> str:
    """Reformate une date ISO (`YYYY-MM-DD`, format de `EvenementCandidature.date`)
    en JJ/MM/AAAA. Retourne la chaîne d'origine si le format n'est pas
    reconnu (ne devrait pas arriver, écrit uniquement par ce module)."""
    try:
        return date_cls.fromisoformat(date_iso).strftime("%d/%m/%Y")
    except ValueError:
        return date_iso


class _LigneCandidature(QWidget):
    """Une rangée composée par candidature : titre + statut + actions à
    gauche (même pattern que `_LigneProfil`, src/gui/vues/accueil.py),
    historique complet (ordre chronologique) à droite."""

    def __init__(
        self,
        reference: str,
        candidature: Candidature,
        on_action: Callable[[str, str, Candidature], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        disposition_principale = QHBoxLayout(self)
        disposition_principale.setContentsMargins(14, 12, 14, 12)
        disposition_principale.setSpacing(20)

        colonne_gauche = QVBoxLayout()
        colonne_gauche.setSpacing(6)

        entete = QHBoxLayout()
        entete.setSpacing(12)
        titre_label = QLabel(candidature["offre_titre"])
        titre_label.setProperty("role", "nom")
        entete.addWidget(titre_label, 1)
        if not candidature.get("disponible", True):
            badge_offre = QLabel("Offre dépubliée")
            badge_offre.setProperty("role", "badgeNeutre")
            entete.addWidget(badge_offre, 0, Qt.AlignmentFlag.AlignVCenter)
        if relance_suggeree(candidature):
            badge = QLabel("Relance suggérée")
            badge.setProperty("role", "badgeAttention")
            entete.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        colonne_gauche.addLayout(entete)

        resume = QLabel(
            f"{candidature['offre_employeur']} · suivi depuis le "
            f"{_reformater_date_iso(candidature['date_candidature'])} · "
            f"{statut_libelle(candidature)}"
        )
        resume.setProperty("role", "sousTexte")
        colonne_gauche.addWidget(resume)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        for texte, action, variant in [
            ("Voir l'offre", "voir", "ligneAction"),
            ("Voir le détail", "detail", "ligneAction"),
            ("Ajouter un événement", "evenement", "ligneAction"),
            ("Supprimer", "supprimer", "ligneActionDanger"),
        ]:
            bouton = QPushButton(texte)
            bouton.setProperty("variant", variant)
            if action == "voir" and not candidature.get("disponible", True):
                bouton.setToolTip(
                    "Cette offre n'est plus en ligne — le lien ne mènera "
                    "plus à rien d'utile, l'historique reste ci-dessus."
                )
            bouton.clicked.connect(partial(on_action, action, reference, candidature))
            actions.addWidget(bouton)
        actions.addStretch()
        colonne_gauche.addLayout(actions)
        disposition_principale.addLayout(colonne_gauche, 1)

        colonne_historique = QWidget()
        colonne_historique.setMinimumWidth(280)
        colonne_historique.setMaximumWidth(380)
        # Sans ça, hérite du fond opaque générique de theme.py (déjà vu sur les QCheckBox).
        colonne_historique.setStyleSheet("background: transparent;")
        disposition_historique = QVBoxLayout(colonne_historique)
        disposition_historique.setContentsMargins(0, 0, 0, 0)
        disposition_historique.setSpacing(3)
        label_titre_historique = QLabel("Historique")
        label_titre_historique.setProperty("role", "nom")
        disposition_historique.addWidget(label_titre_historique)
        historique = sorted(
            candidature.get("historique") or [], key=lambda e: e["date"]
        )
        for evenement in historique:
            libelle = TYPES_EVENEMENT.get(evenement["type"], evenement["type"])
            texte = f"{_reformater_date_iso(evenement['date'])} — {libelle}"
            if evenement.get("note"):
                texte += f" ({evenement['note']})"
            label_evenement = QLabel(texte)
            label_evenement.setProperty("role", "sousTexte")
            label_evenement.setWordWrap(True)
            disposition_historique.addWidget(label_evenement)
        disposition_historique.addStretch()
        disposition_principale.addWidget(colonne_historique, 0)


class VueCandidatures(QWidget):
    """Écran Suivi : liste des candidatures suivies."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._candidatures: dict[str, Candidature] = {}
        self._thread: QThread | None = None
        self._verificateur: VerificateurDisponibilite | None = None
        self._construire_ui()
        self.bouton_verifier.clicked.connect(self._lancer_verification)
        self.rafraichir()

    def _construire_ui(self) -> None:
        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(28, 24, 28, 24)
        disposition.setSpacing(16)

        titre = QLabel("Suivi de candidature")
        titre.setProperty("role", "titre")
        disposition.addWidget(titre)

        entete = QHBoxLayout()
        sous_titre = QLabel(
            "Historique des candidatures envoyées depuis un résultat de recherche."
        )
        sous_titre.setProperty("role", "sousTexte")
        sous_titre.setWordWrap(True)
        entete.addWidget(sous_titre, 1)

        self.bouton_verifier = QPushButton("Vérifier les offres")
        self.bouton_verifier.setToolTip(
            "Vérifie si les offres suivies sont toujours en ligne"
        )
        entete.addWidget(self.bouton_verifier, 0)
        disposition.addLayout(entete)

        self.liste = QListWidget()
        self.liste.setSpacing(0)
        disposition.addWidget(self.liste, 1)

    def _lancer_verification(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return  # vérification déjà en cours
        if not self._candidatures:
            return

        self.bouton_verifier.setEnabled(False)
        self.bouton_verifier.setText("Vérification…")

        self._thread = QThread()
        self._verificateur = VerificateurDisponibilite(dict(self._candidatures))
        self._verificateur.moveToThread(self._thread)
        self._thread.started.connect(self._verificateur.executer)
        self._verificateur.progression.connect(self._on_progression_verification)
        self._verificateur.resultat.connect(self._on_resultat_verification)
        self._verificateur.resultat.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_verification_termine)
        self._thread.start()

    def _on_progression_verification(self, i: int, total: int) -> None:
        self.bouton_verifier.setText(f"Vérification… {i}/{total}")

    def _on_resultat_verification(self, resultats: dict[str, bool | None]) -> None:
        for reference, disponible in resultats.items():
            if disponible is not None:
                marquer_disponibilite(reference, disponible)
        self.rafraichir()

    def _on_thread_verification_termine(self) -> None:
        self._thread = None
        self._verificateur = None
        self.bouton_verifier.setEnabled(True)
        self.bouton_verifier.setText("Vérifier les offres")

    def arreter_verification_en_cours(self) -> None:
        """Arrête proprement une vérification en cours, si besoin — même
        motif que `VueRechercheResultats.arreter_recherche_en_cours` :
        détruire un `QThread` encore actif fait planter le processus."""
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

    def rafraichir(self) -> None:
        """Recharge la liste des candidatures depuis le disque."""
        self._candidatures = charger_candidatures()
        self.liste.clear()
        if not self._candidatures:
            item = QListWidgetItem(
                "Aucune candidature suivie — utilise « Suivre cette offre » "
                "depuis un résultat de recherche"
            )
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.liste.addItem(item)
            return
        for reference, candidature in sorted(
            self._candidatures.items(),
            key=lambda kv: kv[1]["date_candidature"],
            reverse=True,
        ):
            item = QListWidgetItem()
            ligne = _LigneCandidature(reference, candidature, self._traiter_action)
            item.setSizeHint(ligne.sizeHint())
            self.liste.addItem(item)
            self.liste.setItemWidget(item, ligne)

    def _traiter_action(
        self, action: str, reference: str, candidature: Candidature
    ) -> None:
        """Résolution de l'action choisie, appelée par les boutons de la
        tuile — reste testable sans piloter de clic réel."""
        if action == "voir":
            url = candidature["offre_url"]
            if url.startswith("https://"):
                webbrowser.open(url)
        elif action == "detail":
            self._voir_detail(candidature)
        elif action == "evenement":
            self._ajouter_evenement(reference)
        elif action == "supprimer":
            self._supprimer(reference, candidature)

    def _voir_detail(self, candidature: Candidature) -> None:
        """Affiche le détail archivé au moment du suivi — aucun appel
        réseau, fonctionne même si l'offre a depuis été dépubliée."""
        dialogue = DialogueDetailOffre(
            candidature["offre_titre"],
            candidature["offre_employeur"],
            candidature["detail"],
            candidature["offre_url"],
            candidature["offre_reference"],
            self,
        )
        dialogue.exec()

    def _ajouter_evenement(self, reference: str) -> None:
        dialogue = _DialogueEvenement(self)
        if dialogue.exec() == QDialog.DialogCode.Accepted:
            ajouter_evenement(
                reference,
                dialogue.type_choisi(),
                dialogue.date_choisie(),
                dialogue.note_saisie(),
            )
            self.rafraichir()

    def _supprimer(self, reference: str, candidature: Candidature) -> None:
        if question_oui_non(
            self,
            "Arrêter le suivi",
            f"Arrêter le suivi de « {candidature['offre_titre']} » ?",
        ):
            supprimer_candidature(reference)
            self.rafraichir()
