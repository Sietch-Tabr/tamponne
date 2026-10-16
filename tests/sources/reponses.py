"""Réseau simulé pour les tests des clients : un faux gestionnaire de
connexions remplace celui de `src.sources.reseau`, sans toucher au réseau."""

from collections.abc import Callable, Mapping
from typing import Any

import pytest

from src.sources import reseau


class EnTetes:
    """En-têtes d'une réponse (`get` et `getlist`, comme urllib3)."""

    def __init__(self, valeurs: Mapping[str, str | list[str]] | None = None) -> None:
        self._valeurs = {k.lower(): v for k, v in (valeurs or {}).items()}

    def get(self, nom: str, defaut: str | None = None) -> str | None:
        valeur = self._valeurs.get(nom.lower())
        if isinstance(valeur, list):
            return valeur[0] if valeur else defaut
        return valeur if valeur is not None else defaut

    def getlist(self, nom: str) -> list[str]:
        valeur = self._valeurs.get(nom.lower())
        if valeur is None:
            return []
        return valeur if isinstance(valeur, list) else [valeur]


class ReponseHttp:
    """Réponse simulée : corps déjà décompressé, comme celui d'urllib3."""

    def __init__(
        self,
        corps: bytes | str = b"",
        statut: int = 200,
        entetes: Mapping[str, str | list[str]] | None = None,
    ) -> None:
        self.data = corps.encode() if isinstance(corps, str) else corps
        self.status = statut
        self.headers = EnTetes(entetes)


type Comportement = Callable[[str, str, Any, dict[str, str]], ReponseHttp]
"""(méthode, url, corps, en-têtes) → réponse ; lève pour simuler un échec."""


class FauxGestionnaire:
    """Remplace `PoolManager` : garde les requêtes reçues dans `appels`."""

    def __init__(self, comportement: Comportement) -> None:
        self.comportement = comportement
        self.appels: list[tuple[str, str, Any, dict[str, str]]] = []

    def request(
        self,
        methode: str,
        url: str,
        body: Any = None,
        headers: dict[str, str] | None = None,
        **_options: object,
    ) -> ReponseHttp:
        self.appels.append((methode, url, body, dict(headers or {})))
        return self.comportement(methode, url, body, dict(headers or {}))


def simuler_reseau(
    monkeypatch: pytest.MonkeyPatch, comportement: Comportement | ReponseHttp
) -> FauxGestionnaire:
    """Toute requête des sources passe par le faux gestionnaire ; une
    `ReponseHttp` seule est rendue à chaque requête."""
    if isinstance(comportement, ReponseHttp):
        reponse = comportement
        comportement = lambda *_args: reponse  # noqa: E731
    faux = FauxGestionnaire(comportement)
    monkeypatch.setattr(reseau, "_gestionnaire", lambda _url: faux)
    return faux


def echec_reseau(erreur: BaseException) -> Comportement:
    """Comportement qui lève `erreur` à chaque requête."""

    def leve(*_args: object) -> ReponseHttp:
        raise erreur

    return leve
