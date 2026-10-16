"""Boucle de lancement appelée par `Tamponne.command` et `Tamponne.bat`.

Applique une mise à jour en attente, démarre l'interface dans un
sous-processus et la relance quand elle quitte avec `CODE_REDEMARRAGE`
(« Installer et redémarrer », import de données). La boucle vit ici plutôt
que dans les scripts : Python garde ce module en mémoire, une mise à jour
peut donc remplacer les scripts et `src/` pendant qu'il tourne.

Une mise à jour qui ne s'installe pas (synchronisation impossible même
après mise à jour de uv) ou ne démarre pas (interface arrêtée avant d'avoir
chargé sa fenêtre) est annulée : la version précédente, sauvegardée par
`src.maj`, est restaurée et relancée.

Sous Windows, `Tamponne.bat` le lance dans sa console : il s'y relance
aussitôt sans console (`CREATE_NO_WINDOW`) pour que le `.bat` se ferme et
que fermer cette console ne ferme pas l'application. Les erreurs
s'affichent alors dans une boîte de dialogue. La relance utilise
l'interpréteur de base, hors de `.venv` : `uv sync` peut alors recréer
l'environnement sans buter sur un exécutable verrouillé.

Un verrou (`instance_unique`) tient le lanceur seul pour toute sa durée :
un second lancement, par un clic de trop ou un double-clic répété, le dit et
s'arrête au lieu d'ouvrir une deuxième fenêtre ou de relancer l'installation.

Sans dépendance à Qt : l'interface n'est importée que par le sous-processus.
"""

import contextlib
import ctypes
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, TextIO

from src import maj
from src.maj import CHEMIN_RACINE

CODE_REDEMARRAGE = 42
"""Code de sortie de l'interface qui demande à la boucle de la relancer."""
CODE_MAJ_INACHEVEE = 3
"""Code de sortie du lanceur quand une mise à jour n'a pu être terminée
(déjà signalé : distinct du 1 d'une interface arrêtée sur une erreur)."""

JOURNAL_AFFICHE = str(Path("data") / "tamponne.log")
"""Journal (`CHEMIN_JOURNAL`), tel que nommé à l'utilisateur."""
MESSAGE_RELANCER = (
    "La mise à jour de Tamponné n'a pas pu se terminer\u00a0: uv n'a pas pu "
    "télécharger Python ou ses composants, même après sa propre mise à jour.\n\n"
    "Vérifiez que l'ordinateur est connecté à internet (et le proxy éventuel), "
    "puis relancez Tamponné. Si ce message revient, signalez-le sur Codeberg "
    f"en joignant le fichier «\u00a0{JOURNAL_AFFICHE}\u00a0» du dossier de "
    "Tamponné."
)
MESSAGE_ERREUR = (
    "Tamponné s'est arrêté sur une erreur.\n\n"
    "Relancez-le\u00a0; si le problème persiste, signalez-le sur Codeberg en "
    f"joignant le fichier «\u00a0{JOURNAL_AFFICHE}\u00a0» du dossier de "
    "Tamponné."
)
CHEMIN_VERROU = CHEMIN_RACINE / "data" / "tamponne.verrou"
"""Fichier verrouillé par le lanceur tant qu'il tourne (le système libère le
verrou à la mort du processus : jamais de verrou périmé)."""
MESSAGE_DEJA_LANCE = (
    "Tamponné est déjà ouvert, ou en cours d'ouverture.\n\n"
    "Patientez quelques instants (la première ouverture peut durer une "
    "minute), ou cherchez sa fenêtre dans la barre des tâches ou le Dock."
)
DELAI_LECTURE = 6
"""Secondes pendant lesquelles la console du lanceur Windows reste ouverte
pour laisser lire `MESSAGE_DEJA_LANCE`."""
ATTRIBUTS_ANNONCE = "\x1b[1;97;44m"
"""Gras, blanc sur bleu : les messages de Tamponné se distinguent des
sorties de uv et du système."""
FIN_ATTRIBUTS = "\x1b[0m"
EFFACER_FIN_DE_LIGNE = "\x1b[K"
MODE_TERMINAL_VIRTUEL = 0x0004
"""Drapeau Windows qui fait interpréter les séquences `\\x1b[…` par la console."""
TITRE_SYNCHRONISATION = (
    "Tamponné\u00a0: téléchargement de Python et des composants (uv sync), "
    "quelques minutes peuvent être nécessaires…"
)
TITRE_MAJ_UV = "Mise à jour de uv, le gestionnaire de Python de Tamponné…"
MOTIF_SYNCHRONISATION = "Python ou ses composants n'ont pas pu être téléchargés"
MOTIF_DEMARRAGE = "la nouvelle version ne démarrait pas"
MOTIF_TELECHARGEMENT = "elle n'a pas pu être téléchargée"
MOTIF_INSTALLATION = "ses fichiers n'ont pas pu être installés"
LONGUEUR_DETAIL = 300
"""Au-delà, la dernière erreur est tronquée dans la boîte de dialogue (le
journal garde tout)."""
MOTIF_ERREUR = re.compile(r"(error:|[A-Za-z_.]*(Error|Exception)\b)")
DEBUT_EN_TETE = "===== "
"""Début de la ligne qui ouvre chaque lancement dans le journal."""


