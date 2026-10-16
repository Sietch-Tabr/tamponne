"""Tests de src/sources/detail.py et des outils réseau de src/sources/base.py :
fiche et disponibilité d'une offre selon son site (pas de réseau)."""

from collections.abc import Callable

import pytest
import urllib3

from src.sources import base, detail
from src.sources.base import PageIntrouvable, sur_domaine, valider_url
from src.types import DetailOffre
from tests.sources.reponses import (
    Comportement,
    ReponseHttp,
    echec_reseau,
    simuler_reseau,
)

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


def test_consulter_page_rend_url_finale_et_titre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def comportement(
        methode: str, url: str, corps: object, entetes: dict[str, str]
    ) -> ReponseHttp:
        if url.endswith("/x/"):
            return ReponseHttp(
                statut=302,
                entetes={
                    "Location": "https://choisirleservicepublic.gouv.fr/offre-depubliee/"
                },
            )
        return ReponseHttp("<html><title> Offre dépubliée </title></html>")

    simuler_reseau(monkeypatch, comportement)
    assert base.consulter_page("https://choisirleservicepublic.gouv.fr/x/") == (
        "https://choisirleservicepublic.gouv.fr/offre-depubliee/",
        "Offre dépubliée",
    )


@pytest.mark.parametrize("code", [404, 410])
def test_consulter_page_404_et_410_page_introuvable(
    monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    simuler_reseau(monkeypatch, ReponseHttp(statut=code))
    with pytest.raises(PageIntrouvable):
        base.consulter_page("https://emploi.fhf.fr/emploi/1")


@pytest.mark.parametrize(
    "comportement",
    [
        lambda *_a: ReponseHttp(statut=503),
        echec_reseau(urllib3.exceptions.HTTPError("hors ligne")),
        echec_reseau(TimeoutError("délai dépassé")),
    ],
    ids=["http", "reseau", "delai"],
)
def test_consulter_page_autres_echecs_runtime_error(
    monkeypatch: pytest.MonkeyPatch, comportement: Comportement
) -> None:
    simuler_reseau(monkeypatch, comportement)
    with pytest.raises(RuntimeError) as capture:
        base.consulter_page("https://emploi.fhf.fr/emploi/1")
    assert not isinstance(capture.value, PageIntrouvable)


# --- texte_lisible ---


def _bloc(html: str) -> object:
    from bs4 import BeautifulSoup

    return BeautifulSoup(f"<div>{html}</div>", "html.parser").div


def test_texte_lisible_garde_les_sauts_de_ligne_du_site() -> None:
    bloc = _bloc("Gardien brigadier\n      <br/>\n   Brigadier-chef principal<br/>")
    assert base.texte_lisible(bloc) == "Gardien brigadier\nBrigadier-chef principal"  # type: ignore[arg-type]


def test_texte_lisible_met_les_listes_en_puces() -> None:
    bloc = _bloc(
        "<ul><li>SAVOIR-FAIRE - Analyser </li><li>SAVOIR-ÊTRE - Réactivité</li></ul>"
    )
    assert base.texte_lisible(bloc) == (  # type: ignore[arg-type]
        "• SAVOIR-FAIRE - Analyser\n• SAVOIR-ÊTRE - Réactivité"
    )


def test_texte_lisible_separe_les_paragraphes_d_une_ligne_vide() -> None:
    bloc = _bloc("<p>Premier   paragraphe.</p>\n<p>Second.</p><br/><br/><br/>Fin")
    assert base.texte_lisible(bloc) == "Premier paragraphe.\n\nSecond.\n\nFin"  # type: ignore[arg-type]


def test_adresse_cloudflare_decode_l_adresse_masquee() -> None:
    """Code réel d'une fiche FHF (2026-10-13)."""
    assert base.adresse_cloudflare("89edfbe1c9eae1a4ede6fce8e0a7effb") == (
        "drh@ch-douai.fr"
    )
    assert base.adresse_cloudflare("pas-hexa") == ""
    assert base.adresse_cloudflare("89") == ""


def test_texte_lisible_rend_les_adresses_masquees() -> None:
    bloc = _bloc(
        'ou par mail:<br/><a href="/cdn-cgi/l/email-protection" class="__cf_email__"'
        ' data-cfemail="89edfbe1c9eae1a4ede6fce8e0a7effb">[email&#160;protected]</a>'
    )
    assert base.texte_lisible(bloc) == "ou par mail:\ndrh@ch-douai.fr"  # type: ignore[arg-type]
