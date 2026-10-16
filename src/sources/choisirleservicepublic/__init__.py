"""Source choisirleservicepublic.gouv.fr — scraping HTML, GET rewrite URL.

Voir RECHERCHES.md section 7 pour le détail du mécanisme de pagination.
"""

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from src.filtres import (
    CATEGORIES,
    DATES_PUBLICATION,
    DOMAINES,
    EXPERIENCES,
    LOCALISATIONS,
    TYPES_POSTE,
    TYPES_POSTE_DEFAUT,
    VERSANTS,
)
from src.sources.choisirleservicepublic.api import (
    construire_url_filtres,
    obtenir_page_offres,
)
from src.sources.choisirleservicepublic.extraction import (
    DETAIL_VIDE,
    extraire_detail_offre,
    extraire_offres,
    extraire_pagination,
)
from src.types import DetailOffre, FiltresRecherche, Offre, Organisations

MAX_PAGES = 20
_DELAI_COURTOISIE = 0.5  # secondes avant chaque requête de pagination
LECTEURS_PAGES = 3
"""Pages lues en même temps : 3 donnent 12 s pour 20 pages contre 40 s une à une,
6 n'apportent rien de plus (vérifié le 2026-10-16, aucun refus)."""


def _resoudre_ids_organisations(
    noms_organisations: list[str],
    orgas_cache: Organisations,
) -> list[int]:
    """Convertit les noms 'Ministère - Sous-org' en IDs numériques."""
    ids = []
    for nom in noms_organisations:
        parties = nom.split(" - ", 1)
        if len(parties) == 2:
            ministere, sous_org = parties
            ids.append(orgas_cache.get(ministere, {}).get(sous_org, 0))
        else:
            # Fallback : cherche dans tous les ministères
            for sous_orgs in orgas_cache.values():
                if nom in sous_orgs:
                    ids.append(sous_orgs[nom])
                    break
    return [i for i in ids if i]


class ChoisirLeServicePublic:
    """Implémente :class:`~src.sources.base.SourceOffres` pour le portail
    officiel de la fonction publique.
    """

    def __init__(self, orgas_cache: Organisations | None = None) -> None:
        """Args:
        orgas_cache: Cache ministère → sous-organisations → ID, nécessaire
            pour résoudre le filtre "organisations" (voir cache.py).
        """
        self._orgas_cache = orgas_cache or {}

    def rechercher(
        self,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        """Voir :meth:`SourceOffres.rechercher`."""
        categories = [
            CATEGORIES[c] for c in filtres.get("categories", []) if c in CATEGORIES
        ]
        domaines = [DOMAINES[d] for d in filtres.get("domaines", []) if d in DOMAINES]
        locations = [
            LOCALISATIONS[loc]
            for loc in filtres.get("localisations", [])
            if loc in LOCALISATIONS
        ]
        organisations = _resoudre_ids_organisations(
            filtres.get("organisations", []), self._orgas_cache
        )

        versants_cles = filtres.get("versants") or []
        versants = [VERSANTS[v] for v in versants_cles if v in VERSANTS]

        types_poste_filtre = filtres.get("types_poste")
        if types_poste_filtre is None:
            types_poste = TYPES_POSTE_DEFAUT
        elif types_poste_filtre == "__tous__":
            types_poste = []
        else:
            types_poste = [
                TYPES_POSTE[t] for t in types_poste_filtre if t in TYPES_POSTE
            ]

        experience = EXPERIENCES.get(filtres.get("experience") or "")
        date_publication = DATES_PUBLICATION.get(filtres.get("date_publication") or "")
        management = filtres.get("management", False)
        teletravail = filtres.get("teletravail", False)
        query = filtres.get("query", "")

        def _construire_url(page: int) -> str:
            return construire_url_filtres(
                query=query,
                categories=categories,
                locations=locations,
                organisations=organisations,
                versants=versants,
                domaines=domaines,
                types_poste=types_poste,
                experience=experience,
                date_publication=date_publication or None,
                management=management,
                teletravail=teletravail,
                page=page,
            )

        reponse = obtenir_page_offres(_construire_url(1))
        _, nb_pages = extraire_pagination(reponse.get("title", ""))
        toutes_offres = extraire_offres(reponse.get("html", ""))

        arret_anticipe = False
        if nb_pages > 1:
            toutes_offres, nb_pages, arret_anticipe = self._charger_pages_suivantes(
                _construire_url, nb_pages, toutes_offres, on_page
            )
        elif on_page:
            on_page(1, 1)

        return toutes_offres, nb_pages, arret_anticipe

    def _charger_pages_suivantes(
        self,
        construire_url: Callable[[int], str],
        nb_pages: int,
        toutes_offres: list[Offre],
        on_page: Callable[[int, int], None] | None,
    ) -> tuple[list[Offre], int, bool]:
        """Charge les pages 2..nb_pages dans toutes_offres, `LECTEURS_PAGES`
        à la fois (le site met environ 2 s à répondre : lues une à une, 20
        pages prenaient 40 s).

        Les pages sont ensuite examinées dans l'ordre : la lecture s'arrête
        à la première page vide ou dont les références ont déjà été vues
        (boucle de l'API après la dernière page réelle).
        """
        pages_a_charger = min(nb_pages, MAX_PAGES)
        arret_anticipe = False
        refs_vues = {o["reference"] for o in toutes_offres if o.get("reference")}
        if on_page:
            on_page(1, pages_a_charger)

        verrou = threading.Lock()
        lues = [1]

        def _page(numero: int) -> list[Offre]:
            time.sleep(_DELAI_COURTOISIE)
            reponse = obtenir_page_offres(construire_url(numero))
            offres_page = extraire_offres(reponse.get("html", ""))
            with verrou:
                lues[0] += 1
                if on_page:
                    on_page(lues[0], pages_a_charger)
            return offres_page

        with ThreadPoolExecutor(max_workers=LECTEURS_PAGES) as pool:
            pages = pool.map(_page, range(2, pages_a_charger + 1))
            for numero, offres_page in enumerate(pages, start=2):
                refs_page = {o["reference"] for o in offres_page if o.get("reference")}
                if not offres_page or (refs_page and refs_page <= refs_vues):
                    nb_pages = numero - 1
                    arret_anticipe = True
                    break
                toutes_offres.extend(offres_page)
                refs_vues |= refs_page
        return toutes_offres, nb_pages, arret_anticipe


def recuperer_detail_offre(url: str) -> DetailOffre:
    """Récupère et extrait le détail structuré d'une offre depuis sa
    page — utilisé au moment de démarrer un suivi de candidature, pour
    conserver la fiche même si l'offre est dépubliée ensuite.

    Ne lève jamais d'exception : retourne un `DetailOffre` aux champs
    vides si le téléchargement échoue, le suivi basique
    (titre/employeur/url) reste utile même sans le détail enrichi.
    """
    try:
        page = obtenir_page_offres(url)
    except RuntimeError:
        return DETAIL_VIDE
    return extraire_detail_offre(page["html"])
