"""Client HTTP partagé des sources : connexions réutilisées, pages
compressées, proxy et certificats du système.

Les connexions (TLS compris) sont gardées ouvertes d'une requête à l'autre,
y compris entre les lecteurs en parallèle : 60 pages se lisent en 0,35 s au
lieu de 1,06 s avec une connexion par requête. Chaque `Session` garde ses
propres cookies (recherches de Passerelles et d'emploi-territorial).
"""

import ssl
import threading
from collections.abc import Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, NamedTuple
from urllib.parse import unquote, urlencode, urljoin, urlsplit

lazy import truststore
lazy import urllib.request
lazy import urllib3

DELAI = 30
"""Secondes d'attente pour se connecter, puis pour chaque lecture."""
TAILLE_MAX_REPONSE = 32 * 1024 * 1024
"""Octets lus au plus par réponse, décompressés (une page de Choisir le service
public en pèse 4,4 millions) : un site défaillant ne doit pas remplir la mémoire."""
LECTEURS_MAX = 8
"""Connexions gardées ouvertes par site ; au-delà elles sont fermées après usage."""
_REDIRECTIONS_MAX = 8
_STATUTS_REDIRECTION = frozenset({301, 302, 303, 307, 308})
_ENTETES_COMMUNS = {"Accept-Encoding": "gzip, deflate"}

_verrou = threading.Lock()
_gestionnaires: dict[str, Any] = {}
_contexte_ssl: ssl.SSLContext | None = None


class ErreurHttp(RuntimeError):
    """Le site répond par un code d'erreur HTTP (`statut`)."""

    def __init__(self, statut: int, url: str) -> None:
        super().__init__(f"Erreur HTTP {statut} lors du chargement de {url}")
        self.statut = statut


class Reponse(NamedTuple):
    """Réponse finale, redirections suivies et corps décompressé."""

    url: str
    statut: int
    corps: bytes

    def texte(self) -> str:
        """Corps en texte (UTF-8, caractères illisibles remplacés)."""
        return self.corps.decode("utf-8", errors="replace")


def _contexte() -> ssl.SSLContext:
    """Certificats du système, comme le navigateur (`truststore`)."""
    global _contexte_ssl
    if _contexte_ssl is None:
        _contexte_ssl = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return _contexte_ssl


def _gestionnaire(url: str) -> Any:
    """Réserve de connexions du site de `url`, passant par le proxy du système
    (variables d'environnement, réglages de Windows) s'il y en a un."""
    morceaux = urlsplit(url)
    hote = morceaux.hostname or ""
    proxy = ""
    if not urllib.request.proxy_bypass(hote):
        proxy = urllib.request.getproxies().get(morceaux.scheme, "")
    with _verrou:
        if proxy not in _gestionnaires:
            reessais = urllib3.Retry(total=2, backoff_factor=0.3, redirect=0, status=0)
            commun: dict[str, Any] = {
                "maxsize": LECTEURS_MAX,
                "retries": reessais,
                "timeout": urllib3.Timeout(connect=DELAI, read=DELAI),
                "ssl_context": _contexte(),
            }
            if proxy:
                entetes = None
                identifiants = urlsplit(proxy)
                if identifiants.username:
                    # UTF-8 (RFC 7617) : le latin-1 par défaut échoue sur les
                    # identifiants hors de ce jeu de caractères.
                    entetes = urllib3.make_headers(
                        proxy_basic_auth=(
                            f"{unquote(identifiants.username)}:"
                            f"{unquote(identifiants.password or '')}"
                        ),
                        proxy_basic_auth_encoding="utf-8",
                    )
                # Depuis urllib3 2.8, le TLS d'un proxy HTTPS ne reprend plus le
                # contexte de la destination : sans lui, l'AC d'entreprise du
                # proxy, connue du système seulement, serait refusée.
                _gestionnaires[proxy] = urllib3.ProxyManager(
                    proxy,
                    proxy_headers=entetes,
                    proxy_ssl_context=commun["ssl_context"],
                    **commun,
                )
            else:
                _gestionnaires[proxy] = urllib3.PoolManager(**commun)
        return _gestionnaires[proxy]


