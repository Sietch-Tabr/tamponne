"""Suivi de candidature : historique d'événements par offre.

Voir REFONTE.md §7 pour le modèle de données. Données strictement
locales à chaque installation (pas de synchronisation entre
utilisateurs).
"""

import json
import sys
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from src.sources.choisirleservicepublic.api import (
    obtenir_page_offres,
    telecharger_binaire,
)
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE, _valider_url
from src.types import Candidature, DetailOffre, EvenementCandidature
from src.utils import ecriture_atomique

CHEMIN_CANDIDATURES = Path(__file__).parent.parent / "data" / "candidatures.json"
DOSSIER_ARCHIVES = Path(__file__).parent.parent / "data" / "archives"


def chemin_archive_pdf(reference: str) -> Path:
    """Chemin du PDF archivé pour une candidature, qu'il existe ou non."""
    return DOSSIER_ARCHIVES / f"{reference}.pdf"


def _extraire_url_pdf(page_html: str) -> str:
    """URL du PDF officiel de l'offre (lien « Télécharger » du site)."""
    soup = BeautifulSoup(page_html, "html.parser")
    lien = soup.find("a", class_="fr-link--download")
    if not isinstance(lien, Tag):
        return ""
    return _valider_url(str(lien.get("href", "")))


def generer_archive_pdf(reference: str, page_html: str) -> bool:
    """Télécharge et archive le PDF officiel de la fiche de poste.

    Ne lève jamais d'exception : un échec laisse la candidature sans
    archive, le suivi reste utile sans elle.
    """
    url_pdf = _extraire_url_pdf(page_html)
    if not url_pdf:
        print(
            "Avertissement : lien PDF introuvable, archive non générée.",
            file=sys.stderr,
        )
        return False
    try:
        contenu = telecharger_binaire(url_pdf)
    except RuntimeError:
        print(
            f"Avertissement : échec de téléchargement du PDF ({url_pdf}).",
            file=sys.stderr,
        )
        return False

    chemin = chemin_archive_pdf(reference)
    try:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_bytes(contenu)
    except OSError:
        print(
            f"Avertissement : échec d'écriture de l'archive PDF ({chemin}).",
            file=sys.stderr,
        )
        return False
    return True


# Jours sans événement au-delà desquels une relance est suggérée (badge visuel seul).
SEUIL_RELANCE_JOURS = 21

TYPES_EVENEMENT: dict[str, str] = {
    "candidature_envoyee": "Candidature envoyée",
    "accuse_reception": "Accusé de réception",
    "entretien_planifie": "Entretien planifié",
    "entretien_passe": "Entretien passé",
    "relance": "Relance",
    "reponse_positive": "Réponse positive",
    "refus": "Refus",
    "autre": "Autre",
}

# Types d'événement au-delà desquels une relance n'a plus de sens
# (issue déjà connue : la candidature est close, positivement ou non).
_TYPES_CLOTURANTS = {"reponse_positive", "refus"}

# Le site répond HTTP 200 (pas 404) pour une offre retirée, avec ce titre distinct.
MARQUEUR_OFFRE_DEPUBLIEE = "Offre dépubliée"


