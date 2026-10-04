"""Extraction des offres depuis le HTML retourné par l'API."""

import json
import re
import sys
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from src.filtres import RE_GRADE_SUPERIEUR
from src.types import DetailOffre, Offre

_DOMAINE_AUTORISE = "choisirleservicepublic.gouv.fr"
_URL_BASE = "https://choisirleservicepublic.gouv.fr"

_RE_REFERENCE = re.compile(r"reference-(.+?)/?$")
_RE_FR_TAG = re.compile(r"\bfr-tag\b")
_RE_ESPACES = re.compile(r"\s+")
_RE_PARENTHESE = re.compile(r"\s*\(\s*")
_RE_PAGINATION = re.compile(r"page\s+(\d+)\s+sur\s+(\d+)", re.IGNORECASE)
_RE_JSON_LD = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL
)


def _valider_url(url: str) -> str:
    """Retourne l'URL normalisée si elle appartient au domaine attendu, chaîne vide sinon."""
    if url.startswith("/"):
        return f"{_URL_BASE}{url}"
    if url.startswith(("https://", "http://")):
        domaine = urlparse(url).netloc
        if domaine == _DOMAINE_AUTORISE or domaine.endswith(f".{_DOMAINE_AUTORISE}"):
            return url
    return ""


def est_grade_superieur(titre: str) -> bool:
    """Retourne True si le titre indique un grade IDiv, IP* ou AFIPA."""
    return bool(RE_GRADE_SUPERIEUR.match(titre))


# Préfixes de référence vérifiés (via lien_postuler pointant vers le
# portail d'origine réel) — ex. MEF_2026-30262 vient de Bercy/Passerelles.
_SOURCES_CONNUES = {
    "MEF": "Ministère de l'Économie et des Finances",
    "MINT": "Ministère de l'Intérieur",
    "APHP": "AP-HP",
    "AGRI": "Ministère de l'Agriculture",
}


def deriver_source(reference: str) -> str:
    """Origine de l'offre, déduite du préfixe de référence (chaîne vide si
    la référence n'a pas de préfixe)."""
    if "_" not in reference:
        return ""
    prefixe = reference.split("_", 1)[0]
    return _SOURCES_CONNUES.get(prefixe, prefixe)


def extraire_offres(html: str) -> list[Offre]:
    """Extrait toutes les offres du HTML (sans filtre de grade)."""
    soup = BeautifulSoup(html, "html.parser")
    offres: list[Offre] = []

    for carte in soup.find_all("div", class_="fr-card__body"):
        h3 = carte.find("h3")
        lien = h3.find("a") if h3 else None
        if not lien:
            continue

        url = _valider_url(lien.get("href", ""))
        if not url:
            continue
        titre = lien.get_text(strip=True)

        ref_m = _RE_REFERENCE.search(url)
        reference = ref_m.group(1) if ref_m else ""

        tag_domaine = carte.find("a", class_=_RE_FR_TAG)
        domaine = tag_domaine.get_text(strip=True) if tag_domaine else ""

        localisation = versant = employeur = date = ""
        for li in carte.find_all("li"):
            classes = set(li.get("class", []))
            if "fr-icon--sm" not in classes:
                continue
            for sr in li.find_all("span", class_="sr-only"):
                sr.decompose()
            texte = _RE_ESPACES.sub(" ", li.get_text()).strip()

            if "fr-icon-map-pin-2-line" in classes:
                localisation = _RE_PARENTHESE.sub(" (", texte)
            elif "fr-icon-file-line" in classes:
                versant = texte
            elif "fr-icon-user-line" in classes:
                employeur = texte
            elif "fr-icon-calendar-line" in classes:
                date = texte.replace("En ligne depuis le ", "").replace(
                    "En ligne depuis ", ""
                )

        offres.append(
            {
                "titre": titre,
                "url": url,
                "reference": reference,
                "domaine": domaine,
                "employeur": employeur,
                "localisation": localisation,
                "versant": versant,
                "date": date,
                "source": deriver_source(reference),
            }
        )
    return offres


