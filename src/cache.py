"""Cache local des organisations et des offres vues."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from src.sources.choisirleservicepublic.api import telecharger_page_offres
from src.types import Offre, OffreCache, Organisations
from src.utils import VERROU_DONNEES, ecriture_atomique

CHEMIN_CACHE = Path(__file__).parent.parent / "data" / "cache.json"
CHEMIN_OFFRES = Path(__file__).parent.parent / "data" / "offres.json"
TTL_ORGANISATIONS = 7 * 24 * 3600  # 7 jours en secondes
TTL_OFFRES = 30 * 24 * 3600  # 30 jours en secondes


def _charger_cache() -> dict[str, Any]:
    """Charge le cache JSON depuis le disque."""
    if not CHEMIN_CACHE.exists():
        return {}
    try:
        return json.loads(CHEMIN_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        # stderr, pas de bibliothèque d'UI : ce module n'est lié à
        # aucune interface particulière.
        print(
            f"Avertissement : {CHEMIN_CACHE.name} illisible ou corrompu, "
            "cache réinitialisé.",
            file=sys.stderr,
        )
        return {}


def _sauvegarder_cache(cache: dict[str, Any]) -> None:
    """Écrit le cache JSON sur le disque."""
    ecriture_atomique(CHEMIN_CACHE, cache)


def _organisations_expirees(cache: dict[str, Any]) -> bool:
    """Retourne True si le cache organisations est absent ou expiré."""
    entree = cache.get("organisations")
    if not entree:
        return True
    try:
        cached_at = datetime.fromisoformat(entree["cached_at"])
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        return age > TTL_ORGANISATIONS
    except KeyError, ValueError, TypeError:
        return True


def _scraper_organisations() -> Organisations:
    """Scrape /nos-offres/ et retourne {ministère: {sous-org: id}}."""
    html = telecharger_page_offres()
    soup = BeautifulSoup(html, "html.parser")

    parents: dict[str, dict] = {}
    for inp in soup.find_all(
        "input", attrs={"data-slug": "organisations", "data-has-children": True}
    ):
        parent_id = inp.get("id")
        desc = inp.get("data-desc")
        if parent_id and desc:
            parents[parent_id] = {"nom": desc, "enfants": {}}

    for inp in soup.find_all(
        "input", attrs={"data-slug": "organisations", "data-parent": True}
    ):
        parent_id = inp.get("data-parent")
        if not parent_id or parent_id not in parents:
            continue
        desc = inp.get("data-desc")
        valeur = inp.get("value", "")
        if desc and valeur.isdigit():
            parents[parent_id]["enfants"][desc] = int(valeur)

    resultat: dict[str, dict[str, int]] = {}
    for infos in parents.values():
        if infos["enfants"]:
            resultat[infos["nom"]] = dict(sorted(infos["enfants"].items()))

    return dict(sorted(resultat.items()))


def obtenir_organisations(forcer: bool = False) -> Organisations:
    """Retourne les organisations depuis le cache ou scrape si expiré."""
    cache = _charger_cache()

    if forcer or _organisations_expirees(cache):
        data = _scraper_organisations()
        cache["organisations"] = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        _sauvegarder_cache(cache)
        return data

    return cache["organisations"]["data"]


# --- Cache des offres par profil ---


def _charger_offres() -> dict[str, dict[str, OffreCache]]:
    """Charge le cache des offres depuis le disque."""
    if not CHEMIN_OFFRES.exists():
        return {}
    try:
        return json.loads(CHEMIN_OFFRES.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        print(
            f"Avertissement : {CHEMIN_OFFRES.name} illisible ou corrompu, "
            "cache réinitialisé.",
            file=sys.stderr,
        )
        return {}


def _sauvegarder_offres(offres: dict[str, dict[str, OffreCache]]) -> None:
    """Écrit le cache des offres sur le disque."""
    ecriture_atomique(CHEMIN_OFFRES, offres)


def maj_cache_offres(
    nom_profil: str, offres_fraiches: list[Offre], consultation: bool = True
) -> set[str]:
    """Met à jour le cache des offres pour un profil.

    Ajoute les offres inconnues, met à jour ``derniere_vue`` des offres
    existantes, et purge celles absentes depuis plus de TTL_OFFRES secondes.
    Une offre est « nouvelle » tant qu'elle n'a pas été consultée, c'est-à-dire
    affichée dans le registre : le relevé en arrière-plan les compte sans
    les consulter.

    Lors de la purge, si ``derniere_vue`` est absent ou non parsable, la valeur
    par défaut est ``maintenant_iso`` (ISO 8601 UTC), ce qui préserve l'offre
    dans le cache. Si le parsing échoue avec ValueError ou TypeError, l'offre
    est purgée immédiatement.

    Args:
        nom_profil: Clé identifiant le profil dans le cache des offres.
        offres_fraiches: Offres retournées par la dernière recherche.
        consultation: Vrai si les offres sont affichées dans le registre
            (elles deviennent consultées) ; faux pour le relevé en
            arrière-plan.

    Returns:
        Références des offres fraîches pas encore consultées avant cet appel.
    """
    with VERROU_DONNEES:
        maintenant = datetime.now(timezone.utc)
        maintenant_iso = maintenant.isoformat()
        toutes = _charger_offres()
        cache_profil = toutes.get(nom_profil, {})

        refs_fraiches = {o["reference"] for o in offres_fraiches if o.get("reference")}
        nouvelles: set[str] = set()

        for offre in offres_fraiches:
            ref = offre.get("reference")
            if not ref:
                continue
            if ref not in cache_profil:
                nouvelles.add(ref)
                cache_profil[ref] = {
                    **offre,
                    "vu_le": maintenant_iso,
                    "derniere_vue": maintenant_iso,
                    "consultee": consultation,
                }
                continue
            if cache_profil[ref].get("consultee", True) is False:
                nouvelles.add(ref)
            cache_profil[ref].update({**offre, "derniere_vue": maintenant_iso})
            if consultation:
                cache_profil[ref]["consultee"] = True

        # Purge des offres absentes depuis plus de TTL_OFFRES
        a_purger = []
        for ref, donnees in cache_profil.items():
            if ref not in refs_fraiches:
                try:
                    derniere = datetime.fromisoformat(
                        donnees.get("derniere_vue", maintenant_iso)
                    )
                    age = (maintenant - derniere).total_seconds()
                    if age > TTL_OFFRES:
                        a_purger.append(ref)
                except ValueError, TypeError:
                    a_purger.append(ref)
        for ref in a_purger:
            del cache_profil[ref]

        toutes[nom_profil] = cache_profil
        _sauvegarder_offres(toutes)
        return nouvelles


def obtenir_offres_cachetees(nom_profil: str) -> dict[str, OffreCache]:
    """Retourne les offres en cache pour un profil (référence → données)."""
    return _charger_offres().get(nom_profil, {})


# --- Cache des organisations ---


def age_cache_organisations() -> str | None:
    """Retourne une chaîne lisible décrivant l'âge du cache, ou None si absent."""
    cache = _charger_cache()
    entree = cache.get("organisations")
    if not entree:
        return None
    try:
        cached_at = datetime.fromisoformat(entree["cached_at"])
        age_s = (datetime.now(timezone.utc) - cached_at).total_seconds()
        if age_s < 3600:
            return f"il y a {int(age_s // 60)} min"
        if age_s < 86400:
            return f"il y a {int(age_s // 3600)} h"
        return f"il y a {int(age_s // 86400)} j"
    except KeyError, ValueError, TypeError:
        return None
