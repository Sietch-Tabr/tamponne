"""Client HTTP — passerelles.economie.gouv.fr (Talentsoft, Bercy).

Pas de WAF sur ce site (contrairement à emploi-territorial.fr) : un
User-Agent identifié classique suffit, comme choisirleservicepublic.
"""

import re
lazy import http.cookiejar
lazy import urllib.error
import urllib.parse
lazy import urllib.request

from src.sources.base import (
    EN_TETE_COMPRESSION,
    USER_AGENT_IDENTIFIE,
    lire_texte,
)
from src.types import PageAPI

URL_SITE = "https://www.passerelles.economie.gouv.fr"
URL_LISTE = f"{URL_SITE}/offre-de-emploi/liste-toutes-offres.aspx"
URL_RESULTATS = f"{URL_SITE}/offre-de-emploi/liste-offres.aspx"

_TIMEOUT = 30
_HEADERS = {
    "User-Agent": USER_AGENT_IDENTIFIE,
    "Accept-Language": "fr-FR,fr;q=0.9",
    **EN_TETE_COMPRESSION,
}


def nouvelle_session() -> urllib.request.OpenerDirector:
    """Session dédiée à une recherche. Les cookies servent à la recherche
    par formulaire : le site garde les critères dans la session et les
    pages de résultats les lui demandent."""
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )


def _requete(
    opener: urllib.request.OpenerDirector, url: str, donnees: bytes | None = None
) -> str:
    requete = urllib.request.Request(url, data=donnees, headers=_HEADERS)
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


def obtenir_formulaire(opener: urllib.request.OpenerDirector) -> str:
    """Télécharge la page de recherche : son formulaire (jetons et champs)
    et la session dont l'envoi dépend."""
    return _requete(opener, construire_url_recherche())


def construire_url_resultats(page: int) -> str:
    """URL d'une page des résultats de la dernière recherche envoyée dans la
    session (les pages sont indépendantes, vérifié)."""
    return f"{URL_RESULTATS}?{urllib.parse.urlencode({'LCID': '1036', 'page': page})}"


def envoyer_recherche(
    opener: urllib.request.OpenerDirector, champs: dict[str, str]
) -> PageAPI:
    """Envoie le formulaire de recherche ; la réponse est la première page
    des résultats (même forme que `obtenir_page_recherche`)."""
    url = construire_url_recherche()
    html = _requete(opener, url, urllib.parse.urlencode(champs).encode())
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    return {"html": html, "title": title_m.group(1).strip() if title_m else ""}
