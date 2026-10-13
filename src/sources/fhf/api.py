"""Client HTTP — emploi.fhf.fr (Fédération Hospitalière de France).

Pas de WAF sur ce site : un User-Agent identifié classique suffit,
comme choisirleservicepublic. Pagination GET simple, page 0-indexée.
"""

import re
lazy import urllib.error
import urllib.parse
lazy import urllib.request

from src.sources.base import USER_AGENT_IDENTIFIE
from src.types import PageAPI

URL_SITE = "https://emploi.fhf.fr"
URL_RECHERCHE = f"{URL_SITE}/emploi/search"

_TIMEOUT = 30
_HEADERS = {
    "User-Agent": USER_AGENT_IDENTIFIE,
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def nouvelle_session() -> urllib.request.OpenerDirector:
    """Session dédiée à une recherche — pas de dépendance de session
    serveur ici (recherche par GET stateless)."""
    return urllib.request.build_opener()


def _requete(opener: urllib.request.OpenerDirector, url: str) -> str:
    requete = urllib.request.Request(url, headers=_HEADERS)
    try:
        with opener.open(requete, timeout=_TIMEOUT) as reponse:
            return reponse.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Erreur HTTP {e.code} lors du chargement de {url}") from e
    # Délai dépassé en pleine lecture : TimeoutError, pas URLError.
    except OSError as e:
        raise RuntimeError(
            f"Erreur réseau lors du chargement de {url}\u00a0: {getattr(e, 'reason', e)}"
        ) from e


def construire_url_recherche(query: str = "", page: int = 0) -> str:
    """Construit l'URL de recherche (page 0-indexée, vérifié empiriquement :
    `keyword` filtre bien les résultats)."""
    params: list[tuple[str, str]] = []
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
