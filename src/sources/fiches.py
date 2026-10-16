"""Lecture des fiches d'offres pour filtrer les résultats d'un site qui ne
sait pas le faire : en parallèle, et sans relire une fiche déjà connue."""

import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor

from src.sources.base import CacheFiches
from src.types import FicheFiltrage

LECTEURS = 6
DELAI_COURTOISIE = 0.3
"""Pause de chaque lecteur avant sa requête : environ 20 requêtes par seconde
au plus, sans pare-feu sur ces sites."""


def lire_fiches(
    urls: Iterable[str],
    lire: Callable[[str], FicheFiltrage | None],
    cache: CacheFiches | None = None,
    on_fiche: Callable[[int, int], None] | None = None,
) -> dict[str, FicheFiltrage]:
    """Fiches de `urls`, depuis `cache` quand elles y sont, sinon lues par
    `lire` (`None` si la fiche est illisible : absente du résultat, et
    non mémorisée pour être retentée à la prochaine recherche).

    `on_fiche(lues, total)` est appelé après chaque fiche lue sur le site
    (celles du cache n'y comptent pas)."""
    fiches: dict[str, FicheFiltrage] = {}
    a_lire: list[str] = []
    for url in dict.fromkeys(urls):
        if cache is not None and (connue := cache.lire(url)) is not None:
            fiches[url] = connue
        else:
            a_lire.append(url)

    def _lire(url: str) -> tuple[str, FicheFiltrage | None]:
        time.sleep(DELAI_COURTOISIE)
        fiche = lire(url)
        if fiche is not None and cache is not None:
            cache.ecrire(url, fiche)
        return url, fiche

    with ThreadPoolExecutor(max_workers=LECTEURS) as pool:
        for rang, (url, fiche) in enumerate(pool.map(_lire, a_lire), start=1):
            if fiche is not None:
                fiches[url] = fiche
            if on_fiche:
                on_fiche(rang, len(a_lire))
    return fiches