def _cookie_expire(cookie: str) -> bool:
    """Vrai si l'en-tête `Set-Cookie` supprime le cookie (durée nulle ou date
    passée), comme le fait le site pour effacer un cookie. `Max-Age` l'emporte
    sur `Expires`, quel que soit leur ordre."""
    attributs = {}
    for attribut in cookie.split(";")[1:]:
        nom, _, valeur = attribut.strip().partition("=")
        attributs[nom.lower()] = valeur.strip()
    if "max-age" in attributs:
        duree = attributs["max-age"]
        return duree.lstrip("-").isdigit() and int(duree) <= 0
    if "expires" in attributs:
        try:
            return parsedate_to_datetime(attributs["expires"]) < datetime.now(UTC)
        except TypeError, ValueError:
            return False
    return False


def _lire_corps(reponse: Any, url: str) -> bytes:
    """Corps décompressé de `reponse`, par morceaux, sans dépasser
    `TAILLE_MAX_REPONSE`. La connexion est rendue à la réserve, ou fermée si
    la réponse est abandonnée.

    Raises:
        RuntimeError: Réponse plus grosse que la limite.
    """
    morceaux: list[bytes] = []
    total = 0
    try:
        for morceau in reponse.stream(65536, decode_content=True):
            total += len(morceau)
            if total > TAILLE_MAX_REPONSE:
                reponse.close()
                raise RuntimeError(f"Réponse trop volumineuse pour {url}")
            morceaux.append(morceau)
    finally:
        reponse.release_conn()
    return b"".join(morceaux)


class Session:
    """Requêtes d'une même recherche : en-têtes communs et cookies du site.

    Les connexions sont partagées par tout le module ; seule la session
    porte un état (cookies), à ne jamais partager entre deux recherches.

    Args:
        entetes: En-têtes de chaque requête (`User-Agent`, langue…).
    """

    def __init__(self, entetes: Mapping[str, str]) -> None:
        self._entetes = {**_ENTETES_COMMUNS, **entetes}
        self._cookies: dict[str, dict[str, str]] = {}
        self._verrou = threading.Lock()

    def _entetes_pour(self, hote: str) -> dict[str, str]:
        with self._verrou:
            cookies = dict(self._cookies.get(hote, {}))
        entetes = dict(self._entetes)
        if cookies:
            entetes["Cookie"] = "; ".join(f"{nom}={v}" for nom, v in cookies.items())
        return entetes

    def _retenir_cookies(self, hote: str, reponse: Any) -> None:
        recus = reponse.headers.getlist("Set-Cookie")
        if not recus:
            return
        with self._verrou:
            boite = self._cookies.setdefault(hote, {})
            for cookie in recus:
                nom, _, valeur = cookie.split(";", 1)[0].partition("=")
                if _cookie_expire(cookie):
                    boite.pop(nom.strip(), None)
                else:
                    boite[nom.strip()] = valeur.strip()

    def lire(self, url: str, donnees: Mapping[str, str] | None = None) -> Reponse:
        """Charge `url` (en GET, ou en POST de formulaire si `donnees`), en
        suivant les redirections.

        Raises:
            ErreurHttp: Code HTTP d'erreur.
            RuntimeError: Échec réseau (message en français, détail compris).
        """
        methode = "GET" if donnees is None else "POST"
        corps = None if donnees is None else urlencode(donnees)
        courante = url
        for _ in range(_REDIRECTIONS_MAX + 1):
            hote = urlsplit(courante).hostname or ""
            entetes = self._entetes_pour(hote)
            if corps is not None:
                entetes["Content-Type"] = "application/x-www-form-urlencoded"
            try:
                reponse = _gestionnaire(courante).request(
                    methode,
                    courante,
                    body=corps,
                    headers=entetes,
                    redirect=False,
                    preload_content=False,
                )
                contenu = _lire_corps(reponse, url)
            # Les adresses de redirection invalides lèvent des `ValueError`.
            except (urllib3.exceptions.HTTPError, OSError, ValueError) as erreur:
                raise RuntimeError(
                    f"Erreur réseau lors du chargement de {url} : "
                    f"{getattr(erreur, 'reason', erreur)}"
                ) from erreur
            self._retenir_cookies(hote, reponse)
            place = reponse.headers.get("Location")
            if reponse.status in _STATUTS_REDIRECTION and place:
                courante = urljoin(courante, place)
                if reponse.status in (301, 302, 303):
                    methode, corps = "GET", None
                continue
            if reponse.status >= 400:
                raise ErreurHttp(reponse.status, url)
            return Reponse(courante, reponse.status, contenu)
        raise RuntimeError(f"Trop de redirections lors du chargement de {url}")
