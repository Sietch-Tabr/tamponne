"""Source emploi.fhf.fr (Fédération Hospitalière de France) — implémente
`SourceOffres`.

Portail Drupal de la FPH. Le site filtre par mot-clé et par département
(`department=` dans l'adresse) : une recherche par département demandé
donne exactement les offres de ses établissements, sans lire aucune fiche.
"""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from src.filtres import libelle_lieu, numeros_departements
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.fhf.api import (
    DEPARTEMENTS_SITE,
    construire_url_recherche,
    nouvelle_session,
    obtenir_fiche_offre,
    obtenir_page_recherche,
)
from src.sources.fhf.extraction import extraire_detail_offre, extraire_offres
from src.types import DetailOffre, FiltresRecherche, Offre

MAX_PAGES = 20
MAX_PAGES_FILTREE = 100
"""Plafond de pages d'un département (une recherche sans lieu s'arrête à
MAX_PAGES) : Paris en compte une quarantaine."""
LECTEURS = 4
"""Pages lues en même temps (vérifié : 160 pages en 21 s, sans refus)."""
_DELAI_COURTOISIE = 0.3


class Fhf:
    """Implémente :class:`~src.sources.base.SourceOffres` pour le portail
    de la Fédération Hospitalière de France."""

    def rechercher(
        self,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        """Voir :meth:`SourceOffres.rechercher`.

        Pas de total annoncé sur ce site (pager Drupal sans compteur) :
        lecture par lots de pages jusqu'à une page vide ou le plafond. Avec
        une localisation, une recherche par département du site (la liste
        n'affiche qu'une ville, le numéro vient donc de la recherche) ; la
        date de publication est appliquée par l'appelant."""
        del on_fiche  # imposé par le contrat de SourceOffres, sans fiche à lire ici
        query = filtres.get("query", "")
        localisations = filtres.get("localisations", [])
        if not localisations:
            return self._lire_liste(query, "", MAX_PAGES, on_page, 0)

        departements = sorted(
            numero
            for numero in numeros_departements(localisations)
            if numero in DEPARTEMENTS_SITE
        )
        offres: list[Offre] = []
        nb_pages = 0
        plafonne = False
        for numero in departements:
            offres_dep, pages, plafond = self._lire_liste(
                query, numero, MAX_PAGES_FILTREE, on_page, nb_pages
            )
            for offre in offres_dep:
                offre["localisation"] = _lieu_complet(offre["localisation"], numero)
            offres.extend(offres_dep)
            nb_pages += pages
            plafonne = plafonne or plafond
        return offres, nb_pages, plafonne

    def _lire_liste(
        self,
        query: str,
        departement: str,
        max_pages: int,
        on_page: Callable[[int, int], None] | None,
        deja_lues: int,
    ) -> tuple[list[Offre], int, bool]:
        """Pages du mot-clé et du département (tous si vide), par lots de
        `LECTEURS`, jusqu'à la première page vide ou `max_pages`.

        `deja_lues` : pages des départements précédents, pour la progression.
        Retourne les offres, le nombre de pages parcourues (page vide
        comprise) et si le plafond a coupé la liste.
        """
        opener = nouvelle_session()

        def _page(numero: int) -> list[Offre]:
            time.sleep(_DELAI_COURTOISIE)
            url = construire_url_recherche(query, numero, departement)
            return extraire_offres(obtenir_page_recherche(opener, url).get("html", ""))

        offres: list[Offre] = []
        lues = deja_lues
        with ThreadPoolExecutor(max_workers=LECTEURS) as pool:
            for debut in range(0, max_pages, LECTEURS):
                lot = range(debut, min(debut + LECTEURS, max_pages))
                for numero, offres_page in zip(lot, pool.map(_page, lot), strict=True):
                    if not offres_page:
                        if on_page:
                            on_page(lues + 1, lues + 1)
                        return offres, numero + 1, False
                    offres.extend(offres_page)
                    lues += 1
                    if on_page:
                        on_page(lues, max(lues, max_pages))
        return offres, max_pages, True


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
