"""Dossiers de l'installation, communs à tous les modules : un module rangé
dans un sous-dossier de `src/` ne doit pas recalculer la racine lui-même."""

from pathlib import Path

RACINE = Path(__file__).parent.parent
"""Dossier de Tamponné, celui qui contient `src/`, `data/` et `exports/`."""
DATA = RACINE / "data"
EXPORTS = RACINE / "exports"