def premiere_erreur() -> str:
    """Première erreur écrite dans le journal depuis le début du lancement
    en cours (dernier en-tête) : ligne `error:` de uv ou exception Python
    (`…Error: …`), sinon dernière ligne écrite ; la première est la cause,
    les suivantes en découlent."""
    try:
        texte = CHEMIN_JOURNAL.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lancement = texte.rsplit(f"\n{DEBUT_EN_TETE}", 1)[-1]
    lignes = [
        ligne.strip()
        for ligne in lancement.splitlines()
        if ligne.strip() and not ligne.startswith(("$ ", DEBUT_EN_TETE))
    ]
    erreur = next((ligne for ligne in lignes if MOTIF_ERREUR.match(ligne)), None)
    if erreur is None:
        erreur = lignes[-1] if lignes else ""
    return erreur[:LONGUEUR_DETAIL]


def avec_detail(message: str) -> str:
    """`message` suivi de l'erreur réelle (`premiere_erreur`), pour le
    diagnostic."""
    erreur = premiere_erreur()
    return f"{message}\n\nDétail\u00a0: {erreur}" if erreur else message


def message_maj_non_telechargee(version: str, actuelle: str) -> str:
    """Message affiché quand l'archive de la mise à jour `version` n'a pas
    pu être téléchargée : rien n'a changé, Tamponné reste en `actuelle`."""
    mise_a_jour = f"La mise à jour {version}" if version else "La mise à jour"
    return (
        f"{mise_a_jour} de Tamponné n'a pas pu être téléchargée.\n\n"
        f"Tamponné continue dans sa version actuelle ({actuelle})\u00a0; vos "
        "données sont intactes. Vérifiez que l'ordinateur est connecté à "
        "internet (et le proxy éventuel), puis réessayez depuis Réglages, "
        "«\u00a0Avis de mise à jour\u00a0», bouton «\u00a0Installer et "
        "redémarrer\u00a0»."
    )


def message_maj_annulee(version: str, motif: str, precedente: str) -> str:
    """Message affiché quand le lanceur revient à la version `precedente`
    après l'échec de la mise à jour `version` (vide si inconnue)."""
    mise_a_jour = f"La mise à jour {version}" if version else "La mise à jour"
    return (
        f"{mise_a_jour} de Tamponné n'a pas pu être installée\u00a0: {motif}.\n\n"
        f"Pas d'inquiétude\u00a0: Tamponné redémarre dans sa version précédente "
        f"({precedente}) et vos données sont intactes. Vous pourrez réessayer "
        "plus tard depuis Réglages, «\u00a0Avis de mise à jour\u00a0», bouton "
        "«\u00a0Installer et redémarrer\u00a0»."
    )


VARIABLE_DETACHE = "TAMPONNE_SANS_CONSOLE"
"""Posée sur le lanceur relancé sans console (Windows)."""

