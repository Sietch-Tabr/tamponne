"""Écran Suivi de candidature : liste des candidatures suivies."""

import webbrowser
from functools import partial

from PySide6.QtCore import QDate, QEvent, QModelIndex, QObject, QThread, Qt
from PySide6.QtGui import QAction, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.candidatures import (
    TYPES_EVENEMENT,
    ajouter_evenement,
    charger_candidatures,
    marquer_disponibilite,
    supprimer_candidature,
)
from src.gui.travailleurs import VerificateurDisponibilite
from src.gui.widgets.delegue_candidature import (
    ACTIONS,
    ROLE_REFERENCE,
    DelegueCandidature,
    ModeleCandidatures,
)
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
        """Clé du type d'événement choisi (voir `TYPES_EVENEMENT`)."""
        return str(self.type_combo.currentData())

    def date_choisie(self) -> str:
        """Date choisie au format ISO `YYYY-MM-DD`, celui de l'historique."""
        return self.date_edit.date().toString("yyyy-MM-dd")

    def note_saisie(self) -> str:
        """Note libre saisie, sans espaces de début et de fin (vide si aucune)."""
        return self.note_champ.text().strip()


_TOUCHES_ACTIONS: dict[Qt.Key, str] = {
    Qt.Key.Key_Return: "detail",
    Qt.Key.Key_Enter: "detail",
    Qt.Key.Key_Delete: "supprimer",
    Qt.Key.Key_Backspace: "supprimer",
}
"""Touches du clavier → action sur la candidature courante."""


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

        self.label_vide = QLabel(
            "Aucune candidature suivie — utilise « Suivre cette offre » "
            "depuis un résultat de recherche"
        )
        self.label_vide.setProperty("role", "sousTexte")
        self.label_vide.setWordWrap(True)
        self.label_vide.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.modele = ModeleCandidatures(self)
        self.liste = QListView()
        self.liste.setModel(self.modele)
        self.liste.setMouseTracking(True)
        # La hauteur d'une ligne dépend de la largeur (historique replié à la
        # ligne) : Adjust force son recalcul à chaque redimensionnement.
        self.liste.setResizeMode(QListView.ResizeMode.Adjust)
        self.liste.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.liste.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.delegue = DelegueCandidature(self.liste)
        self.liste.setItemDelegate(self.delegue)
        self.delegue.action_demandee.connect(self._on_action_demandee)
        self.liste.doubleClicked.connect(self._on_double_clic)
        self.liste.viewport().installEventFilter(self)
        self._ajouter_actions_clavier()

        self._pile = QStackedWidget()
        self._pile.addWidget(self.label_vide)
        self._pile.addWidget(self.liste)
        disposition.addWidget(self._pile, 1)

    def _ajouter_actions_clavier(self) -> None:
        """Les boutons étant peints, leurs actions sont aussi exposées au
        menu contextuel et au clavier (voir `_TOUCHES_ACTIONS`), sur la
        ligne courante."""
        self.liste.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        for action, libelle in ACTIONS:
            qaction = QAction(libelle, self.liste)
            qaction.triggered.connect(partial(self._declencher_sur_courante, action))
            self.liste.addAction(qaction)
        self.liste.installEventFilter(self)

    def eventFilter(self, objet: QObject, evenement: QEvent) -> bool:
        if objet is self.liste.viewport() and evenement.type() == QEvent.Type.Leave:
            self.delegue.reinitialiser_survol()
        # Filtre plutôt que raccourcis QAction : ceux-ci exigent une
        # fenêtre active, et QListView consomme déjà Entrée.
        if (
            objet is self.liste
            and isinstance(evenement, QKeyEvent)
            and evenement.type() == QEvent.Type.KeyPress
            and evenement.key() in _TOUCHES_ACTIONS
        ):
            self._declencher_sur_courante(_TOUCHES_ACTIONS[Qt.Key(evenement.key())])
            return True
        return super().eventFilter(objet, evenement)

    def _declencher_sur_courante(self, action: str) -> None:
        index = self.liste.currentIndex()
        if index.isValid():
            self._on_action_demandee(action, index.data(ROLE_REFERENCE))

    def _on_double_clic(self, index: QModelIndex) -> None:
        self._on_action_demandee("detail", index.data(ROLE_REFERENCE))

    def _on_action_demandee(self, action: str, reference: str) -> None:
        candidature = self._candidatures.get(reference)
        if candidature is not None:
            self._traiter_action(action, reference, candidature)

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
        self.modele.definir_candidatures(self._candidatures)
        self._pile.setCurrentWidget(
            self.liste if self._candidatures else self.label_vide
        )

    def _traiter_action(
        self, action: str, reference: str, candidature: Candidature
    ) -> None:
        """Résolution de l'action choisie (bouton peint, clavier ou menu
        contextuel) — reste testable sans piloter de clic réel."""
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
