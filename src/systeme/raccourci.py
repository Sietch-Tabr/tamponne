"""Raccourci de Tamponné dans le menu des applications du système.

L'application est portable : le raccourci pointe vers le dossier où elle se
trouve. Ce dossier est enregistré dans `data/raccourci.json` ; s'il ne
correspond plus à l'emplacement actuel, le dossier a été déplacé et le
raccourci est à mettre à jour (au choix de l'utilisateur).

- Windows : `Tamponné.lnk` dans le menu Démarrer de l'utilisateur ;
- macOS : `Tamponné.app` dans `~/Applications` (Spotlight, Launchpad, Dock) ;
- Linux : `tamponne.desktop` dans `~/.local/share/applications`.

Sans dépendance à Qt.
"""

import json
import os
import plistlib
import shlex
import shutil
lazy import subprocess
import sys
from pathlib import Path
from typing import Literal

from src.chemins import DATA, RACINE
from src.utils import ecriture_atomique

CHEMIN_RACINE = RACINE
CHEMIN_PREFERENCE = DATA / "raccourci.json"
NOM = "Tamponné"
IDENTIFIANT_MACOS = "org.codeberg.kwaite.tamponne"

type Systeme = Literal["windows", "macos", "linux"]
type EtatRaccourci = Literal["indisponible", "absent", "a_jour", "deplace"]
type Question = Literal["aucune", "premier_lancement", "deplace"]


class ErreurRaccourci(RuntimeError):
    """Création ou retrait impossible ; le message s'affiche tel quel."""


def systeme_courant() -> Systeme | None:
    """Système pris en charge, `None` pour les autres."""
    # Variable typée `str` : pyright ne fige pas le résultat sur la plateforme
    # d'analyse.
    plateforme: str = sys.platform
    if plateforme == "win32":
        return "windows"
    if plateforme == "darwin":
        return "macos"
    if plateforme.startswith("linux"):
        return "linux"
    return None


def emplacement(systeme: Systeme) -> Path:
    """Chemin du raccourci pour `systeme`, d'après le profil de l'utilisateur."""
    if systeme == "windows":
        menu = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs"
        return menu / f"{NOM}.lnk"
    if systeme == "macos":
        return Path.home() / "Applications" / f"{NOM}.app"
    donnees = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share")
    return Path(donnees) / "applications" / "tamponne.desktop"


# --- Préférence ---


def _lire_preference() -> dict[str, object]:
    """Contenu de `raccourci.json`, vide s'il est absent ou illisible."""
    try:
        donnees = json.loads(CHEMIN_PREFERENCE.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        return {}
    return donnees if isinstance(donnees, dict) else {}


def _enregistrer(dossier: Path | None) -> None:
    """Note le dossier visé par le raccourci (`None` : pas de raccourci) ;
    la question du premier lancement est alors considérée comme posée."""
    ecriture_atomique(
        CHEMIN_PREFERENCE,
        {"question_posee": True, "dossier": str(dossier) if dossier else None},
    )


# --- État ---


def etat(racine: Path = CHEMIN_RACINE) -> EtatRaccourci:
    """État du raccourci pour l'installation située dans `racine`.

    Un raccourci présent sans dossier enregistré (données effacées) est
    considéré comme déplacé : le mettre à jour ne coûte rien.
    """
    systeme = systeme_courant()
    if systeme is None:
        return "indisponible"
    if not emplacement(systeme).exists():
        return "absent"
    dossier = _lire_preference().get("dossier")
    return "a_jour" if dossier == str(racine.resolve()) else "deplace"


def question_au_lancement(racine: Path = CHEMIN_RACINE) -> Question:
    """Question à poser au démarrage : proposer le raccourci une seule fois,
    puis la mise à jour à chaque lancement tant que le dossier a bougé."""
    etat_actuel = etat(racine)
    if etat_actuel == "deplace":
        return "deplace"
    if etat_actuel == "absent" and _lire_preference().get("question_posee") is not True:
        return "premier_lancement"
    return "aucune"


def refuser_premiere_question() -> None:
    """« Non » au premier lancement : ne plus proposer le raccourci."""
    _enregistrer(None)


# --- Création et retrait ---


def creer(racine: Path = CHEMIN_RACINE) -> None:
    """Crée (ou réécrit) le raccourci vers l'installation située dans `racine`.

    Raises:
        ErreurRaccourci: Système non pris en charge ou écriture impossible.
    """
    systeme = systeme_courant()
    if systeme is None:
        raise ErreurRaccourci("Raccourci indisponible sur ce système.")
    racine = racine.resolve()
    cible = emplacement(systeme)
    try:
        if systeme == "windows":
            _creer_lnk(cible, racine)
        elif systeme == "macos":
            _creer_app(cible, racine)
        else:
            _creer_desktop(cible, racine)
    except (OSError, subprocess.SubprocessError) as erreur:
        raise ErreurRaccourci("Impossible de créer le raccourci.") from erreur
    _enregistrer(racine)


def retirer() -> None:
    """Supprime le raccourci s'il existe.

    Raises:
        ErreurRaccourci: Suppression impossible.
    """
    systeme = systeme_courant()
    if systeme is not None:
        cible = emplacement(systeme)
        try:
            if cible.is_dir():
                shutil.rmtree(cible)
            else:
                cible.unlink(missing_ok=True)
        except OSError as erreur:
            raise ErreurRaccourci("Impossible de retirer le raccourci.") from erreur
    _enregistrer(None)


# --- Formats propres à chaque système ---


def _creer_lnk(cible: Path, racine: Path) -> None:
    """`.lnk` créé par PowerShell (objet COM `WScript.Shell`) ; les chemins
    passent par l'environnement pour ne jamais être interprétés."""
    script = (
        "$r = (New-Object -ComObject WScript.Shell).CreateShortcut($env:TAMPONNE_LNK);"
        "$r.TargetPath = $env:TAMPONNE_CIBLE;"
        "$r.WorkingDirectory = $env:TAMPONNE_DOSSIER;"
        "$r.IconLocation = $env:TAMPONNE_ICONE + ',0';"
        "$r.WindowStyle = 7;"
        "$r.Save()"
    )
    cible.parent.mkdir(parents=True, exist_ok=True)
    environnement = {
        **os.environ,
        "TAMPONNE_LNK": str(cible),
        "TAMPONNE_CIBLE": str(racine / "Tamponne.bat"),
        "TAMPONNE_DOSSIER": str(racine),
        "TAMPONNE_ICONE": str(racine / "src/gui/icones/tamponne.ico"),
    }
    # Entrée fermée et délai borné : PowerShell attendrait sinon la console
    # héritée ; sans fenêtre pour ne rien faire clignoter.
    drapeaux = 0
    if sys.platform == "win32":
        drapeaux = subprocess.CREATE_NO_WINDOW
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        env=environnement,
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        creationflags=drapeaux,
    )


