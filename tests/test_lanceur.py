"""Tests de src/lanceur.py : boucle de mise à jour et de redémarrage."""

import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from src import lanceur
from src.lanceur import CODE_REDEMARRAGE, lancer

APPLICATION = [sys.executable, "-m", "src.gui.application"]
APPLIQUER = [sys.executable, "-m", "src.maj", "--appliquer"]


class Executeur:
    """Remplace `subprocess.run` : note les commandes, renvoie les codes prévus."""

    def __init__(self, codes: dict[str, list[int]]) -> None:
        self.codes = codes
        self.commandes: list[list[str]] = []

    def __call__(self, commande: Sequence[str]) -> int:
        self.commandes.append(list(commande))
        cle = "uv" if commande[1] == "sync" else commande[2]
        return self.codes[cle].pop(0)


@pytest.fixture
def marqueur(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    chemin = tmp_path / "maj_disponible.json"
    monkeypatch.setattr(lanceur, "CHEMIN_MARQUEUR", chemin)
    monkeypatch.setattr(lanceur.shutil, "which", lambda _nom: "/bin/uv")
    return chemin


def test_sans_mise_a_jour_lance_l_interface_une_fois(marqueur: Path) -> None:
    executer = Executeur({"src.gui.application": [0]})
    assert lancer(executer) == 0
    assert executer.commandes == [APPLICATION]


def test_redemarre_tant_que_l_interface_le_demande(marqueur: Path) -> None:
    executer = Executeur({"src.gui.application": [CODE_REDEMARRAGE, CODE_REDEMARRAGE, 3]})
    assert lancer(executer) == 3
    assert executer.commandes == [APPLICATION] * 3


def test_mise_a_jour_en_attente_appliquee_puis_synchronisee(marqueur: Path) -> None:
    marqueur.write_text("{}", encoding="utf-8")
    executer = Executeur({"src.maj": [0], "uv": [0], "src.gui.application": [0]})
    assert lancer(executer) == 0
    assert executer.commandes == [APPLIQUER, ["/bin/uv", "sync", "--quiet"], APPLICATION]


def test_mise_a_jour_en_echec_lance_la_version_actuelle(
    marqueur: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marqueur.write_text("{}", encoding="utf-8")
    executer = Executeur({"src.maj": [1], "src.gui.application": [0]})
    assert lancer(executer) == 0
    assert executer.commandes == [APPLIQUER, APPLICATION]
    assert lanceur.MESSAGE_MAJ_INDISPONIBLE in capsys.readouterr().err


def test_synchronisation_en_echec_demande_de_relancer(
    marqueur: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marqueur.write_text("{}", encoding="utf-8")
    executer = Executeur({"src.maj": [0], "uv": [1]})
    assert lancer(executer) == 1
    assert APPLICATION not in executer.commandes
    assert lanceur.MESSAGE_RELANCER in capsys.readouterr().err


def test_retirer_marque_du_web_debloque_l_installation_hors_venv_et_donnees(
    tmp_path: Path,
) -> None:
    """Sur NTFS, `fichier:Zone.Identifier` est un flux ; ici un fichier au
    même nom, supprimé de la même façon."""
    marque = lanceur.FLUX_MARQUE_DU_WEB
    for relatif in ("Tamponne.bat", "src/lanceur.py", ".venv/x.py", "data/p.json"):
        chemin = tmp_path / relatif
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text("", encoding="utf-8")
        Path(str(chemin) + marque).write_text("[ZoneTransfer]", encoding="utf-8")

    assert lanceur.retirer_marque_du_web(tmp_path) == 2
    assert not Path(str(tmp_path / "Tamponne.bat") + marque).exists()
    assert not Path(str(tmp_path / "src/lanceur.py") + marque).exists()
    assert Path(str(tmp_path / ".venv/x.py") + marque).exists()
    assert lanceur.retirer_marque_du_web(tmp_path) == 0
