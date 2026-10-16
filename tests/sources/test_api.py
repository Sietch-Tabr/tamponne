"""Tests des requêtes HTTP des sources (sites simulés) : toute erreur
réseau, délai dépassé compris, devient une RuntimeError lisible."""

from collections.abc import Callable
from typing import Any

import pytest
import urllib3

from src.sources.choisirleservicepublic import api as api_csp
from src.sources.emploiterritorial import api as api_territorial
from src.sources.fhf import api as api_fhf
from src.sources.passerellesmef import api as api_mef
from tests.sources.reponses import (
    Comportement,
    ReponseHttp,
    echec_reseau,
    simuler_reseau,
)

ERREURS = [
    pytest.param(lambda *_a: ReponseHttp(statut=503), "Erreur HTTP 503", id="http"),
    pytest.param(
        echec_reseau(urllib3.exceptions.HTTPError("hôte inconnu")),
        "hôte inconnu",
        id="reseau",
    ),
    pytest.param(
        echec_reseau(TimeoutError("timed out")), "timed out", id="delai-en-lecture"
    ),
]

APPELS_AVEC_SESSION: list[Callable[[], object]] = [
    lambda: api_fhf.obtenir_fiche_offre(
        api_fhf.nouvelle_session(), "https://emploi.fhf.fr/emploi/1"
    ),
    lambda: api_mef.obtenir_fiche_offre(
        api_mef.nouvelle_session(), "https://www.passerelles.economie.gouv.fr/x"
    ),
    lambda: api_territorial.obtenir_fiche_offre(
        api_territorial.nouvelle_session(), "https://www.emploi-territorial.fr/x"
    ),
]


@pytest.mark.parametrize("appel", APPELS_AVEC_SESSION)
@pytest.mark.parametrize(("comportement", "message"), ERREURS)
def test_requete_des_sources_erreur_en_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
    appel: Callable[[], object],
    comportement: Comportement,
    message: str,
) -> None:
    simuler_reseau(monkeypatch, comportement)
    with pytest.raises(RuntimeError, match=message):
        appel()


@pytest.mark.parametrize(
    "module", [api_fhf, api_mef, api_territorial], ids=["fhf", "mef", "territorial"]
)
def test_obtenir_page_recherche_rend_html_et_titre(
    monkeypatch: pytest.MonkeyPatch, module: Any
) -> None:
    simuler_reseau(monkeypatch, ReponseHttp("<html><title> Offres (3) </title></html>"))
    page = module.obtenir_page_recherche(
        module.nouvelle_session(), "https://exemple.test/"
    )
    assert page["title"] == "Offres (3)"


@pytest.mark.parametrize(
    "appel",
    [
        lambda: api_csp.obtenir_page_offres(
            "https://choisirleservicepublic.gouv.fr/x/"
        ),
        lambda: api_csp.telecharger_binaire(
            "https://choisirleservicepublic.gouv.fr/a.pdf"
        ),
        api_csp.telecharger_page_offres,
    ],
    ids=["page", "pdf", "organisations"],
)
@pytest.mark.parametrize(("comportement", "message"), ERREURS)
def test_choisirleservicepublic_erreur_en_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
    appel: Callable[[], object],
    comportement: Comportement,
    message: str,
) -> None:
    simuler_reseau(monkeypatch, comportement)
    with pytest.raises(RuntimeError, match=message):
        appel()
