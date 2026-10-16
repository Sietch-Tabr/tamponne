"""Garde-fous des scripts de lancement `Tamponne.command` et `Tamponne.bat`."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

RACINE = Path(__file__).parent.parent


def test_tamponne_command_executable_et_lu_d_un_bloc() -> None:
    """Le bloc `{ … exit 0 }` est lu en entier avant exécution : une mise à
    jour qui réécrit le script pendant qu'il tourne ne change rien."""
    chemin = RACINE / "Tamponne.command"
    assert os.access(chemin, os.X_OK)
    lignes = chemin.read_text(encoding="utf-8").splitlines()
    assert lignes[0] == "#!/bin/bash"
    assert "{" in lignes and lignes[-2:] == ["exit 0", "}"]
    assert "uv run python -m src.lanceur \\" in lignes


def test_tamponne_command_se_relance_dans_un_terminal_sous_linux() -> None:
    """Double-cliqué sous KDE ou GNOME, le script n'a pas de terminal :
    il s'y relance pour montrer l'installation, une seule fois."""
    contenu = (RACINE / "Tamponne.command").read_text(encoding="utf-8")
    assert 'TAMPONNE_TERMINAL=1 exec "$terminal" "$option" /bin/bash' in contenu
    assert '[ -z "${TAMPONNE_TERMINAL:-}" ]' in contenu


def test_tamponne_bat_lu_d_un_bloc() -> None:
    """cmd relit un `.bat` ligne par ligne, sauf un bloc entre parenthèses,
    analysé en entier : tout le script y tient, sans `goto` ni `%ERRORLEVEL%`
    (développé à l'analyse du bloc)."""
    contenu = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    assert "\r\n" in contenu and "\n" not in contenu.replace("\r\n", "")
    lignes = contenu.splitlines()
    debut = lignes.index("(")
    assert lignes[-1] == ")"
    bloc = "\n".join(lignes[debut:])
    assert "goto" not in bloc.lower() and "%ERRORLEVEL%" not in bloc.upper()
    assert ".venv\\Scripts\\python.exe -m src.lanceur" in bloc


def test_tamponne_bat_transmet_le_proxy_de_windows_a_uv() -> None:
    """uv ne lit pas le proxy de Windows : le lanceur le lui passe par
    `HTTPS_PROXY` avant `uv sync`, sans écraser une valeur déjà définie."""
    contenu = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    lignes = contenu.splitlines()
    detection = next(
        i for i, ligne in enumerate(lignes) if "GetSystemWebProxy()" in ligne
    )
    assert lignes[detection].startswith("if not defined HTTPS_PROXY for /f ")
    assert lignes[detection + 1 : detection + 3] == [
        '    set "HTTPS_PROXY=%%P"',
        '    set "HTTP_PROXY=%%P"',
    ]
    assert detection > lignes.index("(")
    assert detection < next(i for i, ligne in enumerate(lignes) if "uv sync" in ligne)


def test_lanceurs_sans_outils_de_developpement_hors_clone_git() -> None:
    """Une installation n'a pas besoin de mypy ni de pytest : `UV_NO_DEV`,
    posé avant le premier `uv`, vaut aussi pour `src.lanceur`."""
    commande = (RACINE / "Tamponne.command").read_text(encoding="utf-8")
    bat = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    for contenu, garde in (
        (commande, "[ -e .git ] || export UV_NO_DEV=1"),
        (bat, 'if not exist .git set "UV_NO_DEV=1"'),
    ):
        lignes = contenu.splitlines()
        assert garde in lignes
        assert lignes.index(garde) < next(
            i for i, ligne in enumerate(lignes) if ligne.strip().startswith("uv sync")
        )


def test_lanceurs_demandent_de_patienter_au_premier_lancement() -> None:
    """La première ouverture est longue (Qt chargé pour la première fois) :
    la console le dit, et celle de Windows reste ouverte le temps de lire."""
    message = "Installation terminée. Tamponné s'ouvre dans quelques instants"
    commande = (RACINE / "Tamponne.command").read_text(encoding="utf-8")
    assert message in commande
    assert commande.index(message) < commande.index("uv run python")
    bat = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    lignes = bat.splitlines()
    lancement = lignes.index(".venv\\Scripts\\python.exe -m src.lanceur")
    assert lignes[lancement + 1] == "if defined TAMPONNE_PREMIER_LANCEMENT ("
    assert message in lignes[lancement + 2]
    assert lignes.index("setlocal") < lignes.index('set "TAMPONNE_PREMIER_LANCEMENT="')


def test_lanceurs_mettent_uv_a_jour_avant_d_abandonner() -> None:
    """Un uv trop ancien ne connaît pas le Python demandé (`required-version`) :
    les scripts le mettent à jour et resynchronisent avant le message
    d'échec ; sous Windows, l'installeur sert de secours derrière le proxy."""
    commande = (RACINE / "Tamponne.command").read_text(encoding="utf-8")
    assert commande.index("uv self update") < commande.index(
        "même après la mise à jour de uv"
    )
    bat = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    lignes = bat.splitlines()
    mise_a_jour = next(i for i, ligne in enumerate(lignes) if "uv self update" in ligne)
    assert "irm https://astral.sh/uv/install.ps1 | iex" in lignes[mise_a_jour]
    assert lignes[mise_a_jour + 1].strip() == "uv sync"
    assert mise_a_jour < next(
        i
        for i, ligne in enumerate(lignes)
        if "même après la mise à jour de uv" in ligne
    )
    assert mise_a_jour > next(
        i for i, ligne in enumerate(lignes) if "GetSystemWebProxy()" in ligne
    )