FLUX_MARQUE_DU_WEB = ":Zone.Identifier"
"""Flux NTFS posé par Windows sur un fichier téléchargé (ou extrait d'un zip
téléchargé) : il fait afficher un avertissement à chaque ouverture."""
DOSSIERS_SANS_MARQUE = frozenset({".git", ".venv", "data", maj.NOM_PRECEDENTE})
CHEMIN_JOURNAL = CHEMIN_RACINE / "data" / "tamponne.log"
"""Journal de Tamponné : sorties des commandes (uv, interface et ses
erreurs horodatées) et messages du lanceur, lancement après lancement. Sous
Windows, ces sorties n'ont pas de console où s'afficher."""
CHEMIN_JOURNAL_ARCHIVE = CHEMIN_RACINE / "data" / "tamponne.1.log"
"""Journal précédent, gardé une fois `TAILLE_MAX_JOURNAL` dépassée."""
TAILLE_MAX_JOURNAL = 1_000_000
NOM_ANCIEN_JOURNAL = "journal_lancement.log"
"""Journal des versions précédentes (jusqu'à la 1.3.4), retiré par
`ouvrir_journal` : `src.nettoyage` ne touche jamais à `data/`."""
INSTALLEUR_UV_WINDOWS = (
    "powershell",
    "-NoProfile",
    "-ExecutionPolicy",
    "ByPass",
    "-Command",
    "irm https://astral.sh/uv/install.ps1 | iex",
)
"""Secours de `uv self update` : PowerShell passe nativement le proxy
système, et l'installeur ne dépend pas de l'API GitHub."""

type Executer = Callable[[Sequence[str]], int]


def retirer_marque_du_web(racine: Path = CHEMIN_RACINE) -> int:
    """Retire la marque du Web des fichiers de l'installation, comme
    `Unblock-File` : l'utilisateur a déjà accepté de lancer Tamponné, les
    lancements suivants ne l'avertissent plus. Sans effet si `Tamponne.bat`
    n'est pas marqué (déjà fait, ou installation non téléchargée).

    Returns:
        Nombre de fichiers débloqués.
    """
    if not Path(f"{racine / 'Tamponne.bat'}{FLUX_MARQUE_DU_WEB}").exists():
        return 0
    debloques = 0
    for dossier, sous_dossiers, fichiers in racine.walk():
        sous_dossiers[:] = [d for d in sous_dossiers if d not in DOSSIERS_SANS_MARQUE]
        for nom in fichiers:
            if ":" in nom:
                continue
            try:
                Path(f"{dossier / nom}{FLUX_MARQUE_DU_WEB}").unlink()
            except OSError:
                continue
            debloques += 1
    return debloques


def anonymiser(texte: str) -> str:
    """`texte` sans le chemin du dossier personnel, remplacé par `~` : le
    journal est joint aux signalements publics, le nom de la session n'a
    pas à y figurer."""
    personnel = Path.home()
    # Windows ne distingue pas les majuscules dans un chemin.
    casse = re.IGNORECASE if sys.platform == "win32" else 0
    for forme in {str(personnel), personnel.as_posix()}:
        texte = re.sub(re.escape(forme), "~", texte, flags=casse)
    return texte


def ouvrir_journal() -> None:
    """Ouvre le lancement dans le journal : archive le journal s'il dépasse
    `TAILLE_MAX_JOURNAL` (une seule archive, `CHEMIN_JOURNAL_ARCHIVE`), puis
    écrit l'en-tête daté avec les versions de Tamponné, du système et de
    Python. Retire au passage l'ancien journal (`NOM_ANCIEN_JOURNAL`)."""
    with contextlib.suppress(OSError):
        (CHEMIN_JOURNAL.parent / NOM_ANCIEN_JOURNAL).unlink(missing_ok=True)
    try:
        if CHEMIN_JOURNAL.stat().st_size > TAILLE_MAX_JOURNAL:
            CHEMIN_JOURNAL.replace(CHEMIN_JOURNAL_ARCHIVE)
    except OSError:
        pass
    en_tete = (
        f"{DEBUT_EN_TETE}{datetime.now():%Y-%m-%d %H:%M:%S} · Tamponné "
        f"{maj.version_locale()} · {platform.system()} {platform.release()} · "
        f"Python {platform.python_version()} ====="
    )
    noter(en_tete)


def noter(texte: str) -> None:
    """Ajoute `texte` (une ou plusieurs lignes) au journal, anonymisé ; un
    journal impossible à écrire n'empêche jamais le lancement."""
    try:
        CHEMIN_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with CHEMIN_JOURNAL.open("a", encoding="utf-8") as journal:
            journal.write(anonymiser(texte.rstrip("\n") + "\n"))
    except OSError:
        pass


