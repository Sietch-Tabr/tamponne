"""Recherche multi-source : orchestration et post-traitement des résultats.

Ne dépend d'aucune bibliothèque d'UI : la progression est remontée par
callbacks, que `src.gui.travailleurs.TravailleurRecherche` relaie en
signaux Qt.
"""

import logging
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Final

from src.donnees.cache import maj_cache_offres
from src.donnees.parametres_sources import (
    SOURCES_DISPONIBLES,
    VERSANT_SOURCE,
    charger_sources_actives,
)
from src.donnees.profils import noter_lancement
from src.filtres import filtrer_par_grades, resumer_filtres
from src.sources.base import SourceOffres, deduplique_offres
from src.sources.choisirleservicepublic import MAX_PAGES, ChoisirLeServicePublic
from src.sources.choisirleservicepublic.extraction import filtrer_grades_superieurs
from src.sources.emploiterritorial import EmploiTerritorial
from src.sources.fhf import Fhf
from src.sources.fhf.dedoublonnage import filtrer_doublons_fhf
from src.sources.passerellesmef import PasserellesMef
from src.types import FiltresRecherche, Offre, Organisations, ResultatTraite

journal = logging.getLogger(__name__)


class RechercheImpossible(Exception):
    """Aucun résultat exploitable : aucune source active, ou toutes en échec.

    Le message est destiné à être affiché tel quel à l'utilisateur.
    """


def construire_source(cle: str, orgas_cache: Organisations) -> SourceOffres | None:
    """Instancie la source correspondant à `cle`, `None` si inconnue."""
    if cle == "choisirleservicepublic":
        return ChoisirLeServicePublic(orgas_cache)
    if cle == "emploiterritorial":
        return EmploiTerritorial()
    if cle == "passerellesmef":
        return PasserellesMef()
    if cle == "fhf":
        return Fhf()
    return None


# Critères qu'une source n'applique pas du tout : elle renverrait des offres
# hors sujet, elle est donc écartée quand l'un d'eux est renseigné.
CRITERES_NON_HONORES: Final[Mapping[str, tuple[str, ...]]] = {
    "emploiterritorial": ("domaines", "organisations", "date_publication"),
    "passerellesmef": ("experience",),
    "fhf": (
        "localisations",
        "categories",
        "domaines",
        "organisations",
        "experience",
        "date_publication",
        "management",
        "teletravail",
    ),
}

_LIBELLES_CRITERES: Final[Mapping[str, str]] = {
    "localisations": "la localisation",
    "categories": "la catégorie",
    "domaines": "le domaine",
    "organisations": "l'organisation",
    "experience": "l'expérience",
    "date_publication": "la date de publication",
    "management": "le management",
    "teletravail": "le télétravail",
}


def criteres_non_honores(cle: str, filtres: FiltresRecherche) -> list[str]:
    """Libellés des critères renseignés que la source `cle` ne sait pas
    appliquer."""
    return [
        _LIBELLES_CRITERES[critere]
        for critere in CRITERES_NON_HONORES.get(cle, ())
        if filtres.get(critere)
    ]


def sources_a_interroger(
    filtres: FiltresRecherche,
    orgas_cache: Organisations,
    ecartees: list[str] | None = None,
) -> list[tuple[str, str, SourceOffres]]:
    """(clé, nom affiché, source) des sources actives et compatibles avec
    le filtre Versant, dans l'ordre de `SOURCES_DISPONIBLES`.

    Une source qui ne sait pas appliquer un critère renseigné est écartée ;
    si `ecartees` est fourni, un message par source écartée y est ajouté.
    """
    sources_actives = charger_sources_actives()
    versants_filtres = filtres.get("versants") or []
    resultat: list[tuple[str, str, SourceOffres]] = []
    for cle, nom_affiche in SOURCES_DISPONIBLES.items():
        if not sources_actives.get(cle, True):
            continue
        versant_source = VERSANT_SOURCE.get(cle)
        if (
            versant_source is not None
            and versants_filtres
            and versant_source not in versants_filtres
        ):
            continue  # source mono-versant exclue par le filtre Versant
        if ignores := criteres_non_honores(cle, filtres):
            if ecartees is not None:
                ecartees.append(
                    f"{nom_affiche} non interrogée\u00a0: elle ne filtre pas sur "
                    + ", ".join(ignores)
                )
            continue
        source = construire_source(cle, orgas_cache)
        if source is not None:
            resultat.append((cle, nom_affiche, source))
    return resultat


