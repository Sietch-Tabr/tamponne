"""Tests de src/sources/detail.py et des outils réseau de src/sources/base.py :
fiche et disponibilité d'une offre selon son site (pas de réseau)."""

import io
from collections.abc import Callable
import urllib.error
import urllib.request
from email.message import Message

import pytest

from src.sources import base, detail
from src.sources.base import PageIntrouvable, sur_domaine, valider_url
from src.types import DetailOffre

FICHE: DetailOffre = {**detail.DETAIL_VIDE, "description": "Missions"}


# --- valider_url / sur_domaine ---


def test_valider_url_rattache_un_chemin_relatif() -> None:
    assert valider_url("/emploi/1", "https://emploi.fhf.fr", "emploi.fhf.fr") == (
        "https://emploi.fhf.fr/emploi/1"
    )


def test_valider_url_garde_le_domaine_et_ses_sous_domaines() -> None:
    for url in ("https://emploi.fhf.fr/x", "https://www.emploi.fhf.fr/x"):
        assert valider_url(url, "https://emploi.fhf.fr", "emploi.fhf.fr") == url


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/x",
        "https://emploi.fhf.fr.evil.example/x",
        "https://emploi.fhf.fr@evil.example/x",
        "javascript:alert(1)",
        "",
    ],
)
def test_valider_url_refuse_les_autres_sites(url: str) -> None:
    assert valider_url(url, "https://emploi.fhf.fr", "emploi.fhf.fr") == ""


def test_sur_domaine_lit_l_hote_sans_identifiants_ni_port() -> None:
    assert sur_domaine("https://user@emploi.fhf.fr:443/x", "emploi.fhf.fr")
    assert not sur_domaine("https://emploi.fhf.fr@evil.example/x", "emploi.fhf.fr")


# --- recuperer_detail_offre : aiguillage par site ---


@pytest.mark.parametrize(
    ("url", "module"),
    [
        ("https://choisirleservicepublic.gouv.fr/offre/x/", "choisirleservicepublic"),
        ("https://www.emploi-territorial.fr/offre/o1-x", "emploiterritorial"),
        ("https://emploi.fhf.fr/emploi/460175", "fhf"),
        ("https://www.passerelles.economie.gouv.fr/offre_1.aspx", "passerellesmef"),
    ],
)
def test_recuperer_detail_offre_utilise_l_extracteur_du_site(
    monkeypatch: pytest.MonkeyPatch, url: str, module: str
) -> None:
    appels: list[str] = []
    noms = ("choisirleservicepublic", "emploiterritorial", "fhf", "passerellesmef")

    def extracteur(nom: str) -> Callable[[str], DetailOffre]:
        def recuperer(_url: str) -> DetailOffre:
            appels.append(nom)
            return FICHE

        return recuperer

    monkeypatch.setattr(
        detail,
        "_DETAIL_PAR_DOMAINE",
        tuple(
            (domaine, extracteur(nom))
            for (domaine, _), nom in zip(detail._DETAIL_PAR_DOMAINE, noms, strict=True)
        ),
    )
    assert detail.recuperer_detail_offre(url) == FICHE
    assert appels == [module]


def test_recuperer_detail_offre_site_inconnu_fiche_vide() -> None:
    assert detail.recuperer_detail_offre("https://evil.example/offre") == (
        detail.DETAIL_VIDE
    )


# --- verifier_disponibilite ---


def _page(monkeypatch: pytest.MonkeyPatch, url_finale: str, titre: str) -> None:
    monkeypatch.setattr(detail, "consulter_page", lambda _url: (url_finale, titre))


def test_verifier_disponibilite_offre_en_ligne(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://emploi.fhf.fr/emploi/460175"
    _page(monkeypatch, url, "INFIRMIERE PUERICULTRICE")
    assert detail.verifier_disponibilite(url) is True


def test_verifier_disponibilite_page_introuvable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def introuvable(_url: str) -> tuple[str, str]:
        raise PageIntrouvable("Page introuvable (HTTP 404)")

    monkeypatch.setattr(detail, "consulter_page", introuvable)
    assert detail.verifier_disponibilite("https://emploi.fhf.fr/emploi/1") is False


def test_verifier_disponibilite_page_depubliee_csp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _page(
        monkeypatch,
        "https://choisirleservicepublic.gouv.fr/offre-depubliee/",
        "Offre dépubliée | Choisir le service public",
    )
    assert (
        detail.verifier_disponibilite(
            "https://choisirleservicepublic.gouv.fr/offre-emploi/x/"
        )
        is False
    )


def test_verifier_disponibilite_retour_a_l_accueil_passerelles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _page(
        monkeypatch,
        "https://www.passerelles.economie.gouv.fr/accueil.aspx?LCID=1036",
        "MINISTERE DE L'ECONOMIE ET DES FINANCES - Site d'offres d'emploi",
    )
    assert (
        detail.verifier_disponibilite(
            "https://www.passerelles.economie.gouv.fr/offre-de-emploi/emploi-x_1.aspx"
        )
        is False
    )


def test_verifier_disponibilite_site_injoignable_propage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def injoignable(_url: str) -> tuple[str, str]:
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(detail, "consulter_page", injoignable)
    with pytest.raises(RuntimeError, match="Erreur réseau"):
        detail.verifier_disponibilite("https://emploi.fhf.fr/emploi/1")


# --- consulter_page ---


class _Reponse(io.BytesIO):
    def __init__(self, contenu: bytes, url: str) -> None:
        super().__init__(contenu)
        self._url = url

    def geturl(self) -> str:
        return self._url


def test_consulter_page_rend_url_finale_et_titre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda requete, timeout: _Reponse(
            b"<html><title> Offre d\xc3\xa9publi\xc3\xa9e </title></html>",
            "https://choisirleservicepublic.gouv.fr/offre-depubliee/",
        ),
    )
    assert base.consulter_page("https://choisirleservicepublic.gouv.fr/x/") == (
        "https://choisirleservicepublic.gouv.fr/offre-depubliee/",
        "Offre dépubliée",
    )


@pytest.mark.parametrize("code", [404, 410])
def test_consulter_page_404_et_410_page_introuvable(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    def erreur(requete: urllib.request.Request, timeout: float) -> None:
        raise urllib.error.HTTPError(requete.full_url, code, "absent", Message(), None)

    monkeypatch.setattr(urllib.request, "urlopen", erreur)
    with pytest.raises(PageIntrouvable):
        base.consulter_page("https://emploi.fhf.fr/emploi/1")


@pytest.mark.parametrize(
    "erreur",
    [
        urllib.error.HTTPError("https://x", 503, "indisponible", Message(), None),
        urllib.error.URLError("hors ligne"),
        TimeoutError("délai dépassé"),
    ],
)
def test_consulter_page_autres_echecs_runtime_error(
    monkeypatch: pytest.MonkeyPatch, erreur: OSError
) -> None:
    def echec(requete: urllib.request.Request, timeout: float) -> None:
        raise erreur

    monkeypatch.setattr(urllib.request, "urlopen", echec)
    with pytest.raises(RuntimeError) as capture:
        base.consulter_page("https://emploi.fhf.fr/emploi/1")
    assert not isinstance(capture.value, PageIntrouvable)
