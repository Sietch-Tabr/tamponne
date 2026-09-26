"""Dédoublonnage flou FHF — pas de référence partagée avec les autres
sources (contrairement à MEF/territorial), donc pas de match exact
possible. Voir `src.sources.base.deduplique_offres` pour le cas
général par référence.
"""

import re
import unicodedata

from src.types import Offre

_RE_NON_ALPHANUM = re.compile(r"[^a-z0-9\s]")
_RE_ESPACES = re.compile(r"\s+")
_MOTS_GENERIQUES = {
    "centre",
    "hospitalier",
    "hospitaliere",
    "hopital",
    "chu",
    "chr",
    "chi",
    "etablissement",
    "public",
    "sante",
    "de",
    "du",
    "des",
    "la",
    "le",
    "les",
    "et",
    "d",
    "l",
}


def _normaliser(texte: str) -> str:
    """Minuscules, accents retirés, ponctuation retirée, espaces réduits."""
    sans_accents = unicodedata.normalize("NFKD", texte.lower())
    sans_accents = "".join(c for c in sans_accents if not unicodedata.combining(c))
    sans_accents = _RE_NON_ALPHANUM.sub(" ", sans_accents)
    return _RE_ESPACES.sub(" ", sans_accents).strip()


def _mots_significatifs(employeur: str) -> set[str]:
    """Mots de l'employeur hors vocabulaire générique hospitalier —
    seul un mot distinctif partagé (ex. "epsylan") vaut comme indice
    de même établissement, pas un terme générique comme "centre"."""
    return {
        mot
        for mot in _normaliser(employeur).split()
        if len(mot) >= 5 and mot not in _MOTS_GENERIQUES
    }


def filtrer_doublons_fhf(
    offres_fhf: list[Offre], offres_existantes: list[Offre]
) -> list[Offre]:
    """Retire les offres FHF qui semblent déjà présentes parmi
    `offres_existantes` (titre identique + un mot distinctif partagé
    entre les deux employeurs).

    Approximatif par nature (pas de référence commune) — biaisé vers
    le faux négatif (un doublon occasionnel peut passer) plutôt que le
    faux positif (masquer une offre réelle) : un match sur le titre
    seul produirait des faux positifs observés sur les sites (titres
    génériques comme "Infirmier" correspondant à des employeurs
    complètement différents)."""
    titres_existants: dict[str, list[set[str]]] = {}
    for offre in offres_existantes:
        titre_norm = _normaliser(offre["titre"])
        titres_existants.setdefault(titre_norm, []).append(
            _mots_significatifs(offre["employeur"])
        )

    resultat: list[Offre] = []
    for offre in offres_fhf:
        titre_norm = _normaliser(offre["titre"])
        mots_fhf = _mots_significatifs(offre["employeur"])
        candidats = titres_existants.get(titre_norm, [])
        est_doublon = any(mots_fhf & mots_candidat for mots_candidat in candidats)
        if not est_doublon:
            resultat.append(offre)
    return resultat
