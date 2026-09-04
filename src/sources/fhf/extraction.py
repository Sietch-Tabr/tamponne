"""Extraction des offres et fiches détail — HTML de emploi.fhf.fr."""

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from src.types import DetailOffre, Offre

_DOMAINE_AUTORISE = "emploi.fhf.fr"
_URL_BASE = "https://emploi.fhf.fr"
SOURCE_LABEL = "FHF"

_RE_ESPACES = re.compile(r"\s+")
_RE_VILLE = re.compile(r"\(([^)]+)\)\s*$")
_RE_DATE_PUBLICATION_CARTE = re.compile(r"Publié le (\d{2})\.(\d{2})\.(\d{4})")
_RE_URL = re.compile(r"https?://\S+")


def _texte_normalise(tag: Tag) -> str:
    return _RE_ESPACES.sub(" ", tag.get_text(" ", strip=True)).strip()


def _valider_url(url: str) -> str:
    if url.startswith("/"):
        return f"{_URL_BASE}{url}"
    if url.startswith(("https://", "http://")):
        domaine = urlparse(url).netloc
        if domaine == _DOMAINE_AUTORISE or domaine.endswith(f".{_DOMAINE_AUTORISE}"):
            return url
    return ""


def extraire_offres(html: str) -> list[Offre]:
    """Extrait les offres d'une page de résultats.

    L'employeur affiché inclut la ville entre parenthèses
    (`"Centre hospitalier  (Carcassonne)"`) — séparée ici en
    `employeur`/`localisation`, réutilisée telle quelle par le
    dédoublonnage flou (pas besoin de recharger la fiche détail)."""
    soup = BeautifulSoup(html, "html.parser")
    offres: list[Offre] = []

    for carte in soup.find_all("article", class_="card-offer"):
        titre_tag = carte.find("h3", class_="card-title")
        lien = carte.find("a", class_="btn-link")
        if not isinstance(titre_tag, Tag) or not isinstance(lien, Tag):
            continue
        url = _valider_url(str(lien.get("href", "")))
        if not url:
            continue

        id_m = re.search(r"/emploi/(\d+)", url)
        reference = f"FHF_{id_m.group(1)}" if id_m else ""

        etablissement_tag = carte.find("div", class_="field--name-field-establishment")
        employeur = localisation = ""
        if isinstance(etablissement_tag, Tag):
            texte = _texte_normalise(etablissement_tag)
            ville_m = _RE_VILLE.search(texte)
            if ville_m:
                localisation = ville_m.group(1).strip()
                employeur = texte[: ville_m.start()].strip()
            else:
                employeur = texte

        date = ""
        date_tag = carte.find("div", class_="field--name-field-publish-date")
        if isinstance(date_tag, Tag):
            date_m = _RE_DATE_PUBLICATION_CARTE.search(date_tag.get_text())
            if date_m:
                date = f"{date_m.group(1)}/{date_m.group(2)}/{date_m.group(3)}"

        offres.append(
            {
                "titre": _texte_normalise(titre_tag),
                "url": url,
                "reference": reference,
                "domaine": "",
                "employeur": employeur,
                "localisation": localisation,
                "versant": "Fonction publique Hospitalière",
                "date": date,
                "source": SOURCE_LABEL,
            }
        )
    return offres


def _extraire_champs(soup: BeautifulSoup) -> dict[str, str]:
    """Paires libellé → valeur de la fiche détail (`div.section >
    div.section-title` + reste du texte du bloc)."""
    champs: dict[str, str] = {}
    conteneur = soup.find("article", class_="offer") or soup
    if not isinstance(conteneur, Tag):
        return champs

    for bloc in conteneur.find_all("div", class_="section"):
        titre = bloc.find("div", class_="section-title")
        if not isinstance(titre, Tag):
            continue
        label = titre.get_text(strip=True)
        titre.extract()
        valeur = _texte_normalise(bloc)
        if label and valeur:
            champs[label] = valeur
    return champs


def _extraire_date_publication(soup: BeautifulSoup) -> str:
    bloc = soup.find("div", class_="publication-info")
    if not isinstance(bloc, Tag):
        return ""
    return bloc.get_text(strip=True).replace("Publié le", "").strip()


def _extraire_lien_postuler(contact: str) -> str:
    m = _RE_URL.search(contact)
    return m.group(0) if m else ""


def extraire_detail_offre(html: str) -> DetailOffre:
    """Extrait le détail structuré d'une fiche — jamais d'exception, un
    champ manquant reste vide."""
    soup = BeautifulSoup(html, "html.parser")
    champs = _extraire_champs(soup)

    _DEDIES = {"poste proposé", "descriptif"}
    sections_complementaires = {
        label: valeur
        for label, valeur in champs.items()
        if label.lower() not in _DEDIES
    }

    return {
        "description": champs.get("Descriptif", ""),
        "salaire": champs.get("Rémunération", ""),
        "experience_requise": "",
        "formation_requise": "",
        "secteur": "",
        "date_publication": _extraire_date_publication(soup),
        "a_propos_employeur": "",
        "sections_complementaires": sections_complementaires,
        "page_html": html,
        "lien_postuler": _extraire_lien_postuler(
            champs.get("Personne à contacter", "")
        ),
        "date_limite": champs.get("Date limite", ""),
    }
