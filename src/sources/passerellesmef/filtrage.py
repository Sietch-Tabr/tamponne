"""Filtrage côté client des offres de Passerelles/MEF.

Le site n'expose ni département, ni catégorie, ni domaine, ni organisation
dans sa recherche : seules la liste (lieu, date) et la fiche de chaque offre
(catégorie, domaine, direction, télétravail, management) permettent de
trancher.
"""

import unicodedata
from datetime import date, timedelta
from difflib import SequenceMatcher

from src.filtres import (
    CATEGORIES,
    DATES_PUBLICATION,
    NUMEROS_DEPARTEMENTS,
    cle_categorie,
    numero_departement_texte,
    numeros_departements,
)
from src.types import DetailOffre, FiltresRecherche

MINISTERE_BERCY = "Ministères Economiques et Financiers"
"""Ministère du cache des organisations dont relève ce portail."""

_JOURS_PAR_FENETRE = {
    "dernieres_48_heures": 2,
    "7_derniers_jours": 7,
    "14_derniers_jours": 14,
}
_SEUIL_RESSEMBLANCE = 0.9


def _normaliser(texte: str) -> str:
    sans_accents = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in sans_accents if not unicodedata.combining(c))
    return " ".join(sans_accents.lower().split())


def _ressemblent(a: str, b: str) -> bool:
    a, b = _normaliser(a), _normaliser(b)
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
        or filtres.get("management")
        or filtres.get("teletravail")
    )


def numero_depuis_fiche(detail: DetailOffre) -> str | None:
    """Département de la fiche : « Localisation du poste » quand elle donne
    un numéro, sinon le code postal du lieu d'affectation."""
    champs = detail["sections_complementaires"]
    for libelle in ("Localisation du poste", "Lieu d'affectation"):
        if numero := numero_departement_texte(champs.get(libelle, "")):
            return numero
    return None


def libelle_lieu(numero: str) -> str:
    """« Paris (75) » pour un numéro de département connu, chaîne vide sinon
    (même forme que la liste du site)."""
    for nom, numero_nom in NUMEROS_DEPARTEMENTS.items():
        if numero_nom == numero:
            return f"{nom} ({numero})"
    return ""


def lieu_correspond(numero: str | None, localisations: list[str]) -> bool:
    """Vrai si `numero` est un département visé par `localisations` ; un
    numéro inconnu (`None`) est gardé, faute de pouvoir l'écarter."""
    if numero is None:
        return True
    return numero in numeros_departements(localisations)


def date_dans_fenetre(texte: str, cle: str, aujourdhui: date | None = None) -> bool:
    """Vrai si la date « jj/mm/aaaa » tombe dans la fenêtre de publication
    `cle` (clé de `DATES_PUBLICATION`) ; une date illisible est gardée."""
    jours = _JOURS_PAR_FENETRE.get(DATES_PUBLICATION.get(cle, ""), 0)
    if not jours:
        return True
    try:
        jour, mois, annee = (int(p) for p in texte.split("/"))
        publiee = date(annee, mois, jour)
    except ValueError:
        return True
    return publiee >= (aujourdhui or date.today()) - timedelta(days=jours)


def _domaine_correspond(secteur: str, domaines: list[str]) -> bool:
    domaine_fiche = secteur.split(" - ")[0]
    return any(_ressemblent(domaine_fiche, d) for d in domaines)


def _organisation_correspond(direction: str, sous_organisations: list[str]) -> bool:
    if not direction:
        return True
    cible = _normaliser(direction)
    return any(
        _ressemblent(direction, s) or _normaliser(s) in cible
        for s in sous_organisations
    )


def fiche_correspond(detail: DetailOffre, filtres: FiltresRecherche) -> bool:
    """Vrai si la fiche respecte catégories, domaines, organisations,
    management et télétravail ; une fiche illisible est gardée."""
    if not detail["page_html"]:
        return True
    champs = detail["sections_complementaires"]
    if categories := [c for c in filtres.get("categories", []) if c in CATEGORIES]:
        if cle_categorie(champs.get("Catégorie", "")) not in categories:
            return False
    if domaines := filtres.get("domaines"):
        if not _domaine_correspond(detail["secteur"], domaines):
            return False
    if organisations := organisations_de_bercy(filtres.get("organisations", [])):
        if not _organisation_correspond(
            champs.get("Directions et Services", ""), organisations
        ):
            return False
    if filtres.get("management") and champs.get("Management") != "Oui":
        return False
    if filtres.get("teletravail") and champs.get("Télétravail possible") != "Oui":
        return False
    return True
