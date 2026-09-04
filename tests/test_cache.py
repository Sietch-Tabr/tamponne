"""Tests pour src/cache.py — logique TTL et purge des caches."""

from datetime import datetime, timedelta, timezone

import pytest

from src import cache
from src.types import Offre


@pytest.fixture(autouse=True)
def _rediriger_cache_vers_tmp(tmp_path, monkeypatch):
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
    }


# ---------------------------------------------------------------------------
# _organisations_expirees
# ---------------------------------------------------------------------------


def test_organisations_expirees_cache_absent():
    assert cache._organisations_expirees({}) is True


def test_organisations_expirees_cache_frais():
    entree = {"organisations": {"cached_at": _iso_il_y_a(60), "data": {}}}
    assert cache._organisations_expirees(entree) is False


def test_organisations_expirees_cache_perime():
    entree = {
        "organisations": {
            "cached_at": _iso_il_y_a(cache.TTL_ORGANISATIONS + 3600),
            "data": {},
        }
    }
    assert cache._organisations_expirees(entree) is True


def test_organisations_expirees_cached_at_type_invalide():
    """Une valeur cached_at non-str (JSON corrompu) doit être traitée comme expirée."""
    entree = {"organisations": {"cached_at": None, "data": {}}}
    assert cache._organisations_expirees(entree) is True


def test_organisations_expirees_cle_manquante():
    entree = {"organisations": {"data": {}}}
    assert cache._organisations_expirees(entree) is True


# ---------------------------------------------------------------------------
# age_cache_organisations
# ---------------------------------------------------------------------------


def test_age_cache_organisations_absent():
    assert cache.age_cache_organisations() is None


def test_age_cache_organisations_minutes():
    cache._sauvegarder_cache(
        {"organisations": {"cached_at": _iso_il_y_a(120), "data": {}}}
    )
    assert cache.age_cache_organisations() == "il y a 2 min"


def test_age_cache_organisations_heures():
    cache._sauvegarder_cache(
        {"organisations": {"cached_at": _iso_il_y_a(3 * 3600), "data": {}}}
    )
    assert cache.age_cache_organisations() == "il y a 3 h"


def test_age_cache_organisations_type_invalide_retourne_none():
    cache._sauvegarder_cache({"organisations": {"cached_at": None, "data": {}}})
    assert cache.age_cache_organisations() is None


# ---------------------------------------------------------------------------
# _charger_cache / _charger_offres : JSON corrompu
# ---------------------------------------------------------------------------


def test_charger_cache_corrompu_retourne_dict_vide():
    cache.CHEMIN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    cache.CHEMIN_CACHE.write_text("{ceci n'est pas du json", encoding="utf-8")
    assert cache._charger_cache() == {}


def test_charger_offres_corrompu_retourne_dict_vide():
    cache.CHEMIN_OFFRES.parent.mkdir(parents=True, exist_ok=True)
    cache.CHEMIN_OFFRES.write_text("{ceci n'est pas du json", encoding="utf-8")
    assert cache._charger_offres() == {}


# ---------------------------------------------------------------------------
# maj_cache_offres
# ---------------------------------------------------------------------------


def test_maj_cache_offres_toutes_nouvelles_au_premier_passage():
    nouvelles = cache.maj_cache_offres("mon-profil", [_offre("REF1"), _offre("REF2")])
    assert nouvelles == {"REF1", "REF2"}


def test_maj_cache_offres_pas_nouvelle_au_second_passage_immediat():
    cache.maj_cache_offres("mon-profil", [_offre("REF1")])
    nouvelles = cache.maj_cache_offres("mon-profil", [_offre("REF1")])
    # Toujours "nouvelle" tant qu'on est sous TTL_NOUVELLES (vue à l'instant).
    assert nouvelles == {"REF1"}


def test_maj_cache_offres_plus_nouvelle_apres_ttl_nouvelles():
    toutes = {
        "mon-profil": {
            "REF1": {
                **_offre("REF1"),
                "vu_le": _iso_il_y_a(cache.TTL_NOUVELLES + 60),
                "derniere_vue": _iso_il_y_a(60),
            }
        }
    }
    cache._sauvegarder_offres(toutes)
    nouvelles = cache.maj_cache_offres("mon-profil", [_offre("REF1")])
    assert nouvelles == set()


def test_maj_cache_offres_purge_offre_disparue_depuis_longtemps():
    toutes = {
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


def test_maj_cache_offres_conserve_offre_disparue_recemment():
    toutes = {
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


def test_maj_cache_offres_purge_immediate_si_derniere_vue_non_parsable():
    toutes = {
        "mon-profil": {
            "REF1": {**_offre("REF1"), "vu_le": _iso_il_y_a(60), "derniere_vue": None}
        }
    }
    cache._sauvegarder_offres(toutes)
    cache.maj_cache_offres("mon-profil", [])
    assert cache.obtenir_offres_cachetees("mon-profil") == {}


def test_maj_cache_offres_ignore_offres_sans_reference():
    offre_sans_ref = _offre("")
    offre_sans_ref["reference"] = ""
    nouvelles = cache.maj_cache_offres("mon-profil", [offre_sans_ref])
    assert nouvelles == set()
    assert cache.obtenir_offres_cachetees("mon-profil") == {}