def test_lanceurs_montrent_la_progression_de_uv() -> None:
    """Le téléchargement de Python et des composants prend du temps :
    l'utilisateur voit ce qui se passe, jamais un terminal vide."""
    commande = (RACINE / "Tamponne.command").read_text(encoding="utf-8")
    bat = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    for contenu in (commande, bat):
        assert "--quiet" not in contenu and " -q " not in contenu


def test_tamponne_bat_n_affiche_jamais_les_identifiants_du_proxy() -> None:
    """`HTTPS_PROXY` peut contenir `utilisateur:mot de passe@` : le message
    d'erreur, souvent capturé pour un signalement, n'en montre que l'hôte."""
    bat = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    messages = [ligne for ligne in bat.splitlines() if "Proxy utilisé" in ligne]
    assert len(messages) == 2
    for ligne in messages:
        assert "{ $env:HTTPS_PROXY }" not in ligne
        assert "$p.Host + ':' + $p.Port" in ligne


# --- un seul lancement à la fois (macOS et Linux) ---


def _installation_factice(tmp_path: Path, duree: int) -> tuple[Path, dict[str, str]]:
    """Copie du script dans un dossier d'essai, avec un faux `uv` (la
    synchronisation réussit, le lanceur dure `duree` secondes)."""
    dossier = tmp_path / "installation"
    dossier.mkdir()
    script = dossier / "Tamponne.command"
    shutil.copy(RACINE / "Tamponne.command", script)
    script.chmod(0o755)
    maison = tmp_path / "maison"
    (maison / ".local" / "bin").mkdir(parents=True)
    faux_uv = maison / ".local" / "bin" / "uv"
    faux_uv.write_text(
        f'#!/bin/bash\n[ "$1" = run ] && {{ echo lanceur-demarre; sleep {duree}; }}\nexit 0\n',
        encoding="utf-8",
    )
    faux_uv.chmod(0o755)
    environnement = {**os.environ, "HOME": str(maison), "NO_COLOR": "1"}
    environnement.pop("TAMPONNE_TERMINAL", None)
    return script, environnement


@pytest.mark.skipif(sys.platform == "win32", reason="script bash")
def test_tamponne_command_refuse_un_second_lancement(tmp_path: Path) -> None:
    script, env = _installation_factice(tmp_path, duree=4)
    premier = subprocess.Popen(
        ["/bin/bash", str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    verrou = script.parent / "data" / ".lancement.verrou"
    for _ in range(50):
        if (verrou / "pid").exists():
            break
        time.sleep(0.1)
    assert (verrou / "pid").read_text().strip() == str(premier.pid)

    second = subprocess.run(
        ["/bin/bash", str(script)],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )
    assert second.returncode == 0
    assert "déjà ouvert" in second.stderr
    assert "lanceur-demarre" not in second.stdout
    sortie, _ = premier.communicate(timeout=30)
    assert "lanceur-demarre" in sortie
    assert not verrou.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="script bash")
def test_tamponne_command_reprend_le_verrou_d_un_lancement_interrompu(
    tmp_path: Path,
) -> None:
    script, env = _installation_factice(tmp_path, duree=0)
    verrou = script.parent / "data" / ".lancement.verrou"
    verrou.mkdir(parents=True)
    (verrou / "pid").write_text("999999\n", encoding="utf-8")
    resultat = subprocess.run(
        ["/bin/bash", str(script)],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        stdin=subprocess.DEVNULL,
    )
    assert resultat.returncode == 0
    assert "lanceur-demarre" in resultat.stdout
    assert not verrou.exists()


def test_tamponne_command_met_les_messages_en_valeur() -> None:
    """Les messages explicatifs passent par `annoncer`, jamais par un
    simple `echo` noyé dans les sorties de uv."""
    contenu = (RACINE / "Tamponne.command").read_text(encoding="utf-8")
    for debut in (
        "Installation de uv",
        "Premier lancement",
        "Mise à jour de uv",
        "Installation terminée",
    ):
        lignes = [ligne for ligne in contenu.splitlines() if debut in ligne]
        assert any("annoncer" in ligne for ligne in lignes), debut
        assert not any("echo" in ligne for ligne in lignes), debut


def test_tamponne_bat_n_ouvre_qu_une_console_a_la_fois() -> None:
    """La console garde `data\\.lancement.verrou` ouvert en écriture : un
    second double-clic ne peut pas l'ouvrir et prévient au lieu de relancer
    l'installation. Le verrou entoure tout, avant l'installation de uv."""
    bat = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    lignes = bat.splitlines()
    verrou = lignes.index('9>"data\\.lancement.verrou" (')
    assert lignes[verrou - 1] == "2>nul ("
    assert verrou < next(i for i, ligne in enumerate(lignes) if "uv sync" in ligne)
    assert verrou < next(i for i, ligne in enumerate(lignes) if "install.ps1" in ligne)
    assert ") || (" in lignes
    refus = lignes.index(") || (")
    assert "déjà ouvert" in lignes[refus + 1]
    assert lignes[-2:] == ["exit /b", ")"]


def test_tamponne_bat_met_les_messages_en_valeur() -> None:
    """Les messages explicatifs passent par un bandeau PowerShell bleu,
    jamais par un simple `echo` noyé dans les sorties de uv."""
    bat = (RACINE / "Tamponne.bat").read_bytes().decode("utf-8")
    lignes = bat.splitlines()
    for debut in (
        "Installation de uv",
        "Premier lancement",
        "Mise à jour de uv",
        "Installation terminée",
        "Tamponné est déjà ouvert",
    ):
        concernees = [
            ligne for ligne in lignes if debut in ligne and not ligne.startswith("rem ")
        ]
        assert concernees, debut
        for ligne in concernees:
            assert "TAMPONNE_ANNONCE" in ligne and "BackgroundColor" in ligne, debut
            assert "echo" not in ligne.split("powershell")[0], debut
