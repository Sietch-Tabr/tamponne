"""Tests de src/lanceur.py : boucle de mise à jour, de retour arrière et de
redémarrage."""

import io
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from src import lanceur, maj
from src.lanceur import CODE_REDEMARRAGE, lancer

PYTHON = str(lanceur.python_environnement())
APPLICATION = [PYTHON, "-m", "src.gui.application"]
APPLIQUER = [PYTHON, "-m", "src.maj", "--appliquer"]
SYNC = ["/bin/uv", "sync"]
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
    return maj.CHEMIN_MARQUEUR


@pytest.mark.usefixtures("marqueur")
def test_lancer_sans_mise_a_jour_lance_l_interface_une_fois() -> None:
    executer = Executeur({"app": [0]})
    assert lancer(executer) == 0
    assert executer.commandes == [APPLICATION]


@pytest.mark.usefixtures("marqueur")
def test_lancer_redemarre_tant_que_l_interface_le_demande() -> None:
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


def test_lancer_mise_a_jour_non_telechargee_le_dit_et_lance_la_version_actuelle(
    marqueur: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marqueur.write_text('{"version": "1.1.0"}', encoding="utf-8")
    executer = Executeur({"maj": [1], "app": [0]})
    assert lancer(executer) == 0
    assert executer.commandes == [APPLIQUER, APPLICATION]
    assert "La mise à jour 1.1.0 de Tamponné n'a pas pu être téléchargée" in (
        capsys.readouterr().err
    )
    echec = maj.lire_echec()
    assert echec is not None and echec["motif"] == lanceur.MOTIF_TELECHARGEMENT
    assert not marqueur.exists()


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
    assert (
        "Tamponné redémarre dans sa version précédente (1.0.0)"
        in capsys.readouterr().err
    )


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
    assert (
        "Tamponné redémarre dans sa version précédente (1.0.0)"
        in capsys.readouterr().err
    )


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
    echec = maj.lire_echec()
    assert echec is not None and echec["motif"] == lanceur.MOTIF_INSTALLATION


def test_lancer_installation_interrompue_efface_le_marqueur(marqueur: Path) -> None:
    """Un marqueur resté après l'échec ferait rejouer la même mise à jour à
    chaque démarrage, malgré l'échec mémorisé."""
    marqueur.write_text('{"version": "1.1.0"}', encoding="utf-8")

    def installation_interrompue() -> None:
        maj.sauvegarder_version_actuelle()
        maj.CHEMIN_PYPROJECT.write_text("cassé", encoding="utf-8")

    executer = Executeur(
        {"maj": [1], "sync": [0], "app": [0]}, {"maj": installation_interrompue}
    )
    assert lancer(executer) == 0
    assert not marqueur.exists()


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


def test_python_de_base_hors_de_l_environnement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    journal = tmp_path / "tamponne.log"
    journal.write_text(
        "$ uv sync\n"
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
    journal = tmp_path / "tamponne.log"
    journal.write_text(
        "Traceback (most recent call last):\n"
        '  File "src/gui/application.py", line 3, in <module>\n'
        "ModuleNotFoundError: No module named 'PySide6'\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", journal)
    assert lanceur.premiere_erreur() == "ModuleNotFoundError: No module named 'PySide6'"


def test_premiere_erreur_ignore_les_lancements_precedents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = tmp_path / "tamponne.log"
    journal.write_text(
        "===== 2026-10-13 09:00:00 · Tamponné 1.3.3 · Darwin 25 · Python 3.14.0 =====\n"
        "ModuleNotFoundError: No module named 'PySide6'\n"
        "===== 2026-10-14 09:00:00 · Tamponné 1.3.4 · Darwin 25 · Python 3.14.0 =====\n"
        "$ uv sync\n"
        "error: Failed to fetch\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", journal)
    assert lanceur.premiere_erreur() == "error: Failed to fetch"


def test_ouvrir_journal_garde_l_historique_sous_un_en_tete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(maj, "version_locale", lambda: "9.9.9")
    lanceur.CHEMIN_JOURNAL.write_text("lancement d'hier\n", encoding="utf-8")
    lanceur.ouvrir_journal()
    lignes = lanceur.CHEMIN_JOURNAL.read_text(encoding="utf-8").splitlines()
    assert lignes[0] == "lancement d'hier"
    assert lignes[1].startswith(lanceur.DEBUT_EN_TETE)
    assert "· Tamponné 9.9.9 · " in lignes[1]
    assert lignes[1].endswith(" =====")


def test_ouvrir_journal_retire_l_ancien_journal() -> None:
    ancien = lanceur.CHEMIN_JOURNAL.parent / lanceur.NOM_ANCIEN_JOURNAL
    ancien.write_text("ancien format\n", encoding="utf-8")
    lanceur.ouvrir_journal()
    assert not ancien.exists()


def test_ouvrir_journal_archive_au_dela_de_la_taille_maximale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lanceur, "TAILLE_MAX_JOURNAL", 10)
    lanceur.CHEMIN_JOURNAL_ARCHIVE.write_text("très ancien\n", encoding="utf-8")
    lanceur.CHEMIN_JOURNAL.write_text("ancien journal trop long\n", encoding="utf-8")
    lanceur.ouvrir_journal()
    assert lanceur.CHEMIN_JOURNAL_ARCHIVE.read_text(encoding="utf-8") == (
        "ancien journal trop long\n"
    )
    assert lanceur.CHEMIN_JOURNAL.read_text(encoding="utf-8").startswith(
        lanceur.DEBUT_EN_TETE
    )


def test_signaler_note_le_message_dans_le_journal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lanceur.sys, "platform", "linux")
    lanceur.signaler("Mise à jour annulée.")
    contenu = lanceur.CHEMIN_JOURNAL.read_text(encoding="utf-8")
    assert re.search(
        r"^\d\d:\d\d:\d\d ERREUR lanceur\u00a0: Mise à jour annulée\.$", contenu, re.M
    )


