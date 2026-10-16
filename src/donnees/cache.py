"""Cache local des organisations et des offres vues."""

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

lazy from bs4 import BeautifulSoup, Tag

from src.chemins import DATA
from src.sources.choisirleservicepublic.api import telecharger_page_offres
from src.types import DetailOffre, FicheFiltrage, Offre, OffreCache, Organisations
from src.utils import ecriture_atomique

journal = logging.getLogger(__name__)

CHEMIN_CACHE = DATA / "cache.json"
CHEMIN_OFFRES = DATA / "offres.json"
CHEMIN_FICHES = DATA / "fiches.json"
CHEMIN_DETAILS = DATA / "details.json"
TTL_ORGANISATIONS = 7 * 24 * 3600  # 7 jours en secondes
TTL_OFFRES = 30 * 24 * 3600  # 30 jours en secondes
TTL_FICHES = 30 * 24 * 3600  # 30 jours en secondes
TTL_DETAILS = 24 * 3600  # 1 jour : une offre pourvue est dépubliée
MAXIMUM_DETAILS = 300


def _lire_json_dict(chemin: Path) -> dict[str, Any]:
    """Objet JSON de `chemin`, `{}` s'il est absent, illisible ou d'un autre
    type (liste, `null`) : un cache abîmé se reconstruit, il ne fait pas échouer."""
    if not chemin.exists():
        return {}
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        donnees = None
    if not isinstance(donnees, dict):
        # Journal plutôt qu'un message d'interface : ce module n'est lié à
        # aucune interface particulière.
        journal.warning("%s illisible ou corrompu, cache réinitialisé.", chemin.name)
        return {}
    return donnees


def _charger_cache() -> dict[str, Any]:
    """Charge le cache JSON depuis le disque."""
    return _lire_json_dict(CHEMIN_CACHE)


def _sauvegarder_cache(cache: dict[str, Any]) -> None:
    """Écrit le cache JSON sur le disque."""
    ecriture_atomique(CHEMIN_CACHE, cache)


def _organisations_expirees(cache: dict[str, Any]) -> bool:
    """Retourne True si le cache organisations est absent ou expiré."""
    entree = cache.get("organisations")
    if not isinstance(entree, dict) or not isinstance(entree.get("data"), dict):
        return True
    try:
        cached_at = datetime.fromisoformat(entree["cached_at"])
        age = (datetime.now(UTC) - cached_at).total_seconds()
        return age > TTL_ORGANISATIONS
    except KeyError, ValueError, TypeError:
        return True


def _attribut(balise: Tag, nom: str) -> str:
    """Valeur texte d'un attribut HTML, vide s'il est absent (ou multiple,
    ce qui n'arrive pas pour les attributs lus ici)."""
    valeur = balise.get(nom)
    return valeur if isinstance(valeur, str) else ""


def _scraper_organisations() -> Organisations:
    """Scrape /nos-offres/ et retourne {ministère: {sous-org: id}}."""
    html = telecharger_page_offres()
    soup = BeautifulSoup(html, "html.parser")

    parents: dict[str, dict] = {}
    for inp in soup.find_all(
        "input", attrs={"data-slug": "organisations", "data-has-children": True}
    ):
        parent_id = _attribut(inp, "id")
        desc = _attribut(inp, "data-desc")
        if parent_id and desc:
            parents[parent_id] = {"nom": desc, "enfants": {}}

    for inp in soup.find_all(
        "input", attrs={"data-slug": "organisations", "data-parent": True}
    ):
        parent_id = _attribut(inp, "data-parent")
        if not parent_id or parent_id not in parents:
            continue
        desc = _attribut(inp, "data-desc")
        valeur = _attribut(inp, "value")
        if desc and valeur.isdigit():
            parents[parent_id]["enfants"][desc] = int(valeur)

    resultat: dict[str, dict[str, int]] = {}
    for infos in parents.values():
        if infos["enfants"]:
            resultat[infos["nom"]] = dict(sorted(infos["enfants"].items()))

    return dict(sorted(resultat.items()))


