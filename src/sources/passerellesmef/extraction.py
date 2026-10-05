"""Extraction des offres et fiches détail — HTML de passerelles.economie.gouv.fr."""

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from src.types import DetailOffre, Offre

_DOMAINE_AUTORISE = "passerelles.economie.gouv.fr"
_URL_BASE = "https://www.passerelles.economie.gouv.fr"
SOURCE_LABEL = "MEF"

_RE_TOTAUX = re.compile(r"\((\d+) offres, page (\d+)\)")
_RE_ESPACES = re.compile(r"\s+")


def _texte_normalise(texte: str) -> str:
    return _RE_ESPACES.sub(" ", texte).strip()


def _valider_url(url: str) -> str:
    if url.startswith("/"):
        return f"{_URL_BASE}{url}"
    if url.startswith(("https://", "http://")):
        domaine = urlparse(url).netloc
        if domaine == _DOMAINE_AUTORISE or domaine.endswith(f".{_DOMAINE_AUTORISE}"):
            return url
    return ""


def extraire_totaux(titre: str) -> tuple[int, int]:
    """(nb_offres_total, page_courante) depuis le `<title>` de la page
    (`"... (N offres, page P) ..."`) — 15 offres/page, constaté."""
    m = _RE_TOTAUX.search(titre)
    if not m:
        return 0, 1
    return int(m.group(1)), int(m.group(2))


def extraire_offres(html: str) -> list[Offre]:
    """Extrait les offres d'une page de résultats."""
    soup = BeautifulSoup(html, "html.parser")
    offres: list[Offre] = []

    for carte in soup.find_all("div", class_="ts-offer-card"):
        lien = carte.find("a", class_="ts-offer-card__title-link")
        if not isinstance(lien, Tag):
            continue
        url = _valider_url(str(lien.get("href", "")))
        if not url:
            continue
        titre = lien.get_text(strip=True)

        ref_tag = carte.select_one("[data-reference]")
        reference = str(ref_tag.get("data-reference", "")) if ref_tag else ""

        date = employeur = localisation = ""
        items = carte.find("ul", class_="ts-offer-card-content__list")
        if isinstance(items, Tag):
            li = items.find_all("li")
            if len(li) >= 4:
                date = li[1].get_text(strip=True)
                employeur = li[2].get_text(strip=True)
                localisation = li[3].get_text(strip=True)

        offres.append(
            {
                "titre": titre,
                "url": url,
                "reference": reference,
                "domaine": "",
                "employeur": employeur,
                "localisation": localisation,
                "versant": "Fonction publique de l'État",
                "date": date,
                "source": SOURCE_LABEL,
            }
        )
    return offres


def _extraire_champs(soup: BeautifulSoup) -> dict[str, str]:
    """Paires libellé → valeur de la fiche détail — deux structures
    présentes sur cette page : `<div><h3>Label</h3>Texte</div>` (bloc
    infos générales) et `<h3>Label</h3><p ou div>Texte</p>` (siblings,
    reste de la page)."""
    champs: dict[str, str] = {}
    conteneur = soup.find(id="contenu-ficheoffre") or soup
    if not isinstance(conteneur, Tag):
        return champs

    for h3 in conteneur.find_all("h3"):
        label = h3.get_text(strip=True)
        if not label:
            continue
        parent = h3.parent
        if (
            isinstance(parent, Tag)
            and parent.find("h3") is h3
            and len(parent.find_all("h3")) == 1
        ):
            texte_parent = _texte_normalise(parent.get_text(" ", strip=True))
            if texte_parent.startswith(label) and texte_parent != label:
                champs[label] = _texte_normalise(texte_parent[len(label) :])
                continue
        suivant = h3.find_next_sibling(["p", "div"])
        if isinstance(suivant, Tag):
            champs[label] = _texte_normalise(suivant.get_text(" ", strip=True))
    return champs


def _extraire_description(champs: dict[str, str]) -> str:
    """Combine les sections narratives (descriptif employeur, profil
    recherché) — pas de section "Missions" distincte constatée ici."""
    morceaux = [
        valeur
        for label, valeur in champs.items()
        if "descriptif" in label.lower() or "profil recherché" in label.lower()
    ]
    return "\n\n".join(morceaux)


def extraire_detail_offre(html: str) -> DetailOffre:
    """Extrait le détail structuré d'une fiche — jamais d'exception, un
    champ manquant reste vide."""
    soup = BeautifulSoup(html, "html.parser")
    champs = _extraire_champs(soup)

    _DEDIES = {
        "descriptif de l'employeur",
        "descriptif de l'employeur (suite)",
        "description du profil recherché",
        "rémunération indicative",
        "domaine et métier",
        "date de début de publication",
        "date limite d'envoi des candidatures",
        "niveau d'expérience min. requis",
        "niveau d'études min. souhaité",
    }
    sections_complementaires = {
        label: valeur
        for label, valeur in champs.items()
        if label.lower() not in _DEDIES
    }

    return {
        "description": _extraire_description(champs),
        "salaire": champs.get("Rémunération indicative", ""),
        "experience_requise": champs.get("Niveau d'expérience min. requis", ""),
        "formation_requise": champs.get("Niveau d'études min. souhaité", ""),
        "secteur": champs.get("Domaine et métier", ""),
        "date_publication": champs.get("Date de début de publication", ""),
        "a_propos_employeur": "",
        "sections_complementaires": sections_complementaires,
        "page_html": html,
        "lien_postuler": "",
        "date_limite": champs.get("Date limite d'envoi des candidatures", ""),
    }
