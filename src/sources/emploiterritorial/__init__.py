"""Source emploi-territorial.fr — implémente `SourceOffres`.

Portail légal CDG/CNFPT de la fonction publique territoriale. Câblés côté
filtres : mot-clé libre, catégorie, département (une région ou le groupement
DOM est remplacé par ses départements, voir `filtres.codes_departements`),
expérience, management, télétravail, et le
type de poste dans le seul cas net « titulaire uniquement ». Filière et
cadre d'emplois/grade fonctionnent côté site (vérifié) mais restent à
mapper, ignorés silencieusement en attendant plutôt que mappés à l'aveugle.
"""

import time
from collections.abc import Callable

from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.emploiterritorial.api import (
    construire_url_recherche,
    nouvelle_session,
    obtenir_fiche_offre,
    obtenir_page_recherche,
    obtenir_page_suivante,
)
from src.sources.emploiterritorial.extraction import (
    extraire_detail_offre,
    extraire_offres,
    extraire_totaux,
)
from src.sources.emploiterritorial.filtres import (
    CATEGORIES,
    EXPERIENCES,
    TYPE_CONTRAT_TITULAIRE,
    codes_departements,
)
from src.types import DetailOffre, FiltresRecherche, Offre

MAX_PAGES = 20
# WAF actif sur ce site : délai plus prudent que les 0.5s de choisirleservicepublic.
_DELAI_COURTOISIE = 1.0


class EmploiTerritorial:
    """Implémente :class:`~src.sources.base.SourceOffres` pour le portail
    légal de la fonction publique territoriale."""

    def rechercher(
        self,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        """Voir :meth:`SourceOffres.rechercher`.

        Un seul appel de pagination suffit, quel que soit le nombre de
        pages à charger : la réponse à `page=N` contient cumulativement
        toutes les lignes de la page 1 à N (vérifié empiriquement — pas
        une requête par page, plus poli envers le WAF actif sur ce site).
        """
        categories = [
            CATEGORIES[c] for c in filtres.get("categories", []) if c in CATEGORIES
        ]
        localisations = filtres.get("localisations", [])
        departements = codes_departements(localisations)
        if localisations and not departements:
            return [], 1, False  # lieux sans équivalent : ne rien montrer d'ailleurs
        experience = EXPERIENCES.get(filtres.get("experience") or "", "")
        # Seul « titulaire uniquement » a un équivalent net côté ET (Emploi
        # permanent) ; les autres choix n'ont pas de code unique : non filtrés.
        type_contrat = (
            TYPE_CONTRAT_TITULAIRE
            if filtres.get("types_poste") == ["titulaire"]
            else ""
        )

        opener = nouvelle_session()
        url = construire_url_recherche(
            query=filtres.get("query", ""),
            categories=categories,
            departements=departements,
            experience=experience,
            management=bool(filtres.get("management")),
            teletravail=bool(filtres.get("teletravail")),
            type_contrat=type_contrat,
        )

        reponse = obtenir_page_recherche(opener, url)
        html = reponse.get("html", "")
        nb_offres_total, taille_page = extraire_totaux(html)
        taille_page = taille_page or 20
        nb_pages = max(1, -(-nb_offres_total // taille_page))

        if nb_pages <= 1:
            if on_page:
                on_page(1, 1)
            return extraire_offres(html), nb_pages, False

        pages_a_charger = min(nb_pages, MAX_PAGES)
        if on_page:
            on_page(1, pages_a_charger)
        time.sleep(_DELAI_COURTOISIE)
        html_cumule = obtenir_page_suivante(opener, pages_a_charger)
        toutes_offres = extraire_offres(html_cumule)
        if on_page:
            on_page(pages_a_charger, pages_a_charger)

        # Anomalie réelle seulement si on visait tout (pas plafonné par
        # MAX_PAGES) et qu'il manque des offres par rapport au total annoncé.
        attendu = min(pages_a_charger * taille_page, nb_offres_total)
        arret_anticipe = pages_a_charger >= nb_pages and len(toutes_offres) < attendu
        return toutes_offres, nb_pages, arret_anticipe


def recuperer_detail_offre(url: str) -> DetailOffre:
    """Récupère et extrait le détail structuré d'une offre territoriale.

    Ne lève jamais d'exception : retourne un `DetailOffre` vide si le
    téléchargement échoue.
    """
    opener = nouvelle_session()
    try:
        html = obtenir_fiche_offre(opener, url)
    except RuntimeError:
        return DETAIL_VIDE
    return extraire_detail_offre(html)
