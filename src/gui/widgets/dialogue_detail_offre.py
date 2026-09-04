"""Dialogue d'affichage du détail complet d'une offre (fiche de poste).

Réutilisé par l'écran Recherche (détail récupéré à la demande via
`recuperer_detail_offre`) et par l'écran Suivi (détail déjà archivé
dans la `Candidature` au moment du suivi — fonctionne même si l'offre
a depuis été dépubliée).
"""

import webbrowser

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.candidatures import chemin_archive_pdf
from src.types import DetailOffre


def _texte(contenu: str) -> QLabel:
    label = QLabel(contenu)
    label.setProperty("role", "sousTexte")
    label.setWordWrap(True)
    return label


def _ajouter_section(pile: QVBoxLayout, titre: str, contenu: str) -> None:
    groupe = QGroupBox(titre)
    disposition = QVBoxLayout(groupe)
    disposition.addWidget(_texte(contenu))
    pile.addWidget(groupe)


class DialogueDetailOffre(QDialog):
    """Modale affichant le détail structuré d'une offre — description,
    informations pratiques, présentation de l'employeur, sections
    complémentaires (dont la personne à contacter, quand indiquée)."""

    def __init__(
        self,
        titre_offre: str,
        employeur: str,
        detail: DetailOffre,
        url: str = "",
        reference: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(titre_offre)
        self.resize(560, 640)
        disposition = QVBoxLayout(self)

        entete = QLabel(titre_offre)
        entete.setProperty("role", "titre")
        entete.setWordWrap(True)
        disposition.addWidget(entete)

        sous_entete = QLabel(employeur)
        sous_entete.setProperty("role", "sousTexte")
        disposition.addWidget(sous_entete)

        ligne_actions = QHBoxLayout()
        lien_postuler = detail.get("lien_postuler", "")
        self.bouton_postuler = QPushButton("Postuler")
        self.bouton_postuler.setEnabled(lien_postuler.startswith("https://"))
        self.bouton_postuler.clicked.connect(lambda: webbrowser.open(lien_postuler))
        ligne_actions.addWidget(self.bouton_postuler)

        self.bouton_en_ligne = QPushButton("Consulter en ligne")
        self.bouton_en_ligne.setEnabled(url.startswith("https://"))
        self.bouton_en_ligne.clicked.connect(lambda: webbrowser.open(url))
        ligne_actions.addWidget(self.bouton_en_ligne)

        self.bouton_archive = QPushButton("Voir la copie archivée")
        chemin_pdf = chemin_archive_pdf(reference) if reference else None
        archive_disponible = chemin_pdf is not None and chemin_pdf.exists()
        self.bouton_archive.setEnabled(archive_disponible)
        if archive_disponible and chemin_pdf is not None:
            uri_pdf = chemin_pdf.as_uri()
            self.bouton_archive.setToolTip(
                "PDF autonome de la fiche telle qu'elle était au moment "
                "du suivi (aucune ressource externe) — reste consultable "
                "même hors ligne ou si l'offre a depuis été dépubliée."
            )
            self.bouton_archive.clicked.connect(lambda: webbrowser.open(uri_pdf))
        else:
            self.bouton_archive.setToolTip(
                "Aucune archive : elle est générée automatiquement en "
                "cliquant sur « Suivre cette offre »."
            )
        ligne_actions.addWidget(self.bouton_archive)
        ligne_actions.addStretch()
        disposition.addLayout(ligne_actions)

        contenu = QWidget()
        pile = QVBoxLayout(contenu)
        pile.setSpacing(16)

        rien_a_montrer = True

        if detail.get("description"):
            _ajouter_section(pile, "Description du poste", detail["description"])
            rien_a_montrer = False

        infos = []
        if detail.get("salaire"):
            infos.append(f"Salaire : {detail['salaire']}")
        if detail.get("experience_requise"):
            infos.append(f"Expérience requise : {detail['experience_requise']}")
        if detail.get("formation_requise"):
            infos.append(f"Formation requise : {detail['formation_requise']}")
        if detail.get("secteur"):
            infos.append(f"Secteur : {detail['secteur']}")
        if detail.get("date_publication"):
            infos.append(f"Publiée le : {detail['date_publication']}")
        if detail.get("date_limite"):
            infos.append(f"Date limite de candidature : {detail['date_limite']}")
        if infos:
            _ajouter_section(pile, "Informations", "\n".join(infos))
            rien_a_montrer = False

        if detail.get("a_propos_employeur"):
            _ajouter_section(pile, "Qui sommes-nous ?", detail["a_propos_employeur"])
            rien_a_montrer = False

        for section_titre, section_contenu in (
            detail.get("sections_complementaires") or {}
        ).items():
            _ajouter_section(pile, section_titre, section_contenu)
            rien_a_montrer = False

        if rien_a_montrer:
            pile.addWidget(_texte("Aucun détail disponible pour cette offre."))

        pile.addStretch()
        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        defilement.setWidget(contenu)
        disposition.addWidget(defilement, 1)

        boutons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bouton_fermer = boutons.button(QDialogButtonBox.StandardButton.Close)
        if bouton_fermer is not None:
            bouton_fermer.setText("Fermer")
        boutons.rejected.connect(self.close)
        disposition.addWidget(boutons)
