"""Détail et disponibilité d'une offre, selon le site qui la publie.

Chaque source extrait sa propre fiche : la lire avec l'extracteur d'un autre
site donne une fiche vide. Le site est reconnu au domaine de l'URL.
"""

from collections.abc import Callable
from urllib.parse import urlparse

from src.sources import choisirleservicepublic, emploiterritorial, fhf, passerellesmef
from src.sources.base import PageIntrouvable, consulter_page, sur_domaine
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.choisirleservicepublic.extraction import DOMAINE as DOMAINE_CSP
from src.sources.emploiterritorial.extraction import DOMAINE as DOMAINE_TERRITORIAL
from src.sources.fhf.extraction import DOMAINE as DOMAINE_FHF
from src.sources.passerellesmef.extraction import DOMAINE as DOMAINE_PASSERELLES
from src.types import DetailOffre

_DETAIL_PAR_DOMAINE: tuple[tuple[str, Callable[[str], DetailOffre]], ...] = (
    (DOMAINE_CSP, choisirleservicepublic.recuperer_detail_offre),
    (DOMAINE_TERRITORIAL, emploiterritorial.recuperer_detail_offre),
    (DOMAINE_FHF, fhf.recuperer_detail_offre),
    (DOMAINE_PASSERELLES, passerellesmef.recuperer_detail_offre),
)

MARQUEUR_OFFRE_DEPUBLIEE = "Offre dépubliée"
"""Titre de la page vers laquelle choisirleservicepublic redirige une offre
retirée (`/offre-depubliee/`)."""
PAGE_ACCUEIL_PASSERELLES = "/accueil.aspx"
"""Passerelles redirige une offre retirée vers son accueil (constaté le
2026-10-13) ; emploi-territorial et FHF répondent 404."""


def recuperer_detail_offre(url: str) -> DetailOffre:
    """Fiche détaillée de l'offre `url`, lue par l'extracteur de son site.

    Ne lève jamais d'exception : fiche vide si le site n'est pas une source
    connue ou si le téléchargement échoue.
    """
    for domaine, recuperer in _DETAIL_PAR_DOMAINE:
        if sur_domaine(url, domaine):
            return recuperer(url)
    return DETAIL_VIDE


def verifier_disponibilite(url: str) -> bool:
    """Vrai si l'offre `url` est toujours en ligne, faux si le site la dit
    retirée (404/410, page « Offre dépubliée », retour à l'accueil de
    Passerelles).

    Raises:
        RuntimeError: Site injoignable ou erreur inattendue : on ne sait
            pas, le statut stocké ne doit pas être modifié.
    """
    try:
        url_finale, titre = consulter_page(url)
    except PageIntrouvable:
        return False
    if MARQUEUR_OFFRE_DEPUBLIEE in titre:
        return False
    chemin_final = urlparse(url_finale).path.lower()
    return not (
        sur_domaine(url, DOMAINE_PASSERELLES)
        and chemin_final.endswith(PAGE_ACCUEIL_PASSERELLES)
    )
