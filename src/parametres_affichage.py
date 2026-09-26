"""Préférences d'affichage — thème choisi (automatique, sombre ou clair)."""

import json
import sys
from pathlib import Path
from typing import Literal, cast

from src.utils import ecriture_atomique

CHEMIN_AFFICHAGE = Path(__file__).parent.parent / "data" / "affichage.json"

type ModeTheme = Literal["auto", "sombre", "clair"]

MODES_THEME: dict[ModeTheme, str] = {
    "auto": "Automatique (suit le système)",
    "sombre": "Sombre",
    "clair": "Clair",
}
"""Mode de thème → libellé affiché, dans l'ordre de présentation."""

MODE_THEME_DEFAUT: ModeTheme = "auto"


def charger_mode_theme() -> ModeTheme:
    """Mode de thème enregistré — `MODE_THEME_DEFAUT` si aucun choix n'a
    encore été fait, ou si le fichier est illisible ou la valeur inconnue."""
    if not CHEMIN_AFFICHAGE.exists():
        return MODE_THEME_DEFAUT
    try:
        donnees = json.loads(CHEMIN_AFFICHAGE.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        print(
            f"Avertissement : {CHEMIN_AFFICHAGE.name} illisible ou corrompu, "
            "thème automatique utilisé.",
            file=sys.stderr,
        )
        return MODE_THEME_DEFAUT
    mode = donnees.get("theme") if isinstance(donnees, dict) else None
    return cast(ModeTheme, mode) if mode in MODES_THEME else MODE_THEME_DEFAUT


def sauvegarder_mode_theme(mode: ModeTheme) -> None:
    """Écrit le mode de thème dans affichage.json."""
    ecriture_atomique(CHEMIN_AFFICHAGE, {"theme": mode})