def filtrer_grades_superieurs(offres: list[Offre]) -> tuple[list[Offre], int]:
    """Retourne (offres_filtrees, nb_exclus) après suppression des IDiv/IP."""
    filtrees = [o for o in offres if not est_grade_superieur(o["titre"])]
    return filtrees, len(offres) - len(filtrees)


def extraire_pagination(titre: str) -> tuple[int, int]:
    """Extrait (page_courante, nb_pages) depuis le titre de la réponse."""
    m = _RE_PAGINATION.search(titre)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1, 1


DETAIL_VIDE: DetailOffre = {
    "description": "",
    "salaire": "",
    "experience_requise": "",
    "formation_requise": "",
    "secteur": "",
    "date_publication": "",
    "a_propos_employeur": "",
    "sections_complementaires": {},
    "page_html": "",
    "lien_postuler": "",
    "date_limite": "",
}
"""DetailOffre par défaut — réutilisé par `recuperer_detail_offre`
(src/sources/choisirleservicepublic/__init__.py) et `ajouter_candidature`
(src/candidatures.py) quand aucun détail n'a pu être récupéré."""


_RE_ESPACES_HORIZ = re.compile(r"[ \t]+")


def _texte_multiligne(bloc: Tag) -> str:
    """Texte d'un bloc, en convertissant les `<br>` en véritables sauts
    de ligne (au lieu de les perdre silencieusement comme le ferait
    `get_text(" ")`) — vérifié sur une offre réelle : le contenu de la
    fiche de poste est un unique `<p>` truffé de `<br>` pour séparer les
    paragraphes et les items de liste, sans autre balisage. Les lignes
    vides consécutives sont réduites à une seule, pour ne pas laisser de
    grands blancs entre deux `<br><br>`."""
    for br in bloc.find_all("br"):
        br.replace_with("\n")
    lignes = [
        _RE_ESPACES_HORIZ.sub(" ", ligne).strip()
        for ligne in bloc.get_text().split("\n")
    ]
    resultat: list[str] = []
    ligne_vide_precedente = False
    for ligne in lignes:
        if ligne:
            resultat.append(ligne)
            ligne_vide_precedente = False
        elif not ligne_vide_precedente:
            resultat.append("")
            ligne_vide_precedente = True
    return "\n".join(resultat).strip()


def _extraire_description_poste(soup: BeautifulSoup) -> str:
    """Description structurée du poste (« Vos missions en quelques
    mots »), avec ses sauts de ligne d'origine conservés.

    Extraite du DOM plutôt que du champ `Description` du JSON-LD : ce
    dernier est une copie dégradée du même texte, générée par le site
    en aplatissant tous les `<br>` sans aucun séparateur — vérifié sur
    une offre réelle, les phrases s'y retrouvent collées bout à bout,
    illisible tel quel. `extraire_detail_offre` retombe sur le champ
    JSON-LD uniquement si ce bloc est absent de la page.
    """
    bloc = soup.find("div", class_="col-left")
    if not isinstance(bloc, Tag):
        return ""
    titre = bloc.find("h2")
    if isinstance(titre, Tag):
        titre.decompose()
    return _texte_multiligne(bloc)


def _extraire_a_propos_employeur(soup: BeautifulSoup) -> str:
    """Texte de la section « Qui sommes-nous ? » (présentation du
    service/employeur) — vérifié présent sur plusieurs offres réelles.

    Retire le titre (`<h2>`) du DOM avant d'extraire le texte plutôt que
    de retirer un préfixe littéral « Qui sommes-nous ? » : le site
    l'écrit avec une espace insécable (`&nbsp;`), pas une espace normale
    — un retrait de préfixe littéral la manquait silencieusement.
    """
    bloc = soup.find("div", class_="about-agency")
    if not isinstance(bloc, Tag):
        return ""
    titre = bloc.find("h2")
    if isinstance(titre, Tag):
        titre.decompose()
    return _texte_multiligne(bloc)


