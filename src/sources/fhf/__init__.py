"""Source emploi.fhf.fr (Fédération Hospitalière de France) — implémente
`SourceOffres`.

Portail Drupal de la FPH. Le site ne filtre que par mot-clé : la
localisation est appliquée ici, d'après le code postal de l'établissement lu
sur la fiche de chaque offre (voir `filtrage`).
"""

import time
from collections.abc import Callable

from src.filtres import libelle_lieu, lieu_correspond, numero_departement_texte
from src.sources.base import CacheFiches
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.fhf.filtrage import extraire_fiche
from src.sources.fiches import lire_fiches
from src.sources.fhf.api import (
    construire_url_recherche,
    nouvelle_session,
    obtenir_fiche_offre,
    obtenir_page_recherche,
)
from src.sources.fhf.extraction import extraire_detail_offre, extraire_offres
from src.types import DetailOffre, FicheFiltrage, FiltresRecherche, Offre

MAX_PAGES = 20
MAX_PAGES_FILTREE = 100
"""Plafond quand la localisation s'applique après coup : lire tout le portail,
sinon les offres du lieu demandé pourraient se trouver au-delà de MAX_PAGES."""
_DELAI_COURTOISIE = 0.5


class Fhf:
    """Implémente :class:`~src.sources.base.SourceOffres` pour le portail
    de la Fédération Hospitalière de France.

    Args:
        cache_fiches: Fiches déjà lues, pour ne pas les relire d'une
            recherche à l'autre (aucune mémoire si `None`).
    """

    def __init__(self, cache_fiches: CacheFiches | None = None) -> None:
        self._cache_fiches = cache_fiches

    def rechercher(
        self,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        """Voir :meth:`SourceOffres.rechercher`.

        Pas de total annoncé sur ce site (pager Drupal sans compteur) —
        boucle jusqu'à une page vide ou le plafond de pages, comme ailleurs
        dans le projet. Avec une localisation, le lieu se lit sur la fiche
        (le site n'affiche qu'une ville) ; la date de publication est
        appliquée par l'appelant."""
        localisations = filtres.get("localisations", [])
        offres, nb_pages, arret_anticipe = self._lire_liste(
            filtres.get("query", ""),
            MAX_PAGES_FILTREE if localisations else MAX_PAGES,
            on_page,
        )
        if not localisations:
            return offres, nb_pages, arret_anticipe

        fiches = lire_fiches(
            [o["url"] for o in offres], self._lire_fiche, self._cache_fiches, on_fiche
        )
        retenues: list[Offre] = []
        for offre in offres:
            fiche = fiches.get(offre["url"])
            numero = fiche["numero"] if fiche is not None else ""
            if not lieu_correspond(numero, localisations):
                continue
            if numero and numero_departement_texte(offre["localisation"]) is None:
                offre["localisation"] = _lieu_complet(offre["localisation"], numero)
            retenues.append(offre)
        return retenues, nb_pages, arret_anticipe

    def _lire_liste(
        self,
        query: str,
        max_pages: int,
        on_page: Callable[[int, int], None] | None,
    ) -> tuple[list[Offre], int, bool]:
        opener = nouvelle_session()
        toutes_offres: list[Offre] = []
        for page in range(max_pages):
            if page:
                time.sleep(_DELAI_COURTOISIE)
            url = construire_url_recherche(query=query, page=page)
            reponse = obtenir_page_recherche(opener, url)
            offres_page = extraire_offres(reponse.get("html", ""))
            if not offres_page:
                if on_page:
                    on_page(page + 1, page + 1)
                return toutes_offres, page + 1, False
            toutes_offres.extend(offres_page)
            if on_page:
                on_page(page + 1, max_pages)

        return toutes_offres, max_pages, True

    @staticmethod
    def _lire_fiche(url: str) -> FicheFiltrage | None:
        return extraire_fiche(recuperer_detail_offre(url))


def _lieu_complet(ville: str, numero: str) -> str:
    """« Toulouse (31) » pour une ville et son département, ou le département
    seul quand la liste n'affiche aucune ville."""
    if not ville:
        return libelle_lieu(numero)
    return f"{ville} ({numero})"


def recuperer_detail_offre(url: str) -> DetailOffre:
    """Récupère et extrait le détail structuré d'une offre FHF.

    Ne lève jamais d'exception : retourne un `DetailOffre` vide si le
    téléchargement échoue.
    """
    opener = nouvelle_session()
    try:
        html = obtenir_fiche_offre(opener, url)
    except RuntimeError:
        return DETAIL_VIDE
    return extraire_detail_offre(html)
