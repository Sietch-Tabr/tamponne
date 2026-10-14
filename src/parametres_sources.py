"""Sources d'offres actives — quelles sources interroger à la recherche."""

import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from src.utils import ecriture_atomique

journal = logging.getLogger(__name__)

CHEMIN_SOURCES = Path(__file__).parent.parent / "data" / "sources.json"

SOURCES_DISPONIBLES: Final[Mapping[str, str]] = {
    "choisirleservicepublic": "Choisir le service public",
    "emploiterritorial": "Fonction publique territoriale (emploi-territorial.fr)",
    "passerellesmef": "Passerelles - Bercy (passerelles.economie.gouv.fr)",
    "fhf": "Fonction publique hospitalière (emploi.fhf.fr)",
}

VERSANT_SOURCE: Final[Mapping[str, str]] = {
    "emploiterritorial": "territorial",
    "passerellesmef": "etat",
    "fhf": "hospitalier",
}
"""Versant fixe des sources mono-versant, pour ne pas interroger une source
dont le versant est exclu par le filtre (ex. emploi-territorial.fr si seul
« État » est coché). Une source absente est multi-versant
(choisirleservicepublic) et applique déjà le filtre côté serveur."""


def charger_sources_actives() -> dict[str, bool]:
    """Charge l'état actif/inactif de chaque source — toutes actives par
    défaut, y compris une source nouvellement ajoutée non encore
    présente dans le fichier."""
    etats: dict[str, bool] = {}
    if CHEMIN_SOURCES.exists():
        try:
            etats = json.loads(CHEMIN_SOURCES.read_text(encoding="utf-8"))
        except json.JSONDecodeError, OSError:
            journal.warning(
                "%s illisible ou corrompu, toutes les sources sont réactivées.",
                CHEMIN_SOURCES.name,
            )
            etats = {}
    return {cle: etats.get(cle, True) for cle in SOURCES_DISPONIBLES}


def sauvegarder_sources_actives(etats: dict[str, bool]) -> None:
    """Écrit sources.json sur le disque."""
    ecriture_atomique(CHEMIN_SOURCES, etats)
