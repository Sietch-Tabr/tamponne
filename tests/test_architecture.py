"""Architecture de src/ : qui peut importer qui.

Les couches vont du socle (types, utils, filtres, formatage, chemins) vers
l'interface (gui). Un nouveau module ou une dépendance nouvelle entre
composants doit être décidé ici, pas découvert à la relecture."""

import ast
from pathlib import Path
from typing import Final

SRC = Path(__file__).parent.parent / "src"

DEPENDANCES_AUTORISEES: Final[dict[str, set[str]]] = {
    # Socle : ne dépend que de lui-même.
    "types": set(),
    "utils": set(),
    "chemins": set(),
    "filtres": {"types"},
    "formatage": {"types"},
    # Amorçage, sans Qt : le lanceur survit à la mise à jour de src/.
    "maj": {"types", "utils"},
    "nettoyage": set(),
    "lanceur": {"maj"},
    # Couches métier.
    "sources": {"filtres", "types"},
    "systeme": {"chemins", "utils"},
    "donnees": {"chemins", "filtres", "formatage", "maj", "sources", "types", "utils"},
    "recherche": {"chemins", "donnees", "filtres", "sources", "types"},
    # Interface : seule à connaître Qt.
    "gui": {
        "PySide6",
        "donnees",
        "filtres",
        "formatage",
        "lanceur",
        "maj",
        "nettoyage",
        "recherche",
        "sources",
        "systeme",
        "types",
    },
}


def _composant(fichier: Path) -> str:
    """Premier niveau de `src/` d'un fichier : « donnees » pour
    `src/donnees/cache.py`, « types » pour `src/types.py`."""
    return fichier.relative_to(SRC).with_suffix("").parts[0]


def _modules_importes(arbre: ast.AST) -> set[str]:
    """Composants de `src` (et `PySide6`) importés par un fichier."""
    composants: set[str] = set()
    for noeud in ast.walk(arbre):
        modules: list[str] = []
        if isinstance(noeud, ast.ImportFrom) and noeud.level == 0 and noeud.module:
            if noeud.module == "src":
                modules = [f"src.{nom.name}" for nom in noeud.names]
            else:
                modules = [noeud.module]
        elif isinstance(noeud, ast.Import):
            modules = [nom.name for nom in noeud.names]
        for module in modules:
            if module.startswith("src."):
                composants.add(module.split(".")[1])
            elif module.split(".")[0] == "PySide6":
                composants.add("PySide6")
    return composants


def test_chaque_composant_de_src_est_classe() -> None:
    presents = {_composant(f) for f in SRC.rglob("*.py") if f.name != "__init__.py"}
    assert presents <= set(DEPENDANCES_AUTORISEES), (
        "Composant à classer dans DEPENDANCES_AUTORISEES : "
        f"{sorted(presents - set(DEPENDANCES_AUTORISEES))}"
    )


def test_les_dependances_respectent_les_couches() -> None:
    violations: list[str] = []
    for fichier in sorted(SRC.rglob("*.py")):
        composant = _composant(fichier)
        autorises = DEPENDANCES_AUTORISEES.get(composant, set()) | {composant}
        importes = _modules_importes(ast.parse(fichier.read_text(encoding="utf-8")))
        for interdit in sorted(importes - autorises):
            violations.append(
                f"{fichier.relative_to(SRC.parent)} importe {interdit} "
                f"({composant} ne peut pas en dépendre)"
            )
    assert violations == []
