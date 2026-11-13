"""Tests de la lecture parallèle et mémorisée des fiches (src/sources/fiches.py)."""

import threading
from unittest.mock import Mock

import pytest

from src.sources import fiches
from src.sources.fiches import lire_fiches
from src.types import FicheFiltrage


def _fiche(numero: str) -> FicheFiltrage:
    return {
        "numero": numero,
        "categorie": "",
        "secteur": "",
        "direction": "",
        "experience": "",
        "management": False,
        "teletravail": False,
    }


class _Cache:
    def __init__(self, connues: dict[str, FicheFiltrage] | None = None) -> None:
        self.fiches = dict(connues or {})
        self._verrou = threading.Lock()

    def lire(self, url: str) -> FicheFiltrage | None:
        return self.fiches.get(url)

    def ecrire(self, url: str, fiche: FicheFiltrage) -> None:
        with self._verrou:
            self.fiches[url] = fiche


@pytest.fixture(autouse=True)
def _sans_attente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fiches.time, "sleep", Mock(return_value=None))


def test_lire_fiches_lit_en_parallele_et_memorise() -> None:
    cache = _Cache()
    urls = [f"https://x/{n}" for n in range(30)]
    lues = lire_fiches(urls, lambda u: _fiche(u.rsplit("/", 1)[1]), cache)
    assert {u: f["numero"] for u, f in lues.items()} == {
        u: u.rsplit("/", 1)[1] for u in urls
    }
    assert set(cache.fiches) == set(urls)


def test_lire_fiches_ne_relit_pas_une_fiche_connue() -> None:
    cache = _Cache({"https://x/1": _fiche("connue")})
    appels: list[str] = []

    def lire(url: str) -> FicheFiltrage:
        appels.append(url)
        return _fiche("neuve")

    lues = lire_fiches(["https://x/1", "https://x/2"], lire, cache)
    assert appels == ["https://x/2"]
    assert lues["https://x/1"]["numero"] == "connue"


def test_lire_fiches_illisible_absente_et_non_memorisee() -> None:
    cache = _Cache()
    assert lire_fiches(["https://x/1"], Mock(return_value=None), cache) == {}
    assert cache.fiches == {}


def test_lire_fiches_sans_cache_et_urls_en_double() -> None:
    appels: list[str] = []

    def lire(url: str) -> FicheFiltrage:
        appels.append(url)
        return _fiche("1")

    assert len(lire_fiches(["https://x/1", "https://x/1"], lire)) == 1
    assert appels == ["https://x/1"]


def test_lire_fiches_signale_chaque_fiche_lue_sans_compter_le_cache() -> None:
    cache = _Cache({"https://x/1": _fiche("75")})
    suivi: list[tuple[int, int]] = []
    lire_fiches(
        ["https://x/1", "https://x/2", "https://x/3"],
        Mock(return_value=_fiche("93")),
        cache,
        lambda lues, total: suivi.append((lues, total)),
    )
    assert suivi == [(1, 2), (2, 2)]
