"""Mise en forme des offres pour l'affichage (dates, colonnes du tableau).

Ne dépend d'aucune bibliothèque d'UI.
"""

import re

from src.types import Offre

_MOIS_FR = {
    "janvier": 1,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
}

_RE_DATE_JJ_MM_AAAA = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def reformater_date(date_str: str) -> str:
    """Reformate une date française textuelle (ex. « 26 août 2026 »,
    format réel renvoyé par le site) en format compact JJ/MM/AAAA.
    Retourne la chaîne d'origine si le format n'est pas reconnu."""
    parties = date_str.strip().split()
    if len(parties) != 3:
        return date_str
    jour, mois_nom, annee = parties
    if jour.endswith("er"):
        jour = jour[:-2]
    mois = _MOIS_FR.get(mois_nom.lower())
    if mois is None or not jour.isdigit() or not annee.isdigit():
        return date_str
    return f"{int(jour):02d}/{mois:02d}/{annee}"


def offre_vers_ligne(offre: Offre) -> tuple[str, str, str, str, str]:
    """Extrait les 5 colonnes affichées dans le tableau de résultats."""
    return (
        offre["titre"],
        offre["employeur"] or "—",
        offre["localisation"] or "—",
        reformater_date(offre["date"]) if offre["date"] else "—",
        offre.get("source") or "Choisir le service public",
    )


def cle_tri_date(date_affichee: str) -> str:
    """Convertit une date affichée JJ/MM/AAAA en AAAA-MM-JJ, triable
    lexicographiquement. Une date non reconnue (absente, format libre)
    donne une chaîne vide : elle se range avant toutes les autres."""
    correspondance = _RE_DATE_JJ_MM_AAAA.match(date_affichee)
    if correspondance is None:
        return ""
    jour, mois, annee = correspondance.groups()
    return f"{annee}-{mois}-{jour}"