def charger_candidatures() -> dict[str, Candidature]:
    """Charge les candidatures depuis candidatures.json."""
    if not CHEMIN_CANDIDATURES.exists():
        return {}
    try:
        return json.loads(CHEMIN_CANDIDATURES.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print(
            f"Avertissement : {CHEMIN_CANDIDATURES.name} illisible ou corrompu, "
            "aucune candidature chargée.",
            file=sys.stderr,
        )
        return {}


def sauvegarder_candidatures(candidatures: dict[str, Candidature]) -> None:
    """Écrit candidatures.json sur le disque."""
    ecriture_atomique(CHEMIN_CANDIDATURES, candidatures)


def ajouter_candidature(
    reference: str,
    offre_titre: str,
    offre_employeur: str,
    offre_url: str,
    date_candidature: str | None = None,
    *,
    offre_domaine: str = "",
    offre_localisation: str = "",
    offre_versant: str = "",
    offre_date: str = "",
    detail: DetailOffre | None = None,
) -> None:
    """Démarre le suivi d'une candidature pour une offre.

    Écrase une candidature existante pour la même référence (pas de
    fusion) : recandidater à une offre déjà suivie repart d'un
    historique propre, intentionnellement — un doute sur l'état
    précédent vaut mieux qu'un historique mélangé.

    Args:
        detail: Détail structuré + archive HTML brute de la fiche de
            poste (voir `DetailOffre`), récupéré à l'appel via
            `recuperer_detail_offre` — absent (`None`) si l'appelant ne
            l'a pas récupéré, ou si le téléchargement a échoué.
    """
    candidatures = charger_candidatures()
    date_effective = date_candidature or date.today().isoformat()
    candidatures[reference] = {
        "offre_titre": offre_titre,
        "offre_employeur": offre_employeur,
        "offre_url": offre_url,
        "offre_reference": reference,
        "offre_domaine": offre_domaine,
        "offre_localisation": offre_localisation,
        "offre_versant": offre_versant,
        "offre_date": offre_date,
        "date_candidature": date_effective,
        # Pas d'événement préinséré : rien ne garantit que la candidature a été envoyée.
        "historique": [],
        "disponible": True,
        "derniere_verification": "",
        "detail": detail or DETAIL_VIDE,
    }
    sauvegarder_candidatures(candidatures)


def ajouter_evenement(
    reference: str,
    type_evenement: str,
    evenement_date: str | None = None,
    note: str = "",
) -> None:
    """Ajoute un événement à l'historique d'une candidature suivie."""
    candidatures = charger_candidatures()
    if reference not in candidatures:
        raise KeyError(f"Candidature introuvable : {reference}")
    evenement: EvenementCandidature = {
        "date": evenement_date or date.today().isoformat(),
        "type": type_evenement,
        "note": note,
    }
    candidatures[reference]["historique"].append(evenement)
    sauvegarder_candidatures(candidatures)


def supprimer_candidature(reference: str) -> None:
    """Arrête le suivi d'une candidature et supprime son archive PDF
    éventuelle (pas d'orphelin laissé dans data/archives/)."""
    candidatures = charger_candidatures()
    candidatures.pop(reference, None)
    sauvegarder_candidatures(candidatures)
    chemin_archive_pdf(reference).unlink(missing_ok=True)


def dernier_evenement(candidature: Candidature) -> EvenementCandidature | None:
    """Retourne l'événement le plus récent de l'historique.

    Trié par date (tri stable : à date égale, l'ordre d'ajout est
    conservé) — le statut affiché ne doit jamais dépendre de l'ordre
    d'insertion seul, un événement peut être ajouté après coup avec une
    date antérieure (ex. saisie tardive d'un entretien déjà passé).
    """
    historique = candidature.get("historique") or []
    if not historique:
        return None
    return sorted(historique, key=lambda e: e["date"])[-1]


def statut_libelle(candidature: Candidature) -> str:
    """Libellé lisible du statut courant, dérivé du dernier événement."""
    dernier = dernier_evenement(candidature)
    if dernier is None:
        return "Aucun événement"
    return TYPES_EVENEMENT.get(dernier["type"], dernier["type"])


def verifier_disponibilite(url: str) -> bool | None:
    """Vérifie si l'offre est toujours en ligne sur le site.

    Returns:
        ``True`` si l'offre semble toujours disponible, ``False`` si le
        marqueur de dépublication est détecté, ``None`` si la
        vérification a échoué (erreur réseau) — dans ce cas, le statut
        stocké ne doit pas être modifié (on ne sait juste pas).
    """
    try:
        page = obtenir_page_offres(url)
    except RuntimeError:
        return None
    return MARQUEUR_OFFRE_DEPUBLIEE not in page["title"]


def marquer_disponibilite(reference: str, disponible: bool) -> None:
    """Persiste le résultat d'une vérification de disponibilité."""
    candidatures = charger_candidatures()
    if reference not in candidatures:
        return
    candidatures[reference]["disponible"] = disponible
    candidatures[reference]["derniere_verification"] = date.today().isoformat()
    sauvegarder_candidatures(candidatures)


def relance_suggeree(candidature: Candidature) -> bool:
    """True si aucun événement depuis plus de `SEUIL_RELANCE_JOURS` et
    que la candidature n'est pas déjà close (réponse positive/refus)."""
    dernier = dernier_evenement(candidature)
    if dernier is None or dernier["type"] in _TYPES_CLOTURANTS:
        return False
    try:
        jours_ecoules = (date.today() - date.fromisoformat(dernier["date"])).days
    except ValueError:
        return False
    return jours_ecoules >= SEUIL_RELANCE_JOURS
