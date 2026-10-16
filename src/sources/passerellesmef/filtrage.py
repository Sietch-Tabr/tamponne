"""Filtrage côté client des offres de Passerelles/MEF.

Le site n'expose ni département, ni catégorie, ni domaine, ni organisation
dans sa recherche : seules la liste (lieu) et la fiche de chaque offre
(catégorie, domaine, direction, expérience, télétravail, management)
permettent de trancher.
"""

import unicodedata
from difflib import SequenceMatcher

from src.filtres import (
    CATEGORIES,
    EXPERIENCES,
    cle_categorie,
    numero_departement_texte,
)
from src.types import DetailOffre, FicheFiltrage, FiltresRecherche

MINISTERE_BERCY = "Ministères Economiques et Financiers"
"""Ministère du cache des organisations dont relève ce portail."""

_SEUIL_RESSEMBLANCE = 0.9


def normaliser(texte: str) -> str:
    """Texte sans accents, en minuscules, espaces simples."""
    sans_accents = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in sans_accents if not unicodedata.combining(c))
    return " ".join(sans_accents.lower().split())


def ressemblent(a: str, b: str) -> bool:
    """Vrai si deux libellés ne diffèrent que par un détail d'écriture."""
    a, b = normaliser(a), normaliser(b)
    return bool(a) and SequenceMatcher(None, a, b).ratio() >= _SEUIL_RESSEMBLANCE


def organisations_de_bercy(organisations: list[str]) -> list[str]:
    """Sous-organisations de Bercy parmi `organisations` (« Ministère -
    Sous-organisation »)."""
    prefixe = f"{MINISTERE_BERCY} - "
    return [o.removeprefix(prefixe) for o in organisations if o.startswith(prefixe)]


def fiche_necessaire(filtres: FiltresRecherche) -> bool:
    """Vrai si un critère actif ne se lit que sur la fiche de l'offre."""
    return bool(
        filtres.get("categories")
        or filtres.get("domaines")
        or filtres.get("organisations")
        or filtres.get("experience")
        or filtres.get("management")
        or filtres.get("teletravail")
    )


def extraire_fiche(detail: DetailOffre) -> FicheFiltrage | None:
    """Ce que la fiche apprend pour filtrer, `None` si elle est illisible.

    Le département vient de « Localisation du poste » quand elle donne un
    numéro, sinon du code postal du lieu d'affectation.
    """
    if not detail["page_html"]:
        return None
    champs = detail["sections_complementaires"]
    numero = ""
    for libelle in ("Localisation du poste", "Lieu d'affectation"):
        numero = numero_departement_texte(champs.get(libelle, "")) or ""
        if numero:
            break
    return {
        "numero": numero,
        "categorie": cle_categorie(champs.get("Catégorie", "")) or "",
        "secteur": detail["secteur"],
        "direction": champs.get("Directions et Services", ""),
        "experience": detail["experience_requise"],
        "management": champs.get("Management") == "Oui",
        "teletravail": champs.get("Télétravail possible") == "Oui",
    }


def _domaine_correspond(secteur: str, domaines: list[str]) -> bool:
    domaine_fiche = secteur.split(" - ")[0]
    return any(ressemblent(domaine_fiche, d) for d in domaines)


def _organisation_correspond(direction: str, sous_organisations: list[str]) -> bool:
    cible = normaliser(direction)
    return any(
        ressemblent(direction, s) or normaliser(s) in cible for s in sous_organisations
    )


def fiche_correspond(fiche: FicheFiltrage, filtres: FiltresRecherche) -> bool:
    """Vrai si la fiche respecte catégories, domaines, organisations,
    expérience, management et télétravail. Une information absente de la
    fiche n'écarte pas l'offre."""
    if categories := [c for c in filtres.get("categories", []) if c in CATEGORIES]:
        if fiche["categorie"] and fiche["categorie"] not in categories:
            return False
    if domaines := filtres.get("domaines"):
        if fiche["secteur"] and not _domaine_correspond(fiche["secteur"], domaines):
            return False
    if organisations := organisations_de_bercy(filtres.get("organisations", [])):
        if fiche["direction"] and not _organisation_correspond(
            fiche["direction"], organisations
        ):
            return False
    experience = filtres.get("experience") or ""
    if experience in EXPERIENCES and fiche["experience"]:
        if normaliser(fiche["experience"]) != normaliser(experience):
            return False
    if filtres.get("management") and not fiche["management"]:
        return False
    if filtres.get("teletravail") and not fiche["teletravail"]:
        return False
    return True
