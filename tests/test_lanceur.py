"""Tests de src/lanceur.py : boucle de mise à jour, de retour arrière et de
redémarrage."""

import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from src import lanceur, maj
from src.lanceur import CODE_REDEMARRAGE, lancer

PYTHON = str(lanceur.python_environnement())
APPLICATION = [PYTHON, "-m", "src.gui.application"]
APPLIQUER = [PYTHON, "-m", "src.maj", "--appliquer"]
SYNC = ["/bin/uv", "sync", "--quiet"]
MAJ_UV = ["/bin/uv", "self", "update"]


def _role(commande: Sequence[str]) -> str:
    if commande[0] == "powershell":
        return "installeur"
    if commande[0] == "/bin/uv":
        return "sync" if commande[1] == "sync" else "self"
    return "maj" if commande[2] == "src.maj" else "app"


class Executeur:
    """Remplace `subprocess.run` : note les commandes, joue l'effet éventuel
    de la commande et renvoie le code prévu pour son rôle."""

    def __init__(
        self,
        codes: dict[str, list[int]],
        effets: dict[str, Callable[[], None]] | None = None,
    ) -> None:
        self.codes = codes
        self.effets = effets or {}
        self.commandes: list[list[str]] = []

    def __call__(self, commande: Sequence[str]) -> int:
        self.commandes.append(list(commande))
        role = _role(commande)
        if role in self.effets:
            self.effets[role]()
        return self.codes[role].pop(0)


def _installer_1_1() -> None:
    """Effet de `src.maj --appliquer` réussi : sauvegarde de la 1.0, puis 1.1."""
    maj.sauvegarder_version_actuelle()
    maj.CHEMIN_PYPROJECT.write_text('[project]\nversion = "1.1.0"\n', encoding="utf-8")
    maj.effacer_maj_disponible()