def _creer_app(cible: Path, racine: Path) -> None:
    """Petite application qui lance `Tamponne.command` par bash : exécuter
    directement le script, mis en quarantaine au téléchargement, serait
    bloqué par Gatekeeper."""
    if cible.exists():
        shutil.rmtree(cible)
    contenu = cible / "Contents"
    (contenu / "MacOS").mkdir(parents=True)
    (contenu / "Resources").mkdir()
    shutil.copyfile(
        racine / "src/gui/icones/tamponne.icns", contenu / "Resources/tamponne.icns"
    )
    infos = {
        "CFBundleName": NOM,
        "CFBundleDisplayName": NOM,
        "CFBundleIdentifier": IDENTIFIANT_MACOS,
        "CFBundleExecutable": "tamponne",
        "CFBundleIconFile": "tamponne",
        "CFBundlePackageType": "APPL",
        "NSHighResolutionCapable": True,
    }
    with (contenu / "Info.plist").open("wb") as fichier:
        plistlib.dump(infos, fichier)
    executable = contenu / "MacOS/tamponne"
    commande = shlex.quote(str(racine / "Tamponne.command"))
    executable.write_text(f"#!/bin/bash\nexec /bin/bash {commande}\n", encoding="utf-8")
    executable.chmod(0o755)


def _echapper_desktop(valeur: str) -> str:
    """Échappement d'une valeur de type chaîne d'un fichier `.desktop`."""
    return valeur.replace("\\", "\\\\").replace("\n", "\\n")


def _argument_exec(valeur: str) -> str:
    """Argument entre guillemets de la clé `Exec` : échappement des
    guillemets, puis de la chaîne, et `%` doublé (codes de champ)."""
    for caractere in ("\\", '"', "`", "$"):
        valeur = valeur.replace(caractere, "\\" + caractere)
    return '"' + _echapper_desktop(valeur).replace("%", "%%") + '"'


def _creer_desktop(cible: Path, racine: Path) -> None:
    """Entrée `.desktop` du menu des applications (spécification freedesktop)."""
    lignes = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={NOM}",
        "Comment=Offres d'emploi de la fonction publique",
        f"Exec=/bin/bash {_argument_exec(str(racine / 'Tamponne.command'))}",
        f"Path={_echapper_desktop(str(racine))}",
        f"Icon={_echapper_desktop(str(racine / 'src/gui/icones/tamponne.png'))}",
        "Terminal=false",
        "Categories=Office;",
        "StartupWMClass=tamponne",
    ]
    cible.parent.mkdir(parents=True, exist_ok=True)
    ecriture = cible.with_name(cible.name + ".tmp")
    ecriture.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    ecriture.replace(cible)
