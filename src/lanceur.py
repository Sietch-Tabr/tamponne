"""Boucle de lancement appelée par `Tamponne.command` et `Tamponne.bat`.

Applique une mise à jour en attente, démarre l'interface dans un
sous-processus et la relance quand elle quitte avec `CODE_REDEMARRAGE`
(« Installer et redémarrer », import de données). La boucle vit ici plutôt
que dans les scripts : Python garde ce module en mémoire, une mise à jour
peut donc remplacer les scripts et `src/` pendant qu'il tourne.

Sous Windows, `Tamponne.bat` le lance dans sa console : il s'y relance
aussitôt sans console (`CREATE_NO_WINDOW`) pour que le `.bat` se ferme et
que fermer cette console ne ferme pas l'application. Les erreurs
s'affichent alors dans une boîte de dialogue.

Sans dépendance à Qt : l'interface n'est importée que par le sous-processus.
"""

import ctypes
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from src.maj import CHEMIN_MARQUEUR, CHEMIN_RACINE

CODE_REDEMARRAGE = 42
"""Code de sortie de l'interface qui demande à la boucle de la relancer."""
CODE_MAJ_INACHEVEE = 3
"""Code de sortie du lanceur quand une mise à jour n'a pu être terminée
(déjà signalé : distinct du 1 d'une interface arrêtée sur une erreur)."""

MESSAGE_MAJ_INDISPONIBLE = (
    "Mise à jour indisponible, on continue avec la version actuelle."
)
MESSAGE_RELANCER = "Relancez Tamponné pour terminer la mise à jour."
MESSAGE_ERREUR = (
    "Tamponné s'est arrêté sur une erreur. Relancez-le\u00a0; si le problème "
    "persiste, signalez-le sur Codeberg."
)
VARIABLE_DETACHE = "TAMPONNE_SANS_CONSOLE"
"""Posée sur le lanceur relancé sans console (Windows)."""

FLUX_MARQUE_DU_WEB = ":Zone.Identifier"
"""Flux NTFS posé par Windows sur un fichier téléchargé (ou extrait d'un zip
téléchargé) : il fait afficher un avertissement à chaque ouverture."""
DOSSIERS_SANS_MARQUE = {".git", ".venv", "data"}

type Executer = Callable[[Sequence[str]], int]


def retirer_marque_du_web(racine: Path = CHEMIN_RACINE) -> int:
    """Retire la marque du Web des fichiers de l'installation, comme
    `Unblock-File` : l'utilisateur a déjà accepté de lancer Tamponné, les
    lancements suivants ne l'avertissent plus. Sans effet si `Tamponne.bat`
    n'est pas marqué (déjà fait, ou installation non téléchargée).

    Returns:
        Nombre de fichiers débloqués.
    """
    if not os.path.exists(str(racine / "Tamponne.bat") + FLUX_MARQUE_DU_WEB):
        return 0
    debloques = 0
    for dossier, sous_dossiers, fichiers in os.walk(racine):
        sous_dossiers[:] = [d for d in sous_dossiers if d not in DOSSIERS_SANS_MARQUE]
        for nom in fichiers:
            if ":" in nom:
                continue
            try:
                os.remove(os.path.join(dossier, nom) + FLUX_MARQUE_DU_WEB)
            except OSError:
                continue
            debloques += 1
    return debloques


def _executer(commande: Sequence[str]) -> int:
    """Lance `commande` depuis la racine de l'installation et attend sa fin ;
    sous Windows, sans fenêtre de console."""
    if sys.platform == "win32":
        return subprocess.run(
            commande,
            cwd=CHEMIN_RACINE,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).returncode
    return subprocess.run(commande, cwd=CHEMIN_RACINE, check=False).returncode


def signaler(message: str) -> None:
    """Message d'erreur sur la sortie d'erreur et, sous Windows où le
    lanceur tourne sans console, dans une boîte de dialogue."""
    print(message, file=sys.stderr)
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(None, message, "Tamponné", 0x10)


def _relancer_sans_console() -> None:
    """Relance ce lanceur hors de la console de `Tamponne.bat` (Windows).

    Le processus quitte un éventuel job de son parent (lanceur Python de
    l'environnement) pour survivre à la fermeture de la console ; si le job
    l'interdit, il reste dedans, ce qui suffit tant que le parent vit.
    """
    if sys.platform != "win32":
        return
    environnement = {**os.environ, VARIABLE_DETACHE: "1"}
    commande = [sys.executable, "-m", "src.lanceur"]
    drapeaux = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen(
            commande,
            cwd=CHEMIN_RACINE,
            env=environnement,
            creationflags=drapeaux | subprocess.CREATE_BREAKAWAY_FROM_JOB,
        )
    except OSError:
        subprocess.Popen(
            commande, cwd=CHEMIN_RACINE, env=environnement, creationflags=drapeaux
        )


def _appliquer_maj_en_attente(executer: Executer) -> bool:
    """Applique la mise à jour en attente puis resynchronise les dépendances.

    Returns:
        Faux si la synchronisation a échoué : l'environnement Python peut
        alors être incomplet et il faut relancer depuis le script.
    """
    if executer([sys.executable, "-m", "src.maj", "--appliquer"]) != 0:
        print(MESSAGE_MAJ_INDISPONIBLE, file=sys.stderr)
        return True
    uv = shutil.which("uv")
    if uv is None or executer([uv, "sync", "--quiet"]) != 0:
        signaler(MESSAGE_RELANCER)
        return False
    return True


def lancer(executer: Executer = _executer) -> int:
    """Démarre l'interface, en la relançant tant qu'elle le demande.

    Args:
        executer: Lance une commande et renvoie son code de sortie
            (remplaçable en test).

    Returns:
        Code de sortie de la dernière exécution de l'interface, ou
        `CODE_MAJ_INACHEVEE` si une mise à jour n'a pas pu être terminée.
    """
    while True:
        if CHEMIN_MARQUEUR.exists() and not _appliquer_maj_en_attente(executer):
            return CODE_MAJ_INACHEVEE
        code = executer([sys.executable, "-m", "src.gui.application"])
        if code != CODE_REDEMARRAGE:
            return code


if __name__ == "__main__":
    if sys.platform == "win32" and VARIABLE_DETACHE not in os.environ:
        retirer_marque_du_web()
        _relancer_sans_console()
        raise SystemExit(0)
    code_sortie = lancer()
    if sys.platform == "win32" and code_sortie not in (0, CODE_MAJ_INACHEVEE):
        signaler(MESSAGE_ERREUR)
    raise SystemExit(code_sortie)
