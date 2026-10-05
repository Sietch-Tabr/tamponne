"""Client HTTP — passerelles.economie.gouv.fr (Talentsoft, Bercy).

Pas de WAF sur ce site (contrairement à emploi-territorial.fr) : un
User-Agent identifié classique suffit, comme choisirleservicepublic.
"""

import re
import urllib.error
import urllib.parse
import urllib.request

from src.sources.base import USER_AGENT_IDENTIFIE
from src.types import PageAPI

URL_SITE = "https://www.passerelles.economie.gouv.fr"
URL_LISTE = f"{URL_SITE}/offre-de-emploi/liste-toutes-offres.aspx"

_TIMEOUT = 30
_HEADERS = {
    "User-Agent": USER_AGENT_IDENTIFIE,
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def nouvelle_session() -> urllib.request.OpenerDirector:
    """Session dédiée à une recherche — même interface que les autres
    sources, pas de dépendance de session serveur ici (recherche par
    GET stateless)."""
    return urllib.request.build_opener()


def _requete(opener: urllib.request.OpenerDirector, url: str) -> str:
    requete = urllib.request.Request(url, headers=_HEADERS)
    try:
        with opener.open(requete, timeout=_TIMEOUT) as reponse:
            return reponse.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Erreur HTTP {e.code} lors du chargement de {url}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Erreur réseau lors du chargement de {url}\u00a0: {e.reason}"
        ) from e


def construire_url_recherche(query: str = "", page: int = 1) -> str:
    """Construit l'URL de recherche (vérifié empiriquement : `Keywords`
    filtre bien, `page` n'est pas cumulatif contrairement au territorial)."""
    params: list[tuple[str, str]] = [("LCID", "1036"), ("showSearchUrl", "1")]
    if query:
        params.append(("Keywords", query))
    if page > 1:
        params.append(("page", str(page)))
    return f"{URL_LISTE}?{urllib.parse.urlencode(params)}"


def obtenir_page_recherche(opener: urllib.request.OpenerDirector, url: str) -> PageAPI:
    """Télécharge une page de résultats — le titre contient le total
    annoncé (`"... (N offres, page P) ..."`)."""
    html = _requete(opener, url)
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    return {"html": html, "title": title_m.group(1).strip() if title_m else ""}


def obtenir_fiche_offre(opener: urllib.request.OpenerDirector, url: str) -> str:
    """Télécharge le HTML complet d'une fiche offre."""
    return _requete(opener, url)
