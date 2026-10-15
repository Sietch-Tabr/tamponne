"""Chemins de données : ceux des vrais modules, hors redirections de test.

`conftest.py` redirige toutes les constantes de chemin vers un dossier
temporaire : sans ce test, un module déplacé dans un sous-dossier de `src/`
pourrait pointer vers un mauvais dossier sans qu'aucun autre test ne le voie.
Un sous-processus relit donc les constantes telles que le code les définit."""

import json
import subprocess
import sys
from pathlib import Path

from src import chemins

CONSTANTES = {
    "src.donnees.cache": ["CHEMIN_CACHE", "CHEMIN_OFFRES"],
    "src.donnees.candidatures": ["CHEMIN_CANDIDATURES", "DOSSIER_ARCHIVES"],
    "src.donnees.profils": ["CHEMIN_PROFILS"],
    "src.donnees.parametres_sources": ["CHEMIN_SOURCES"],
    "src.donnees.parametres_affichage": ["CHEMIN_AFFICHAGE"],
    "src.recherche.export": ["DOSSIER_EXPORTS"],
    "src.systeme.raccourci": ["CHEMIN_PREFERENCE", "CHEMIN_RACINE"],
    "src.maj": ["CHEMIN_RACINE"],
    "src.nettoyage": ["CHEMIN_RACINE"],
}

SCRIPT = """
import importlib, json, sys
resultat = {}
for module, noms in json.loads(sys.argv[1]).items():
    importe = importlib.import_module(module)
    for nom in noms:
        resultat[f"{module}.{nom}"] = str(getattr(importe, nom))
print(json.dumps(resultat))
"""


def _chemins_reels() -> dict[str, Path]:
    sortie = subprocess.run(
        [sys.executable, "-c", SCRIPT, json.dumps(CONSTANTES)],
        cwd=chemins.RACINE,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {nom: Path(valeur) for nom, valeur in json.loads(sortie).items()}


def test_racine_est_le_dossier_du_projet() -> None:
    assert (chemins.RACINE / "pyproject.toml").is_file()
    assert (chemins.RACINE / "src").is_dir()


def test_donnees_et_exports_sont_sous_la_racine() -> None:
    for nom, chemin in _chemins_reels().items():
        if nom.endswith("CHEMIN_RACINE"):
            assert chemin == chemins.RACINE, nom
        elif nom.endswith("DOSSIER_EXPORTS"):
            assert chemin == chemins.RACINE / "exports", nom
        else:
            assert chemin.parent in (chemins.DATA, chemins.DATA / "archives"), nom
            assert chemins.DATA in chemin.parents, nom