def organisations_en_cache() -> tuple[Organisations, bool]:
    """Organisations lues sur le disque, même périmées, sans accès réseau.

    Returns:
        Les organisations (vides si le cache est absent ou illisible) et
        vrai s'il faut les rafraîchir (absentes ou plus vieilles que
        `TTL_ORGANISATIONS`).
    """
    cache = _charger_cache()
    entree = cache.get("organisations")
    donnees = entree.get("data") if isinstance(entree, dict) else None
    return (
        donnees if isinstance(donnees, dict) else {},
        _organisations_expirees(cache),
    )


def obtenir_organisations(forcer: bool = False) -> Organisations:
    """Retourne les organisations depuis le cache ou scrape si expiré."""
    cache = _charger_cache()

    if forcer or _organisations_expirees(cache):
        data = _scraper_organisations()
        cache["organisations"] = {
            "cached_at": datetime.now(UTC).isoformat(),
            "data": data,
        }
        _sauvegarder_cache(cache)
        return data

    return cache["organisations"]["data"]


# --- Cache des offres par profil ---


def _charger_offres() -> dict[str, dict[str, OffreCache]]:
    """Charge le cache des offres depuis le disque."""
    return cast(dict[str, dict[str, OffreCache]], _lire_json_dict(CHEMIN_OFFRES))


def _sauvegarder_offres(offres: dict[str, dict[str, OffreCache]]) -> None:
    """Écrit le cache des offres sur le disque."""
    ecriture_atomique(CHEMIN_OFFRES, offres)


def maj_cache_offres(nom_profil: str, offres_fraiches: list[Offre]) -> set[str]:
    """Met à jour le cache des offres pour un profil.

    Ajoute les offres inconnues, met à jour ``derniere_vue`` des offres
    existantes, et purge celles absentes depuis plus de TTL_OFFRES secondes.

    Lors de la purge, si ``derniere_vue`` est absent ou non parsable, la valeur
    par défaut est ``maintenant_iso`` (ISO 8601 UTC), ce qui préserve l'offre
    dans le cache. Si le parsing échoue avec ValueError ou TypeError, l'offre
    est purgée immédiatement.

    Args:
        nom_profil: Clé identifiant le profil dans le cache des offres.
        offres_fraiches: Offres retournées par la dernière recherche.

    Returns:
        Références des offres jamais vues pour ce profil avant cet appel.
    """
    maintenant = datetime.now(UTC)
    maintenant_iso = maintenant.isoformat()
    toutes = _charger_offres()
    cache_profil = toutes.get(nom_profil)
    if not isinstance(cache_profil, dict):
        cache_profil = {}

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
            }
        else:
            cache_profil[ref].update({**offre, "derniere_vue": maintenant_iso})

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
    try:
        _sauvegarder_offres(toutes)
    except OSError as erreur:
        # Les offres s'affichent quand même ; elles seront de nouveau « nouvelles ».
        journal.warning("%s non enregistré\u00a0: %s", CHEMIN_OFFRES.name, erreur)
    return nouvelles


# --- Cache des organisations ---


def date_cache_organisations() -> datetime | None:
    """Moment (UTC) où les organisations ont été mises en cache, ou None si
    le cache est absent ou illisible."""
    entree = _charger_cache().get("organisations")
    if not entree:
        return None
    try:
        return datetime.fromisoformat(entree["cached_at"])
    except KeyError, ValueError, TypeError:
        return None


# --- Caches de pages lues sur les sites (fiches pour filtrer, fiches de poste) ---

_CLES_FICHE = frozenset(FicheFiltrage.__annotations__)
_CLES_DETAIL = frozenset(DetailOffre.__annotations__)


