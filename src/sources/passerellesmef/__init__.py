"""Source passerelles.economie.gouv.fr (Bercy) — implémente `SourceOffres`.

Portail Talentsoft des ministères économiques et financiers. Seul le
mot-clé libre (`query`) est câblé pour l'instant côté filtres.
"""

import time
from collections.abc import Callable

from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.passerellesmef.api import (
    construire_url_recherche,
    nouvelle_session,
    obtenir_fiche_offre,
    obtenir_page_recherche,
)
from src.sources.passerellesmef.extraction import (
    extraire_detail_offre,
    extraire_offres,
    extraire_totaux,
)
from src.types import DetailOffre, FiltresRecherche, Offre

MAX_PAGES = 20
_TAILLE_PAGE = 15
_DELAI_COURTOISIE = 0.5


class PasserellesMef:
    """Implémente :class:`~src.sources.base.SourceOffres` pour le portail
    Talentsoft des ministères économiques et financiers."""

    def rechercher(
        self,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        """Voir :meth:`SourceOffres.rechercher`.

        Contrairement au territorial, chaque page est une requête GET
        indépendante (pas cumulatif) — vérifié empiriquement."""
        opener = nouvelle_session()
        query = filtres.get("query", "")

        url = construire_url_recherche(query=query, page=1)
        reponse = obtenir_page_recherche(opener, url)
        nb_offres_total, _ = extraire_totaux(reponse.get("title", ""))
        nb_pages = max(1, -(-nb_offres_total // _TAILLE_PAGE))

        toutes_offres = extraire_offres(reponse.get("html", ""))
        if on_page:
            on_page(1, min(nb_pages, MAX_PAGES))

        pages_a_charger = min(nb_pages, MAX_PAGES)
        for page in range(2, pages_a_charger + 1):
            time.sleep(_DELAI_COURTOISIE)
            url = construire_url_recherche(query=query, page=page)
            reponse = obtenir_page_recherche(opener, url)
            offres_page = extraire_offres(reponse.get("html", ""))
            if not offres_page:
                if on_page:
                    on_page(page, pages_a_charger)
                return toutes_offres, nb_pages, True
            toutes_offres.extend(offres_page)
            if on_page:
                on_page(page, pages_a_charger)

        arret_anticipe = pages_a_charger < nb_pages
        return toutes_offres, nb_pages, arret_anticipe


def recuperer_detail_offre(url: str) -> DetailOffre:
    """Récupère et extrait le détail structuré d'une offre Passerelles/MEF.

    Ne lève jamais d'exception : retourne un `DetailOffre` vide si le
    téléchargement échoue.
    """
    opener = nouvelle_session()
    try:
        html = obtenir_fiche_offre(opener, url)
    except RuntimeError:
        return DETAIL_VIDE
    return extraire_detail_offre(html)
