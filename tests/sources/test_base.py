"""Tests du dédoublonnage multi-source (src/sources/base.py)."""

import gzip
import urllib.request
from collections.abc import Callable

import pytest

from src.sources.base import (
    EN_TETE_COMPRESSION,
    USER_AGENT_IDENTIFIE,
    deduplique_offres,
    lire_reponse,
    lire_texte,
)
from src.sources.choisirleservicepublic import api as api_csp
from src.sources.fhf import api as api_fhf
from src.sources.passerellesmef import api as api_mef
from src.types import Offre
from tests.sources.reponses import ReponseHttp


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
    assert api_fhf._HEADERS["User-Agent"] == USER_AGENT_IDENTIFIE
    assert api_mef._HEADERS["User-Agent"] == USER_AGENT_IDENTIFIE


@pytest.mark.parametrize(
    "telecharger",
    [
        lambda: api_csp.obtenir_page_offres("https://exemple.test/"),
        lambda: api_csp.telecharger_binaire("https://exemple.test/a.pdf"),
        api_csp.telecharger_page_offres,
    ],
)
def test_choisirleservicepublic_envoie_le_user_agent_identifie(
    monkeypatch: pytest.MonkeyPatch, telecharger: Callable[[], object]
) -> None:
    requetes: list[urllib.request.Request] = []

    def urlopen_factice(requete: urllib.request.Request, timeout: float) -> ReponseHttp:
        requetes.append(requete)
        return ReponseHttp(b"<title>t</title>")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_factice)
    telecharger()

    assert requetes[0].get_header("User-agent") == USER_AGENT_IDENTIFIE


def test_reseau_interdit_pendant_les_tests() -> None:
    """Garde-fou de conftest : un vrai appel réseau échoue tout de suite."""
    with pytest.raises(OSError, match="interdite"):
        urllib.request.urlopen("https://codeberg.org", timeout=5)


def test_les_clients_demandent_des_pages_compressees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requetes: list[urllib.request.Request] = []

    def urlopen_factice(requete: urllib.request.Request, timeout: float) -> ReponseHttp:
        requetes.append(requete)
        return ReponseHttp(b"<title>t</title>")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_factice)
    api_csp.telecharger_page_offres()

    assert requetes[0].get_header("Accept-encoding") == "gzip"
    assert EN_TETE_COMPRESSION == {"Accept-Encoding": "gzip"}


def test_lire_texte_decompresse_une_reponse_gzip() -> None:
    texte = "Chargé de mission numérique" * 50
    reponse = ReponseHttp(
        gzip.compress(texte.encode()), headers={"Content-Encoding": "gzip"}
    )
    assert lire_texte(reponse) == texte


def test_lire_reponse_laisse_une_reponse_non_compressee_telle_quelle() -> None:
    assert lire_reponse(ReponseHttp(b"abc")) == b"abc"


def test_lire_reponse_gzip_illisible_est_une_erreur_reseau() -> None:
    reponse = ReponseHttp(b"pas du gzip", headers={"Content-Encoding": "gzip"})
    with pytest.raises(OSError, match="illisible"):
        lire_reponse(reponse)
