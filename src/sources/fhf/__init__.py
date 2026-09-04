"""Source emploi.fhf.fr (Fédération Hospitalière de France) — implémente
`SourceOffres`.

Portail Drupal de la FPH. Seul le mot-clé libre (`query`) est câblé
pour l'instant côté filtres.
"""

import time
from collections.abc import Callable

from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.fhf.api import (
    construire_url_recherche,
    nouvelle_session,
    obtenir_fiche_offre,
    obtenir_page_recherche,
)
from src.sources.fhf.extraction import extraire_detail_offre, extraire_offres
from src.types import DetailOffre, FiltresRecherche, Offre

MAX_PAGES = 20
_DELAI_COURTOISIE = 0.5


class Fhf:
    """Implémente :class:`~src.sources.base.SourceOffres` pour le portail
    de la Fédération Hospitalière de France."""

    def rechercher(
        self,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        """Voir :meth:`SourceOffres.rechercher`.

        Pas de total annoncé sur ce site (pager Drupal sans compteur) —
        boucle jusqu'à une page vide ou `MAX_PAGES`, comme ailleurs
        dans le projet (détection de fin de pagination par page vide)."""
        opener = nouvelle_session()
        query = filtres.get("query", "")

        toutes_offres: list[Offre] = []
        for page in range(MAX_PAGES):
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
                on_page(page + 1, MAX_PAGES)

        return toutes_offres, MAX_PAGES, True


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
