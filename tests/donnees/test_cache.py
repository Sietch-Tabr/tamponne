"""Tests pour src/donnees/cache.py — logique TTL et purge des caches."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from src.donnees import cache
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.types import DetailOffre, FicheFiltrage, Offre, OffreCache


@pytest.fixture(autouse=True)
def _rediriger_cache_vers_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirige les fichiers de cache vers un répertoire temporaire isolé."""
    monkeypatch.setattr(cache, "CHEMIN_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(cache, "CHEMIN_OFFRES", tmp_path / "offres.json")
    monkeypatch.setattr(cache, "CHEMIN_FICHES", tmp_path / "fiches.json")
    monkeypatch.setattr(cache, "CHEMIN_DETAILS", tmp_path / "details.json")


def _iso_il_y_a(secondes: float) -> str:
    return (datetime.now(UTC) - timedelta(seconds=secondes)).isoformat()


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


# --- date_cache_organisations ---


def test_date_cache_organisations_absent() -> None:
    assert cache.date_cache_organisations() is None


def test_date_cache_organisations_lue_dans_le_cache() -> None:
    moment = datetime(2026, 10, 12, 12, 5, tzinfo=UTC)
    cache._sauvegarder_cache(
        {"organisations": {"cached_at": moment.isoformat(), "data": {}}}
    )
    assert cache.date_cache_organisations() == moment


def test_date_cache_organisations_type_invalide_retourne_none() -> None:
    cache._sauvegarder_cache({"organisations": {"cached_at": None, "data": {}}})
    assert cache.date_cache_organisations() is None


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


# --- organisations_en_cache ---


def test_organisations_en_cache_absentes_a_rafraichir() -> None:
    assert cache.organisations_en_cache() == ({}, True)


def test_organisations_en_cache_perimees_gardees_en_attendant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Le démarrage ne consulte jamais le site : une liste périmée sert en
    attendant son rafraîchissement en arrière-plan."""

    def interdit() -> str:
        raise AssertionError("aucun accès réseau attendu")

    monkeypatch.setattr(cache, "telecharger_page_offres", interdit)
    orgas = {"Ministère": {"Direction": 12}}
    cache._sauvegarder_cache(
        {
            "organisations": {
                "cached_at": _iso_il_y_a(cache.TTL_ORGANISATIONS + 60),
                "data": orgas,
            }
        }
    )
    assert cache.organisations_en_cache() == (orgas, True)
    cache._sauvegarder_cache(
        {"organisations": {"cached_at": _iso_il_y_a(60), "data": orgas}}
    )
    assert cache.organisations_en_cache() == (orgas, False)


# --- cache des fiches lues pour filtrer ---


def _fiche(numero: str = "75") -> FicheFiltrage:
    return {
        "numero": numero,
        "categorie": "A",
        "secteur": "Numérique - Développeur",
        "direction": "DGFiP",
        "experience": "Confirmé",
        "management": False,
        "teletravail": True,
    }


def test_cache_fiches_ecrit_puis_relit_apres_rechargement() -> None:
    cache_fiches = cache.CacheFichesDisque()
    assert cache_fiches.lire("https://x/1") is None
    cache_fiches.ecrire("https://x/1", _fiche())
    cache_fiches.enregistrer()
    assert cache.CacheFichesDisque().lire("https://x/1") == _fiche()


def test_cache_fiches_n_ecrit_rien_sans_modification() -> None:
    cache.CacheFichesDisque().enregistrer()
    assert not cache.CHEMIN_FICHES.exists()


def test_cache_fiches_ignore_et_purge_une_fiche_perimee() -> None:
    ancienne = datetime.now(UTC) - timedelta(seconds=cache.TTL_FICHES + 60)
    cache.CHEMIN_FICHES.write_text(
        json.dumps(
            {
                "https://x/vieille": {
                    "lu_le": ancienne.isoformat(),
                    "fiche": _fiche(),
                }
            }
        ),
        encoding="utf-8",
    )
    cache_fiches = cache.CacheFichesDisque()
    assert cache_fiches.lire("https://x/vieille") is None
    cache_fiches.ecrire("https://x/neuve", _fiche("92"))
    cache_fiches.enregistrer()
    assert set(json.loads(cache.CHEMIN_FICHES.read_text(encoding="utf-8"))) == {
        "https://x/neuve"
    }


def test_cache_fiches_fichier_corrompu_repart_de_zero() -> None:
    cache.CHEMIN_FICHES.write_text("pas du json", encoding="utf-8")
    assert cache.CacheFichesDisque().lire("https://x/1") is None


def test_cache_fiches_entree_au_format_inattendu_est_ignoree() -> None:
    cache.CHEMIN_FICHES.write_text(
        json.dumps({"https://x/1": {"lu_le": "x", "fiche": {"numero": "75"}}}),
        encoding="utf-8",
    )
    assert cache.CacheFichesDisque().lire("https://x/1") is None


def _detail(description: str = "Missions.") -> DetailOffre:
    return {
        **DETAIL_VIDE,
        "description": description,
        "page_html": "<html>" + "x" * 1000,
    }


def test_cache_details_garde_le_texte_mais_pas_la_page() -> None:
    cache_details = cache.CacheDetailsDisque()
    cache_details.ecrire("https://x/1", _detail())
    cache_details.enregistrer()

    relu = cache.CacheDetailsDisque().lire("https://x/1")
    assert relu is not None
    assert relu["description"] == "Missions."
    assert relu["page_html"] == ""


def test_cache_details_ignore_un_detail_perime() -> None:
    cache.CHEMIN_DETAILS.write_text(
        json.dumps(
            {
                "https://x/vieux": {
                    "lu_le": _iso_il_y_a(cache.TTL_DETAILS + 60),
                    "detail": _detail(),
                }
            }
        ),
        encoding="utf-8",
    )
    assert cache.CacheDetailsDisque().lire("https://x/vieux") is None


def test_cache_details_ne_garde_que_les_plus_recents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cache.CacheDetailsDisque, "_maximum", 2)
    cache_details = cache.CacheDetailsDisque()
    for numero in (1, 2, 3):
        cache_details.ecrire(f"https://x/{numero}", _detail(f"Poste {numero}"))
    cache_details.enregistrer()

    assert set(json.loads(cache.CHEMIN_DETAILS.read_text(encoding="utf-8"))) == {
        "https://x/2",
        "https://x/3",
    }


def test_cache_details_entree_au_format_inattendu_est_ignoree() -> None:
    cache.CHEMIN_DETAILS.write_text(
        json.dumps({"https://x/1": {"lu_le": _iso_il_y_a(5), "detail": {"a": 1}}}),
        encoding="utf-8",
    )
    assert cache.CacheDetailsDisque().lire("https://x/1") is None


def test_cache_details_non_enregistre_sans_lever_si_le_fichier_est_tenu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(_chemin: Path, _donnees: dict[str, Any]) -> None:
        raise PermissionError("tenu par l'antivirus")

    monkeypatch.setattr(cache, "ecriture_atomique", refuse)
    cache_details = cache.CacheDetailsDisque()
    cache_details.ecrire("https://x/1", _detail())
    cache_details.enregistrer()  # ne lève pas
    assert not cache.CHEMIN_DETAILS.exists()

    monkeypatch.undo()
    cache_details.enregistrer()  # réessayé à l'occasion suivante
    assert cache.CHEMIN_DETAILS.exists()


def test_cache_fiches_non_enregistre_sans_lever_si_le_fichier_est_tenu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(_chemin: Path, _donnees: dict[str, Any]) -> None:
        raise PermissionError("tenu")

    monkeypatch.setattr(cache, "ecriture_atomique", refuse)
    cache_fiches = cache.CacheFichesDisque()
    cache_fiches.ecrire("https://x/1", _fiche())
    cache_fiches.enregistrer()  # ne lève pas


def test_maj_cache_offres_rend_les_nouvelles_meme_si_l_ecriture_echoue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(_offres: object) -> None:
        raise PermissionError("tenu")

    monkeypatch.setattr(cache, "_sauvegarder_offres", refuse)
    assert cache.maj_cache_offres("mon-profil", [_offre("REF1")]) == {"REF1"}
