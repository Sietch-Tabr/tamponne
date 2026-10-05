"""Boucle de lancement appelée par `Tamponne.command` et `Tamponne.bat`.

Applique une mise à jour en attente, démarre l'interface dans un
sous-processus et la relance quand elle quitte avec `CODE_REDEMARRAGE`
(« Installer et redémarrer », import de données). La boucle vit ici plutôt
que dans les scripts : Python garde ce module en mémoire, une mise à jour
peut donc remplacer les scripts et `src/` pendant qu'il tourne.

Sans dépendance à Qt : l'interface n'est importée que par le sous-processus.
"""

import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence

from src.maj import CHEMIN_MARQUEUR, CHEMIN_RACINE

CODE_REDEMARRAGE = 42
"""Code de sortie de l'interface qui demande à la boucle de la relancer."""

MESSAGE_MAJ_INDISPONIBLE = (
    "Mise à jour indisponible, on continue avec la version actuelle."
)
MESSAGE_RELANCER = "Relancez Tamponné pour terminer la mise à jour."

type Executer = Callable[[Sequence[str]], int]


def _executer(commande: Sequence[str]) -> int:
    """Lance `commande` depuis la racine de l'installation et attend sa fin."""
    return subprocess.run(commande, cwd=CHEMIN_RACINE, check=False).returncode


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
        print(MESSAGE_RELANCER, file=sys.stderr)
        return False
    return True


def lancer(executer: Executer = _executer) -> int:
    """Démarre l'interface, en la relançant tant qu'elle le demande.

    Args:
        executer: Lance une commande et renvoie son code de sortie
            (remplaçable en test).

    Returns:
        Code de sortie de la dernière exécution de l'interface, ou 1 si une
        mise à jour n'a pas pu être terminée.
    """
    while True:
        if CHEMIN_MARQUEUR.exists() and not _appliquer_maj_en_attente(executer):
            return 1
        code = executer([sys.executable, "-m", "src.gui.application"])
        if code != CODE_REDEMARRAGE:
            return code


if __name__ == "__main__":
    raise SystemExit(lancer())
