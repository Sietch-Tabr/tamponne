"""Tests de src/raccourci.py : création, déplacement et retrait du raccourci
pour chaque système (profil utilisateur redirigé par `conftest.py`)."""

import os
import plistlib
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from src import raccourci
from src.raccourci import ErreurRaccourci, Systeme


@pytest.fixture
def racine(tmp_path: Path) -> Path:
    """Installation factice, avec l'icône copiée dans le bundle macOS."""
    dossier = tmp_path / "Mes logiciels" / "tamponne"
    (dossier / "src/gui/icones").mkdir(parents=True)
    (dossier / "src/gui/icones/tamponne.icns").write_bytes(b"icns")
    return dossier


def _sur(monkeypatch: pytest.MonkeyPatch, systeme: Systeme | None) -> None:
    monkeypatch.setattr(raccourci, "systeme_courant", lambda: systeme)


def test_systeme_non_pris_en_charge(
    monkeypatch: pytest.MonkeyPatch, racine: Path
) -> None:
    _sur(monkeypatch, None)
    assert raccourci.etat(racine) == "indisponible"
    assert raccourci.question_au_lancement(racine) == "aucune"
    with pytest.raises(ErreurRaccourci):
        raccourci.creer(racine)


def test_premier_lancement_question_posee_une_seule_fois(
    monkeypatch: pytest.MonkeyPatch, racine: Path
) -> None:
    _sur(monkeypatch, "linux")
    assert raccourci.question_au_lancement(racine) == "premier_lancement"
    raccourci.refuser_premiere_question()
    assert raccourci.question_au_lancement(racine) == "aucune"
    assert raccourci.etat(racine) == "absent"


def test_linux_desktop_cree_puis_deplace_puis_retire(
    monkeypatch: pytest.MonkeyPatch, racine: Path, tmp_path: Path
) -> None:
    _sur(monkeypatch, "linux")
    raccourci.creer(racine)

    fichier = Path(os.environ["XDG_DATA_HOME"]) / "applications/tamponne.desktop"
    lignes = fichier.read_text(encoding="utf-8").splitlines()
    assert lignes[0] == "[Desktop Entry]"
    assert f'Exec=/bin/bash "{racine}/Tamponne.command"' in lignes
    assert f"Icon={racine}/src/gui/icones/tamponne.png" in lignes
    assert "Terminal=false" in lignes
    assert raccourci.etat(racine) == "a_jour"
    assert raccourci.question_au_lancement(racine) == "aucune"

    deplacee = racine.rename(tmp_path / "ailleurs")
    assert raccourci.etat(deplacee) == "deplace"
    assert raccourci.question_au_lancement(deplacee) == "deplace"
    raccourci.creer(deplacee)
    assert raccourci.etat(deplacee) == "a_jour"

    raccourci.retirer()
    assert not fichier.exists()
    assert raccourci.etat(deplacee) == "absent"
    assert raccourci.question_au_lancement(deplacee) == "aucune"


def test_linux_exec_echappe_guillemets_dollar_et_pourcent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _sur(monkeypatch, "linux")
    racine = tmp_path / 'a"b$c%d'
    racine.mkdir()
    raccourci.creer(racine)
    contenu = (
        Path(os.environ["XDG_DATA_HOME"]) / "applications/tamponne.desktop"
    ).read_text(encoding="utf-8")
    # Guillemet et dollar échappés par une barre, elle-même doublée (chaîne).
    assert '\\\\"b\\\\$c%%d/Tamponne.command"' in contenu


def test_macos_application_creee(monkeypatch: pytest.MonkeyPatch, racine: Path) -> None:
    _sur(monkeypatch, "macos")
    raccourci.creer(racine)

    app = Path(os.environ["HOME"]) / "Applications/Tamponné.app/Contents"
    with (app / "Info.plist").open("rb") as fichier:
        infos = plistlib.load(fichier)
    assert infos["CFBundleExecutable"] == "tamponne"
    assert infos["CFBundleIconFile"] == "tamponne"
    executable = app / "MacOS/tamponne"
    assert os.access(executable, os.X_OK)
    assert executable.read_text(encoding="utf-8") == (
        f"#!/bin/bash\nexec /bin/bash '{racine}/Tamponne.command'\n"
    )
    assert (app / "Resources/tamponne.icns").read_bytes() == b"icns"

    raccourci.retirer()
    assert not app.parent.exists()


def test_windows_lnk_par_powershell_chemins_dans_l_environnement(
    monkeypatch: pytest.MonkeyPatch, racine: Path
) -> None:
    _sur(monkeypatch, "windows")
    appels: list[tuple[Sequence[str], dict[str, str]]] = []

    def faux_run(commande: Sequence[str], **options: Any) -> None:
        appels.append((commande, options["env"]))
        Path(options["env"]["TAMPONNE_LNK"]).write_bytes(b"lnk")

    monkeypatch.setattr(raccourci.subprocess, "run", faux_run)
    raccourci.creer(racine)

    commande, environnement = appels[0]
    assert commande[0] == "powershell"
    assert str(racine) not in commande[-1]
    assert environnement["TAMPONNE_CIBLE"] == str(racine / "Tamponne.bat")
    lnk = Path(os.environ["APPDATA"]) / (
        "Microsoft/Windows/Start Menu/Programs/Tamponné.lnk"
    )
    assert environnement["TAMPONNE_LNK"] == str(lnk)
    assert raccourci.etat(racine) == "a_jour"


def test_echec_de_creation_message_en_francais(
    monkeypatch: pytest.MonkeyPatch, racine: Path
) -> None:
    _sur(monkeypatch, "windows")

    def echec(commande: Sequence[str], **_options: Any) -> None:
        raise subprocess.CalledProcessError(1, commande)

    monkeypatch.setattr(raccourci.subprocess, "run", echec)
    with pytest.raises(ErreurRaccourci, match="Impossible de créer le raccourci"):
        raccourci.creer(racine)
    assert raccourci.etat(racine) == "absent"


def test_raccourci_present_sans_preference_considere_deplace(
    monkeypatch: pytest.MonkeyPatch, racine: Path
) -> None:
    _sur(monkeypatch, "linux")
    raccourci.creer(racine)
    raccourci.CHEMIN_PREFERENCE.unlink()
    assert raccourci.etat(racine) == "deplace"
