"""Tests pour src/cache.py — logique TTL et purge des caches."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

import pytest

from src import cache
from src.types import Offre, OffreCache


@pytest.fixture(autouse=True)
def _rediriger_cache_vers_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirige les fichiers de cache vers un répertoire temporaire isolé."""
    monkeypatch.setattr(cache, "CHEMIN_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(cache, "CHEMIN_OFFRES", tmp_path / "offres.json")


def _iso_il_y_a(secondes: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=secondes)).isoformat()


def _offre(reference: str) -> Offre:
    return {
        "titre": f"Poste {reference}",
        "url": "",
        "reference": reference,
        "domaine": "",
        "employeur": "",
        "localisation": "",
        "versant": "",
        "date": "",
        "source": "",
    }


# --- _organisations_expirees ---


def test_organisations_expirees_cache_absent() -> None:
    assert cache._organisations_expirees({}) is True


def test_organisations_expirees_cache_frais() -> None:
    entree = {"organisations": {"cached_at": _iso_il_y_a(60), "data": {}}}
    assert cache._organisations_expirees(entree) is False


def test_organisations_expirees_cache_perime() -> None:
    entree = {
        "organisations": {
            "cached_at": _iso_il_y_a(cache.TTL_ORGANISATIONS + 3600),
            "data": {},
        }
    }
    assert cache._organisations_expirees(entree) is True


def test_organisations_expirees_cached_at_type_invalide() -> None:
    """Une valeur cached_at non-str (JSON corrompu) doit être traitée comme expirée."""
    entree: dict[str, Any] = {"organisations": {"cached_at": None, "data": {}}}
    assert cache._organisations_expirees(entree) is True


def test_organisations_expirees_cle_manquante() -> None:
    entree: dict[str, Any] = {"organisations": {"data": {}}}
    assert cache._organisations_expirees(entree) is True


# --- age_cache_organisations ---


def test_age_cache_organisations_absent() -> None:
    assert cache.age_cache_organisations() is None


def test_age_cache_organisations_minutes() -> None:
    cache._sauvegarder_cache(
        {"organisations": {"cached_at": _iso_il_y_a(120), "data": {}}}
    )
    assert cache.age_cache_organisations() == "il y a 2 min"


def test_age_cache_organisations_heures() -> None:
    cache._sauvegarder_cache(
        {"organisations": {"cached_at": _iso_il_y_a(3 * 3600), "data": {}}}
    )
    assert cache.age_cache_organisations() == "il y a 3 h"


def test_age_cache_organisations_type_invalide_retourne_none() -> None:
    cache._sauvegarder_cache({"organisations": {"cached_at": None, "data": {}}})
    assert cache.age_cache_organisations() is None


# --- _charger_cache / _charger_offres : JSON corrompu ---


def test_charger_cache_corrompu_retourne_dict_vide() -> None:
    cache.CHEMIN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache.CHEMIN_CACHE.write_text("{ceci n'est pas du json", encoding="utf-8")
    assert cache._charger_cache() == {}


def test_charger_offres_corrompu_retourne_dict_vide() -> None:
    cache.CHEMIN_OFFRES.parent.mkdir(parents=True, exist_ok=True)
    cache.CHEMIN_OFFRES.write_text("{ceci n'est pas du json", encoding="utf-8")
    assert cache._charger_offres() == {}


# --- maj_cache_offres ---


def test_maj_cache_offres_toutes_nouvelles_au_premier_passage() -> None:
    nouvelles = cache.maj_cache_offres("mon-profil", [_offre("REF1"), _offre("REF2")])
    assert nouvelles == {"REF1", "REF2"}


def test_maj_cache_offres_deja_vue_n_est_plus_nouvelle() -> None:
    cache.maj_cache_offres("mon-profil", [_offre("REF1")])
    nouvelles = cache.maj_cache_offres("mon-profil", [_offre("REF1"), _offre("REF2")])
    assert nouvelles == {"REF2"}


def test_maj_cache_offres_purge_offre_disparue_depuis_longtemps() -> None:
    toutes: dict[str, dict[str, OffreCache]] = {
        "mon-profil": {
            "REF1": {
                **_offre("REF1"),
                "vu_le": _iso_il_y_a(cache.TTL_OFFRES + 3600),
                "derniere_vue": _iso_il_y_a(cache.TTL_OFFRES + 3600),
            }
        }
    }
    cache._sauvegarder_offres(toutes)
    cache.maj_cache_offres("mon-profil", [])
    assert cache.obtenir_offres_cachetees("mon-profil") == {}


def test_maj_cache_offres_conserve_offre_disparue_recemment() -> None:
    toutes: dict[str, dict[str, OffreCache]] = {
        "mon-profil": {
            "REF1": {
                **_offre("REF1"),
                "vu_le": _iso_il_y_a(60),
                "derniere_vue": _iso_il_y_a(60),
            }
        }
    }
    cache._sauvegarder_offres(toutes)
    cache.maj_cache_offres("mon-profil", [])
    assert "REF1" in cache.obtenir_offres_cachetees("mon-profil")


def test_maj_cache_offres_purge_immediate_si_derniere_vue_non_parsable() -> None:
    toutes: dict[str, dict[str, OffreCache]] = {
        "mon-profil": {
            # derniere_vue invalide volontairement : cas d'un cache corrompu.
            "REF1": cast(
                OffreCache,
                {**_offre("REF1"), "vu_le": _iso_il_y_a(60), "derniere_vue": None},
            )
        }
    }
    cache._sauvegarder_offres(toutes)
    cache.maj_cache_offres("mon-profil", [])
    assert cache.obtenir_offres_cachetees("mon-profil") == {}


def test_maj_cache_offres_ignore_offres_sans_reference() -> None:
    offre_sans_ref = _offre("")
    offre_sans_ref["reference"] = ""
    nouvelles = cache.maj_cache_offres("mon-profil", [offre_sans_ref])
    assert nouvelles == set()
    assert cache.obtenir_offres_cachetees("mon-profil") == {}
