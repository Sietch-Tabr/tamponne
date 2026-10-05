"""Utilitaires partagés entre les modules du projet."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any


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
        os.replace(chemin_tmp, chemin)
    except (
        Exception
    ):  # générique intentionnel : nettoyage du temporaire quelle que soit l'erreur
        try:
            os.unlink(chemin_tmp)
        except OSError:
            pass
        raise