def _extraire_sections_complementaires(soup: BeautifulSoup) -> dict[str, str]:
    """Sections de la partie « À propos de l'offre » (accordéon
    générique titre → contenu) — inclut la personne à contacter quand
    l'offre en indique une (section « Informations complémentaires »),
    conditions d'exercice, fondement juridique, statut du poste, métier
    de référence... Variable d'une offre à l'autre, jamais deviné : on
    prend tout ce que l'accordéon contient, quel qu'il soit."""
    sections: dict[str, str] = {}
    for section in soup.find_all("section", class_="fr-accordion"):
        bouton = section.find("button", class_="fr-accordion__btn")
        contenu = section.find("div", class_="fr-collapse")
        if bouton is None or contenu is None:
            continue
        label = bouton.get_text(strip=True)
        if label and isinstance(contenu, Tag):
            sections[label] = _texte_multiligne(contenu)
    return sections


_RE_DATE_LIMITE = re.compile(r"Date limite de candidature\s*:\s*(\S+)", re.IGNORECASE)


def _extraire_lien_postuler(soup: BeautifulSoup) -> str:
    """URL du portail de candidature réel — souvent externe au site."""
    lien = soup.find("a", string=re.compile(r"Postuler sur le site employeur", re.I))
    if not isinstance(lien, Tag):
        return ""
    return str(lien.get("href", ""))


def _extraire_date_limite(soup: BeautifulSoup) -> str:
    """Date limite de candidature — absente sur certaines offres."""
    texte = soup.find(string=_RE_DATE_LIMITE)
    if texte is None:
        return ""
    m = _RE_DATE_LIMITE.search(str(texte))
    return m.group(1) if m else ""


def extraire_detail_offre(html: str) -> DetailOffre:
    """Extrait le détail structuré d'une fiche de poste : description
    du poste (DOM, « Vos missions en quelques mots »), bloc JSON-LD
    (schema.org JobPosting) pour le salaire/expérience/formation/
    secteur (et filet de sécurité pour la description si ce bloc DOM
    est absent), section « Qui sommes-nous ? » pour la présentation de
    l'employeur, accordéon « À propos de l'offre » pour le reste (dont
    la personne à contacter, quand indiquée) — chaque partie vérifiée
    sur plusieurs offres réelles, structure stable. `page_html`
    conserve le HTML brut complet en filet de sécurité si un champ
    manque à l'extraction ci-dessus ou si la structure du site change.

    Ne lève jamais d'exception : un bloc absent ou invalide laisse
    simplement les champs correspondants vides, le suivi de candidature
    reste utile même sans le détail enrichi.
    """
    soup = BeautifulSoup(html, "html.parser")

    data: dict[str, object] = {}
    m = _RE_JSON_LD.search(html)
    if m:
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            print(
                "Avertissement : bloc JSON-LD de la fiche de poste illisible "
                "(JSON invalide) — détail structuré incomplet pour cette offre.",
                file=sys.stderr,
            )
    else:
        print(
            "Avertissement : bloc JSON-LD absent de la fiche de poste — "
            "détail structuré incomplet pour cette offre, seul le HTML brut "
            "est conservé.",
            file=sys.stderr,
        )

    description = _extraire_description_poste(soup)
    if not description:
        # Filet de sécurité : bloc DOM absent, retombe sur le JSON-LD dégradé.
        description = str(data.get("Description", "")).strip()
    if data and not description:
        print(
            "Avertissement : champ Description vide dans le JSON-LD de la "
            "fiche de poste.",
            file=sys.stderr,
        )

    return {
        "description": description,
        "salaire": str(data.get("baseSalary", "")),
        "experience_requise": str(data.get("experienceRequirements", "")),
        "formation_requise": str(data.get("educationRequirements", "")),
        "secteur": str(data.get("industry", "")),
        "date_publication": str(data.get("datePosted", "")),
        "a_propos_employeur": _extraire_a_propos_employeur(soup),
        "sections_complementaires": _extraire_sections_complementaires(soup),
        "page_html": html,
        "lien_postuler": _extraire_lien_postuler(soup),
        "date_limite": _extraire_date_limite(soup),
    }
