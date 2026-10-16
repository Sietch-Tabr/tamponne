"""Source passerelles.economie.gouv.fr (Bercy) — implémente `SourceOffres`.

Portail Talentsoft des ministères économiques et financiers. Le site ne
filtre que par mot-clé : localisation, catégorie, domaine, organisation,
date, management et télétravail sont appliqués ici, sur la liste puis sur
la fiche de chaque offre (voir `filtrage`).
"""

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import cast


from src.filtres import libelle_lieu, lieu_correspond, numero_departement_texte
from src.sources.base import CacheFiches
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.fiches import LECTEURS, lire_fiches
from src.sources.reseau import Session
from src.sources.passerellesmef.api import (
    construire_url_recherche,
    construire_url_resultats,
    envoyer_recherche,
    nouvelle_session,
    obtenir_fiche_offre,
    obtenir_formulaire,
    obtenir_page_recherche,
)
from src.sources.passerellesmef.extraction import (
    extraire_detail_offre,
    extraire_offres,
    extraire_totaux,
)
from src.sources.passerellesmef.formulaire import (
    analyser_formulaire,
    construire_recherche,
)
from src.sources.passerellesmef.filtrage import (
    extraire_fiche,
    fiche_correspond,
    fiche_necessaire,
    organisations_de_bercy,
)
from src.types import DetailOffre, FicheFiltrage, FiltresRecherche, Offre, PageAPI

journal = logging.getLogger(__name__)

MAX_PAGES = 20
MAX_PAGES_FILTREE = 100
"""Plafond quand des filtres s'appliquent après coup : lire tout le portail,
sinon les offres du lieu demandé pourraient se trouver au-delà de MAX_PAGES."""
_TAILLE_PAGE = 15
_DELAI_COURTOISIE = 0.3


