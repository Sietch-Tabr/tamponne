"""Tests du client HTTP partagé (src/sources/reseau.py) : cookies,
redirections, erreurs et proxy sur un faux gestionnaire ; réutilisation des
connexions et compression sur un vrai serveur local."""

import base64
import gzip
import socket
import socketserver
import threading
import urllib.request
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import urllib3

from src.sources import reseau
from src.sources.reseau import ErreurHttp, Session
from tests.sources.reponses import (
    ReponseHttp,
    echec_reseau,
    simuler_reseau,
)

# Pris avant la fixture qui interdit le réseau : seul le serveur local s'en sert.
_CONNEXION_REELLE = socket.socket.connect
_CREATION_REELLE = socket.create_connection


def test_lire_rend_le_texte_de_la_reponse(monkeypatch: pytest.MonkeyPatch) -> None:
    simuler_reseau(monkeypatch, ReponseHttp("Chargé de mission"))
    reponse = Session({}).lire("https://exemple.test/")
    assert reponse.texte() == "Chargé de mission"
    assert reponse.url == "https://exemple.test/"


def test_les_cookies_recus_sont_renvoyes_au_meme_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    faux = simuler_reseau(
        monkeypatch,
        lambda *_a: ReponseHttp(
            entetes={"Set-Cookie": ["PHPSESSID=abc; path=/; HttpOnly", "x=1"]}
        ),
    )
    session = Session({"User-Agent": "test"})
    session.lire("https://exemple.test/a")
    session.lire("https://exemple.test/b")
    session.lire("https://autre.test/")

    assert "Cookie" not in faux.appels[0][3]
    assert faux.appels[1][3]["Cookie"] == "PHPSESSID=abc; x=1"
    assert "Cookie" not in faux.appels[2][3]


def test_un_cookie_efface_par_le_site_n_est_plus_renvoye(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    faux = simuler_reseau(
        monkeypatch,
        lambda *_a: ReponseHttp(
            entetes={
                "Set-Cookie": [
                    "keep=1; path=/",
                    "map_set=deleted; expires=Thu, 01-Jan-1970 00:00:01 GMT; Max-Age=0",
                    "vieux=1; expires=Thu, 01 Jan 1970 00:00:01 GMT",
                ]
            }
        ),
    )
    session = Session({})
    session.lire("https://exemple.test/a")
    session.lire("https://exemple.test/b")
    assert faux.appels[1][3]["Cookie"] == "keep=1"


def test_deux_sessions_ne_partagent_pas_leurs_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    faux = simuler_reseau(
        monkeypatch, lambda *_a: ReponseHttp(entetes={"Set-Cookie": "s=1"})
    )
    Session({}).lire("https://exemple.test/")
    Session({}).lire("https://exemple.test/")
    assert "Cookie" not in faux.appels[1][3]


def test_une_redirection_apres_un_post_devient_un_get_avec_les_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def comportement(
        methode: str, url: str, corps: object, entetes: dict[str, str]
    ) -> ReponseHttp:
        if methode == "POST":
            return ReponseHttp(
                statut=302,
                entetes={"Location": "/resultats", "Set-Cookie": "critere=a"},
            )
        return ReponseHttp("page 1")

    faux = simuler_reseau(monkeypatch, comportement)
    reponse = Session({}).lire("https://exemple.test/recherche", {"q": "réseau"})

    assert reponse.url == "https://exemple.test/resultats"
    assert reponse.texte() == "page 1"
    assert faux.appels[0][0] == "POST"
    assert faux.appels[0][3]["Content-Type"] == "application/x-www-form-urlencoded"
    assert faux.appels[1][0] == "GET"
    assert faux.appels[1][2] is None
    assert faux.appels[1][3]["Cookie"] == "critere=a"


def test_une_redirection_307_garde_le_post(monkeypatch: pytest.MonkeyPatch) -> None:
    def comportement(
        methode: str, url: str, corps: object, entetes: dict[str, str]
    ) -> ReponseHttp:
        if url.endswith("/a"):
            return ReponseHttp(statut=307, entetes={"Location": "/b"})
        return ReponseHttp("ok")

    faux = simuler_reseau(monkeypatch, comportement)
    Session({}).lire("https://exemple.test/a", {"q": "1"})
    assert [(m, c) for m, _, c, _ in faux.appels] == [("POST", "q=1"), ("POST", "q=1")]


def test_trop_de_redirections_est_une_erreur(monkeypatch: pytest.MonkeyPatch) -> None:
    simuler_reseau(
        monkeypatch, ReponseHttp(statut=302, entetes={"Location": "/encore"})
    )
    with pytest.raises(RuntimeError, match="Trop de redirections"):
        Session({}).lire("https://exemple.test/")


def test_un_code_d_erreur_http_porte_son_statut(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    simuler_reseau(monkeypatch, ReponseHttp(statut=404))
    with pytest.raises(ErreurHttp) as capture:
        Session({}).lire("https://exemple.test/absent")
    assert capture.value.statut == 404
    assert "Erreur HTTP 404" in str(capture.value)


@pytest.mark.parametrize(
    "erreur",
    [urllib3.exceptions.HTTPError("coupé"), TimeoutError("délai"), OSError("réseau")],
)
def test_une_erreur_reseau_devient_une_runtime_error(
    monkeypatch: pytest.MonkeyPatch, erreur: BaseException
) -> None:
    simuler_reseau(monkeypatch, echec_reseau(erreur))
    with pytest.raises(RuntimeError, match="Erreur réseau"):
        Session({}).lire("https://exemple.test/")


# --- proxy ---


@pytest.fixture
def _sans_gestionnaires(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reseau, "_gestionnaires", {})


def test_sans_proxy_les_connexions_sont_directes(
    monkeypatch: pytest.MonkeyPatch, _sans_gestionnaires: None
) -> None:
    monkeypatch.setattr(urllib.request, "getproxies", lambda: {})
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda _h: False)
    gestionnaire = reseau._gestionnaire("https://exemple.test/")
    assert type(gestionnaire) is urllib3.PoolManager


def test_le_proxy_du_systeme_est_utilise(
    monkeypatch: pytest.MonkeyPatch, _sans_gestionnaires: None
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "getproxies",
        lambda: {"https": "http://u%40x:mdp@proxy.test:3128"},
    )
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda _h: False)
    gestionnaire = reseau._gestionnaire("https://exemple.test/")
    assert isinstance(gestionnaire, urllib3.ProxyManager)
    assert gestionnaire.proxy is not None and gestionnaire.proxy.host == "proxy.test"
    assert gestionnaire.proxy_headers["proxy-authorization"].startswith("Basic ")