@contextmanager
def _ctrl_c_laisse_a_l_enfant() -> Iterator[None]:
    """Le terminal envoie Ctrl+C à tout le groupe de processus : le lanceur
    l'ignore le temps de l'exécution, le processus lancé le traite seul (un
    gestionnaire, contrairement à `SIG_IGN`, n'est pas hérité par l'enfant)."""
    try:
        precedent = signal.signal(signal.SIGINT, lambda *_: None)
    except ValueError:  # hors du fil principal
        yield
        return
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, precedent)


CODE_LANCEMENT_IMPOSSIBLE = 127
"""Code rendu quand la commande n'a pas pu démarrer (convention du shell)."""


def _executer(commande: Sequence[str]) -> int:
    """Lance `commande` depuis la racine de l'installation et attend sa fin.
    Ses sorties s'affichent au fil de l'eau (`_afficher`) et sont ajoutées à
    `CHEMIN_JOURNAL`, anonymisées ; sous Windows, sans fenêtre propre."""
    CHEMIN_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    with CHEMIN_JOURNAL.open("a", encoding="utf-8") as journal:
        journal.write(anonymiser(f"$ {' '.join(commande)}\n"))
        journal.flush()
        drapeaux = 0
        if sys.platform == "win32":
            drapeaux = subprocess.CREATE_NO_WINDOW
        with _ctrl_c_laisse_a_l_enfant():
            try:
                processus = subprocess.Popen(
                    commande,
                    cwd=CHEMIN_RACINE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=drapeaux,
                )
            except OSError as erreur:
                # Programme introuvable ou refusé : un code d'échec, pas une trace.
                message = f"Impossible de lancer {commande[0]}\u00a0: {erreur}\n"
                journal.write(anonymiser(message))
                _afficher(anonymiser(message))
                return CODE_LANCEMENT_IMPOSSIBLE
            if processus.stdout is None:
                return processus.wait()
            for ligne in processus.stdout:
                journal.write(anonymiser(ligne))
                journal.flush()
                _afficher(ligne)
            return processus.wait()


_sortie: TextIO | None = sys.stdout
"""Où `_afficher` écrit : le terminal, ou la console ouverte par
`console_visible` (le lanceur Windows n'en a pas)."""
_couleurs_actives = True
"""Faux si la console ouverte par `console_visible` ne sait pas colorer."""


def _afficher(texte: str) -> None:
    """Écrit `texte` pour l'utilisateur, si une sortie est disponible."""
    if _sortie is None:
        return
    try:
        _sortie.write(texte)
        _sortie.flush()
    except OSError, ValueError:
        pass


def _couleurs_possibles() -> bool:
    """Vrai si la sortie est un terminal qui affiche les couleurs (et que
    l'utilisateur ne les a pas refusées avec `NO_COLOR`)."""
    if _sortie is None or not _couleurs_actives or "NO_COLOR" in os.environ:
        return False
    try:
        return _sortie.isatty()
    except ValueError:
        return False


def mettre_en_valeur(texte: str, couleurs: bool) -> str:
    """`texte` en bandeau bleu sur trois lignes (une marge au-dessus et
    au-dessous), ou introduit par `>>>` quand les couleurs sont refusées :
    un message de Tamponné ne se confond pas avec les sorties de uv."""
    if not couleurs:
        return f"\n>>> {texte}\n\n"

    def ligne(contenu: str) -> str:
        return f"{ATTRIBUTS_ANNONCE}  {contenu}{EFFACER_FIN_DE_LIGNE}{FIN_ATTRIBUTS}\n"

    return f"\n{ligne('')}{ligne(texte)}{ligne('')}\n"


def annoncer(texte: str) -> None:
    """Affiche `texte`, un message de Tamponné, bien distinct des sorties
    des commandes (voir `mettre_en_valeur`)."""
    _afficher(mettre_en_valeur(texte, _couleurs_possibles()))


def _activer_couleurs_console() -> bool:
    """Active les séquences de couleur de la console Windows ouverte ;
    faux si elle ne les prend pas en charge (très ancien Windows)."""
    if sys.platform != "win32":
        return False
    noyau = ctypes.windll.kernel32
    poignee = noyau.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    mode = ctypes.c_ulong()
    if not noyau.GetConsoleMode(poignee, ctypes.byref(mode)):
        return False
    return bool(noyau.SetConsoleMode(poignee, mode.value | MODE_TERMINAL_VIRTUEL))


