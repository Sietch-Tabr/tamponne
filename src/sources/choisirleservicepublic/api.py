"""Client API — requêtes GET filtrées (format WordPress rewrite URL)."""

import re
import urllib.parse

from src.filtres import VALEUR_TOGGLE_ACTIF
from src.sources.base import USER_AGENT_IDENTIFIE
from src.sources.reseau import Session
from src.types import PageAPI

URL_SITE = "https://choisirleservicepublic.gouv.fr"
URL_OFFRES = f"{URL_SITE}/nos-offres/"

_HEADERS = {"User-Agent": USER_AGENT_IDENTIFIE}

# Ordre et nommage des filtres dans l'URL WordPress (issu de url_keywords côté JS)
_URL_KEYWORD_MAP = [
    ("locations", "localisation"),
    ("domaines", "domaine"),
    ("versants", "versant"),
    ("categories", "categorie"),
    ("organisations", "organisme"),
    ("types_poste", "type"),
]


def construire_url_filtres(
    query: str = "",
    categories: list[int] | None = None,
    locations: list[int] | None = None,
    organisations: list[int] | None = None,
    versants: list[int] | None = None,
    domaines: list[int] | None = None,
    types_poste: list[int] | None = None,
    experience: int | None = None,
    date_publication: str | None = None,
    management: bool = False,
    teletravail: bool = False,
    page: int = 1,
) -> str:
    """Construit l'URL de recherche filtrée au format WordPress rewrite."""
    params = {
        "locations": locations or [],
        "domaines": domaines or [],
        "versants": versants or [],
        "categories": categories or [],
        "organisations": organisations or [],
        "types_poste": types_poste or [],
    }

    filtres_url = ""
    if query:
        query_sanitise = query.replace("/", "---")
        filtres_url += f"mot-cles/{urllib.parse.quote(query_sanitise, safe='')}/"
    for key, url_key in _URL_KEYWORD_MAP:
        ids = params[key]
        if ids:
            filtres_url += f"{url_key}/{'-'.join(str(i) for i in ids)}/"
    # Ordre imposé par les rewrite rules WordPress (issu de url_keywords côté JS) :
    # ces segments doivent venir après type/ et dans cet ordre précis.
    if management:
        filtres_url += f"management/{VALEUR_TOGGLE_ACTIF}/"
    if teletravail:
        filtres_url += f"teletravail/{VALEUR_TOGGLE_ACTIF}/"
    if experience:
        filtres_url += f"experience/{experience}/"
    if date_publication:
        filtres_url += f"date-de-publication/{date_publication}/"

    url = URL_OFFRES
    if filtres_url:
        url += f"filtres/{filtres_url}"
    if page > 1:
        url += f"page/{page}/"
    return url


def obtenir_page_offres(url: str) -> PageAPI:
    """Télécharge une page de résultats et retourne {html, title}.

    Args:
        url: URL complète de la page à télécharger (format WordPress rewrite).

    Returns:
        Dictionnaire avec les clés ``html`` (contenu brut de la page) et
        ``title`` (contenu de la balise ``<title>``, chaîne vide si absente).

    Raises:
        RuntimeError: Si le serveur retourne un code HTTP d'erreur, ou si la
            connexion échoue pour une raison réseau.
    """
    contenu = Session(_HEADERS).lire(url).texte()
    title_m = re.search(r"<title>(.*?)</title>", contenu)
    return {
        "html": contenu,
        "title": title_m.group(1) if title_m else "",
    }


def telecharger_binaire(url: str) -> bytes:
    """Télécharge le contenu binaire d'une URL (ex. PDF officiel d'une offre)."""
    return Session(_HEADERS).lire(url).corps


def telecharger_page_offres() -> str:
    """Télécharge le HTML brut de /nos-offres/ (pour le cache organisations)."""
    return Session(_HEADERS).lire(URL_OFFRES).texte()
