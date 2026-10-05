"""Mise à jour de l'application via les publications (Releases) Codeberg.

Uniquement les publications explicitement faites sur le dépôt — jamais un
`git pull`/`fetch` sur une branche — pour garantir que seul ce qui a été
publié est déployé. `/releases/latest` de l'API Forgejo/Gitea exclut déjà
nativement les brouillons et pré-versions.

Ne dépend d'aucune bibliothèque d'UI : ce module est appelé aussi bien
depuis le vérificateur en arrière-plan (`src.gui.travailleurs`) que depuis
la ligne de commande par `src.lanceur` (voir `if __name__ ==
"__main__"` en bas de fichier) avant même que l'application Qt démarre.
"""

import json
import re
import shutil
import sys
import tempfile
import tomllib
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from src.types import InfoMaj
from src.utils import ecriture_atomique

URL_API_RELEASES = "https://codeberg.org/api/v1/repos/Kwaite/tamponne/releases/latest"
CHEMIN_RACINE = Path(__file__).parent.parent
CHEMIN_PYPROJECT = CHEMIN_RACINE / "pyproject.toml"
CHEMIN_MARQUEUR = CHEMIN_RACINE / "data" / "maj_disponible.json"
_TIMEOUT = 15


def version_locale() -> str:
    """Lit la version courante depuis `pyproject.toml`."""
    with CHEMIN_PYPROJECT.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def version_plus_recente(distante: str, locale: str) -> bool:
    """Compare deux versions par tuple d'entiers (`"1.2.0"` -> `(1, 2, 0)`),
    tolère un préfixe `v` (format des tags Codeberg, ex. `v1.2.0`)."""

    def _tuple(v: str) -> tuple[int, ...]:
        v = v.strip().lstrip("vV")
        return tuple(int(p) for p in re.findall(r"\d+", v))

    return _tuple(distante) > _tuple(locale)


