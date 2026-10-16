"""Client HTTP — emploi.fhf.fr (Fédération Hospitalière de France).

Pas de WAF sur ce site : un User-Agent identifié classique suffit,
comme choisirleservicepublic. Pagination GET simple, page 0-indexée.
"""

import re
import urllib.parse

from src.sources.base import USER_AGENT_IDENTIFIE
from src.sources.reseau import Session
from src.types import PageAPI

URL_SITE = "https://emploi.fhf.fr"
URL_RECHERCHE = f"{URL_SITE}/emploi/search"

_HEADERS = {
    "User-Agent": USER_AGENT_IDENTIFIE,
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def nouvelle_session() -> Session:
    """Session dédiée à une recherche (les connexions sont partagées)."""
    return Session(_HEADERS)


DEPARTEMENTS_SITE = frozenset(
    [
        *(f"{n:02d}" for n in range(1, 96) if n != 20),
        "2A",
        "2B",
        "971",
        "972",
        "973",
        "974",
        "976",
        "987",
        "988",
    ]
)
"""Départements de la liste de choix du site (relevés le 2026-10-16) : un autre
numéro n'a aucune offre FHF."""


def construire_url_recherche(
    query: str = "", page: int = 0, departement: str = ""
) -> str:
    """Construit l'URL de recherche (page 0-indexée, vérifié empiriquement :
    `keyword` et `department` filtrent bien les résultats)."""
    params: list[tuple[str, str]] = []
    if departement:
        params.append(("department", departement))
    if query:
        params.append(("keyword", query))
    if page:
        params.append(("page", str(page)))
    if not params:
        return URL_RECHERCHE
    return f"{URL_RECHERCHE}?{urllib.parse.urlencode(params)}"


def obtenir_page_recherche(session: Session, url: str) -> PageAPI:
    """Télécharge une page de résultats."""
    html = session.lire(url).texte()
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    return {"html": html, "title": title_m.group(1).strip() if title_m else ""}


def obtenir_fiche_offre(session: Session, url: str) -> str:
    """Télécharge le HTML complet d'une fiche offre."""
    return session.lire(url).texte()
