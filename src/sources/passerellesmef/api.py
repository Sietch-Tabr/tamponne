"""Client HTTP — passerelles.economie.gouv.fr (Talentsoft, Bercy).

Pas de WAF sur ce site (contrairement à emploi-territorial.fr) : un
User-Agent identifié classique suffit, comme choisirleservicepublic.
"""

import re
import urllib.parse

from src.sources.base import USER_AGENT_IDENTIFIE
from src.sources.reseau import Session
from src.types import PageAPI

URL_SITE = "https://www.passerelles.economie.gouv.fr"
URL_LISTE = f"{URL_SITE}/offre-de-emploi/liste-toutes-offres.aspx"
URL_RESULTATS = f"{URL_SITE}/offre-de-emploi/liste-offres.aspx"

_HEADERS = {
    "User-Agent": USER_AGENT_IDENTIFIE,
    "Accept-Language": "fr-FR,fr;q=0.9",
}


def nouvelle_session() -> Session:
    """Session dédiée à une recherche. Les cookies servent à la recherche
    par formulaire : le site garde les critères dans la session et les
    pages de résultats les lui demandent."""
    return Session(_HEADERS)


def construire_url_recherche(query: str = "", page: int = 1) -> str:
    """Construit l'URL de recherche (vérifié empiriquement : `Keywords`
    filtre bien, `page` n'est pas cumulatif contrairement au territorial)."""
    params: list[tuple[str, str]] = [("LCID", "1036"), ("showSearchUrl", "1")]
    if query:
        params.append(("Keywords", query))
    if page > 1:
        params.append(("page", str(page)))
    return f"{URL_LISTE}?{urllib.parse.urlencode(params)}"


def obtenir_page_recherche(session: Session, url: str) -> PageAPI:
    """Télécharge une page de résultats — le titre contient le total
    annoncé (`"... (N offres, page P) ..."`)."""
    html = session.lire(url).texte()
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    return {"html": html, "title": title_m.group(1).strip() if title_m else ""}


def obtenir_fiche_offre(session: Session, url: str) -> str:
    """Télécharge le HTML complet d'une fiche offre."""
    return session.lire(url).texte()


def obtenir_formulaire(session: Session) -> str:
    """Télécharge la page de recherche : son formulaire (jetons et champs)
    et la session dont l'envoi dépend."""
    return session.lire(construire_url_recherche()).texte()


def construire_url_resultats(page: int) -> str:
    """URL d'une page des résultats de la dernière recherche envoyée dans la
    session (les pages sont indépendantes, vérifié)."""
    return f"{URL_RESULTATS}?{urllib.parse.urlencode({'LCID': '1036', 'page': page})}"


def envoyer_recherche(session: Session, champs: dict[str, str]) -> PageAPI:
    """Envoie le formulaire de recherche ; la réponse est la première page
    des résultats (même forme que `obtenir_page_recherche`)."""
    url = construire_url_recherche()
    html = session.lire(url, champs).texte()
    title_m = re.search(r"<title>(.*?)</title>", html, re.S)
    return {"html": html, "title": title_m.group(1).strip() if title_m else ""}
