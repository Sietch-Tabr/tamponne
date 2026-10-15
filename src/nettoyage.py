"""Nettoyage des fichiers retirés que la mise à jour laisse sur le disque.

La mise à jour de la 1.0.x copiait la nouvelle version par-dessus l'ancienne
sans rien supprimer, et `maj.py` ne purge que `src/` : les anciens lanceurs
de la racine et les fichiers de développement livrés jusqu'à la 1.2.2
resteraient. Ce nettoyage, lancé au démarrage, les retire une fois pour toutes.
"""

import logging
import shutil
from pathlib import Path

journal = logging.getLogger(__name__)

CHEMIN_RACINE = Path(__file__).parent.parent

FICHIERS_OBSOLETES: tuple[str, ...] = (
    "lancer.bat",
    "lancer.sh",
    "src/gui/app.py",
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
relatifs à la racine ; un dossier est retiré avec tout son contenu. Les
lanceurs remplacés par `Tamponne.*` en 1.2.0 sont supprimés même en cours
d'exécution : bash a déjà lu tout son bloc."""

FICHIERS_DEVELOPPEMENT: tuple[str, ...] = (
    ".gitattributes",
    ".gitignore",
    "RECHERCHES.md",
    "docs",
    "outils",
    "tests",
)
"""Fichiers du dépôt qui ne servent qu'au développement : exclus du zip des
publications (`export-ignore` dans `.gitattributes`) depuis la 1.2.3, mais
livrés avant."""

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
    """Supprime les fichiers et dossiers de `FICHIERS_OBSOLETES` et de
    `FICHIERS_DEVELOPPEMENT` encore présents.

    Sans effet sur un clone de développement (`.git/` présent : git gère
    déjà les suppressions) et sans effet si tout est déjà propre. Une
    suppression impossible est notée dans le journal sans empêcher le
    lancement.

    Args:
        racine: Dossier d'installation (racine du projet).

    Returns:
        Chemins relatifs effectivement supprimés.
    """
    if (racine / ".git").exists():
        return []
    supprimes: list[str] = []
    for relatif in FICHIERS_OBSOLETES + FICHIERS_DEVELOPPEMENT:
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
            journal.warning("Impossible de supprimer %s (%s).", relatif, erreur)
            continue
        supprimes.append(relatif)
    return supprimes
