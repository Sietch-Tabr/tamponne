"""Écran Recherche côté Python : demande de recherche (formulaire),
lancement en arrière-plan, registre des offres et actions sur une offre."""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

from PySide6.QtCore import (
    Property,
    QModelIndex,
    QObject,
    QThread,
    QUrl,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtQml import QJSValue

from src.donnees.candidatures import chemin_archive_pdf, suivre_offre
from src.donnees.profils import (
    ajouter_profil,
    categories_compatibles,
    charger_profils,
    modifier_profil,
    versants_compatibles,
)
from src.filtres import (
    CORPS_GRADES,
    DATES_PUBLICATION,
    DOMAINES,
    EXPERIENCES,
    LIBELLES_CATEGORIES,
    LOCALISATIONS,
    NUMEROS_DEPARTEMENTS,
    resumer_filtres,
)
from src.gui.modeles.offres import ProxyOffres
from src.gui.modeles.registre import ModeleRegistre
from src.gui.presentation import contenu_detail, libelle_selection, resume_registre
from src.gui.travailleurs import TacheReseau, TravailleurRecherche
from src.recherche.export import exporter_html
from src.recherche.orchestration import post_traiter_resultats
from src.sources.choisirleservicepublic import MAX_PAGES
from src.sources.detail import recuperer_detail_offre
from src.types import FiltresRecherche, Offre, Organisations, Profil

journal = logging.getLogger(__name__)

INDIFFERENTE = "Indifférente"


VERSANTS: list[tuple[str, str]] = [
    ("etat", "État"),
    ("hospitalier", "Hospitalier"),
    ("territorial", "Territorial"),
]

TYPES_POSTE: list[tuple[str, list[str] | str | None]] = [
    ("Titulaire-éligible (titulaires + postes ouverts aux deux statuts)", None),
    ("Titulaire uniquement", ["titulaire"]),
    ("Contractuel uniquement", ["contractuel"]),
    ("Tous (y compris contractuels)", "__tous__"),
]
"""(libellé, valeur de `FiltresRecherche.types_poste`)."""

LIBELLE_LANCER = "Lancer la recherche"
LIBELLE_MODIFIER = "Modifier la fiche"
MESSAGE_ORGANISATIONS_ABSENTES = (
    "La liste des organisations n'est pas encore chargée\u00a0: relancez la "
    "recherche dans un instant, ou rafraîchissez-la dans Réglages."
)


def _libelle_localisation(lieu: str) -> str:
    """« Paris (75) » pour un département : saisir le numéro le retrouve."""
    numero = NUMEROS_DEPARTEMENTS.get(lieu)
    return f"{lieu} ({numero})" if numero else lieu


LISTES_SELECTION = ("domaines", "localisations", "organisations", "grades")


def _etat_initial() -> dict[str, Any]:
    return {
        "categories": [],
        "versants": ["etat"],
        "domaines": [],
        "localisations": [],
        "organisations": [],
        "grades": [],
        "type_poste": 0,
        "experience": INDIFFERENTE,
        "date_publication": INDIFFERENTE,
        "management": False,
        "teletravail": False,
        "grades_superieurs": False,
        "mot_cle": "",
    }


class ControleurRecherche(QObject):
    """Actions et états de l'écran Recherche (objet `pont.recherche`)."""

    etat_change = Signal()
    """Formulaire, avancement ou registre modifié."""
    detail_pret = Signal(dict)
    """Fiche de poste d'une offre, à afficher (même format que le Suivi)."""
    suivi_termine = Signal(str)
    """Intitulé de l'offre ajoutée au suivi."""
    retour_profils = Signal()
    """Fiche modifiée enregistrée : retour à l'écran Profils."""
    action_echouee = Signal(str)
    """Message à afficher quand un appel réseau ponctuel échoue."""

    def __init__(
        self, orgas_cache: Organisations, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._orgas_cache = orgas_cache
        self._etat = _etat_initial()
        self._modele = ModeleRegistre(self)
        self._proxy = ProxyOffres(self)
        self._proxy.setSourceModel(self._modele)
        self._nom_profil: str | None = None
        self._filtres_fiche: FiltresRecherche | None = None
        # Fiche à laquelle la recherche affichée est rattachée (cache des
        # offres vues, nouvelles, export) : seulement si ses critères sont intacts.
        self._profil_lance: str | None = None
        self._filtres_lances: FiltresRecherche = {}
        self._edition = False
        self._phase = "vide"
        self._resume = ""
        self._erreur = ""
        self._avertissements: list[str] = []
        self._sources: dict[str, str] = {}
        self._pages: dict[str, tuple[int, int]] = {}
        self._pages_liste: dict[str, int] = {}
        self._nb_nouvelles = 0
        self._nb_pages = 1
        self._ligne_selectionnee = -1
        self._thread: QThread | None = None
        self._travailleur: TravailleurRecherche | None = None
        self._taches: list[tuple[QThread, TacheReseau]] = []
        self._suites: dict[int, Callable[[object], None]] = {}
        self._grades: list[str] = []
        self._grades_superieurs = False
        self._chargement_organisations = False

    # --- Propriétés exposées au QML ---

    def _lire_etat(self) -> dict[str, Any]:
        etat = dict(self._etat)
        for liste in LISTES_SELECTION:
            etat[f"libelle_{liste}"] = libelle_selection(self._etat[liste])
        return etat

    def _lire_modele(self) -> QObject:
        return self._proxy

    def _lire_phase(self) -> str:
        return self._phase

    def _lire_texte_bouton(self) -> str:
        if self._thread is not None:
            pages, total = self._totaux_pages()
            if total <= 1:
                return "Recherche en cours…"
            return f"{self._unite_progression().capitalize()} {pages}/{total}…"
        return LIBELLE_MODIFIER if self._edition else LIBELLE_LANCER

    def _lire_statut(self) -> str:
        pages, total = self._totaux_pages()
        suffixe = f" {self._unite_progression()} {pages}/{total}" if total > 1 else ""
        return f"Recherche en cours…{suffixe}"

    def _lire_avancement(self) -> list[dict[str, str]]:
        return [{"nom": nom, "etat": etat} for nom, etat in self._sources.items()]

    def _lire_resume(self) -> str:
        return self._resume

    def _lire_avertissements(self) -> str:
        return "\n".join(self._avertissements)

    def _lire_erreur(self) -> str:
        return self._erreur

    def _lire_etat_organisations(self) -> str:
        if self._orgas_cache:
            return ""
        return "chargement…" if self._chargement_organisations else "indisponible"

    def _lire_edition(self) -> bool:
        return self._edition

    def _lire_intitule_edition(self) -> str:
        if not self._edition or self._nom_profil is None:
            return ""
        profil = charger_profils().get(self._nom_profil, {})
        return profil.get("label") or self._nom_profil

    def _lire_peut_filtrer_nouvelles(self) -> bool:
        return 0 < self._nb_nouvelles < self._modele.rowCount()

    def _lire_ligne_selectionnee(self) -> int:
        return self._ligne_selectionnee

    def _lire_numero_selection(self) -> str:
        if self._ligne_selectionnee < 0:
            return ""
        source = self._proxy.mapToSource(
            self._proxy.index(self._ligne_selectionnee, 0, QModelIndex())
        )
        return self._modele.numero(source.row()) if source.isValid() else ""

    def _lire_choix(self) -> dict[str, Any]:
        return {
            "categories": [
                {"cle": cle, "libelle": libelle}
                for cle, libelle in LIBELLES_CATEGORIES.items()
            ],
            "versants": [{"cle": cle, "libelle": lib} for cle, lib in VERSANTS],
            "types_poste": [libelle for libelle, _ in TYPES_POSTE],
            "experiences": [INDIFFERENTE, *EXPERIENCES],
            "dates_publication": [INDIFFERENTE, *DATES_PUBLICATION],
        }

    etat = Property(dict, _lire_etat, notify=etat_change)
    """Valeurs du formulaire et libellés des listes de choix."""
    modele = Property(QObject, _lire_modele, constant=True)
    """Registre trié et filtré (`ProxyOffres` sur `ModeleRegistre`)."""
    phase = Property(str, _lire_phase, notify=etat_change)
    """« vide », « en_cours », « resultats », « aucun » ou « erreur »."""
    texte_bouton = Property(str, _lire_texte_bouton, notify=etat_change)
    statut = Property(str, _lire_statut, notify=etat_change)
    avancement = Property(list, _lire_avancement, notify=etat_change)
    """Une entrée `{nom, etat}` par source interrogée."""
    resume = Property(str, _lire_resume, notify=etat_change)
    avertissements = Property(str, _lire_avertissements, notify=etat_change)
    erreur = Property(str, _lire_erreur, notify=etat_change)
    etat_organisations = Property(str, _lire_etat_organisations, notify=etat_change)
    """Vide si la liste des organisations est chargée, sinon « chargement… »
    ou « indisponible », affiché à la place de la sélection."""
    edition = Property(bool, _lire_edition, notify=etat_change)
    intitule_edition = Property(str, _lire_intitule_edition, notify=etat_change)
    peut_filtrer_nouvelles = Property(
        bool, _lire_peut_filtrer_nouvelles, notify=etat_change
    )
    ligne_selectionnee = Property(int, _lire_ligne_selectionnee, notify=etat_change)
    """Ligne du registre (après tri et filtre) sélectionnée, -1 sinon."""
    numero_selection = Property(str, _lire_numero_selection, notify=etat_change)
    """N° (colonne du registre) de l'offre sélectionnée, vide sinon."""
    choix = Property(dict, _lire_choix, constant=True)

    # --- Formulaire ---

    @Slot(str, "QVariant")
    def definir(self, champ: str, valeur: Any) -> None:
        """Modifie une valeur du formulaire (case, liste, texte). Un tableau
        JavaScript arrive en `QJSValue`, converti ici en liste Python."""
        if champ not in self._etat:
            return
        if isinstance(valeur, QJSValue):
            valeur = valeur.toVariant()
        self._etat[champ] = (
            list(valeur) if isinstance(self._etat[champ], list) else valeur
        )
        self.etat_change.emit()

    @Slot(str, str, bool)
    def basculer(self, champ: str, valeur: str, coche: bool) -> None:
        """Coche ou décoche une valeur d'une liste à cases (catégories, versants)."""
        if champ not in ("categories", "versants"):
            return
        liste = [v for v in self._etat[champ] if v != valeur]
        if coche:
            liste.append(valeur)
        self._etat[champ] = liste
        self.etat_change.emit()

    @Slot(str, result=list)
    def groupes_selection(self, liste: str) -> list[dict[str, Any]]:
        """Éléments proposés par la fenêtre de sélection de `liste`, par
        groupes `{groupe, elements: [{valeur, libelle}]}` (groupe vide pour
        une liste simple)."""
        if liste == "domaines":
            return [
                {
                    "groupe": "",
                    "elements": [{"valeur": d, "libelle": d} for d in sorted(DOMAINES)],
                }
            ]
        if liste == "localisations":
            return [
                {
                    "groupe": "",
                    "elements": [
                        {"valeur": lieu, "libelle": _libelle_localisation(lieu)}
                        for lieu in sorted(LOCALISATIONS)
                    ],
                }
            ]
        if liste == "grades":
            return [
                {
                    "groupe": corps,
                    "elements": [{"valeur": g, "libelle": g} for g in grades],
                }
                for corps, grades in CORPS_GRADES.items()
            ]
        if liste == "organisations":
            return [
                {
                    "groupe": ministere,
                    "elements": [
                        {"valeur": f"{ministere} - {sous}", "libelle": sous}
                        for sous in sorted(self._orgas_cache[ministere])
                    ],
                }
                for ministere in sorted(self._orgas_cache)
            ]
        return []

    @Slot()
    def reinitialiser(self) -> None:
        """Remet le formulaire à son état par défaut (bouton RAZ)."""
        self._etat = _etat_initial()
        self.etat_change.emit()

    def construire_filtres(self) -> FiltresRecherche:
        """Filtres de recherche correspondant au formulaire."""
        experience = self._etat["experience"]
        date_publication = self._etat["date_publication"]
        return {
            "categories": list(self._etat["categories"]),
            "domaines": list(self._etat["domaines"]),
            "localisations": list(self._etat["localisations"]),
            "organisations": list(self._etat["organisations"]),
            "grades": list(self._etat["grades"]),
            "versants": list(self._etat["versants"]),
            "types_poste": TYPES_POSTE[int(self._etat["type_poste"])][1],
            "experience": "" if experience == INDIFFERENTE else experience,
            "date_publication": (
                "" if date_publication == INDIFFERENTE else date_publication
            ),
            "management": bool(self._etat["management"]),
            "teletravail": bool(self._etat["teletravail"]),
            "query": str(self._etat["mot_cle"]).strip(),
            "grades_superieurs": bool(self._etat["grades_superieurs"]),
        }

    def _charger_profil(self, nom: str) -> bool:
        profil = charger_profils().get(nom)
        if profil is None:
            return False
        types_poste = profil.get("types_poste")
        index_type = next(
            (
                rang
                for rang, (_, valeur) in enumerate(TYPES_POSTE)
                if valeur == types_poste
            ),
            0,
        )
        self._etat = {
            **_etat_initial(),
            "categories": categories_compatibles(profil),
            "versants": versants_compatibles(profil),
            "domaines": list(profil.get("domaines") or []),
            "localisations": list(profil.get("localisations") or []),
            "organisations": list(profil.get("organisations") or []),
            "grades": list(profil.get("grades") or []),
            "type_poste": index_type,
            "experience": profil.get("experience") or INDIFFERENTE,
            "date_publication": profil.get("date_publication") or INDIFFERENTE,
            "management": bool(profil.get("management")),
            "teletravail": bool(profil.get("teletravail")),
            "mot_cle": profil.get("query") or "",
            "grades_superieurs": bool(profil.get("grades_superieurs")),
        }
        self._nom_profil = nom
        self._filtres_fiche = self.construire_filtres()
        return True

    @Slot(str)
    def lancer_profil(self, nom: str) -> None:
        """Remplit le formulaire avec la fiche `nom` et lance sa recherche."""
        if self._thread is not None or not self._charger_profil(nom):
            return
        self._edition = False
        self.lancer()

    @Slot(str)
    def modifier_profil(self, nom: str) -> None:
        """Remplit le formulaire avec la fiche `nom` en mode édition."""
        if self._thread is not None or not self._charger_profil(nom):
            return
        self._edition = True
        self.etat_change.emit()

    @Slot()
    def nouvelle_recherche(self) -> None:
        """Formulaire vierge, hors fiche et hors édition."""
        if self._thread is not None:
            return
        self._etat = _etat_initial()
        self._nom_profil = None
        self._edition = False
        self.etat_change.emit()

    @Slot()
    def annuler_edition(self) -> None:
        """Quitte le mode édition sans enregistrer."""
        self._edition = False
        self._nom_profil = None
        self.etat_change.emit()
        self.retour_profils.emit()

    @Slot()
    def valider(self) -> None:
        """Bouton principal du formulaire : enregistre la fiche en édition,
        lance la recherche sinon."""
        if self._edition and self._nom_profil is not None:
            modifier_profil(self._nom_profil, self.construire_filtres())
            self._edition = False
            self.etat_change.emit()
            self.retour_profils.emit()
            return
        self.lancer()

    @Slot(str, str, result=str)
    def classer(self, nom: str, intitule: str) -> str:
        """Classe la demande actuelle en profil.

        Returns:
            Message d'erreur à afficher, chaîne vide si la fiche est créée.
        """
        nom = nom.strip()
        if not nom:
            return "Donner un nom à la fiche."
        if nom in charger_profils():
            return "Une fiche porte déjà ce nom."
        filtres = self.construire_filtres()
        ajouter_profil(nom, cast(Profil, {**filtres, "label": intitule.strip() or nom}))
        return ""

    # --- Recherche ---

    def _unite_progression(self) -> str:
        """« page » tant qu'aucune source n'a commencé à lire des fiches."""
        return "étape" if self._pages_liste else "page"

    def _totaux_pages(self) -> tuple[int, int]:
        return (
            sum(page for page, _ in self._pages.values()),
            sum(total for _, total in self._pages.values()),
        )

    @Slot()
    def lancer(self) -> None:
        """Lance la recherche en arrière-plan ; sans effet si une
        recherche tourne déjà."""
        if self._thread is not None:
            return
        filtres = self.construire_filtres()
        if filtres.get("organisations") and not self._orgas_cache:
            # Sans la liste, le filtre serait abandonné sans rien dire.
            self._phase = "erreur"
            self._erreur = MESSAGE_ORGANISATIONS_ABSENTES
            self.etat_change.emit()
            return
        self._filtres_lances = filtres
        self._profil_lance = (
            self._nom_profil
            if not self._edition and filtres == self._filtres_fiche
            else None
        )
        self._grades = list(filtres.get("grades") or [])
        self._grades_superieurs = bool(self._etat["grades_superieurs"])
        self._sources = {}
        self._pages = {}
        self._pages_liste = {}
        self._avertissements = []
        self._erreur = ""
        self._phase = "en_cours"

        self._thread = QThread()
        self._travailleur = TravailleurRecherche(filtres, self._orgas_cache)
        self._travailleur.moveToThread(self._thread)
        self._thread.started.connect(self._travailleur.executer)
        self._travailleur.source_en_cours.connect(self._on_source_en_cours)
        self._travailleur.progression.connect(self._on_progression)
        self._travailleur.fiches.connect(self._on_fiches)
        self._travailleur.offres_source.connect(self._on_offres_source)
        self._travailleur.avertissement.connect(self._on_avertissement)
        self._travailleur.resultat.connect(self._on_resultat)
        self._travailleur.erreur.connect(self._on_erreur)
        self._travailleur.resultat.connect(self._thread.quit)
        self._travailleur.erreur.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_termine)
        self.etat_change.emit()
        self._thread.start()

    def _on_source_en_cours(self, nom: str) -> None:
        self._sources[nom] = "en cours…"
        self.etat_change.emit()

    def _on_progression(self, nom: str, page: int, total: int) -> None:
        self._pages[nom] = (page, total)
        if total > 1:
            self._sources[nom] = f"page {page}/{total}"
        self.etat_change.emit()

    def _on_fiches(self, nom: str, lues: int, total: int) -> None:
        pages, _ = self._pages.get(nom, (0, 0))
        base = self._pages_liste.setdefault(nom, pages)
        self._pages[nom] = (base + lues, base + total)
        self._sources[nom] = f"fiches {lues}/{total}"
        self.etat_change.emit()

    def _on_offres_source(self, nom: str, nombre: int) -> None:
        self._sources[nom] = f"terminé · {nombre} offre{'s' if nombre > 1 else ''}"
        self.etat_change.emit()

    def _on_avertissement(self, message: str) -> None:
        self._avertissements.append(message)
        nom = message.split(" indisponible", 1)[0]
        if nom in self._sources:
            self._sources[nom] = "indisponible"
        self.etat_change.emit()

    def _on_resultat(
        self, offres: list[Offre], nb_pages: int, arret_anticipe: bool
    ) -> None:
        profil = self._profil_lance
        resultat = post_traiter_resultats(
            offres, self._grades, self._grades_superieurs, profil
        )
        self._nb_nouvelles = len(resultat["nouvelles"])
        self._nb_pages = nb_pages
        self._proxy.definir_nouvelles_seulement(False)
        self._modele.definir_offres(resultat["offres"], resultat["nouvelles"])
        self._ligne_selectionnee = -1
        if arret_anticipe:
            self._avertissements.append(f"Arrêt à la page {nb_pages} (page vide)")
        elif nb_pages > MAX_PAGES:
            self._avertissements.append(
                f"{nb_pages} pages au total\u00a0: seules les {MAX_PAGES} premières chargées."
            )
        self._resume = resume_registre(
            len(resultat["offres"]),
            self._nb_nouvelles,
            resultat["nb_exclus"],
            datetime.now(),
        )
        self._phase = "resultats" if resultat["offres"] else "aucun"
        self.etat_change.emit()

    def _on_erreur(self, message: str) -> None:
        self._erreur = message
        self._phase = "erreur"
        self.etat_change.emit()

    def _on_thread_termine(self) -> None:
        self._thread = None
        self._travailleur = None
        self.etat_change.emit()

    def remplacer_organisations(self, organisations: Organisations) -> None:
        """Nouveau cache des organisations (Réglages › Rafraîchir le cache,
        ou au lancement), utilisé dès la prochaine sélection ou recherche."""
        self._orgas_cache = organisations
        self.etat_change.emit()

    def definir_chargement_organisations(self, en_cours: bool) -> None:
        """Signale un chargement de la liste des organisations en cours."""
        if en_cours != self._chargement_organisations:
            self._chargement_organisations = en_cours
            self.etat_change.emit()

    def arreter(self) -> None:
        """Attend la fin d'une recherche ou d'un appel réseau en cours :
        détruire un `QThread` encore actif fait planter le processus."""
        threads = [t for t, _ in self._taches]
        if self._thread is not None:
            threads.append(self._thread)
        for thread in threads:
            if thread.isRunning():
                thread.quit()
                thread.wait()

    # --- Registre ---

    @Slot(str)
    def filtrer(self, texte: str) -> None:
        """Filtre le registre sur toutes les colonnes, sans relancer."""
        self._proxy.setFilterFixedString(texte)
        self._ligne_selectionnee = -1
        self.etat_change.emit()

    @Slot(bool)
    def nouvelles_seulement(self, actif: bool) -> None:
        """Restreint le registre aux offres nouvelles."""
        self._proxy.definir_nouvelles_seulement(actif)
        self._ligne_selectionnee = -1
        self.etat_change.emit()

    @Slot(int)
    def trier(self, colonne: int) -> None:
        """Trie sur `colonne` ; un second clic inverse l'ordre."""
        croissant = Qt.SortOrder.AscendingOrder
        ordre = (
            Qt.SortOrder.DescendingOrder
            if self._proxy.sortColumn() == colonne
            and self._proxy.sortOrder() == croissant
            else croissant
        )
        self._proxy.sort(colonne, ordre)
        self._ligne_selectionnee = -1
        self.etat_change.emit()

    def _lire_tri(self) -> dict[str, int]:
        return {
            "colonne": self._proxy.sortColumn(),
            "ordre": int(self._proxy.sortOrder().value),
        }

    tri = Property(dict, _lire_tri, notify=etat_change)
    """Colonne triée (-1 si aucune) et ordre (0 croissant, 1 décroissant)."""

    @Slot(int)
    def selectionner(self, ligne: int) -> None:
        """Sélectionne une ligne du registre (-1 pour aucune)."""
        self._ligne_selectionnee = ligne if 0 <= ligne < self._proxy.rowCount() else -1
        self.etat_change.emit()

    def _offre_selectionnee(self) -> Offre | None:
        if self._ligne_selectionnee < 0:
            return None
        source = self._proxy.mapToSource(
            self._proxy.index(self._ligne_selectionnee, 0, QModelIndex())
        )
        return self._modele.offre(source.row()) if source.isValid() else None

    @Slot(int)
    def consulter_ligne(self, ligne: int) -> None:
        """Sélectionne la ligne puis ouvre sa fiche de poste dans
        l'application (double-clic, Entrée)."""
        self.selectionner(ligne)
        self.consulter()

    def _lancer_tache(
        self, fonction: Callable[[], object], suite: Callable[[object], None]
    ) -> None:
        thread = QThread()
        tache = TacheReseau(fonction)
        tache.moveToThread(thread)
        thread.started.connect(tache.executer)
        tache.termine.connect(self._on_tache_terminee)
        tache.echec.connect(self._on_tache_echouee)
        tache.termine.connect(thread.quit)
        tache.echec.connect(thread.quit)
        thread.finished.connect(self._on_thread_tache_fini)
        self._suites[id(tache)] = suite
        self._taches.append((thread, tache))
        thread.start()

    def _on_tache_terminee(self, resultat: object) -> None:
        tache = self.sender()
        suite = self._suites.pop(id(tache), None)
        if suite is not None:
            suite(resultat)

    def _on_tache_echouee(self, message: str) -> None:
        journal.warning("Fiche ou suivi impossible\u00a0: %s", message)
        self._suites.pop(id(self.sender()), None)
        self.action_echouee.emit(f"Opération impossible\u00a0: {message}")

    def _on_thread_tache_fini(self) -> None:
        self._taches = [(t, tache) for t, tache in self._taches if t.isRunning()]

    @Slot()
    def consulter(self) -> None:
        """Télécharge la fiche de poste de l'offre sélectionnée puis
        émet `detail_pret`."""
        offre = self._offre_selectionnee()
        if offre is None:
            return

        def afficher(detail: object) -> None:
            contenu = contenu_detail(
                offre["reference"],
                offre["titre"],
                [offre["employeur"], offre["localisation"], offre.get("source") or ""],
                cast(Any, detail),
                offre["url"],
                chemin_archive_pdf(offre["reference"]).exists(),
            )
            self.detail_pret.emit(
                {
                    "reference": contenu.reference,
                    "titre": contenu.titre,
                    "sousTitre": contenu.sous_titre,
                    "description": contenu.description,
                    "informations": [
                        {
                            "libelle": libelle,
                            "valeur": valeur,
                            "date": libelle in ("Publiée le", "Date limite"),
                        }
                        for libelle, valeur in contenu.informations
                    ],
                    "rubriques": [
                        {"titre": titre, "texte": texte}
                        for titre, texte in contenu.rubriques
                    ],
                    "peutPostuler": bool(contenu.lien_postuler),
                    "lienPostuler": contenu.lien_postuler,
                    "enLigne": bool(contenu.url),
                    "url": contenu.url,
                    "archivePresente": contenu.archive_presente,
                }
            )

        self._lancer_tache(lambda: recuperer_detail_offre(offre["url"]), afficher)

    @Slot(str)
    def ouvrir_lien(self, url: str) -> None:
        """Ouvre un lien https (Postuler, Consulter en ligne)."""
        if url.startswith("https://"):
            QDesktopServices.openUrl(QUrl(url))

    @Slot()
    def tamponner_pour_suivi(self) -> None:
        """Ajoute l'offre sélectionnée au suivi (fiche archivée), puis
        émet `suivi_termine`."""
        offre = self._offre_selectionnee()
        if offre is None:
            return
        self._lancer_tache(
            lambda: suivre_offre(offre),
            lambda _: self.suivi_termine.emit(offre["titre"]),
        )

    @Slot(result=dict)
    def exporter(self) -> dict[str, Any]:
        """Exporte le registre affiché (tri et filtres compris) en HTML.

        Returns:
            `{chemin, nombre}` du fichier produit.
        """
        offres = self._proxy.offres_visibles()
        # Critères de la recherche affichée, même si le formulaire a changé depuis.
        resume = resumer_filtres(self._filtres_lances)
        chemin = exporter_html(offres, resume, self._nb_pages, self._profil_lance)
        return {"chemin": str(chemin), "nombre": len(offres)}

    @Slot(str)
    def ouvrir_fichier(self, chemin: str) -> None:
        """Ouvre un fichier local (export) dans l'application par défaut."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(chemin))
