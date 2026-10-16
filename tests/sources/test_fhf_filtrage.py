"""Tests du filtrage par localisation de la source FHF (pas de réseau)."""

import pytest

from src.sources import fhf
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.fhf.filtrage import extraire_fiche
from src.types import DetailOffre, Offre


def _detail(adresse: str) -> DetailOffre:
    return {
        **DETAIL_VIDE,
        "page_html": "<html>",
        "sections_complementaires": {"Etablissement": adresse},
    }


def _offre(reference: str, ville: str) -> Offre:
    return {
        "titre": f"Offre {reference}",
        "url": f"https://exemple.test/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": "",
        "localisation": ville,
        "versant": "",
        "date": "",
        "source": "",
    }


def test_extraire_fiche_lit_le_departement_dans_l_adresse_de_l_etablissement() -> None:
    fiche = extraire_fiche(
        _detail("Site hospitalier Broussais\n1, rue de la Marne\n35403 Saint-Malo")
    )
    assert fiche is not None
    assert fiche["numero"] == "35"


def test_extraire_fiche_illisible_retourne_none() -> None:
    assert extraire_fiche(DETAIL_VIDE) is None


@pytest.fixture
def _site(monkeypatch: pytest.MonkeyPatch) -> dict[str, DetailOffre]:
    fiches: dict[str, DetailOffre] = {}
    pages = iter(
        [
            [_offre("toulouse", "Toulouse"), _offre("brest", "Brest")],
            [_offre("sans-ville", "")],
            [],
        ]
    )
    monkeypatch.setattr(fhf.time, "sleep", lambda _s: None)
    monkeypatch.setattr(fhf, "nouvelle_session", lambda: None)
    monkeypatch.setattr(
        fhf, "obtenir_page_recherche", lambda _o, _u: {"html": "", "title": ""}
    )
    monkeypatch.setattr(fhf, "extraire_offres", lambda _h: next(pages, []))
    monkeypatch.setattr(
        fhf,
        "recuperer_detail_offre",
        lambda url: fiches.get(url.rsplit("/", 1)[1], DETAIL_VIDE),
    )
    return fiches


def test_rechercher_localisation_filtre_sur_le_code_postal_de_la_fiche(
    _site: dict[str, DetailOffre],
) -> None:
    _site["toulouse"] = _detail("Hôtel-Dieu\n31059 Toulouse Cedex")
    _site["brest"] = _detail("CHU\n29200 Brest")
    _site["sans-ville"] = _detail("Hôpital\n31000 Toulouse")
    offres, _, _ = fhf.Fhf().rechercher({"localisations": ["Haute Garonne"]})
    assert [(o["reference"], o["localisation"]) for o in offres] == [
        ("toulouse", "Toulouse (31)"),
        ("sans-ville", "Haute Garonne (31)"),
    ]


def test_rechercher_localisation_fiche_illisible_est_gardee(
    _site: dict[str, DetailOffre],
) -> None:
    offres, _, _ = fhf.Fhf().rechercher({"localisations": ["Paris"]})
    assert len(offres) == 3
