"""Vue combinée Recherche + Résultats, panneaux côte à côte.

Décision de disposition du 2026-09-01 (REFONTE.md §8) : un seul écran
plutôt que deux vues séparées comme en TUI — la contrainte de largeur
de terminal qui justifiait deux écrans ne s'applique plus à une
fenêtre GUI redimensionnable.

La recherche réseau tourne dans un `QThread` (voir `travailleurs.py`) —
le worker n'émet ses signaux qu'en direction de méthodes liées de cette
classe, jamais de fonctions/lambdas (règle vérifiée §8, étape 2).
"""

import webbrowser
from typing import cast

from PySide6.QtCore import QModelIndex, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.cache import maj_cache_offres
from src.candidatures import ajouter_candidature, generer_archive_pdf
from src.export import exporter_html, ouvrir_dans_navigateur
from src.filtres import (
    CORPS_GRADES,
    DATES_PUBLICATION,
    DOMAINES,
    EXPERIENCES,
    LOCALISATIONS,
    filtrer_par_grades,
    resumer_filtres,
)
from src.gui.modele_offres import ROLE_OFFRE, ModeleOffres, ProxyOffres
from src.gui.travailleurs import TravailleurRecherche
from src.gui.widgets.case_a_cocher import CaseACocher
from src.gui.widgets.dialogue_detail_offre import DialogueDetailOffre
from src.gui.widgets.dialogue_selection import (
    DialogueSelectionGrades,
    DialogueSelectionListe,
    DialogueSelectionOrganisations,
    question_oui_non,
)
from src.gui.widgets.ligne_responsive import LigneResponsive
from src.profils import ajouter_profil, mettre_a_jour_stats, modifier_profil
from src.sources.choisirleservicepublic import MAX_PAGES, recuperer_detail_offre
from src.sources.choisirleservicepublic.extraction import filtrer_grades_superieurs
from src.types import FiltresRecherche, Offre, Organisations, Profil

_INDIFFERENT = "Indifférente"

_CATEGORIES_SUPERIEURES = [
    ("A+\n(direction)", "A+ (direction)"),
    ("A+\n(autres)", "A+ (autres emplois fonctionnels)"),
]
_CATEGORIES_SIMPLES = [
    ("A", "A"),
    ("B", "B"),
    ("C", "C"),
]

_VERSANTS_CHOIX = [
    ("etat", "FPE", "Fonction publique de l'État"),
    ("hospitalier", "FPH", "Fonction publique Hospitalière"),
    ("territorial", "FPT", "Fonction publique Territoriale"),
]

_TYPES_POSTE_CHOIX = [
    ("Titulaire-éligible (titulaires + postes ouverts aux deux statuts)", None),
    ("Titulaire uniquement", ["titulaire"]),
    ("Contractuel uniquement", ["contractuel"]),
    ("Tous (y compris contractuels)", "__tous__"),
]


def _libelle_selection(prefixe: str, selection: list[str]) -> str:
    """Libellé (sur 2 lignes : nom du filtre, puis état) du bouton
    résumant une sélection multiple (Domaines, Localisations,
    Organisations) — évite d'empiler une liste longue dans la barre de
    gauche, voir `DialogueSelectionListe`."""
    if not selection:
        etat = "Tous"
    elif len(selection) == 1:
        etat = "1 sélectionné"
    else:
        etat = f"{len(selection)} sélectionnés"
    return f"{prefixe}\n{etat}"


def _titre_section(texte: str) -> QLabel:
    """Titre de section fixe (les sections ne se replient plus)."""
    label = QLabel(texte)
    label.setProperty("role", "nom")
    return label


def _bouton_selection() -> QPushButton:
    """Bouton résumant une sélection multiple (voir `_libelle_selection`) —
    largeur adaptée au contenu plutôt qu'étirée sur tout le panneau."""
    bouton = QPushButton()
    bouton.setMinimumWidth(130)
    return bouton


def _ligne_solo(widget: QWidget) -> QHBoxLayout:
    """Empêche un widget seul de s'étirer sur toute la largeur du panneau
    dans le `QVBoxLayout` parent — `QSizePolicy` seule n'y suffit pas
    (vérifié : un `QVBoxLayout` étire son unique enfant quelle que soit sa
    politique de taille horizontale), il faut un `addStretch()` à côté,
    même pattern que `_ajouter_ligne`/`ligne_versants`/`ligne_options`."""
    ligne = QHBoxLayout()
    ligne.addWidget(widget)
    ligne.addStretch()
    return ligne


