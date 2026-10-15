"""Tests pour src/sources/choisirleservicepublic/__init__.py."""

import pytest

import src.sources.choisirleservicepublic as source
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE

_HTML_AVEC_JSON_LD = """
<script type="application/ld+json">
{"Description": "Missions principales : piloter le projet X."}
</script>
"""


def test_recuperer_detail_offre_succes_retourne_le_detail_extrait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        source,
        "obtenir_page_offres",
        lambda url: {"html": _HTML_AVEC_JSON_LD, "title": "Offre de test"},
    )
    detail = source.recuperer_detail_offre(
        "https://choisirleservicepublic.gouv.fr/offre-1/"
    )
    assert detail["description"] == "Missions principales : piloter le projet X."


def test_recuperer_detail_offre_echec_reseau_retourne_detail_vide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _leve_erreur(url: str) -> None:
        raise RuntimeError("Erreur réseau lors du chargement")

    monkeypatch.setattr(source, "obtenir_page_offres", _leve_erreur)
    assert (
        source.recuperer_detail_offre("https://choisirleservicepublic.gouv.fr/offre-1/")
        == DETAIL_VIDE
    )