@contextmanager
def console_visible(titre: str) -> Iterator[None]:
    """Sous Windows, ouvre une console le temps du bloc pour montrer la
    progression (téléchargements de uv) au lieu de travailler sans rien
    afficher ; ailleurs, le terminal du lanceur suffit. `titre` est annoncé
    en tête."""
    global _sortie, _couleurs_actives
    if sys.platform != "win32" or not ctypes.windll.kernel32.AllocConsole():
        annoncer(titre)
        yield
        return
    precedente, couleurs_precedentes = _sortie, _couleurs_actives
    try:
        with open("CONOUT$", "w", encoding="utf-8") as console:
            _sortie = console
            _couleurs_actives = _activer_couleurs_console()
            ctypes.windll.kernel32.SetConsoleTitleW("Tamponné")
            annoncer(titre)
            yield
    finally:
        _sortie, _couleurs_actives = precedente, couleurs_precedentes
        ctypes.windll.kernel32.FreeConsole()


def python_environnement() -> Path:
    """Interpréteur de `.venv`, celui qui fait tourner l'interface et
    `src.maj` (le lanceur peut tourner sur l'interpréteur de base)."""
    if sys.platform == "win32":
        return CHEMIN_RACINE / ".venv" / "Scripts" / "python.exe"
    return CHEMIN_RACINE / ".venv" / "bin" / "python"


def python_de_base() -> Path:
    """Interpréteur Windows dont dérive `.venv`, sur lequel le lanceur se
    relance pour ne pas verrouiller `.venv` pendant `uv sync`."""
    return Path(sys.base_prefix) / "python.exe"


class DejaLance(RuntimeError):
    """Un autre lanceur tient déjà `CHEMIN_VERROU`."""