def test_avec_detail_sans_journal_garde_le_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", tmp_path / "absent.log")
    assert lanceur.avec_detail("Message.") == "Message."


def test_executer_affiche_et_journalise_les_sorties(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    journal = tmp_path / "tamponne.log"
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", journal)
    monkeypatch.setattr(lanceur, "_sortie", sys.stdout)
    code = lanceur._executer(
        [sys.executable, "-c", "import sys; print('Téléchargement…'); sys.exit(3)"]
    )
    assert code == 3
    assert "Téléchargement…" in capsys.readouterr().out
    assert "Téléchargement…" in journal.read_text(encoding="utf-8")


@pytest.mark.usefixtures("marqueur")
def test_synchroniser_annonce_le_telechargement(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lanceur, "_sortie", sys.stdout)
    assert lanceur.synchroniser(Executeur({"sync": [0]}))
    assert lanceur.TITRE_SYNCHRONISATION in capsys.readouterr().out


def test_lanceur_sans_option_silencieuse() -> None:
    source = Path(lanceur.__file__).read_text(encoding="utf-8")
    assert '"--quiet"' not in source


def test_executer_anonymise_le_dossier_personnel_dans_le_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = tmp_path / "tamponne.log"
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", journal)
    monkeypatch.setattr(lanceur, "_sortie", None)
    personnel = str(Path.home())
    lanceur._executer([sys.executable, "-c", f"print({personnel!r} + '/data')"])
    contenu = journal.read_text(encoding="utf-8")
    assert personnel not in contenu
    assert "~/data" in contenu


@pytest.mark.skipif(sys.platform == "win32", reason="SIGINT POSIX")
def test_executer_survit_a_ctrl_c_pendant_l_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", tmp_path / "tamponne.log")
    monkeypatch.setattr(lanceur, "_sortie", None)
    # L'enfant envoie SIGINT à son parent (le lanceur), comme le ferait le terminal.
    script = "import os, signal; os.kill(os.getppid(), signal.SIGINT)"
    assert lanceur._executer([sys.executable, "-c", script]) == 0


# --- messages mis en valeur ---


def test_mettre_en_valeur_en_couleurs_encadre_le_message() -> None:
    texte = lanceur.mettre_en_valeur("Installation de uv", couleurs=True)
    lignes = texte.strip("\n").splitlines()
    assert len(lignes) == 3
    assert all(ligne.startswith(lanceur.ATTRIBUTS_ANNONCE) for ligne in lignes)
    assert all(ligne.endswith(lanceur.FIN_ATTRIBUTS) for ligne in lignes)
    assert "Installation de uv" in lignes[1]
    assert "Installation de uv" not in lignes[0] + lignes[2]


def test_mettre_en_valeur_sans_couleurs_garde_un_repere_visible() -> None:
    assert lanceur.mettre_en_valeur("Installation de uv", couleurs=False) == (
        "\n>>> Installation de uv\n\n"
    )


class _Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_annoncer_colore_sur_un_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    sortie = _Terminal()
    monkeypatch.setattr(lanceur, "_sortie", sortie)
    monkeypatch.delenv("NO_COLOR", raising=False)
    lanceur.annoncer("Mise à jour de uv")
    assert lanceur.ATTRIBUTS_ANNONCE in sortie.getvalue()
    assert "Mise à jour de uv" in sortie.getvalue()


def test_annoncer_respecte_no_color_et_les_sorties_redirigees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    terminal = _Terminal()
    monkeypatch.setattr(lanceur, "_sortie", terminal)
    monkeypatch.setenv("NO_COLOR", "1")
    lanceur.annoncer("Message")
    assert lanceur.ATTRIBUTS_ANNONCE not in terminal.getvalue()
    assert ">>> Message" in terminal.getvalue()

    fichier = io.StringIO()
    monkeypatch.delenv("NO_COLOR")
    monkeypatch.setattr(lanceur, "_sortie", fichier)
    lanceur.annoncer("Message")
    assert lanceur.ATTRIBUTS_ANNONCE not in fichier.getvalue()


@pytest.mark.usefixtures("marqueur")
def test_synchroniser_annonce_la_mise_a_jour_de_uv_en_valeur(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sortie = _Terminal()
    monkeypatch.setattr(lanceur, "_sortie", sortie)
    monkeypatch.delenv("NO_COLOR", raising=False)
    executeur = Executeur({"sync": [1, 0], "self": [0]})
    assert lanceur.synchroniser(executeur)
    assert lanceur.ATTRIBUTS_ANNONCE + "  " + lanceur.TITRE_MAJ_UV in sortie.getvalue()


# --- un seul lanceur à la fois ---


@pytest.fixture
def verrou(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    chemin = tmp_path / "tamponne.verrou"
    monkeypatch.setattr(lanceur, "CHEMIN_VERROU", chemin)
    return chemin


@pytest.mark.usefixtures("verrou")
@pytest.mark.skipif(sys.platform == "win32", reason="verrou testé sous POSIX")
def test_instance_unique_refuse_un_second_lanceur_puis_se_libere() -> None:
    with lanceur.instance_unique():
        assert not lanceur.verrou_libre()
        with pytest.raises(lanceur.DejaLance):
            with lanceur.instance_unique():
                pass
    assert lanceur.verrou_libre()


@pytest.mark.skipif(sys.platform == "win32", reason="verrou testé sous POSIX")
def test_instance_unique_survit_a_un_fichier_laisse_par_un_lanceur_mort(
    verrou: Path,
) -> None:
    verrou.write_text("reste d'un lancement interrompu", encoding="utf-8")
    assert lanceur.verrou_libre()


@pytest.mark.skipif(sys.platform == "win32", reason="verrou testé sous POSIX")
def test_principal_deuxieme_lancement_le_dit_sans_rien_lancer(
    verrou: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    lances: list[str] = []

    def lancer_espion() -> int:
        lances.append("lancé")
        return 0

    monkeypatch.setattr(lanceur, "lancer", lancer_espion)
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", verrou.parent / "tamponne.log")
    with lanceur.instance_unique():
        assert lanceur.principal() == 0
    assert lances == []
    assert lanceur.MESSAGE_DEJA_LANCE in capsys.readouterr().err
    assert "déjà ouvert" in (verrou.parent / "tamponne.log").read_text(encoding="utf-8")


@pytest.mark.skipif(sys.platform == "win32", reason="verrou testé sous POSIX")
def test_principal_lance_une_fois_et_libere_le_verrou(
    verrou: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lanceur, "CHEMIN_JOURNAL", verrou.parent / "tamponne.log")
    pendant: list[bool] = []

    def lancer_factice() -> int:
        pendant.append(lanceur.verrou_libre())
        return 7

    monkeypatch.setattr(lanceur, "lancer", lancer_factice)
    assert lanceur.principal() == 7
    assert pendant == [False]
    assert lanceur.verrou_libre()


def test_anonymiser_ignore_la_casse_sous_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lanceur.Path, "home", lambda: Path("/Users/Cedric"))
    monkeypatch.setattr(lanceur.sys, "platform", "win32")
    assert lanceur.anonymiser("/users/CEDRIC/data et /Users/Cedric/x") == (
        "~/data et ~/x"
    )


def test_anonymiser_respecte_la_casse_hors_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lanceur.Path, "home", lambda: Path("/home/Cedric"))
    monkeypatch.setattr(lanceur.sys, "platform", "linux")
    assert lanceur.anonymiser("/home/cedric/x et /home/Cedric/y") == (
        "/home/cedric/x et ~/y"
    )


def test_executer_commande_introuvable_rend_un_code_d_echec_et_le_journalise(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lanceur, "_sortie", sys.stdout)
    code = lanceur._executer(["programme-qui-n-existe-pas", "--option"])

    assert code == lanceur.CODE_LANCEMENT_IMPOSSIBLE
    assert "Impossible de lancer programme-qui-n-existe-pas" in capsys.readouterr().out
    assert "Impossible de lancer programme-qui-n-existe-pas" in (
        lanceur.CHEMIN_JOURNAL.read_text(encoding="utf-8")
    )