def test_le_proxy_recoit_le_contexte_tls_du_systeme_et_des_identifiants_utf8(
    monkeypatch: pytest.MonkeyPatch, _sans_gestionnaires: None
) -> None:
    """Depuis urllib3 2.8, le TLS du proxy ne reprend plus le contexte de la
    destination : il doit lui être donné, sinon l'AC d'entreprise est refusée."""
    monkeypatch.setattr(
        urllib.request,
        "getproxies",
        lambda: {"https": "https://%C3%A9l:mdp@proxy.test:3128"},
    )
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda _h: False)
    gestionnaire = reseau._gestionnaire("https://exemple.test/")
    assert gestionnaire.proxy_ssl_context is reseau._contexte()
    jeton = gestionnaire.proxy_headers["proxy-authorization"].removeprefix("Basic ")
    assert base64.b64decode(jeton).decode("utf-8") == "él:mdp"


def test_un_hote_exclu_du_proxy_est_joint_directement(
    monkeypatch: pytest.MonkeyPatch, _sans_gestionnaires: None
) -> None:
    monkeypatch.setattr(
        urllib.request, "getproxies", lambda: {"https": "http://proxy.test:3128"}
    )
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda _h: True)
    assert type(reseau._gestionnaire("https://interne.test/")) is urllib3.PoolManager


# --- serveur local : vraies connexions ---


class _Site(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Gestionnaire)
        self.connexions = 0
        self.cookies_vus: list[str] = []

    def server_bind(self) -> None:
        # Sans cela, HTTPServer résout le nom de la machine (jusqu'à 35 s).
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = "127.0.0.1", self.server_address[1]


