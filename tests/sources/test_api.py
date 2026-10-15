"""Tests des requêtes HTTP des sources (sites simulés) : toute erreur
réseau, délai dépassé compris, devient une RuntimeError lisible."""

import io
import urllib.error
import urllib.request
from collections.abc import Callable
from email.message import Message

import pytest

from src.sources.choisirleservicepublic import api as api_csp
from src.sources.emploiterritorial import api as api_territorial
from src.sources.fhf import api as api_fhf
from src.sources.passerellesmef import api as api_mef

ERREURS = [
    pytest.param(
        urllib.error.HTTPError("https://x", 503, "indisponible", Message(), None),
        "Erreur HTTP 503",
        id="http",
    ),
    pytest.param(urllib.error.URLError("hôte inconnu"), "hôte inconnu", id="reseau"),
    pytest.param(TimeoutError("timed out"), "timed out", id="delai-en-lecture"),
]


class _Ouvreur:
    """`OpenerDirector` simulé : rend `contenu` ou lève `erreur`."""

    def __init__(self, contenu: bytes = b"", erreur: OSError | None = None) -> None:
        self.contenu = contenu
        self.erreur = erreur

    def open(self, _requete: urllib.request.Request, timeout: float) -> io.BytesIO:
        if self.erreur is not None:
            raise self.erreur
        return io.BytesIO(self.contenu)


APPELS_AVEC_OUVREUR: list[Callable[[object], object]] = [
    lambda o: api_fhf.obtenir_fiche_offre(o, "https://emploi.fhf.fr/emploi/1"),  # type: ignore[arg-type]
    lambda o: api_mef.obtenir_fiche_offre(o, "https://www.passerelles.economie.gouv.fr/x"),  # type: ignore[arg-type]
    lambda o: api_territorial.obtenir_fiche_offre(o, "https://www.emploi-territorial.fr/x"),  # type: ignore[arg-type]
]


@pytest.mark.parametrize("appel", APPELS_AVEC_OUVREUR)
@pytest.mark.parametrize(("erreur", "message"), ERREURS)
def test_requete_des_sources_erreur_en_runtime_error(
    appel: Callable[[object], object], erreur: OSError, message: str
) -> None:
    with pytest.raises(RuntimeError, match=message):
        appel(_Ouvreur(erreur=erreur))


@pytest.mark.parametrize(
    "module", [api_fhf, api_mef, api_territorial], ids=["fhf", "mef", "territorial"]
)
def test_obtenir_page_recherche_rend_html_et_titre(module: object) -> None:
    ouvreur = _Ouvreur(b"<html><title> Offres (3) </title></html>")
    page = module.obtenir_page_recherche(ouvreur, "https://exemple.test/")  # type: ignore[attr-defined]
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
@pytest.mark.parametrize(("erreur", "message"), ERREURS)
def test_choisirleservicepublic_erreur_en_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
    appel: Callable[[], object],
    erreur: OSError,
    message: str,
) -> None:
    def echec(_requete: urllib.request.Request, timeout: float) -> None:
        raise erreur

    monkeypatch.setattr(urllib.request, "urlopen", echec)
    with pytest.raises(RuntimeError, match=message):
        appel()
