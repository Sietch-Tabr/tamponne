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
lazy import urllib.error
lazy import urllib.request
lazy import zipfile
from datetime import date
from pathlib import Path

from src.types import EchecMaj, InfoMaj
from src.utils import ecriture_atomique

URL_API_RELEASES = "https://codeberg.org/api/v1/repos/Kwaite/tamponne/releases/latest"
PREFIXE_ARCHIVES = "https://codeberg.org/Kwaite/tamponne/"
"""Seules les archives du dépôt sont téléchargées, quoi que dise l'API."""
CHEMIN_RACINE = Path(__file__).parent.parent
CHEMIN_PYPROJECT = CHEMIN_RACINE / "pyproject.toml"
CHEMIN_MARQUEUR = CHEMIN_RACINE / "data" / "maj_disponible.json"
CHEMIN_ECHEC = CHEMIN_RACINE / "data" / "maj_echouee.json"
"""Dernière mise à jour annulée : pas de nouvel essai automatique."""
NOM_PRECEDENTE = ".maj-precedente"
"""Copie de la version remplacée, à la racine (hors de l'export de `data/`),
supprimée une fois la nouvelle version démarrée."""
EXCLUS_SAUVEGARDE = {".git", ".venv", "data", NOM_PRECEDENTE}
_TIMEOUT = 15
_TIMEOUT_TELECHARGEMENT = 60
"""Délai maximal sans données reçues pendant le téléchargement de l'archive."""


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


class VerificationImpossible(RuntimeError):
    """Codeberg n'a pas pu être interrogé ; le message est le détail
    technique (erreur réseau, réponse illisible)."""


def verifier_derniere_publication() -> InfoMaj | None:
    """Interroge la dernière publication Codeberg — `None` si aucune
    publication ou si elle n'est pas plus récente.

    Raises:
        VerificationImpossible: Codeberg injoignable ou réponse illisible :
            on ne sait pas s'il existe une version plus récente.
    """
    try:
        requete = urllib.request.Request(
            URL_API_RELEASES, headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(requete, timeout=_TIMEOUT) as reponse:
            donnees = json.loads(reponse.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError) as erreur:
        raise VerificationImpossible(str(erreur)) from erreur

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


def lire_echec() -> EchecMaj | None:
    """Dernière mise à jour annulée, `None` si aucune (ou fichier illisible)."""
    if not CHEMIN_ECHEC.exists():
        return None
    try:
        return json.loads(CHEMIN_ECHEC.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        return None


def enregistrer_echec(version: str, motif: str) -> None:
    """Mémorise l'annulation de `version` : la vérification ne la reprogramme
    plus d'elle-même, seul « Installer et redémarrer » la retente."""
    echec: EchecMaj = {
        "version": version,
        "motif": motif,
        "date": date.today().isoformat(),
    }
    ecriture_atomique(CHEMIN_ECHEC, dict(echec))


def maj_en_echec(version: str) -> bool:
    """Vrai si `version` est la dernière mise à jour annulée."""
    echec = lire_echec()
    return echec is not None and echec["version"] == version


def dossier_precedente() -> Path:
    """Copie de la version remplacée par la dernière mise à jour."""
    return CHEMIN_RACINE / NOM_PRECEDENTE


def sauvegarder_version_actuelle() -> None:
    """Copie l'installation (hors `EXCLUS_SAUVEGARDE`) dans
    `dossier_precedente()`, pour revenir en arrière si la mise à jour ne
    démarre pas. Écrite à côté puis renommée : une copie interrompue n'est
    jamais prise pour une sauvegarde complète."""
    dossier = dossier_precedente()
    temporaire = dossier.with_name(dossier.name + ".tmp")
    shutil.rmtree(temporaire, ignore_errors=True)
    temporaire.mkdir()
    for element in CHEMIN_RACINE.iterdir():
        if element.name in EXCLUS_SAUVEGARDE or element == temporaire:
            continue
        if element.is_dir():
            shutil.copytree(
                element,
                temporaire / element.name,
                symlinks=True,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        else:
            shutil.copy2(element, temporaire / element.name)
    shutil.rmtree(dossier, ignore_errors=True)
    temporaire.replace(dossier)


def restaurer_version_precedente() -> bool:
    """Réinstalle la version sauvegardée avant la dernière mise à jour
    (fichiers ajoutés depuis sous `src/` retirés), puis efface la copie.

    Returns:
        Faux s'il n'y avait aucune sauvegarde.
    """
    dossier = dossier_precedente()
    if not dossier.is_dir():
        return False
    installer_archive(dossier, CHEMIN_RACINE)
    shutil.rmtree(dossier, ignore_errors=True)
    return True


def valider_maj() -> None:
    """Rend la dernière mise à jour définitive, une fois l'interface
    chargée : plus de retour arrière possible, échec antérieur oublié."""
    dossier = dossier_precedente()
    if dossier.exists():
        shutil.rmtree(dossier, ignore_errors=True)
        CHEMIN_ECHEC.unlink(missing_ok=True)


def _telecharger(url: str, destination: Path) -> None:
    """Enregistre `url` dans `destination`, sans jamais attendre plus de
    `_TIMEOUT_TELECHARGEMENT` secondes une réponse ou des données."""
    with (
        urllib.request.urlopen(url, timeout=_TIMEOUT_TELECHARGEMENT) as reponse,
        destination.open("wb") as fichier,
    ):
        shutil.copyfileobj(reponse, fichier)


def appliquer_maj(info: InfoMaj) -> None:
    """Télécharge et applique la publication `info`.

    Installe les fichiers de l'archive dans la racine du projet (voir
    `installer_archive`) : l'archive Codeberg ne contient que les fichiers
    suivis par git et publiés, donc `data/`, `.git/` et les fichiers non
    versionnés hors de `src/` ne sont jamais touchés. La version remplacée
    est d'abord copiée (`sauvegarder_version_actuelle`) pour le retour
    arrière du lanceur.

    Raises:
        RuntimeError: Archive hors du dépôt, téléchargement, extraction ou
            sauvegarde impossible, rien n'est installé — l'appelant décide de continuer avec la
            version actuelle plutôt que bloquer.
    """
    if not info["url_zip"]:
        raise RuntimeError("URL de l'archive de mise à jour manquante.")
    if not info["url_zip"].startswith(PREFIXE_ARCHIVES):
        raise RuntimeError(
            f"Archive de mise à jour hors du dépôt Tamponné refusée\u00a0: {info['url_zip']}"
        )

    with tempfile.TemporaryDirectory(prefix="tamponne-maj-") as dossier_tmp:
        chemin_zip = Path(dossier_tmp) / "maj.zip"
        try:
            _telecharger(info["url_zip"], chemin_zip)
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

        try:
            sauvegarder_version_actuelle()
        except OSError as e:
            raise RuntimeError(
                f"Impossible de sauvegarder la version actuelle\u00a0: {e}"
            ) from e
        installer_archive(dossier_extrait, CHEMIN_RACINE)


DOSSIERS_PURGES = ("src",)
"""Dossiers où un fichier absent de la nouvelle version est supprimé."""


def installer_archive(dossier_extrait: Path, racine: Path) -> None:
    """Installe le contenu extrait d'une publication dans `racine`.

    Chaque fichier est écrit dans un temporaire puis renommé : un script en
    cours d'exécution (`Tamponne.command` lu par bash) garde son ancien
    contenu au lieu d'être réécrit sous ses pieds. Ensuite, sous `src/`
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
