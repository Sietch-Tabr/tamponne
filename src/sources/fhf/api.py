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
    (
        "01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 2A 2B 21 22 23 24 25 "
        "26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 "
        "52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 "
        "78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 971 972 973 974 976 "
        "987 988"
    ).split()
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
