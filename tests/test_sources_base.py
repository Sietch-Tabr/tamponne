"""Tests du dédoublonnage multi-source (src/sources/base.py)."""

from src.sources.base import USER_AGENT_IDENTIFIE, deduplique_offres
from src.sources.choisirleservicepublic import api as api_csp
from src.sources.fhf import api as api_fhf
from src.sources.passerellesmef import api as api_mef
from src.types import Offre


def _offre(reference: str, titre: str = "x", source: str = "") -> Offre:
    return {
        "titre": titre,
        "url": "",
        "reference": reference,
        "domaine": "",
        "employeur": "",
        "localisation": "",
        "versant": "",
        "date": "",
        "source": source,
    }


def test_deduplique_conserve_la_premiere_occurrence() -> None:
    csp = _offre("O123", titre="Version CSP", source="")
    territorial = _offre("O123", titre="Version territoriale", source="Territorial")
    resultat = deduplique_offres([csp, territorial])
    assert len(resultat) == 1
    assert resultat[0]["titre"] == "Version CSP"


def test_deduplique_ignore_la_casse() -> None:
    csp = _offre("o123")
    territorial = _offre("O123")
    resultat = deduplique_offres([csp, territorial])
    assert len(resultat) == 1


def test_deduplique_garde_les_offres_uniques_a_chaque_source() -> None:
    csp_seule = _offre("MEF_2026-1")
    territorial_seule = _offre("O456")
    resultat = deduplique_offres([csp_seule, territorial_seule])
    assert len(resultat) == 2


def test_deduplique_reference_vide_jamais_fusionnee() -> None:
    a = _offre("", titre="Offre A")
    b = _offre("", titre="Offre B")
    resultat = deduplique_offres([a, b])
    assert len(resultat) == 2


def test_deduplique_liste_vide() -> None:
    assert deduplique_offres([]) == []


def test_user_agent_identifie_designe_le_depot_codeberg() -> None:
    assert USER_AGENT_IDENTIFIE.startswith("tamponne ")
    assert "https://codeberg.org/Kwaite/tamponne" in USER_AGENT_IDENTIFIE


def test_sources_sans_waf_envoient_le_user_agent_identifie() -> None:
    assert ("User-Agent", USER_AGENT_IDENTIFIE) in api_csp._OPENER.addheaders
    assert api_fhf._HEADERS["User-Agent"] == USER_AGENT_IDENTIFIE
    assert api_mef._HEADERS["User-Agent"] == USER_AGENT_IDENTIFIE