def _ignorer(*_args: object) -> None:
    return None


def rechercher_toutes_sources(
    filtres: FiltresRecherche,
    orgas_cache: Organisations,
    *,
    on_source_en_cours: Callable[[str], None] = _ignorer,
    on_progression: Callable[[str, int, int], None] = _ignorer,
    on_source_terminee: Callable[[str], None] = _ignorer,
    on_avertissement: Callable[[str], None] = _ignorer,
    on_offres_source: Callable[[str, int], None] = _ignorer,
) -> tuple[list[Offre], int, bool]:
    """Interroge les sources actives en parallèle, puis fusionne et
    dédoublonne leurs résultats.

    Les sources tournent simultanément (une par thread) mais sont
    fusionnées dans l'ordre de `SOURCES_DISPONIBLES` : le dédoublonnage
    garde la première occurrence (choisirleservicepublic) et FHF est
    comparée aux offres des sources qui la précèdent.

    Args:
        filtres: Filtres génériques de la recherche.
        orgas_cache: Organisations en cache (pour choisirleservicepublic).
        on_source_en_cours: Appelé avec le nom affiché d'une source dont
            l'interrogation démarre.
        on_progression: Appelé avec (nom affiché, page chargée, nb pages
            à charger) — depuis les threads du pool.
        on_source_terminee: Appelé quand une source a fini (succès ou
            échec) — depuis les threads du pool.
        on_avertissement: Appelé pour chaque source en échec, sans
            interrompre les autres.
        on_offres_source: Appelé avec (nom affiché, nombre d'offres
            trouvées avant dédoublonnage) quand une source réussit —
            depuis les threads du pool.

    Returns:
        ``(offres, nb_pages, arret_anticipe)`` ; ``nb_pages`` et
        ``arret_anticipe`` sont ceux de choisirleservicepublic (1 et
        ``False`` si elle n'a pas été interrogée).

    Raises:
        RechercheImpossible: aucune source active, ou toutes en échec.
    """
    ecartees: list[str] = []
    sources = sources_a_interroger(filtres, orgas_cache, ecartees)
    if not sources:
        raise RechercheImpossible(
            "Aucune source ne sait appliquer ces critères."
            if ecartees
            else "Aucune source cochée\u00a0: voir Réglages › Sources consultées."
        )
    for message in ecartees:
        on_avertissement(message)

    def _interroger(
        nom_affiche: str, source: SourceOffres
    ) -> tuple[list[Offre], int, bool]:
        def _on_page(page: int, total: int) -> None:
            on_progression(nom_affiche, page, total)

        try:
            resultat = source.rechercher(filtres, on_page=_on_page)
            on_offres_source(nom_affiche, len(resultat[0]))
            return resultat
        finally:
            on_source_terminee(nom_affiche)

    with ThreadPoolExecutor(max_workers=len(sources)) as pool:
        futurs: list[tuple[str, str, Future[tuple[list[Offre], int, bool]]]] = []
        for cle, nom_affiche, source in sources:
            on_source_en_cours(nom_affiche)
            futurs.append(
                (cle, nom_affiche, pool.submit(_interroger, nom_affiche, source))
            )

        toutes_offres: list[Offre] = []
        nb_pages_reference = 1
        arret_anticipe_reference = False
        nb_echecs = 0
        for cle, nom_affiche, futur in futurs:
            try:
                offres, nb_pages, arret_anticipe = futur.result()
            except RuntimeError as erreur:
                nb_echecs += 1
                journal.warning("%s indisponible\u00a0: %s", nom_affiche, erreur)
                on_avertissement(f"{nom_affiche} indisponible\u00a0: {erreur}")
                continue
            # Page au format imprévu (site modifié) : cette source seule est
            # perdue, les autres restent affichées.
            except Exception as erreur:  # noqa: BLE001
                nb_echecs += 1
                journal.exception("%s\u00a0: réponse inattendue du site", nom_affiche)
                on_avertissement(
                    f"{nom_affiche} indisponible\u00a0: réponse inattendue du site "
                    f"({type(erreur).__name__}\u00a0: {erreur})"
                )
                continue
            if cle == "fhf":
                offres = filtrer_doublons_fhf(offres, toutes_offres)
            toutes_offres.extend(offres)
            if cle == "choisirleservicepublic":
                nb_pages_reference = nb_pages
                arret_anticipe_reference = arret_anticipe

    if nb_echecs == len(sources):
        journal.error("Recherche impossible\u00a0: toutes les sources ont échoué")
        raise RechercheImpossible(
            "Toutes les sources actives sont indisponibles. Réessayer dans un moment."
        )

    return (
        deduplique_offres(toutes_offres),
        nb_pages_reference,
        arret_anticipe_reference,
    )