class _Gestionnaire(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def setup(self) -> None:
        super().setup()
        self.server.connexions += 1  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: object) -> None:
        pass

    def _repondre(self, statut: int, corps: bytes, entetes: dict[str, str]) -> None:
        self.send_response(statut)
        for nom, valeur in entetes.items():
            self.send_header(nom, valeur)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self) -> None:
        self.server.cookies_vus.append(self.headers.get("Cookie", ""))  # type: ignore[attr-defined]
        if self.path == "/redirige":
            self._repondre(302, b"", {"Location": "/page", "Set-Cookie": "s=1"})
            return
        corps = ("Chargé de mission " * 200).encode()
        if "gzip" in self.headers.get("Accept-Encoding", ""):
            self._repondre(200, gzip.compress(corps), {"Content-Encoding": "gzip"})
        else:
            self._repondre(200, corps, {})


@pytest.fixture
def site_local(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Site]:
    monkeypatch.setattr(socket.socket, "connect", _CONNEXION_REELLE)
    monkeypatch.setattr(socket, "create_connection", _CREATION_REELLE)
    monkeypatch.setattr(urllib.request, "getproxies", lambda: {})
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda _h: True)
    monkeypatch.setattr(reseau, "_gestionnaires", {})
    site = _Site()
    fil = threading.Thread(
        target=site.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    fil.start()
    yield site
    site.shutdown()
    site.server_close()


def test_les_connexions_sont_reutilisees_et_les_pages_decompressees(
    site_local: _Site,
) -> None:
    url = f"http://127.0.0.1:{site_local.server_address[1]}/page"
    session = Session({})

    textes = [session.lire(url).texte() for _ in range(6)]

    assert all(t.startswith("Chargé de mission") for t in textes)
    assert len(textes[0]) == len("Chargé de mission " * 200)
    assert site_local.connexions == 1


def test_une_nouvelle_session_reutilise_les_connexions_du_module(
    site_local: _Site,
) -> None:
    url = f"http://127.0.0.1:{site_local.server_address[1]}/page"
    Session({}).lire(url)
    Session({}).lire(url)
    assert site_local.connexions == 1


def test_les_cookies_suivent_une_redirection_sur_le_vrai_serveur(
    site_local: _Site,
) -> None:
    base = f"http://127.0.0.1:{site_local.server_address[1]}"
    reponse = Session({}).lire(f"{base}/redirige")
    assert reponse.url == f"{base}/page"
    assert site_local.cookies_vus == ["", "s=1"]


# --- robustesse (revue de code) ---


def test_une_redirection_vers_un_schema_inconnu_est_une_erreur_reseau(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def comportement(
        methode: str, url: str, corps: object, entetes: dict[str, str]
    ) -> ReponseHttp:
        if url.startswith("https://exemple.test"):
            return ReponseHttp(statut=302, entetes={"Location": "ftp://pirate.test/x"})
        raise urllib3.exceptions.URLSchemeUnknown("ftp")

    simuler_reseau(monkeypatch, comportement)
    with pytest.raises(RuntimeError, match="Erreur réseau"):
        Session({}).lire("https://exemple.test/")


def test_une_reponse_trop_volumineuse_est_refusee_et_la_connexion_fermee(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reseau, "TAILLE_MAX_REPONSE", 100_000)
    reponse = ReponseHttp(b"x" * 300_000)
    simuler_reseau(monkeypatch, reponse)

    with pytest.raises(RuntimeError, match="trop volumineuse"):
        Session({}).lire("https://exemple.test/")
    assert reponse.fermee is True


def test_la_connexion_est_rendue_a_la_reserve_apres_lecture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reponse = ReponseHttp("page")
    simuler_reseau(monkeypatch, reponse)
    assert Session({}).lire("https://exemple.test/").texte() == "page"
    assert reponse.rendue is True and reponse.fermee is False


def test_max_age_l_emporte_sur_expires_quel_que_soit_l_ordre() -> None:
    passe = "Thu, 01 Jan 1970 00:00:01 GMT"
    futur = "Fri, 01 Jan 2100 00:00:01 GMT"
    assert reseau._cookie_expire(f"a=1; Expires={passe}; Max-Age=3600") is False
    assert reseau._cookie_expire(f"a=1; Max-Age=3600; Expires={passe}") is False
    assert reseau._cookie_expire(f"a=1; Expires={futur}; Max-Age=0") is True
    assert reseau._cookie_expire("a=1; Max-Age=-1") is True
    assert reseau._cookie_expire("a=1; Max-Age=abc") is False
    assert reseau._cookie_expire(f"a=1; Expires={futur}") is False
    assert reseau._cookie_expire("a=1") is False
