"""Utilitaires partagés entre les modules du projet."""

import contextlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

ESSAIS_REMPLACEMENT = 4
DELAI_REMPLACEMENT = 0.1
"""Secondes d'attente avant le deuxième essai, doublées ensuite."""


def _remplacer(source: str, destination: Path) -> None:
    """`os.replace`, retenté si le fichier est tenu un instant par un autre
    processus (antivirus, indexation) : `PermissionError` sous Windows."""
    for essai in range(ESSAIS_REMPLACEMENT):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if essai == ESSAIS_REMPLACEMENT - 1:
                raise
            time.sleep(DELAI_REMPLACEMENT * 2**essai)


def ecriture_atomique(chemin: Path, donnees: dict[str, Any]) -> None:
    """Écrit un dict JSON de manière atomique (temp + rename).

    Garantit qu'une écriture partielle ne corrompt pas le fichier existant.
    En cas d'erreur, le fichier temporaire est supprimé avant de re-propager
    l'exception.

    Args:
        chemin: Chemin du fichier JSON de destination.
        donnees: Dictionnaire à sérialiser.
    """
    chemin.parent.mkdir(parents=True, exist_ok=True)
    contenu = json.dumps(donnees, ensure_ascii=False, indent=2)
    fd, chemin_tmp = tempfile.mkstemp(dir=chemin.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(contenu)
        _remplacer(chemin_tmp, chemin)
    except BaseException:  # nettoyage du temporaire même sur Ctrl+C
        with contextlib.suppress(OSError):
            os.unlink(chemin_tmp)
        raise