@pytest.fixture
def marqueur(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Installation 1.0 dans la racine de test (conftest), uv trouvé."""
    pyproject = maj.CHEMIN_RACINE / "pyproject.toml"
    pyproject.write_text('[project]\nversion = "1.0.0"\n', encoding="utf-8")
    monkeypatch.setattr(maj, "CHEMIN_PYPROJECT", pyproject)
    monkeypatch.setattr(lanceur.shutil, "which", lambda _nom: "/bin/uv")
    monkeypatch.setattr(
        lanceur, "CHEMIN_JOURNAL", maj.CHEMIN_RACINE / "journal_lancement.log"
    )
    return maj.CHEMIN_MARQUEUR


def test_lancer_sans_mise_a_jour_lance_l_interface_une_fois(marqueur: Path) -> None:
    executer = Executeur({"app": [0]})
    assert lancer(executer) == 0
    assert executer.commandes == [APPLICATION]


def test_lancer_redemarre_tant_que_l_interface_le_demande(marqueur: Path) -> None:
    executer = Executeur({"app": [CODE_REDEMARRAGE, CODE_REDEMARRAGE, 3]})
    assert lancer(executer) == 3
    assert executer.commandes == [APPLICATION] * 3


def test_lancer_mise_a_jour_appliquee_synchronisee_puis_validee(marqueur: Path) -> None:
    marqueur.write_text('{"version": "1.1.0"}', encoding="utf-8")
    executer = Executeur(
        {"maj": [0], "sync": [0], "app": [0]},
        {"maj": _installer_1_1, "app": maj.valider_maj},
    )
    assert lancer(executer) == 0
    assert executer.commandes == [APPLIQUER, SYNC, APPLICATION]
    assert maj.version_locale() == "1.1.0"


def test_lancer_mise_a_jour_indisponible_lance_la_version_actuelle(
    marqueur: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marqueur.write_text('{"version": "1.1.0"}', encoding="utf-8")
    executer = Executeur({"maj": [1], "app": [0]})
    assert lancer(executer) == 0
    assert executer.commandes == [APPLIQUER, APPLICATION]
    assert lanceur.MESSAGE_MAJ_INDISPONIBLE in capsys.readouterr().err


def test_lancer_synchronisation_en_echec_met_uv_a_jour_puis_reessaie(
    marqueur: Path,
) -> None:
    marqueur.write_text('{"version": "1.1.0"}', encoding="utf-8")
    executer = Executeur(
        {"maj": [0], "sync": [1, 0], "self": [0], "app": [0]},
        {"maj": _installer_1_1, "app": maj.valider_maj},
    )
    assert lancer(executer) == 0
    assert executer.commandes == [APPLIQUER, SYNC, MAJ_UV, SYNC, APPLICATION]
    assert maj.lire_echec() is None


def test_lancer_synchronisation_impossible_revient_a_la_version_precedente(
    marqueur: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marqueur.write_text('{"version": "1.1.0"}', encoding="utf-8")
    executer = Executeur(
        {"maj": [0], "sync": [1, 1, 0], "self": [0], "app": [0]},
        {"maj": _installer_1_1, "app": maj.valider_maj},
    )
    assert lancer(executer) == 0
    assert executer.commandes == [APPLIQUER, SYNC, MAJ_UV, SYNC, SYNC, APPLICATION]
    assert maj.version_locale() == "1.0.0"
    assert not maj.dossier_precedente().exists()
    assert maj.lire_echec() == {
        "version": "1.1.0",
        "motif": lanceur.MOTIF_SYNCHRONISATION,
        "date": maj.lire_echec()["date"],  # type: ignore[index]
    }
    assert "Tamponné redémarre dans sa version précédente (1.0.0)" in capsys.readouterr().err


def test_lancer_version_precedente_non_synchronisable_demande_de_relancer(
    marqueur: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marqueur.write_text('{"version": "1.1.0"}', encoding="utf-8")
    executer = Executeur(
        {"maj": [0], "sync": [1, 1, 1, 1], "self": [1, 1]}, {"maj": _installer_1_1}
    )
    assert lancer(executer) == lanceur.CODE_MAJ_INACHEVEE
    assert APPLICATION not in executer.commandes
    assert maj.version_locale() == "1.0.0"
    assert lanceur.MESSAGE_RELANCER in capsys.readouterr().err


def test_lancer_interface_arretee_avant_validation_revient_en_arriere(
    marqueur: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marqueur.write_text('{"version": "1.1.0"}', encoding="utf-8")
    executer = Executeur(
        {"maj": [0], "sync": [0, 0], "app": [1, 0]},
        {"maj": _installer_1_1},
    )
    assert lancer(executer) == 0
    assert executer.commandes == [APPLIQUER, SYNC, APPLICATION, SYNC, APPLICATION]
    assert maj.version_locale() == "1.0.0"
    echec = maj.lire_echec()
    assert echec is not None and echec["motif"] == lanceur.MOTIF_DEMARRAGE
    assert "Tamponné redémarre dans sa version précédente (1.0.0)" in capsys.readouterr().err


def test_lancer_installation_interrompue_restaure_la_sauvegarde(
    marqueur: Path,
) -> None:
    """`src.maj` arrêté en pleine installation, sauvegarde déjà faite et
    pyproject.toml illisible : version annulée lue dans le marqueur."""
    marqueur.write_text('{"version": "1.1.0"}', encoding="utf-8")

    def installation_interrompue() -> None:
        maj.sauvegarder_version_actuelle()
        maj.CHEMIN_PYPROJECT.write_text("cassé", encoding="utf-8")

    executer = Executeur(
        {"maj": [1], "sync": [0], "app": [0]}, {"maj": installation_interrompue}
    )
    assert lancer(executer) == 0
    assert executer.commandes == [APPLIQUER, SYNC, APPLICATION]
    assert maj.version_locale() == "1.0.0"
    assert maj.maj_en_echec("1.1.0")


def test_mettre_a_jour_uv_sous_windows_relance_l_installeur_en_secours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lanceur.sys, "platform", "win32")
    executer = Executeur({"self": [1], "installeur": [0]})
    assert lanceur._mettre_a_jour_uv(executer, "/bin/uv")
    assert executer.commandes == [MAJ_UV, list(lanceur.INSTALLEUR_UV_WINDOWS)]


def test_mettre_a_jour_uv_hors_windows_sans_installeur(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lanceur.sys, "platform", "darwin")
    executer = Executeur({"self": [1]})
    assert not lanceur._mettre_a_jour_uv(executer, "/bin/uv")
    assert executer.commandes == [MAJ_UV]


def test_python_de_base_hors_de_l_environnement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lanceur.sys, "base_prefix", "/base")
    assert lanceur.python_de_base() == Path("/base") / "python.exe"
    assert ".venv" not in lanceur.python_de_base().parts


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


def test_message_maj_annulee_nomme_versions_motif_et_marche_a_suivre() -> None:
    message = lanceur.message_maj_annulee("1.3.0", lanceur.MOTIF_DEMARRAGE, "1.2.3")
    assert message.startswith(
        "La mise à jour 1.3.0 de Tamponné n'a pas pu être installée\u00a0: "
        "la nouvelle version ne démarrait pas."
    )
    assert "version précédente (1.2.3)" in message
    assert "«\u00a0Installer et redémarrer\u00a0»" in message


def test_messages_d_echec_designent_le_journal() -> None:
    for message in (lanceur.MESSAGE_RELANCER, lanceur.MESSAGE_ERREUR):
        assert lanceur.JOURNAL_AFFICHE in message


def test_avec_detail_donne_la_premiere_erreur_du_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """La cause (uv trop ancien), pas l'échec de sa mise à jour qui suit."""
    journal = tmp_path / "journal_lancement.log"
    journal.write_text(
        "$ uv sync --quiet\n"
        "error: Required uv version `>=0.13.0` does not match the running version\n"
        "$ uv self update\n"
        "error: uv was installed through an external package manager\n"
        "hint: run `brew upgrade uv`\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", journal)
    assert lanceur.avec_detail("Message.") == (
        "Message.\n\nDétail\u00a0: error: Required uv version `>=0.13.0` does "
        "not match the running version"
    )


def test_avec_detail_donne_l_exception_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = tmp_path / "journal_lancement.log"
    journal.write_text(
        "Traceback (most recent call last):\n"
        '  File "src/gui/application.py", line 3, in <module>\n'
        "ModuleNotFoundError: No module named 'PySide6'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", journal)
    assert lanceur.premiere_erreur() == "ModuleNotFoundError: No module named 'PySide6'"


def test_avec_detail_sans_journal_garde_le_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", tmp_path / "absent.log")
    assert lanceur.avec_detail("Message.") == "Message."