class _CacheTemporel:
    """Entrées datées par URL, gardées `ttl` secondes dans un fichier JSON.

    L'écriture est groupée : appeler :meth:`enregistrer` en fin d'opération.
    Sous-classes : `_champ` (clé de la donnée dans l'entrée), `_ttl`,
    `_maximum` (nombre d'entrées gardées, les plus anciennes partent d'abord),
    `_chemin()` et `_donnee_valide()`.
    """

    _champ = ""
    _ttl = 0
    _maximum = 1_000_000

    def __init__(self) -> None:
        self._verrou = threading.Lock()
        self._modifie = False
        self._entrees = self._charger()

    @staticmethod
    def _chemin() -> Path:
        raise NotImplementedError

    @staticmethod
    def _donnee_valide(donnee: object) -> bool:
        raise NotImplementedError

    def _charger(self) -> dict[str, dict[str, Any]]:
        chemin = self._chemin()
        if not chemin.exists():
            return {}
        try:
            donnees = json.loads(chemin.read_text(encoding="utf-8"))
        except json.JSONDecodeError, OSError:
            journal.warning(
                "%s illisible ou corrompu, cache réinitialisé.", chemin.name
            )
            return {}
        return donnees if isinstance(donnees, dict) else {}

    def _valide(self, entree: object) -> bool:
        if not isinstance(entree, dict):
            return False
        lu_le = entree.get("lu_le")
        if not self._donnee_valide(entree.get(self._champ)) or not isinstance(
            lu_le, str
        ):
            return False
        try:
            age = datetime.now(UTC) - datetime.fromisoformat(lu_le)
        except ValueError:
            return False
        return age.total_seconds() < self._ttl

    def _lire(self, url: str) -> Any | None:
        with self._verrou:
            entree = self._entrees.get(url)
        return entree[self._champ] if self._valide(entree) and entree else None

    def _ecrire(self, url: str, donnee: dict[str, Any]) -> None:
        with self._verrou:
            self._entrees[url] = {
                "lu_le": datetime.now(UTC).isoformat(),
                self._champ: donnee,
            }
            self._modifie = True

    def enregistrer(self) -> None:
        """Écrit le cache sur le disque (sans les entrées périmées ni, au-delà
        du maximum, les plus anciennes) s'il a changé."""
        with self._verrou:
            if not self._modifie:
                return
            valides = [(u, e) for u, e in self._entrees.items() if self._valide(e)]
            valides.sort(key=lambda couple: couple[1]["lu_le"])
            self._entrees = dict(valides[-self._maximum :])
            try:
                ecriture_atomique(self._chemin(), self._entrees)
            except OSError as erreur:
                # Un cache non écrit ne gâche ni une recherche ni une consultation :
                # il sera réécrit à la prochaine occasion.
                journal.warning(
                    "%s non enregistré\u00a0: %s", self._chemin().name, erreur
                )
                return
            self._modifie = False


class CacheFichesDisque(_CacheTemporel):
    """Fiches d'offres déjà lues (voir :class:`~src.sources.base.CacheFiches`),
    gardées `TTL_FICHES` dans `data/fiches.json`.

    Une recherche qui filtre sur la fiche relit sinon des centaines de pages :
    seules les offres nouvelles sont lues. Appeler :meth:`enregistrer` en fin
    de recherche.
    """

    _champ = "fiche"
    _ttl = TTL_FICHES

    @staticmethod
    def _chemin() -> Path:
        return CHEMIN_FICHES

    @staticmethod
    def _donnee_valide(donnee: object) -> bool:
        return isinstance(donnee, dict) and set(donnee) == _CLES_FICHE

    def lire(self, url: str) -> FicheFiltrage | None:
        """Fiche mémorisée de `url`, `None` si absente ou trop ancienne."""
        return self._lire(url)

    def ecrire(self, url: str, fiche: FicheFiltrage) -> None:
        """Mémorise la fiche de `url`."""
        self._ecrire(url, dict(fiche))


class CacheDetailsDisque(_CacheTemporel):
    """Fiches de poste déjà consultées, gardées `TTL_DETAILS` (un jour : une
    offre pourvue est dépubliée) dans `data/details.json`, les `MAXIMUM_DETAILS`
    plus récentes : rouvrir une offre, ou la préparer dès sa sélection,
    n'attend plus le site.

    Seul le texte est gardé, jamais la page (`page_html` vidé).
    """

    _champ = "detail"
    _ttl = TTL_DETAILS
    _maximum = MAXIMUM_DETAILS

    @staticmethod
    def _chemin() -> Path:
        return CHEMIN_DETAILS

    @staticmethod
    def _donnee_valide(donnee: object) -> bool:
        return isinstance(donnee, dict) and set(donnee) == _CLES_DETAIL

    def lire(self, url: str) -> DetailOffre | None:
        """Fiche de poste mémorisée de `url`, `None` si absente ou trop ancienne."""
        return self._lire(url)

    def ecrire(self, url: str, detail: DetailOffre) -> None:
        """Mémorise la fiche de poste de `url` (sans la page brute)."""
        self._ecrire(url, {**detail, "page_html": ""})
