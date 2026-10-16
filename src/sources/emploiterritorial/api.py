"""Client HTTP — emploi-territorial.fr (session PHP + pagination AJAX).

Recherche initiale en GET, pose le filtre côté session serveur
(PHPSESSID). Pagination en POST sur un endpoint séparé, sans renvoyer
le filtre — la session doit être conservée entre les deux appels.

WAF F5 BIG-IP actif sur ce site : un User-Agent identifié (comme pour
choisirleservicepublic) y est bloqué, un User-Agent de navigateur est
nécessaire pour passer.
"""

import re
import urllib.parse

from src.sources.emploiterritorial.filtres import VALEUR_OUI
from src.sources.reseau import Session
from src.types import PageAPI

URL_SITE = "https://www.emploi-territorial.fr"
URL_RECHERCHE = f"{URL_SITE}/rechercher"
URL_PAGINATION = f"{URL_SITE}/recherche_emploi_mobilite/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def nouvelle_session() -> Session:
    """Session dédiée à une recherche — à ne jamais partager entre deux
    recherches (le filtre est gardé côté session serveur)."""
    return Session(_HEADERS)


def construire_url_recherche(
    query: str = "",
    filiere: str = "",
    departements: list[str] | None = None,
    categories: list[str] | None = None,
    experience: str = "",
    management: bool = False,
    teletravail: bool = False,
    type_contrat: str = "",
) -> str:
    """Construit l'URL de recherche initiale (segments GET vérifiés
    empiriquement — encodage à crochets pour le formulaire brut).

    Args:
        categories: Codes `search_offre_form[searchcat][]` (ex. "A+", "A").
        experience: Code `search_offre_form[experience][]` ("1"/"2"/"3").
        management: Champ à bascule Oui/Non, absent de l'URL si False.
        teletravail: Champ à bascule Oui/Non, absent de l'URL si False.
        type_contrat: Code `search_offre_form[searchtypecontrat][]`.
    """
    params: list[tuple[str, str]] = []
    if filiere:
        params.append(("search-filiere", filiere))
    if query:
        params.append(("search_offre_form[advsearch]", query))
    for departement in departements or []:
        params.append(("search_offre_form[searchdept][]", departement))
    for categorie in categories or []:
        params.append(("search_offre_form[searchcat][]", categorie))
    if experience:
        params.append(("search_offre_form[experience][]", experience))
    if management:
        params.append(("search_offre_form[management]", VALEUR_OUI))
    if teletravail:
        params.append(("search_offre_form[teletravail]", VALEUR_OUI))
    if type_contrat:
        params.append(("search_offre_form[searchtypecontrat][]", type_contrat))
    if not params:
        return URL_RECHERCHE
    return f"{URL_RECHERCHE}?{urllib.parse.urlencode(params)}"


def obtenir_page_recherche(session: Session, url: str) -> PageAPI:
    """Requête initiale — pose la recherche côté session serveur."""
    html = session.lire(url).texte()
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    return {"html": html, "title": title_m.group(1).strip() if title_m else ""}


def obtenir_page_suivante(session: Session, page: int) -> str:
    """Page suivante de la recherche en cours (même session) — retourne
    un fragment HTML brut (`<tr>` à ajouter), pas du JSON."""
    return session.lire(URL_PAGINATION, {"page": str(page), "ajax": "1"}).texte()


def obtenir_fiche_offre(session: Session, url: str) -> str:
    """Télécharge le HTML complet d'une fiche offre."""
    return session.lire(url).texte()