def post_traiter_resultats(
    offres: list[Offre],
    grades: list[str],
    afficher_grades_superieurs: bool,
    nom_profil: str | None,
) -> ResultatTraite:
    """Filtre les offres brutes d'une recherche et repère les nouvelles.

    Args:
        offres: Offres fusionnées et dédoublonnées.
        grades: Grades sélectionnés (liste vide = pas de filtre).
        afficher_grades_superieurs: Conserve les offres IDiv/IP au lieu
            de les exclure par leur titre.
        nom_profil: Profil sauvegardé dont on met à jour le cache des
            offres vues et la date du dernier lancement ; `None` hors profil
            (ou critères modifiés) : aucune offre n'est alors marquée nouvelle.
    """
    if afficher_grades_superieurs:
        offres_filtrees, nb_exclus = offres, 0
    else:
        offres_filtrees, nb_exclus = filtrer_grades_superieurs(offres)
    offres_filtrees = filtrer_par_grades(offres_filtrees, grades)

    nouvelles: set[str] = set()
    if nom_profil:
        nouvelles = maj_cache_offres(nom_profil, offres_filtrees)
        noter_lancement(nom_profil)

    return {"offres": offres_filtrees, "nb_exclus": nb_exclus, "nouvelles": nouvelles}


def lignes_resume(
    filtres: FiltresRecherche,
    resultat: ResultatTraite,
    nb_pages: int,
    arret_anticipe: bool,
    avertissements: list[str],
) -> list[str]:
    """Lignes de texte résumant une recherche terminée (filtres, nombre
    d'offres, nouvelles, exclusions, pagination, avertissements)."""
    offres = resultat["offres"]
    nouvelles = resultat["nouvelles"]
    lignes = [
        f"Filtres\u00a0: {resumer_filtres(filtres)}",
        f"{len(offres)} offre(s)" + (f" · {nb_pages} page(s)" if nb_pages > 1 else ""),
    ]
    if nouvelles:
        lignes.append(
            f"{len(nouvelles)} nouvelle(s) offre(s) depuis la dernière recherche"
        )
    if resultat["nb_exclus"]:
        lignes.append(
            f"{resultat['nb_exclus']} offre(s) IDiv/IP exclue(s) (filtre de titre)"
        )
    if arret_anticipe:
        lignes.append(f"Arrêt à la page {nb_pages} (page vide)")
    elif nb_pages > MAX_PAGES:
        lignes.append(
            f"{nb_pages} pages au total — seules les {MAX_PAGES} premières chargées."
        )
    if not offres:
        lignes.append("Aucune offre trouvée.")
    lignes.extend(avertissements)
    return lignes