def _verrouiller(fichier: BinaryIO) -> None:
    """Prend le verrou exclusif de `fichier` sans attendre.

    Raises:
        DejaLance: un autre processus le tient.
    """
    try:
        if sys.platform == "win32":
            import msvcrt

            fichier.seek(0)
            msvcrt.locking(fichier.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fichier.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as erreur:
        raise DejaLance from erreur


@contextmanager
def instance_unique() -> Iterator[None]:
    """Garde le verrou du lanceur le temps du bloc : un second lanceur, qui
    attend la fin de l'installation ou de l'interface, n'a rien à faire.

    Raises:
        DejaLance: un autre lanceur tourne déjà.
    """
    CHEMIN_VERROU.parent.mkdir(parents=True, exist_ok=True)
    with CHEMIN_VERROU.open("a+b") as fichier:
        _verrouiller(fichier)
        yield


def verrou_libre() -> bool:
    """Vrai si aucun lanceur ne tourne (le verrou est repris aussitôt
    rendu : simple vérification)."""
    try:
        with instance_unique():
            return True
    except DejaLance:
        return False


def signaler(message: str) -> None:
    """Message d'erreur dans le journal, sur la sortie d'erreur et, sous
    Windows où le lanceur tourne sans console, dans une boîte de dialogue."""
    noter(f"{datetime.now():%H:%M:%S} ERREUR lanceur\u00a0: {message}")
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
    commande = [str(python_de_base()), "-m", "src.lanceur"]
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


def _mettre_a_jour_uv(executer: Executer, uv: str) -> bool:
    """`uv self update`, puis l'installeur sous Windows s'il échoue. Le
    proxy arrive par `HTTPS_PROXY`, posé par `Tamponne.bat` et hérité."""
    if executer([uv, "self", "update"]) == 0:
        return True
    return sys.platform == "win32" and executer(INSTALLEUR_UV_WINDOWS) == 0


def synchroniser(executer: Executer) -> bool:
    """`uv sync`, retenté une fois après mise à jour de uv : un uv trop
    ancien ne connaît pas les dernières versions de Python
    (`required-version` de `pyproject.toml`). La progression reste visible
    (`console_visible`) : le téléchargement peut prendre plusieurs minutes.

    Returns:
        Vrai si l'environnement est à jour.
    """
    uv = shutil.which("uv")
    if uv is None:
        return False
    with console_visible(TITRE_SYNCHRONISATION):
        if executer([uv, "sync"]) == 0:
            return True
        annoncer(TITRE_MAJ_UV)
        return _mettre_a_jour_uv(executer, uv) and executer([uv, "sync"]) == 0


def _annuler_maj(executer: Executer, motif: str, version: str) -> bool:
    """Revient à la version sauvegardée avant la mise à jour, mémorise
    l'échec de `version` (pas de nouvel essai automatique) et resynchronise.

    Returns:
        Faux si l'ancienne version n'a pas pu être remise en état : il faut
        alors relancer depuis le script.
    """
    if not maj.restaurer_version_precedente():
        signaler(avec_detail(MESSAGE_RELANCER))
        return False
    maj.enregistrer_echec(version, motif)
    if not synchroniser(executer):
        signaler(avec_detail(MESSAGE_RELANCER))
        return False
    signaler(avec_detail(message_maj_annulee(version, motif, maj.version_locale())))
    return True


def _appliquer_maj_en_attente(executer: Executer) -> bool:
    """Applique la mise à jour en attente puis resynchronise les
    dépendances ; l'annule si l'une ou l'autre étape échoue.

    Returns:
        Faux si aucune version utilisable n'a pu être remise en état.
    """
    # Version lue avant l'installation : interrompue, elle peut laisser un
    # pyproject.toml illisible.
    info = maj.lire_maj_disponible()
    version = info.get("version", "") if info is not None else ""
    if executer([str(python_environnement()), "-m", "src.maj", "--appliquer"]) != 0:
        if maj.dossier_precedente().is_dir():
            return _annuler_maj(executer, MOTIF_INSTALLATION, version)
        # Rien d'installé : pas de nouvel essai silencieux à chaque lancement,
        # l'avis de Réglages donne le motif et permet de réessayer.
        maj.enregistrer_echec(version, MOTIF_TELECHARGEMENT)
        maj.effacer_maj_disponible()
        signaler(
            avec_detail(message_maj_non_telechargee(version, maj.version_locale()))
        )
        return True
    if synchroniser(executer):
        return True
    return _annuler_maj(executer, MOTIF_SYNCHRONISATION, version)


def lancer(executer: Executer = _executer) -> int:
    """Démarre l'interface, en la relançant tant qu'elle le demande.

    Une interface arrêtée avant de valider la mise à jour (`maj.valider_maj`,
    appelée une fois la fenêtre chargée) déclenche le retour à la version
    précédente, puis la relance.

    Args:
        executer: Lance une commande et renvoie son code de sortie
            (remplaçable en test).

    Returns:
        Code de sortie de la dernière exécution de l'interface, ou
        `CODE_MAJ_INACHEVEE` si une mise à jour n'a pas pu être terminée.
    """
    while True:
        if maj.CHEMIN_MARQUEUR.exists() and not _appliquer_maj_en_attente(executer):
            return CODE_MAJ_INACHEVEE
        code = executer([str(python_environnement()), "-m", "src.gui.application"])
        if maj.dossier_precedente().is_dir():
            if not _annuler_maj(executer, MOTIF_DEMARRAGE, maj.version_locale()):
                return CODE_MAJ_INACHEVEE
            continue
        if code != CODE_REDEMARRAGE:
            return code


def principal() -> int:
    """Point d'entrée : sous Windows, relance le lanceur sans console ;
    partout, ne tourne qu'un lanceur à la fois.

    Returns:
        Code de sortie du processus (0 si un autre lanceur tourne déjà).
    """
    if sys.platform == "win32" and VARIABLE_DETACHE not in os.environ:
        if not verrou_libre():
            # Console de Tamponne.bat encore visible : le message s'y lit.
            print(MESSAGE_DEJA_LANCE)
            time.sleep(DELAI_LECTURE)
            return 0
        retirer_marque_du_web()
        _relancer_sans_console()
        return 0
    try:
        with instance_unique():
            ouvrir_journal()
            code = lancer()
            if sys.platform == "win32" and code not in (0, CODE_MAJ_INACHEVEE):
                signaler(avec_detail(MESSAGE_ERREUR))
            return code
    except DejaLance:
        noter(f"{datetime.now():%H:%M:%S} lancement ignoré\u00a0: déjà ouvert")
        print(MESSAGE_DEJA_LANCE, file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(principal())
