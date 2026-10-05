"""Nettoyage des fichiers de l'ancienne interface après la mise à jour 1.0.x.

La mise à jour de la 1.0.x copie la nouvelle version par-dessus l'ancienne
sans rien supprimer : les modules de l'interface Widgets resteraient sur le
disque. Ce nettoyage, lancé au démarrage, les retire une fois pour toutes.
"""

import shutil
import sys
from pathlib import Path

CHEMIN_RACINE = Path(__file__).parent.parent

FICHIERS_OBSOLETES: tuple[str, ...] = (
    "src/gui/theme.py",
    "src/gui/vues",
    "src/gui/widgets",
    "tests/test_gui_accueil.py",
    "tests/test_gui_aide_parametres.py",
    "tests/test_gui_app.py",
    "tests/test_gui_candidatures.py",
    "tests/test_gui_dialogue_detail_offre.py",
    "tests/test_gui_dialogue_selection.py",
    "tests/test_gui_recherche_resultats.py",
    "tests/test_gui_sources.py",
    "tests/test_gui_theme.py",
    "tests/test_gui_widgets_case_a_cocher.py",
    "tests/test_gui_widgets_ligne_responsive.py",
)
"""Chemins supprimés depuis la 1.0.5 (`git diff --diff-filter=D v1.0.5`),
relatifs à la racine ; un dossier est retiré avec tout son contenu."""

_DOSSIERS_INTERDITS = ("data", ".git")


def _cible_autorisee(cible: Path, racine: Path) -> bool:
    """Vrai si `cible` est sous `racine`, hors de `data/` et de `.git/`."""
    try:
        relatif = cible.resolve().relative_to(racine.resolve())
    except ValueError:
        return False
    return bool(relatif.parts) and relatif.parts[0] not in _DOSSIERS_INTERDITS


def _cache_compile(chemin: Path) -> list[Path]:
    """Fichiers compilés (`__pycache__`) d'un module supprimé."""
    if chemin.suffix != ".py":
        return []
    cache = chemin.parent / "__pycache__"
    return sorted(cache.glob(f"{chemin.stem}.*.pyc")) if cache.is_dir() else []


def nettoyer_fichiers_obsoletes(racine: Path = CHEMIN_RACINE) -> list[str]:
    """Supprime les fichiers et dossiers de `FICHIERS_OBSOLETES` encore présents.

    Sans effet sur un clone de développement (`.git/` présent : git gère
    déjà les suppressions) et sans effet si tout est déjà propre. Une
    suppression impossible est signalée sur la sortie d'erreur sans
    empêcher le lancement.

    Args:
        racine: Dossier d'installation (racine du projet).

    Returns:
        Chemins relatifs effectivement supprimés.
    """
    if (racine / ".git").exists():
        return []
    supprimes: list[str] = []
    for relatif in FICHIERS_OBSOLETES:
        cible = racine / relatif
        if not cible.exists() or not _cible_autorisee(cible, racine):
            continue
        try:
            if cible.is_dir():
                shutil.rmtree(cible)
            else:
                for compile_ in _cache_compile(cible):
                    compile_.unlink(missing_ok=True)
                cible.unlink()
        except OSError as erreur:
            print(
                f"Avertissement : impossible de supprimer {relatif} ({erreur}).",
                file=sys.stderr,
            )
            continue
        supprimes.append(relatif)
    return supprimes
