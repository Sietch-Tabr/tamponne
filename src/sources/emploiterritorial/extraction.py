"""Extraction des offres et fiches détail — HTML d'emploi-territorial.fr."""

import re
import sys

lazy from bs4 import BeautifulSoup, Tag

from src.sources.base import texte_lisible, valider_url
from src.types import DetailOffre, Offre

DOMAINE = "emploi-territorial.fr"
URL_BASE = "https://www.emploi-territorial.fr"
SOURCE_LABEL = "Fonction publique territoriale"

_RE_DATE_TOOLTIP = re.compile(r"le (\d{2}/\d{2}/\d{4})")
_RE_ESPACES = re.compile(r"\s+")


def _texte_normalise(tag: Tag) -> str:
    """Texte d'un tag, espaces/retours à la ligne internes réduits à un seul."""
    return _RE_ESPACES.sub(" ", tag.get_text(" ", strip=True)).strip()


# Libellés déjà mappés vers un champ dédié de DetailOffre — exclus de
# sections_complementaires pour ne pas les dupliquer.
_LIBELLES_DEDIES = frozenset(
    {
        "rémunération indicative",
        "experience souhaitée",
        "expérience souhaitée",
        "famille de métiers",
        "lien de candidature",
        "date limite de candidature",
    }
)


def _valider_url(url: str) -> str:
    """URL normalisée si elle appartient au domaine du site, chaîne vide sinon."""
    return valider_url(url, URL_BASE, DOMAINE)


def extraire_totaux(html: str) -> tuple[int, int]:
    """(nb_offres_total, taille_de_page) depuis les champs cachés de la
    page de recherche (#nb-offres / #search-limit)."""
    soup = BeautifulSoup(html, "html.parser")
    nb_offres_input = soup.find("input", id="nb-offres")
    limite_input = soup.find("input", id="search-limit")
    nb_offres = (
        int(str(nb_offres_input.get("value", "0")))
        if isinstance(nb_offres_input, Tag)
        else 0
    )
    limite = (
        int(str(limite_input.get("value", "20")))
        if isinstance(limite_input, Tag)
        else 20
    )
    return nb_offres, limite


def _date_depuis_tooltip(bouton: Tag) -> str:
    m = _RE_DATE_TOOLTIP.search(str(bouton.get("data-tooltip", "")))
    return m.group(1) if m else ""


def extraire_offres(html: str) -> list[Offre]:
    """Extrait les offres d'une page de résultats (recherche initiale ou
    fragment de pagination)."""
    soup = BeautifulSoup(html, "html.parser")
    offres: list[Offre] = []

    for tr in soup.find_all("tr", id=re.compile(r"^O")):
        # Deux blocs dupliqués existent pour le responsive (mobile/desktop) —
        # on ne parse que le premier, l'autre est un doublon caché en CSS.
        bloc = tr.find("div", class_="detail-offres")
        if not isinstance(bloc, Tag):
            continue
        lien = bloc.find("a", class_="lien-details-offre")
        if not isinstance(lien, Tag):
            continue
        url = _valider_url(str(lien.get("href", "")))
        if not url:
            continue
        titre = lien.get_text(strip=True)
        reference = str(tr.get("id", ""))

        employeur = localisation = ""
        bloc_collectivite = bloc.find("div", class_="detail-offre-collectivite")
        if isinstance(bloc_collectivite, Tag):
            valeur = bloc_collectivite.find("span", class_="valeur")
            if isinstance(valeur, Tag):
                employeur = valeur.get_text(strip=True)
            departement = bloc_collectivite.find(
                "span", class_=lambda c: bool(c) and "text-secondary" in c
            )
            if isinstance(departement, Tag):
                localisation = departement.get_text(strip=True)

        date = ""
        for bouton in bloc.find_all("button", attrs={"data-tooltip": True}):
            tooltip = str(bouton.get("data-tooltip", ""))
            if tooltip.startswith("publié le"):
                date = _date_depuis_tooltip(bouton)
                break

        offres.append(
            {
                "titre": titre,
                "url": url,
                "reference": reference,
                "domaine": "",
                "employeur": employeur,
                "localisation": localisation,
                "versant": "Fonction publique Territoriale",
                "date": date,
                "source": SOURCE_LABEL,
            }
        )
    return offres


def _extraire_champs_labels(soup: BeautifulSoup) -> dict[str, str]:
    """Paires libellé → valeur de la fiche détail (`div.offre-item-label`
    / `div.offre-item-value`), génériques et robustes au redesign."""
    champs: dict[str, str] = {}
    for bloc in soup.find_all("div", class_="offre-item"):
        label = bloc.find("div", class_="offre-item-label")
        valeur = bloc.find("div", class_="offre-item-value")
        if isinstance(label, Tag) and isinstance(valeur, Tag):
            champs[label.get_text(strip=True)] = texte_lisible(valeur)
    return champs


def _extraire_date_publication(soup: BeautifulSoup) -> str:
    for bloc in soup.find_all("div", class_="row"):
        texte = bloc.get_text(strip=True)
        if texte.startswith("Publiée le"):
            span = bloc.find("span")
            if isinstance(span, Tag):
                return span.get_text(strip=True)
    return ""


def _extraire_lien_postuler(champs: dict[str, str]) -> str:
    valeur = champs.get("Lien de candidature", "")
    return valeur if valeur.startswith(("https://", "http://")) else ""


def _extraire_description(soup: BeautifulSoup) -> str:
    """Sections narratives (Descriptif, Missions, Profils recherchés...) —
    un `div.offre-item` ne portant qu'un libellé (pas de
    `.offre-item-value`), suivi d'un `div.offre-item-text` séparé
    contenant le texte. Absentes sur les offres purement statutaires
    (grade/métier uniquement, sans texte libre)."""
    morceaux = []
    for bloc in soup.find_all("div", class_="offre-item"):
        label = bloc.find("div", class_="offre-item-label")
        valeur = bloc.find("div", class_="offre-item-value")
        if not isinstance(label, Tag) or valeur is not None:
            continue
        texte_bloc = bloc.find_next_sibling("div", class_="offre-item-text")
        if isinstance(texte_bloc, Tag):
            morceaux.append(texte_lisible(texte_bloc))
    return "\n\n".join(m for m in morceaux if m)


def extraire_detail_offre(html: str) -> DetailOffre:
    """Extrait le détail structuré d'une fiche — jamais d'exception, un
    champ manquant reste vide plutôt que de faire planter le suivi."""
    soup = BeautifulSoup(html, "html.parser")
    champs = _extraire_champs_labels(soup)

    sections_complementaires = {
        label: valeur
        for label, valeur in champs.items()
        if label.lower() not in _LIBELLES_DEDIES
    }
    if not champs and not soup.find("h2"):
        print(
            "Avertissement\u00a0: structure de fiche inattendue sur "
            "emploi-territorial.fr, détail incomplet pour cette offre.",
            file=sys.stderr,
        )

    return {
        "description": _extraire_description(soup),
        "salaire": champs.get("Rémunération indicative", ""),
        "experience_requise": champs.get(
            "Experience souhaitée", champs.get("Expérience souhaitée", "")
        ),
        "formation_requise": "",
        "secteur": champs.get("Famille de métiers", ""),
        "date_publication": _extraire_date_publication(soup),
        "a_propos_employeur": "",
        "sections_complementaires": sections_complementaires,
        "page_html": html,
        "lien_postuler": _extraire_lien_postuler(champs),
        "date_limite": champs.get("Date limite de candidature", ""),
    }