class VueRechercheResultats(QWidget):
    """Panneau de filtres (gauche) + tableau de résultats (droite)."""

    demande_retour = Signal()
    """Émis une fois le profil enregistré, en mode édition."""

    def __init__(
        self,
        orgas_cache: Organisations | None = None,
        *,
        filtres_existants: FiltresRecherche | None = None,
        nom_profil: str | None = None,
        mode_edition: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._orgas_cache = orgas_cache or {}
        self._filtres_existants: FiltresRecherche = filtres_existants or {}
        self.nom_profil = nom_profil
        self.mode_edition = mode_edition

        self._categories_cases: list[tuple[CaseACocher, str]] = []
        self._domaines_selection: list[str] = list(
            self._filtres_existants.get("domaines") or []
        )
        self._localisations_selection: list[str] = list(
            self._filtres_existants.get("localisations") or []
        )
        self._organisations_selection: list[str] = list(
            self._filtres_existants.get("organisations") or []
        )
        self._grades_selection: list[str] = list(
            self._filtres_existants.get("grades") or []
        )
        self.bouton_domaines: QPushButton
        self.bouton_localisations: QPushButton
        self.bouton_organisations: QPushButton
        self.bouton_grades: QPushButton
        self._versants_cases: list[tuple[CaseACocher, str]] = []
        self._type_poste_combo: QComboBox
        self._experience_combo: QComboBox
        self._date_pub_combo: QComboBox
        self._management_case: CaseACocher
        self._teletravail_case: CaseACocher
        self._grades_superieurs_case: CaseACocher
        self._mot_cle_champ: QLineEdit
        self.bouton_lancer: QPushButton
        self.bouton_raz: QPushButton
        self.bouton_suivre: QPushButton
        self.bouton_voir_detail: QPushButton
        self.table_resultats: QTableView
        self.champ_filtre_resultats: QLineEdit
        self.label_entete: QLabel
        self.barre_progression: QProgressBar
        self.case_nouvelles_seulement: CaseACocher

        self._afficher_tout = False
        self._grades_filtrage: list[str] = []
        self._offres_affichees: list[Offre] = []
        self._modele_offres = ModeleOffres(self)
        self._proxy_offres = ProxyOffres(self)
        self._proxy_offres.setSourceModel(self._modele_offres)
        self._nouvelles: set[str] = set()
        self._dernier_nb_pages = 1
        self._thread: QThread | None = None
        self._travailleur: TravailleurRecherche | None = None
        self._pages_par_source: dict[str, tuple[int, int]] = {}
        self._nb_sources_lancees = 0
        self._nb_sources_terminees = 0
        self._avertissements: list[str] = []

        self._construire_ui()
        self.bouton_lancer.clicked.connect(self._on_bouton_clique)
        self.bouton_raz.clicked.connect(self._reinitialiser_filtres)
        self.bouton_sauvegarder.clicked.connect(self._sauvegarder_comme_profil)
        self.bouton_exporter.clicked.connect(self._exporter_html)
        self.bouton_suivre.clicked.connect(self._suivre_candidature)
        self.bouton_voir_detail.clicked.connect(self._voir_detail_offre)
        self.case_nouvelles_seulement.toggled.connect(
            self._on_toggle_nouvelles_seulement
        )
        self.champ_filtre_resultats.textChanged.connect(
            self._proxy_offres.setFilterFixedString
        )
        self.table_resultats.doubleClicked.connect(self._ouvrir_offre)
        self.table_resultats.selectionModel().selectionChanged.connect(
            self._maj_boutons_selection
        )
        # Un reset du modèle vide la sélection sans émettre selectionChanged.
        self._proxy_offres.modelReset.connect(self._maj_boutons_selection)

    # --- Construction ---

    def _construire_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        panneau_filtres = self._construire_panneau_filtres()
        # Garde-fou : jamais écrasé au redimensionnement. 280 (pas 260) car
        # le cadre + la barre de défilement verticale du QScrollArea
        # mangent ~12px de la largeur allouée (vérifié empiriquement).
        panneau_filtres.setMinimumWidth(280)
        splitter.addWidget(panneau_filtres)
        splitter.addWidget(self._construire_panneau_resultats())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)

        disposition = QVBoxLayout(self)
        disposition.addWidget(splitter)

    def _versants_existants_compat(self) -> list[str]:
        """Résout la sélection de versants initiale, avec compatibilité
        pour les profils sauvegardés au format singulier historique
        (``"versant": "etat"|"hospitalier"|"territorial"|"__tous__"``,
        avant le passage à des cases à cocher multi-sélection)."""
        versants = self._filtres_existants.get("versants")
        if versants is not None:
            return list(versants)
        # "versant" (singulier) : champ hérité d'anciens profils, plus dans FiltresRecherche.
        ancien = cast(dict, self._filtres_existants).get("versant")
        if ancien is None or ancien == "etat":
            return ["etat"]
        if ancien == "__tous__":
            return []
        return [ancien]

    def _construire_panneau_filtres(self) -> QWidget:
        contenu = QWidget()
        disposition = QVBoxLayout(contenu)

        categories_existantes = self._filtres_existants.get("categories") or []

        # Titres de section fixes plutôt que des sections repliables :
        # tout reste visible, plus besoin de plier/déplier.
        disposition.addWidget(_titre_section("Catégorie"))

        def _ajouter_ligne(choix: list[tuple[str, str]]) -> None:
            ligne = QHBoxLayout()
            ligne.setSpacing(16)
            for label, valeur in choix:
                case = CaseACocher(label)
                case.setChecked(valeur in categories_existantes)
                self._categories_cases.append((case, valeur))
                ligne.addWidget(case)
            ligne.addStretch()
            disposition.addLayout(ligne)

        # A+ : description nécessaire (distinction pas évidente entre
        # direction et autres emplois fonctionnels), sur une ligne.
        _ajouter_ligne(_CATEGORIES_SUPERIEURES)
        # A / B / C : pas de descriptif (connu de tous), sur une ligne.
        _ajouter_ligne(_CATEGORIES_SIMPLES)

        # Rattaché à Catégorie (pas à Versant) : c'est un sous-filtre de la
        # catégorie A, sans lien avec le versant.
        self.bouton_grades = _bouton_selection()
        self.bouton_grades.clicked.connect(self._ouvrir_selection_grades)
        disposition.addLayout(_ligne_solo(self.bouton_grades))
        disposition.addSpacing(12)

        disposition.addWidget(_titre_section("Versant"))
        ligne_versants = QHBoxLayout()
        ligne_versants.setSpacing(16)
        versants_existants = self._versants_existants_compat()
        for cle, abrege, nom_complet in _VERSANTS_CHOIX:
            case = CaseACocher(abrege)
            case.setToolTip(nom_complet)
            case.setChecked(cle in versants_existants)
            self._versants_cases.append((case, cle))
            ligne_versants.addWidget(case)
        ligne_versants.addStretch()
        disposition.addLayout(ligne_versants)
        disposition.addSpacing(12)

        disposition.addWidget(_titre_section("Poste"))

        # Bouton résumé + dialogue modal (recherche) plutôt que liste embarquée :
        # jusqu'à ~2400 sous-organisations côté Organisation(s), inutilisable en
        # défilement imbriqué — même motif appliqué par cohérence ici.
        self.bouton_domaines = _bouton_selection()
        self.bouton_domaines.clicked.connect(self._ouvrir_selection_domaines)
        disposition.addLayout(_ligne_solo(self.bouton_domaines))

        types_poste_existant = self._filtres_existants.get("types_poste")
        self._type_poste_combo = QComboBox()
        # Largeur bornée plutôt qu'ajustée au libellé le plus long (66
        # caractères) : sinon ce combo impose sa largeur à tout le panneau.
        # Qt affiche « … » nativement pour le texte tronqué.
        self._type_poste_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self._type_poste_combo.setMinimumContentsLength(22)
        for label, valeur_poste in _TYPES_POSTE_CHOIX:
            self._type_poste_combo.addItem(label)
            if valeur_poste == types_poste_existant:
                self._type_poste_combo.setCurrentIndex(
                    self._type_poste_combo.count() - 1
                )
        self._type_poste_combo.currentTextChanged.connect(
            self._type_poste_combo.setToolTip
        )
        self._type_poste_combo.setToolTip(self._type_poste_combo.currentText())
        disposition.addWidget(QLabel("Type de poste"))
        disposition.addWidget(self._type_poste_combo)

        experience_existante = self._filtres_existants.get("experience") or _INDIFFERENT
        self._experience_combo = QComboBox()
        self._experience_combo.addItems([_INDIFFERENT, *EXPERIENCES])
        self._experience_combo.setCurrentText(experience_existante)
        disposition.addWidget(QLabel("Expérience souhaitée"))
        disposition.addWidget(self._experience_combo)

        date_pub_existante = (
            self._filtres_existants.get("date_publication") or _INDIFFERENT
        )
        self._date_pub_combo = QComboBox()
        self._date_pub_combo.addItems([_INDIFFERENT, *DATES_PUBLICATION])
        self._date_pub_combo.setCurrentText(date_pub_existante)
        disposition.addWidget(QLabel("Date de publication"))
        disposition.addWidget(self._date_pub_combo)
        disposition.addSpacing(12)

        disposition.addWidget(_titre_section("Lieu & Organisation"))

        self.bouton_localisations = _bouton_selection()
        self.bouton_localisations.clicked.connect(self._ouvrir_selection_localisations)

        self.bouton_organisations = _bouton_selection()
        self.bouton_organisations.clicked.connect(self._ouvrir_selection_organisations)

        disposition.addWidget(
            LigneResponsive(self.bouton_localisations, self.bouton_organisations)
        )
        disposition.addSpacing(12)

        self._maj_libelles_selection()

        disposition.addWidget(_titre_section("Options"))

        self._management_case = CaseACocher("Management")
        self._management_case.setChecked(
            bool(self._filtres_existants.get("management"))
        )
        self._teletravail_case = CaseACocher("Télétravail")
        self._teletravail_case.setChecked(
            bool(self._filtres_existants.get("teletravail"))
        )
        ligne_options = QHBoxLayout()
        ligne_options.setSpacing(16)
        ligne_options.addWidget(self._management_case)
        ligne_options.addWidget(self._teletravail_case)
        ligne_options.addStretch()
        disposition.addLayout(ligne_options)

        self._grades_superieurs_case = CaseACocher(
            "Afficher aussi les grades supérieurs"
        )
        disposition.addWidget(self._grades_superieurs_case)

        self._mot_cle_champ = QLineEdit(self._filtres_existants.get("query", ""))
        self._mot_cle_champ.setPlaceholderText("Mot-clé libre (ex: IDIV)")
        disposition.addWidget(QLabel("Mot-clé libre"))
        disposition.addWidget(self._mot_cle_champ)

        ligne_actions = QHBoxLayout()
        self.bouton_lancer = QPushButton(
            "Enregistrer les modifications"
            if self.mode_edition
            else "Lancer la recherche"
        )
        self.bouton_lancer.setProperty("variant", "primaire")
        ligne_actions.addWidget(self.bouton_lancer, 1)

        self.bouton_raz = QPushButton("RAZ")
        self.bouton_raz.setToolTip("Réinitialise tous les filtres de cet écran")
        ligne_actions.addWidget(self.bouton_raz)
        disposition.addLayout(ligne_actions)

        self.bouton_sauvegarder = QPushButton("Sauvegarder comme profil")
        self.bouton_sauvegarder.setVisible(
            not self.mode_edition and self.nom_profil is None
        )
        disposition.addWidget(self.bouton_sauvegarder)

        disposition.addStretch()

        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        defilement.setWidget(contenu)
        return defilement

    def _maj_libelles_selection(self) -> None:
        self.bouton_domaines.setText(
            _libelle_selection("Domaine(s)", self._domaines_selection)
        )
        self.bouton_localisations.setText(
            _libelle_selection("Localisation(s)", self._localisations_selection)
        )
        self.bouton_organisations.setText(
            _libelle_selection("Organisation(s)", self._organisations_selection)
        )
        self.bouton_grades.setText(
            _libelle_selection("Corps / Grade", self._grades_selection)
        )

    def _ouvrir_selection_grades(self) -> None:
        corps_grades = {corps: list(grades) for corps, grades in CORPS_GRADES.items()}
        dialogue = DialogueSelectionGrades(corps_grades, self._grades_selection, self)
        if dialogue.exec() == QDialog.DialogCode.Accepted:
            self._grades_selection = dialogue.selection()
            self._maj_libelles_selection()

    def _ouvrir_selection_domaines(self) -> None:
        dialogue = DialogueSelectionListe(
            "Domaine(s) métier", sorted(DOMAINES), self._domaines_selection, self
        )
        if dialogue.exec() == QDialog.DialogCode.Accepted:
            self._domaines_selection = dialogue.selection()
            self._maj_libelles_selection()

    def _ouvrir_selection_localisations(self) -> None:
        dialogue = DialogueSelectionListe(
            "Localisation(s)",
            sorted(LOCALISATIONS),
            self._localisations_selection,
            self,
        )
        if dialogue.exec() == QDialog.DialogCode.Accepted:
            self._localisations_selection = dialogue.selection()
            self._maj_libelles_selection()

    def _ouvrir_selection_organisations(self) -> None:
        dialogue = DialogueSelectionOrganisations(
            self._orgas_cache, self._organisations_selection, self
        )
        if dialogue.exec() == QDialog.DialogCode.Accepted:
            self._organisations_selection = dialogue.selection()
            self._maj_libelles_selection()

    def _construire_panneau_resultats(self) -> QWidget:
        panneau = QWidget()
        disposition = QVBoxLayout(panneau)
        self.label_entete = QLabel("Aucune recherche lancée.")
        self.label_entete.setProperty("role", "sousTexte")
        self.label_entete.setWordWrap(True)
        disposition.addWidget(self.label_entete)

        self.barre_progression = QProgressBar()
        self.barre_progression.setTextVisible(False)
        self.barre_progression.setVisible(False)
        disposition.addWidget(self.barre_progression)

        self.case_nouvelles_seulement = CaseACocher(
            "Afficher les nouvelles offres seulement"
        )
        self.case_nouvelles_seulement.setVisible(False)
        disposition.addWidget(self.case_nouvelles_seulement)

        self.champ_filtre_resultats = QLineEdit()
        self.champ_filtre_resultats.setPlaceholderText("Filtrer les résultats…")
        self.champ_filtre_resultats.setClearButtonEnabled(True)
        self.champ_filtre_resultats.setToolTip(
            "Filtre les offres affichées sur toutes les colonnes, sans relancer "
            "de recherche"
        )
        disposition.addWidget(self.champ_filtre_resultats)

        self.table_resultats = QTableView()
        self.table_resultats.setModel(self._proxy_offres)
        entete = self.table_resultats.horizontalHeader()
        # Aucune colonne triée au départ : l'ordre d'origine des sources
        # est conservé tant que l'utilisateur ne clique pas un en-tête.
        entete.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.table_resultats.setSortingEnabled(True)
        # Titre étiré (colonne la plus lue), date et source compactes.
        entete.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        entete.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        entete.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table_resultats.setColumnWidth(3, 96)
        self.table_resultats.setColumnWidth(4, 130)
        self.table_resultats.setWordWrap(True)
        self.table_resultats.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_resultats.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table_resultats.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_resultats.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        disposition.addWidget(self.table_resultats)

        ligne_actions_resultats = QHBoxLayout()
        self.bouton_voir_detail = QPushButton("Voir le détail")
        self.bouton_voir_detail.setToolTip(
            "Affiche la fiche complète de l'offre sélectionnée dans l'app "
            "(un seul GET, à la demande)"
        )
        self.bouton_voir_detail.setEnabled(False)
        ligne_actions_resultats.addWidget(self.bouton_voir_detail)

        self.bouton_suivre = QPushButton("Suivre cette offre")
        self.bouton_suivre.setToolTip(
            "Démarre le suivi de candidature pour l'offre sélectionnée"
        )
        self.bouton_suivre.setEnabled(False)
        ligne_actions_resultats.addWidget(self.bouton_suivre)
        disposition.addLayout(ligne_actions_resultats)

        self.bouton_exporter = QPushButton("Exporter en HTML")
        self.bouton_exporter.setEnabled(False)
        disposition.addWidget(self.bouton_exporter)

        return panneau

    # --- Lecture de l'état des filtres ---

    def construire_filtres(self) -> FiltresRecherche:
        """Lit l'état actuel des widgets et retourne les filtres correspondants."""
        type_poste_valeur = _TYPES_POSTE_CHOIX[self._type_poste_combo.currentIndex()][1]
        experience = self._experience_combo.currentText()
        date_publication = self._date_pub_combo.currentText()

        return {
            "categories": [
                valeur for case, valeur in self._categories_cases if case.isChecked()
            ],
            "domaines": list(self._domaines_selection),
            "localisations": list(self._localisations_selection),
            "organisations": list(self._organisations_selection),
            "grades": list(self._grades_selection),
            "versants": [cle for case, cle in self._versants_cases if case.isChecked()],
            "types_poste": type_poste_valeur,
            "experience": "" if experience == _INDIFFERENT else experience,
            "date_publication": (
                "" if date_publication == _INDIFFERENT else date_publication
            ),
            "management": self._management_case.isChecked(),
            "teletravail": self._teletravail_case.isChecked(),
            "query": self._mot_cle_champ.text().strip(),
        }

    def afficher_grades_superieurs(self) -> bool:
        """État de la case « Afficher aussi les grades supérieurs »."""
        return self._grades_superieurs_case.isChecked()

    def _reinitialiser_filtres(self) -> None:
        """Remet chaque filtre à son état par défaut, sans changer d'écran
        ni relancer de recherche (bouton RAZ)."""
        for case, _ in self._categories_cases:
            case.setChecked(False)
        self._domaines_selection = []
        self._localisations_selection = []
        self._organisations_selection = []
        self._grades_selection = []
        self._maj_libelles_selection()
        # Versant : retour au défaut FPE seul (comportement de l'ancien combo).
        for case, cle in self._versants_cases:
            case.setChecked(cle == "etat")
        self._type_poste_combo.setCurrentIndex(0)
        self._experience_combo.setCurrentText(_INDIFFERENT)
        self._date_pub_combo.setCurrentText(_INDIFFERENT)
        self._management_case.setChecked(False)
        self._teletravail_case.setChecked(False)
        self._grades_superieurs_case.setChecked(False)
        self._mot_cle_champ.clear()

    # --- Recherche / enregistrement ---

    def lancer_recherche_immediatement(self) -> None:
        """Lance la recherche dès l'ouverture de l'écran (ex. depuis le
        bouton « Lancer » d'un profil sauvegardé sur l'Accueil), sans
        attendre un clic sur le bouton — la recherche est déjà entièrement
        paramétrée à ce stade, faire recliquer serait une friction inutile.
        """
        self._lancer_recherche()

    def _on_bouton_clique(self) -> None:
        if self.mode_edition:
            self._enregistrer_modifications()
        else:
            self._lancer_recherche()

    def _enregistrer_modifications(self) -> None:
        assert self.nom_profil is not None  # garanti par le mode édition
        modifier_profil(self.nom_profil, self.construire_filtres())
        self.demande_retour.emit()

    def _lancer_recherche(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return  # recherche déjà en cours, pas de double lancement

        filtres = self.construire_filtres()
        self._afficher_tout = self.afficher_grades_superieurs()
        self._grades_filtrage = filtres.get("grades") or []
        self.bouton_lancer.setEnabled(False)
        self.bouton_lancer.setText("Recherche en cours…")
        self._definir_statut_recherche("Recherche en cours…")
        # Mode indéterminé : le nombre de pages n'est connu qu'après le 1er appel.
        self.barre_progression.setRange(0, 0)
        self.barre_progression.setVisible(True)

        self._pages_par_source = {}
        self._nb_sources_lancees = 0
        self._nb_sources_terminees = 0
        self._avertissements = []

        self._thread = QThread()
        self._travailleur = TravailleurRecherche(filtres, self._orgas_cache)
        self._travailleur.moveToThread(self._thread)
        self._thread.started.connect(self._travailleur.executer)
        self._travailleur.progression.connect(self._on_progression)
        self._travailleur.resultat.connect(self._on_resultat)
        self._travailleur.erreur.connect(self._on_erreur)
        self._travailleur.avertissement.connect(self._on_avertissement)
        self._travailleur.source_en_cours.connect(self._on_source_en_cours)
        self._travailleur.source_terminee.connect(self._on_source_terminee)
        self._travailleur.resultat.connect(self._thread.quit)
        self._travailleur.erreur.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_termine)
        self._thread.start()

    def _on_source_en_cours(self, _nom: str) -> None:
        self._nb_sources_lancees += 1
        self._maj_statut_progression()

    def _on_source_terminee(self, _nom: str) -> None:
        self._nb_sources_terminees += 1
        self._maj_statut_progression()

    def _on_avertissement(self, message: str) -> None:
        self._avertissements.append(message)

    def _on_progression(self, nom: str, page: int, total: int) -> None:
        self._pages_par_source[nom] = (page, total)
        self._maj_statut_progression()

    def _maj_statut_progression(self) -> None:
        """Statut agrégé des sources interrogées en parallèle : pages
        chargées sur pages annoncées (toutes sources confondues) et
        nombre de sources terminées."""
        pages = sum(page for page, _ in self._pages_par_source.values())
        total = sum(total for _, total in self._pages_par_source.values())
        morceaux = []
        if total > 1:
            morceaux.append(f"page {pages}/{total}")
            self.bouton_lancer.setText(f"Page {pages}/{total}…")
            # Nombre de pages connu : bascule en mode déterminé.
            self.barre_progression.setRange(0, total)
            self.barre_progression.setValue(pages)
        if self._nb_sources_lancees > 1:
            morceaux.append(
                f"{self._nb_sources_terminees}/{self._nb_sources_lancees} "
                "sources terminées"
            )
        suffixe = f" {' · '.join(morceaux)}" if morceaux else ""
        self._definir_statut_recherche(f"Recherche en cours…{suffixe}")

    def _definir_statut_recherche(self, texte: str) -> None:
        """Affiche un texte de statut bien visible (accent, gras) pendant
        une recherche — un `role="sousTexte"` discret passait inaperçu,
        d'où l'impression de blocage sans indice visuel signalée par
        l'utilisateur."""
        self.label_entete.setProperty("role", "statut")
        self.label_entete.setText(texte)
        self.label_entete.style().unpolish(self.label_entete)
        self.label_entete.style().polish(self.label_entete)

    def _reinitialiser_role_entete(self) -> None:
        self.label_entete.setProperty("role", "sousTexte")
        self.label_entete.style().unpolish(self.label_entete)
        self.label_entete.style().polish(self.label_entete)

    def _on_resultat(
        self, offres: list[Offre], nb_pages: int, arret_anticipe: bool
    ) -> None:
        if self._afficher_tout:
            offres_filtrees, nb_exclus = offres, 0
        else:
            offres_filtrees, nb_exclus = filtrer_grades_superieurs(offres)
        offres_filtrees = filtrer_par_grades(offres_filtrees, self._grades_filtrage)

        self._offres_affichees = offres_filtrees
        self._dernier_nb_pages = nb_pages

        # Badge nouvelles offres : seulement pour un profil sauvegardé, pas en édition.
        if self.nom_profil and not self.mode_edition:
            self._nouvelles = maj_cache_offres(self.nom_profil, offres_filtrees)
            mettre_a_jour_stats(self.nom_profil, len(self._nouvelles))
        else:
            self._nouvelles = set()

        # N'a de sens que s'il reste des offres à exclure.
        peut_filtrer_nouvelles = bool(self._nouvelles) and len(self._nouvelles) < len(
            offres_filtrees
        )
        self.case_nouvelles_seulement.blockSignals(True)
        self.case_nouvelles_seulement.setVisible(peut_filtrer_nouvelles)
        self.case_nouvelles_seulement.setChecked(False)
        self.case_nouvelles_seulement.blockSignals(False)

        self._peupler_table(offres_filtrees)
        self.bouton_exporter.setEnabled(bool(offres_filtrees))

        resume = resumer_filtres(self.construire_filtres())
        lignes = [
            f"Filtres : {resume}",
            f"{len(offres_filtrees)} offre(s)"
            + (f" · {nb_pages} page(s)" if nb_pages > 1 else ""),
        ]
        if self._nouvelles:
            lignes.append(
                f"{len(self._nouvelles)} nouvelle(s) offre(s) depuis la dernière recherche"
            )
        if nb_exclus:
            lignes.append(f"{nb_exclus} offre(s) IDiv/IP exclue(s) (filtre de titre)")
        if arret_anticipe:
            lignes.append(f"Arrêt à la page {nb_pages} (page vide)")
        elif nb_pages > MAX_PAGES:
            lignes.append(
                f"{nb_pages} pages au total — seules les {MAX_PAGES} premières chargées."
            )
        if not offres_filtrees:
            lignes.append("Aucune offre trouvée.")
        lignes.extend(self._avertissements)
        self.barre_progression.setVisible(False)
        self._reinitialiser_role_entete()
        self.label_entete.setText("\n".join(lignes))

        self.bouton_lancer.setEnabled(True)
        self.bouton_lancer.setText("Lancer la recherche")

    def _on_erreur(self, message: str) -> None:
        self.barre_progression.setVisible(False)
        self._reinitialiser_role_entete()
        self.label_entete.setText(f"Erreur : {message}")
        self.bouton_lancer.setEnabled(True)
        self.bouton_lancer.setText("Lancer la recherche")

    def _on_thread_termine(self) -> None:
        self._thread = None
        self._travailleur = None

    def arreter_recherche_en_cours(self) -> None:
        """Arrête proprement une recherche en cours, si besoin.

        À appeler avant que cette vue soit détruite (navigation vers un
        autre écran, fermeture) — Qt plante si un `QThread` est détruit
        pendant qu'il tourne encore (vérifié en pratique : abandon
        natif avec `QThread::~QThread` dans la pile d'appel).

        Bloque le thread principal jusqu'à la fin des sources en cours
        d'interrogation (en parallèle) — borné par le timeout HTTP
        (30 s, `api.py`) de la requête en cours de chaque source. Rare en
        pratique (il faut naviguer ailleurs pendant qu'une recherche
        tourne) ; accepté comme compromis plutôt que de laisser un
        thread orphelin continuer en arrière-plan sur une vue détruite.
        """
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

    def _on_toggle_nouvelles_seulement(self, coche: bool) -> None:
        """Filtre le tableau sur les seules offres nouvelles, sans relancer
        de recherche — équivalent du choix « Afficher nouvelles seulement »
        du CLI historique (`_construire_choices_navigation`)."""
        self._proxy_offres.definir_nouvelles_seulement(coche)
        self.table_resultats.resizeRowsToContents()

    def _peupler_table(self, offres: list[Offre]) -> None:
        self._proxy_offres.definir_nouvelles_seulement(False)
        self._modele_offres.definir_offres(offres, self._nouvelles)
        self.table_resultats.resizeRowsToContents()

    @property
    def _offres_visibles(self) -> list[Offre]:
        """Offres affichées dans l'ordre courant du tableau (tri, filtre
        texte et « nouvelles seulement » compris)."""
        return self._proxy_offres.offres_visibles()

    def _offre_selectionnee(self) -> Offre | None:
        lignes = self.table_resultats.selectionModel().selectedRows()
        if not lignes:
            return None
        return lignes[0].data(ROLE_OFFRE)

    def _ouvrir_offre(self, index: QModelIndex) -> None:
        offre = index.data(ROLE_OFFRE) if index.isValid() else None
        if offre is not None and offre["url"].startswith("https://"):
            webbrowser.open(offre["url"])

    def _maj_boutons_selection(self) -> None:
        selection = self.table_resultats.selectionModel().hasSelection()
        self.bouton_suivre.setEnabled(selection)
        self.bouton_voir_detail.setEnabled(selection)

    def _voir_detail_offre(self) -> None:
        offre = self._offre_selectionnee()
        if offre is None:
            return

        # GET synchrone ponctuel, pas besoin d'un QThread dédié.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            detail = recuperer_detail_offre(offre["url"])
        finally:
            QApplication.restoreOverrideCursor()

        dialogue = DialogueDetailOffre(
            offre["titre"],
            offre["employeur"],
            detail,
            offre["url"],
            offre["reference"],
            self,
        )
        dialogue.exec()

    def _suivre_candidature(self) -> None:
        offre = self._offre_selectionnee()
        if offre is None:
            return

        # GET synchrone ponctuel, même compromis que le rafraîchissement du cache.
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            detail = recuperer_detail_offre(offre["url"])
            generer_archive_pdf(offre["reference"], detail["page_html"])
        finally:
            QApplication.restoreOverrideCursor()

        ajouter_candidature(
            offre["reference"],
            offre["titre"],
            offre["employeur"],
            offre["url"],
            offre_domaine=offre["domaine"],
            offre_localisation=offre["localisation"],
            offre_versant=offre["versant"],
            offre_date=offre["date"],
            detail=detail,
        )
        QMessageBox.information(
            self, "Candidature suivie", f"« {offre['titre']} » ajoutée au suivi."
        )

    def _sauvegarder_comme_profil(self) -> None:
        nom, ok = QInputDialog.getText(
            self, "Sauvegarder comme profil", "Nom du profil (ex: dgal-paris) :"
        )
        if not ok or not nom.strip():
            return
        nom = nom.strip()
        label, _ = QInputDialog.getText(
            self, "Sauvegarder comme profil", "Description courte :", text=nom
        )
        filtres = self.construire_filtres()
        ajouter_profil(nom, cast(Profil, {**filtres, "label": label or nom}))

    def _exporter_html(self) -> None:
        resume = resumer_filtres(self.construire_filtres())
        if self.case_nouvelles_seulement.isChecked():
            resume += " — nouvelles seulement"
        chemin = exporter_html(
            self._offres_visibles, resume, self._dernier_nb_pages, self.nom_profil
        )
        if question_oui_non(
            self,
            "Export généré",
            f"Export généré : {chemin}\n\nOuvrir dans le navigateur ?",
        ):
            ouvrir_dans_navigateur(chemin)
