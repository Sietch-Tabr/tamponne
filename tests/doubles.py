"""Doublures de test partagées entre les paquets de tests."""

from collections.abc import Callable
from typing import NamedTuple

from src.types import FiltresRecherche, Offre

type Rappel = Callable[[int, int], None]
type Resultat = tuple[list[Offre], int, bool]


class Appel(NamedTuple):
    """Arguments reçus par `rechercher`."""

    filtres: FiltresRecherche
    on_page: Rappel | None
    on_fiche: Rappel | None


class SourceFactice:
    """Double de `SourceOffres.rechercher` qui mémorise ses appels.

    `comportement` reçoit l'appel et rend le résultat de la recherche ; il peut
    appeler les rappels, attendre une barrière ou lever une erreur. Brancher
    `source.rechercher` avec `monkeypatch.setattr(Classe, "rechercher", ...)`.
    """

    def __init__(self, comportement: Callable[[Appel], Resultat]) -> None:
        self.appels: list[Appel] = []
        self._comportement = comportement

    def rechercher(
        self,
        filtres: FiltresRecherche,
        on_page: Rappel | None = None,
        on_fiche: Rappel | None = None,
    ) -> Resultat:
        appel = Appel(filtres, on_page, on_fiche)
        self.appels.append(appel)
        return self._comportement(appel)
