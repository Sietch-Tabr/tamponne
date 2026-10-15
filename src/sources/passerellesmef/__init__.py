"""Source passerelles.economie.gouv.fr (Bercy) — implémente `SourceOffres`.

Portail Talentsoft des ministères économiques et financiers. Le site ne
filtre que par mot-clé : localisation, catégorie, domaine, organisation,
date, management et télétravail sont appliqués ici, sur la liste puis sur
la fiche de chaque offre (voir `filtrage`).
"""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from src.filtres import numero_departement_texte
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.passerellesmef.api import (
    construire_url_recherche,
    nouvelle_session,
    obtenir_fiche_offre,
    obtenir_page_recherche,
)
from src.sources.passerellesmef.filtrage import (
    date_dans_fenetre,
    fiche_correspond,
    fiche_necessaire,
    libelle_lieu,
    lieu_correspond,
    numero_depuis_fiche,
    organisations_de_bercy,
)
from src.sources.passerellesmef.extraction import (
    extraire_detail_offre,
    extraire_offres,
    extraire_totaux,
)
from src.types import DetailOffre, FiltresRecherche, Offre

MAX_PAGES = 20
MAX_PAGES_FILTREE = 100
"""Plafond quand des filtres s'appliquent après coup : lire tout le portail,
sinon les offres du lieu demandé pourraient se trouver au-delà de MAX_PAGES."""
_TAILLE_PAGE = 15
_DELAI_COURTOISIE = 0.5
_LECTEURS_FICHES = 4


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
        organisations = filtres.get("organisations", [])
        if organisations and not organisations_de_bercy(organisations):
            return [], 1, False  # aucune organisation de ce portail demandée

        localisations = filtres.get("localisations", [])
        lire_fiches = fiche_necessaire(filtres)
        filtre_apres_coup = bool(localisations) or lire_fiches
        offres, nb_pages, arret_anticipe = self._lire_liste(
            filtres.get("query", ""),
            MAX_PAGES_FILTREE if filtre_apres_coup else MAX_PAGES,
            on_page,
        )

        if date_publication := filtres.get("date_publication"):
            offres = [
                o for o in offres if date_dans_fenetre(o["date"], date_publication)
            ]
        if not (localisations or lire_fiches):
            return offres, nb_pages, arret_anticipe

        # Sans numéro dans la liste, le lieu ne se lit que sur la fiche.
        numeros = [numero_departement_texte(o["localisation"]) for o in offres]
        if localisations:
            garder = [lieu_correspond(n, localisations) for n in numeros]
            offres = [o for o, g in zip(offres, garder, strict=True) if g]
            numeros = [n for n, g in zip(numeros, garder, strict=True) if g]
        a_lire = [
            o for o, n in zip(offres, numeros, strict=True) if lire_fiches or n is None
        ]
        fiches = self._lire_fiches([o["url"] for o in a_lire])

        retenues: list[Offre] = []
        for offre, numero in zip(offres, numeros, strict=True):
            detail = fiches.get(offre["url"])
            if detail is not None:
                if numero is None:
                    numero = numero_depuis_fiche(detail)
                    if numero and not offre["localisation"]:
                        offre["localisation"] = libelle_lieu(numero)
                if lire_fiches and not fiche_correspond(detail, filtres):
                    continue
            if localisations and not lieu_correspond(numero, localisations):
                continue
            retenues.append(offre)
        return retenues, nb_pages, arret_anticipe

    def _lire_liste(
        self,
        query: str,
        max_pages: int,
        on_page: Callable[[int, int], None] | None,
    ) -> tuple[list[Offre], int, bool]:
        """Pages de résultats du mot-clé, jusqu'à `max_pages`."""
        opener = nouvelle_session()
        url = construire_url_recherche(query=query, page=1)
        reponse = obtenir_page_recherche(opener, url)
        nb_offres_total, _ = extraire_totaux(reponse.get("title", ""))
        nb_pages = max(1, -(-nb_offres_total // _TAILLE_PAGE))

        toutes_offres = extraire_offres(reponse.get("html", ""))
        pages_a_charger = min(nb_pages, max_pages)
        if on_page:
            on_page(1, pages_a_charger)

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

        return toutes_offres, nb_pages, pages_a_charger < nb_pages

    @staticmethod
    def _lire_fiches(urls: list[str]) -> dict[str, DetailOffre]:
        """Fiches des offres `urls` (quelques lectures en parallèle) ; une
        fiche illisible est absente du résultat."""

        def _lire(url: str) -> tuple[str, DetailOffre]:
            time.sleep(_DELAI_COURTOISIE)
            return url, recuperer_detail_offre(url)

        with ThreadPoolExecutor(max_workers=_LECTEURS_FICHES) as pool:
            lues = list(pool.map(_lire, urls))
        return {url: detail for url, detail in lues if detail["page_html"]}


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