def verifier_derniere_publication() -> InfoMaj | None:
    """Interroge la dernière publication Codeberg — `None` si aucune
    publication, si elle n'est pas plus récente, ou en cas d'échec réseau
    (jamais bloquant : pas de mise à jour tant que rien n'est confirmé)."""
    try:
        requete = urllib.request.Request(
            URL_API_RELEASES, headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(requete, timeout=_TIMEOUT) as reponse:
            donnees = json.loads(reponse.read().decode("utf-8"))
    except urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError:
        return None
    except json.JSONDecodeError:
        return None

    tag = str(donnees.get("tag_name", ""))
    if not tag or not version_plus_recente(tag, version_locale()):
        return None

    return {
        "version": tag.lstrip("vV"),
        "notes": str(donnees.get("body", "")),
        "url_zip": str(donnees.get("zipball_url", "")),
        "url_publication": str(donnees.get("html_url", "")),
    }


def lire_maj_disponible() -> InfoMaj | None:
    """Lit le marqueur de mise à jour en attente, `None` si absent/corrompu."""
    if not CHEMIN_MARQUEUR.exists():
        return None
    try:
        return json.loads(CHEMIN_MARQUEUR.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        return None


def ecrire_maj_disponible(info: InfoMaj) -> None:
    """Pose le marqueur — déclenche l'application automatique au prochain
    lancement (`src.lanceur`), indépendamment d'un clic utilisateur."""
    ecriture_atomique(CHEMIN_MARQUEUR, dict(info))


def effacer_maj_disponible() -> None:
    CHEMIN_MARQUEUR.unlink(missing_ok=True)


def appliquer_maj(info: InfoMaj) -> None:
    """Télécharge et applique la publication `info`.

    Installe les fichiers de l'archive dans la racine du projet (voir
    `installer_archive`) : l'archive Codeberg ne contient que les fichiers
    suivis par git, donc `data/`, `.git/` et les fichiers non versionnés
    hors de `src/` et `tests/` ne sont jamais touchés.

    Raises:
        RuntimeError: Téléchargement ou extraction impossible — l'appelant
            décide de continuer avec la version actuelle plutôt que bloquer.
    """
    if not info["url_zip"]:
        raise RuntimeError("URL de l'archive de mise à jour manquante.")

    with tempfile.TemporaryDirectory(prefix="tamponne-maj-") as dossier_tmp:
        chemin_zip = Path(dossier_tmp) / "maj.zip"
        try:
            urllib.request.urlretrieve(info["url_zip"], chemin_zip)
            with zipfile.ZipFile(chemin_zip) as archive:
                archive.extractall(dossier_tmp)
                # extractall() n'applique pas les bits Unix (rwx) codés dans
                # l'archive : sans ça, Tamponne.command perd son +x à chaque maj.
                for membre in archive.infolist():
                    permissions = (membre.external_attr >> 16) & 0o777
                    if permissions:
                        (Path(dossier_tmp) / membre.filename).chmod(permissions)
        except (urllib.error.URLError, OSError, zipfile.BadZipFile) as e:
            raise RuntimeError(
                f"Impossible de télécharger ou d'extraire la mise à jour\u00a0: {e}"
            ) from e

        # Dossier racine unique de l'archive (ex. « tamponne-abc1234/ ») déduit
        # plutôt que deviné : la convention de nommage Forgejo peut changer.
        racines = [p for p in Path(dossier_tmp).iterdir() if p.is_dir()]
        if len(racines) != 1:
            raise RuntimeError(
                "Structure d'archive inattendue (racine unique attendue)."
            )
        dossier_extrait = racines[0]

        installer_archive(dossier_extrait, CHEMIN_RACINE)


DOSSIERS_PURGES = ("src", "tests")
"""Dossiers où un fichier absent de la nouvelle version est supprimé."""


def installer_archive(dossier_extrait: Path, racine: Path) -> None:
    """Installe le contenu extrait d'une publication dans `racine`.

    Chaque fichier est écrit dans un temporaire puis renommé : un script en
    cours d'exécution (`Tamponne.command` lu par bash) garde son ancien
    contenu au lieu d'être réécrit sous ses pieds. Ensuite, sous `src/` et `tests/`
    seulement, les fichiers absents de la publication sont supprimés avec
    leurs `__pycache__` ; rien n'est purgé dans un clone git (`.git/`).

    Args:
        dossier_extrait: Racine de l'archive extraite.
        racine: Dossier d'installation.
    """
    fichiers_publies: set[Path] = set()
    for fichier_source in dossier_extrait.rglob("*"):
        if fichier_source.is_dir():
            continue
        chemin_relatif = fichier_source.relative_to(dossier_extrait)
        fichiers_publies.add(chemin_relatif)
        fichier_dest = racine / chemin_relatif
        fichier_dest.parent.mkdir(parents=True, exist_ok=True)
        temporaire = fichier_dest.with_name(fichier_dest.name + ".maj")
        shutil.copy2(fichier_source, temporaire)
        temporaire.replace(fichier_dest)
    if not (racine / ".git").exists():
        _purger(racine, fichiers_publies)


def _purger(racine: Path, fichiers_publies: set[Path]) -> None:
    """Supprime sous `DOSSIERS_PURGES` ce que la publication ne contient plus."""
    for nom in DOSSIERS_PURGES:
        dossier = racine / nom
        if not dossier.is_dir():
            continue
        for cache in sorted(dossier.rglob("__pycache__"), reverse=True):
            shutil.rmtree(cache, ignore_errors=True)
        for fichier in sorted(dossier.rglob("*"), reverse=True):
            relatif = fichier.relative_to(racine)
            if fichier.is_file() and relatif not in fichiers_publies:
                fichier.unlink()
            elif fichier.is_dir() and not any(fichier.iterdir()):
                fichier.rmdir()


if __name__ == "__main__":
    if "--appliquer" not in sys.argv:
        print("Usage\u00a0: python -m src.maj --appliquer", file=sys.stderr)
        sys.exit(1)

    info_en_attente = lire_maj_disponible()
    if info_en_attente is None:
        sys.exit(0)  # rien à appliquer, pas une erreur

    try:
        appliquer_maj(info_en_attente)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    effacer_maj_disponible()
