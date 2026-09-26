"""Écran d'aide : vocabulaire et fonctionnement, accessible depuis le bandeau.

Widgets natifs (`QGroupBox` + `QLabel`, même langage visuel que le
reste de l'app — panneaux « Autres filtres » de l'écran Recherche,
tuiles de l'Accueil/Suivi) plutôt qu'un bloc HTML brut dans un
`QTextBrowser`, qui rendait avec les puces/polices par défaut du moteur
rich-text de Qt, sans rapport avec l'identité visuelle de l'app.
"""

from PySide6.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget


def _texte(contenu: str) -> QLabel:
    label = QLabel(contenu)
    label.setProperty("role", "sousTexte")
    label.setWordWrap(True)
    return label


def _entree(disposition: QVBoxLayout, terme: str, description: str) -> None:
    """Une entrée terme + description, même paire de rôles que les
    tuiles de profil/candidature (`role="nom"` + `role="sousTexte"`)."""
    label_terme = QLabel(terme)
    label_terme.setProperty("role", "nom")
    disposition.addWidget(label_terme)
    disposition.addWidget(_texte(description))


class VueAide(QWidget):
    """Écran d'aide statique — vocabulaire et fonctionnement de l'app.

    Pas de bouton retour propre : couvert par le bandeau de navigation
    persistant de `FenetrePrincipale` (« Accueil »).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(28, 24, 28, 24)
        disposition.setSpacing(16)

        titre = QLabel("Aide")
        titre.setProperty("role", "titre")
        disposition.addWidget(titre)

        contenu = QWidget()
        pile = QVBoxLayout(contenu)
        pile.setSpacing(16)
        pile.addWidget(self._section_filtres())
        pile.addWidget(self._section_exemples())
        pile.addWidget(self._section_grades_superieurs())
        pile.addWidget(self._section_profils())
        pile.addWidget(self._section_suivi())
        pile.addStretch()

        defilement = QScrollArea()
        defilement.setWidgetResizable(True)
        defilement.setWidget(contenu)
        disposition.addWidget(defilement, 1)

    @staticmethod
    def _section_filtres() -> QGroupBox:
        groupe = QGroupBox("Les filtres")
        disposition = QVBoxLayout(groupe)
        disposition.setSpacing(10)
        _entree(
            disposition,
            "Catégorie",
            "Niveau hiérarchique du poste : A+ (encadrement supérieur), A "
            "(cadre), B (profession intermédiaire), C (employé).",
        )
        _entree(
            disposition,
            "Versant",
            "La branche de la fonction publique : État (FPE), Hospitalière "
            "(FPH), Territoriale (FPT) — plusieurs cases à la fois "
            "possibles, aucune cochée = tous les versants.",
        )
        _entree(
            disposition,
            "Domaine(s) / Localisation(s) / Organisation(s)",
            "Un bouton résumé ouvre une fenêtre de sélection avec un champ "
            "de recherche — pratique vu le nombre d'options (114 "
            "localisations, ~2400 sous-organisations).",
        )
        _entree(
            disposition,
            "Type de poste",
            "Par défaut, l'app ne montre que les postes ouverts aux "
            "titulaires (titulaires + postes ouverts aux deux statuts). "
            "Choisir « Tous » pour voir aussi les postes réservés aux "
            "contractuels.",
        )
        _entree(
            disposition,
            "Management / Télétravail",
            "Cases à cocher, cochées = ne montrer que les postes concernés.",
        )
        _entree(
            disposition,
            "Mot-clé libre",
            "Recherche dans le titre et le corps de l'offre, pas seulement "
            "l'intitulé.",
        )
        return groupe

    @staticmethod
    def _section_exemples() -> QGroupBox:
        groupe = QGroupBox("Exemples de recherche")
        disposition = QVBoxLayout(groupe)
        disposition.setSpacing(10)
        _entree(
            disposition,
            "Attaché principal territorial (Hérault)",
            "Catégorie → A\n"
            "Grade → Attaché principal\n"
            "Versant → Territoriale\n"
            "Lieu & Organisation → Localisation Hérault\n\n"
            "Le filtre Grade repère « attaché principal » dans le titre, "
            "quel que soit le versant — pas besoin de le recocher si la "
            "recherche est élargie à l'État ou l'Hospitalière.",
        )
        _entree(
            disposition,
            "Chef de projet informatique (DGFiP → fonction publique d'État)",
            "Catégorie → A\n"
            "Versant → État\n"
            "Poste → Domaine « Numérique »\n"
            "Options → mot-clé libre « chef de projet »\n\n"
            "Pas de grade statutaire dédié pour ce métier (contrairement à "
            "« attaché ») — le mot-clé resserre sur l'intitulé du poste.",
        )
        return groupe

    @staticmethod
    def _section_grades_superieurs() -> QGroupBox:
        groupe = QGroupBox("Grades supérieurs (IDIV / IP / AFIPA)")
        disposition = QVBoxLayout(groupe)
        disposition.setSpacing(10)
        disposition.addWidget(
            _texte(
                "Par défaut, l'app masque les offres dont le titre commence "
                "par un grade d'encadrement supérieur de la DGFiP (IDIV, "
                "AFIPA, IP suivi d'une majuscule — ex. IPFiP) : ce sont en "
                "général des postes très spécifiques, peu pertinents pour "
                "une recherche large."
            )
        )
        disposition.addWidget(
            _texte(
                "Pour les voir quand même, active « Afficher aussi les "
                "grades supérieurs » dans l'écran Recherche."
            )
        )
        return groupe

    @staticmethod
    def _section_profils() -> QGroupBox:
        groupe = QGroupBox("Les profils")
        disposition = QVBoxLayout(groupe)
        disposition.setSpacing(10)
        disposition.addWidget(
            _texte(
                "Un profil, c'est une recherche sauvegardée avec un nom. "
                "Sur l'Accueil, double-clique sur un profil (ou son bouton "
                "« Lancer ») pour lancer sa recherche immédiatement — les "
                "autres actions sont aussi des boutons directs sur la "
                "tuile :"
            )
        )
        _entree(disposition, "Lancer", "Lance la recherche immédiatement.")
        _entree(
            disposition,
            "Modifier",
            "Change les filtres du profil sans lancer de recherche.",
        )
        _entree(disposition, "Dupliquer", "Copie le profil sous un nouveau nom.")
        _entree(disposition, "Supprimer", "Supprime le profil (confirmation demandée).")
        return groupe

    @staticmethod
    def _section_suivi() -> QGroupBox:
        groupe = QGroupBox("Suivi de candidature")
        disposition = QVBoxLayout(groupe)
        disposition.setSpacing(10)
        disposition.addWidget(
            _texte(
                "Depuis l'écran Recherche, sélectionne une offre puis "
                "« Suivre cette offre » pour démarrer son suivi. Le statut "
                "affiché est toujours celui du dernier événement ajouté "
                "(candidature envoyée, accusé de réception, entretien, "
                "réponse...), jamais un champ à part qu'on pourrait perdre."
            )
        )
        _entree(
            disposition,
            "Relance suggérée",
            "Badge affiché si aucun événement depuis 3 semaines et que la "
            "candidature n'est pas déjà close (réponse positive ou refus).",
        )
        _entree(
            disposition,
            "Offre dépubliée",
            "Badge affiché quand l'offre a disparu du site — vérifiable "
            "avec le bouton « Vérifier les offres » de cet écran. "
            "L'essentiel de la fiche de poste reste consultable même "
            "après dépublication.",
        )
        _entree(
            disposition,
            "Clavier",
            "Entrée (ou double-clic) ouvre le détail de la candidature "
            "sélectionnée, Suppr arrête son suivi ; clic droit pour toutes "
            "les actions.",
        )
        return groupe
