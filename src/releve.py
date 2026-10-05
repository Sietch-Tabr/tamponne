"""Relevé quotidien des fiches : compte, en arrière-plan, les offres de
chaque fiche pas encore consultées dans le registre.

Ne dépend d'aucune bibliothèque d'UI (`src.gui.travailleurs.ReleveFiches`
l'exécute dans un `QThread`).
"""

from collections.abc import Callable
from datetime import date

from src.profils import versants_compatibles
from src.recherche import post_traiter_resultats, rechercher_toutes_sources
from src.types import FiltresRecherche, Organisations, Profil

_CLES_FILTRES = (
    "categories",
    "domaines",
    "localisations",
    "organisations",
    "grades",
    "types_poste",
    "experience",
    "date_publication",
    "management",
    "teletravail",
    "query",
)


def fiches_a_relever(profils: dict[str, Profil], aujourd_hui: date) -> list[str]:
    """Fiches dont les nouvelles n'ont pas encore été comptées aujourd'hui
    (relevé ou lancement), dans l'ordre d'enregistrement."""
    jour = aujourd_hui.isoformat()
    return [
        nom for nom, profil in profils.items() if profil.get("nouvelles_le") != jour
    ]


def filtres_de_la_fiche(profil: Profil) -> FiltresRecherche:
    """Filtres de recherche d'une fiche, comme le formulaire les reconstruit
    (versant au format historique compris)."""
    filtres: FiltresRecherche = {}
    for cle in _CLES_FILTRES:
        if cle in profil:
            filtres[cle] = profil[cle]  # type: ignore[literal-required]
    filtres["versants"] = versants_compatibles(profil)
    return filtres


def relever_fiche(
    nom: str,
    profil: Profil,
    orgas_cache: Organisations,
    doit_arreter: Callable[[], bool],
) -> int:
    """Interroge les sources pour la fiche `nom` et enregistre le nombre
    d'offres pas encore consultées, sans les marquer consultées.

    Args:
        nom: Nom de la fiche (clé de `profils.json`).
        profil: Fiche enregistrée.
        orgas_cache: Organisations en cache (pour choisirleservicepublic).
        doit_arreter: Arrêt demandé (fermeture de l'application).

    Returns:
        Nombre d'offres pas encore consultées.

    Raises:
        RechercheImpossible: aucune source active, ou toutes en échec.
        RechercheInterrompue: arrêt demandé pendant la recherche.
    """
    filtres = filtres_de_la_fiche(profil)
    offres, _, _ = rechercher_toutes_sources(
        filtres, orgas_cache, doit_arreter=doit_arreter
    )
    resultat = post_traiter_resultats(
        offres, list(filtres.get("grades") or []), False, nom, consultation=False
    )
    return len(resultat["nouvelles"])
