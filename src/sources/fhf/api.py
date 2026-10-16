"""Client HTTP — emploi.fhf.fr (Fédération Hospitalière de France).

Pas de WAF sur ce site : un User-Agent identifié classique suffit,
comme choisirleservicepublic. Pagination GET simple, page 0-indexée.
"""

import re
lazy import urllib.error
import urllib.parse
lazy import urllib.request

from src.sources.base import (
    EN_TETE_COMPRESSION,
    USER_AGENT_IDENTIFIE,
    lire_texte,
)
from src.types import PageAPI

URL_SITE = "https://emploi.fhf.fr"
URL_RECHERCHE = f"{URL_SITE}/emploi/search"

_TIMEOUT = 30
_HEADERS = {
    "User-Agent": USER_AGENT_IDENTIFIE,
    "Accept-Language": "fr-FR,fr;q=0.9",
    **EN_TETE_COMPRESSION,
}


def nouvelle_session() -> urllib.request.OpenerDirector:
    """Session dédiée à une recherche — pas de dépendance de session
    serveur ici (recherche par GET stateless)."""
    return urllib.request.build_opener()


def _requete(opener: urllib.request.OpenerDirector, url: str) -> str:
    requete = urllib.request.Request(url, headers=_HEADERS)
    try:
        with opener.open(requete, timeout=_TIMEOUT) as reponse:
            return lire_texte(reponse)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Erreur HTTP {e.code} lors du chargement de {url}") from e
    # Délai dépassé en pleine lecture : TimeoutError, pas URLError.
    except OSError as e:
        raise RuntimeError(
            f"Erreur réseau lors du chargement de {url}\u00a0: {getattr(e, 'reason', e)}"
        ) from e


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


def obtenir_page_recherche(opener: urllib.request.OpenerDirector, url: str) -> PageAPI:
    """Télécharge une page de résultats."""
    html = _requete(opener, url)
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    return {"html": html, "title": title_m.group(1).strip() if title_m else ""}


def obtenir_fiche_offre(opener: urllib.request.OpenerDirector, url: str) -> str:
    """Télécharge le HTML complet d'une fiche offre."""
    return _requete(opener, url)