class PasserellesMef:
    """Implémente :class:`~src.sources.base.SourceOffres` pour le portail
    Talentsoft des ministères économiques et financiers.

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

        Catégorie, domaine, organisation et région sont demandés au site
        quand ils s'y rattachent sans ambiguïté (voir `formulaire`) : il
        renvoie bien moins de pages et de fiches à lire. Le reste (département,
        expérience, management, télétravail) est appliqué ici, sur la liste
        puis sur la fiche. Les pages sont indépendantes (pas cumulatives,
        vérifié) et lues en parallèle ; la date de publication l'est par
        l'appelant."""
        organisations = filtres.get("organisations", [])
        if organisations and not organisations_de_bercy(organisations):
            return [], 1, False  # aucune organisation de ce portail demandée

        localisations = filtres.get("localisations", [])
        session = nouvelle_session()
        premiere, appliques = self._rechercher_sur_le_site(session, filtres)
        # Ce que le site a appliqué n'est pas revérifié sur les fiches.
        restants: FiltresRecherche = cast(
            FiltresRecherche,
            {c: v for c, v in filtres.items() if c not in appliques},
        )
        lire_les_fiches = fiche_necessaire(restants)
        offres, nb_pages, arret_anticipe = self._lire_liste(
            session,
            filtres.get("query", ""),
            (
                MAX_PAGES_FILTREE
                if localisations or lire_les_fiches or appliques
                else MAX_PAGES
            ),
            on_page,
            premiere,
        )
        if not (localisations or lire_les_fiches):
            return offres, nb_pages, arret_anticipe

        # Un lieu de la liste hors de la demande écarte l'offre sans lire sa
        # fiche ; sans numéro dans la liste, le lieu ne se lit que sur la fiche.
        offres = [
            o
            for o in offres
            if not localisations
            or not (numero := _numero_liste(o["localisation"]))
            or lieu_correspond(numero, localisations)
        ]
        fiches = lire_fiches(
            [
                o["url"]
                for o in offres
                if lire_les_fiches or not _numero_liste(o["localisation"])
            ],
            self._lire_fiche,
            self._cache_fiches,
            on_fiche,
        )
        retenues: list[Offre] = []
        for offre in offres:
            fiche = fiches.get(offre["url"])
            numero = _numero_liste(offre["localisation"])
            if fiche is not None:
                numero = numero or fiche["numero"]
                if not offre["localisation"] and numero:
                    offre["localisation"] = libelle_lieu(numero)
                if not fiche_correspond(fiche, restants):
                    continue
            if localisations and not lieu_correspond(numero, localisations):
                continue
            retenues.append(offre)
        return retenues, nb_pages, arret_anticipe

    @staticmethod
    def _rechercher_sur_le_site(
        session: Session, filtres: FiltresRecherche
    ) -> tuple[PageAPI | None, frozenset[str]]:
        """Première page des résultats filtrés par le site et critères qu'il
        a appliqués ; `(None, ∅)` si rien ne lui est demandé ou si le site
        n'a pas filtré (la recherche se fait alors par mot-clé seul)."""
        if not any(
            filtres.get(c)
            for c in ("categories", "domaines", "organisations", "localisations")
        ):
            return None, frozenset()
        formulaire = analyser_formulaire(obtenir_formulaire(session))
        if not formulaire.exploitable():
            journal.warning("Passerelles\u00a0: formulaire de recherche introuvable")
            return None, frozenset()
        champs, appliques = construire_recherche(
            formulaire,
            filtres,
            organisations_de_bercy(filtres.get("organisations", [])),
        )
        if not champs:
            return None, frozenset()
        champs.update(formulaire.caches)
        champs[formulaire.bouton[0]] = formulaire.bouton[1]
        reponse = envoyer_recherche(session, champs)
        if "Tout afficher" in reponse["title"]:
            journal.warning("Passerelles\u00a0: le site n'a pas appliqué les critères")
            return None, frozenset()
        return reponse, appliques

    def _lire_liste(
        self,
        session: Session,
        query: str,
        max_pages: int,
        on_page: Callable[[int, int], None] | None,
        premiere: PageAPI | None,
    ) -> tuple[list[Offre], int, bool]:
        """Pages de résultats, jusqu'à `max_pages` : celles du mot-clé, ou
        celles de la recherche déjà envoyée au site (`premiere`)."""
        url_page: Callable[[int], str]
        if premiere is None:
            reponse = obtenir_page_recherche(
                session, construire_url_recherche(query=query, page=1)
            )
            url_page = lambda numero: construire_url_recherche(query, numero)
        else:
            reponse = premiere
            url_page = construire_url_resultats
        nb_offres_total, _ = extraire_totaux(reponse.get("title", ""))
        nb_pages = max(1, -(-nb_offres_total // _TAILLE_PAGE))
        pages_a_charger = min(nb_pages, max_pages)

        toutes_offres = extraire_offres(reponse.get("html", ""))
        if on_page:
            on_page(1, pages_a_charger)

        verrou = threading.Lock()
        lues = [1]

        def _page(numero: int) -> list[Offre]:
            time.sleep(_DELAI_COURTOISIE)
            offres_page = extraire_offres(
                obtenir_page_recherche(session, url_page(numero)).get("html", "")
            )
            with verrou:
                lues[0] += 1
                if on_page:
                    on_page(lues[0], pages_a_charger)
            return offres_page

        with ThreadPoolExecutor(max_workers=LECTEURS) as pool:
            pages = list(pool.map(_page, range(2, pages_a_charger + 1)))
        for offres_page in pages:
            if not offres_page:
                return toutes_offres, nb_pages, True
            toutes_offres.extend(offres_page)
        return toutes_offres, nb_pages, pages_a_charger < nb_pages

    @staticmethod
    def _lire_fiche(url: str) -> FicheFiltrage | None:
        return extraire_fiche(recuperer_detail_offre(url))


def _numero_liste(localisation: str) -> str:
    """Numéro de département du lieu affiché dans la liste, vide s'il n'y en a pas."""
    return numero_departement_texte(localisation) or ""


def recuperer_detail_offre(url: str) -> DetailOffre:
    """Récupère et extrait le détail structuré d'une offre Passerelles/MEF.

    Ne lève jamais d'exception : retourne un `DetailOffre` vide si le
    téléchargement échoue.
    """
    session = nouvelle_session()
    try:
        html = obtenir_fiche_offre(session, url)
    except RuntimeError:
        return DETAIL_VIDE
    return extraire_detail_offre(html)
