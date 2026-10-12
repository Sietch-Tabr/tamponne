"""Tests pour src/maj.py — vérification et application des mises à jour."""

import json
import shutil
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Literal, Self
from urllib.error import URLError

import pytest

from src import maj
from src.types import InfoMaj


@pytest.fixture(autouse=True)
def _rediriger_maj_vers_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirige marqueur, pyproject et racine du projet vers un répertoire
    temporaire isolé — jamais de vrai appel réseau ni d'écriture dans le
    vrai dépôt pendant les tests."""
    monkeypatch.setattr(maj, "CHEMIN_MARQUEUR", tmp_path / "maj_disponible.json")
    chemin_pyproject = tmp_path / "pyproject.toml"
    chemin_pyproject.write_text('[project]\nversion = "1.0.0"\n', encoding="utf-8")
    monkeypatch.setattr(maj, "CHEMIN_PYPROJECT", chemin_pyproject)
    monkeypatch.setattr(maj, "CHEMIN_RACINE", tmp_path)


def _info(version: str = "1.1.0") -> InfoMaj:
    return {
        "version": version,
        "notes": "notes de version",
        "url_zip": "https://codeberg.org/x.zip",
        "url_publication": "https://codeberg.org/x",
    }


# --- version_plus_recente ---


def test_version_plus_recente_patch_superieur() -> None:
    assert maj.version_plus_recente("1.0.1", "1.0.0")


def test_version_plus_recente_egale_nest_pas_plus_recente() -> None:
    assert not maj.version_plus_recente("1.0.0", "1.0.0")


def test_version_plus_recente_inferieure() -> None:
    assert not maj.version_plus_recente("0.9.0", "1.0.0")


def test_version_plus_recente_tolere_prefixe_v() -> None:
    assert maj.version_plus_recente("v2.0.0", "1.0.0")


def test_version_plus_recente_major_superieur() -> None:
    assert maj.version_plus_recente("2.0.0", "1.9.9")


# --- version_locale ---


def test_version_locale_lit_pyproject() -> None:
    assert maj.version_locale() == "1.0.0"


# --- marqueur ---


def test_marqueur_absent_par_defaut() -> None:
    assert maj.lire_maj_disponible() is None


def test_marqueur_ecriture_puis_lecture() -> None:
    maj.ecrire_maj_disponible(_info())
    assert maj.lire_maj_disponible() == _info()


def test_marqueur_effacement() -> None:
    maj.ecrire_maj_disponible(_info())
    maj.effacer_maj_disponible()
    assert maj.lire_maj_disponible() is None


def test_marqueur_effacement_sans_marqueur_ne_leve_pas() -> None:
    maj.effacer_maj_disponible()  # ne doit pas lever


# --- verifier_derniere_publication ---


def test_verifier_derniere_publication_version_plus_recente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reponse = json.dumps(
        {
            "tag_name": "v1.1.0",
            "body": "notes",
            "zipball_url": "https://codeberg.org/x.zip",
            "html_url": "https://codeberg.org/x",
        }
    ).encode("utf-8")
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_factice(reponse))
    info = maj.verifier_derniere_publication()
    assert info == {
        "version": "1.1.0",
        "notes": "notes",
        "url_zip": "https://codeberg.org/x.zip",
        "url_publication": "https://codeberg.org/x",
    }


def test_verifier_derniere_publication_deja_a_jour_retourne_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reponse = json.dumps({"tag_name": "v1.0.0", "body": "", "zipball_url": ""}).encode(
        "utf-8"
    )
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_factice(reponse))
    assert maj.verifier_derniere_publication() is None


def test_verifier_derniere_publication_erreur_reseau_leve_verification_impossible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _leve(*args: object, **kwargs: object) -> None:
        raise URLError("hors ligne")

    monkeypatch.setattr(urllib.request, "urlopen", _leve)
    with pytest.raises(maj.VerificationImpossible, match="hors ligne"):
        maj.verifier_derniere_publication()


def test_verifier_derniere_publication_json_invalide_leve_verification_impossible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_factice(b"pas du json"))
    with pytest.raises(maj.VerificationImpossible):
        maj.verifier_derniere_publication()


def _urlopen_factice(contenu: bytes) -> Callable[..., object]:
    class _ReponseFactice:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *a: object) -> Literal[False]:
            return False

        def read(self) -> bytes:
            return contenu

    return lambda *args, **kwargs: _ReponseFactice()


# --- appliquer_maj ---


def _construire_zip_test(tmp_path: Path) -> str:
    """Zip avec un unique dossier racine (comme les archives Gitea/Forgejo)
    contenant un fichier modifié et un fichier nouveau."""
    chemin_zip = tmp_path / "source.zip"
    with zipfile.ZipFile(chemin_zip, "w") as archive:
        archive.writestr(
            "tamponne-abc123/pyproject.toml", '[project]\nversion = "1.1.0"\n'
        )
        archive.writestr("tamponne-abc123/src/nouveau.py", "# nouveau fichier\n")
    return str(chemin_zip)


def test_appliquer_maj_copie_les_fichiers_de_larchive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chemin_zip = _construire_zip_test(tmp_path)
    monkeypatch.setattr(
        urllib.request,
        "urlretrieve",
        lambda url, filename: shutil.copy(chemin_zip, filename),
    )

    maj.appliquer_maj(_info())

    assert (maj.CHEMIN_RACINE / "pyproject.toml").read_text(
        encoding="utf-8"
    ) == '[project]\nversion = "1.1.0"\n'
    assert (maj.CHEMIN_RACINE / "src" / "nouveau.py").exists()


def _construire_zip_test_avec_executable(tmp_path: Path) -> str:
    """Zip avec un fichier marqué exécutable dans `external_attr` (bit Unix
    rwxr-xr-x), comme le produit `git archive --format=zip` pour Tamponne.command."""
    chemin_zip = tmp_path / "source_executable.zip"
    with zipfile.ZipFile(chemin_zip, "w") as archive:
        info = zipfile.ZipInfo("tamponne-abc123/Tamponne.command")
        info.external_attr = 0o100755 << 16
        archive.writestr(info, "#!/bin/sh\necho lancement\n")
    return str(chemin_zip)


def test_appliquer_maj_fichier_executable_dans_larchive_reste_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """extractall() n'applique pas les bits Unix de l'archive : sans
    restauration manuelle, Tamponne.command perdrait son +x à chaque mise à jour."""
    chemin_zip = _construire_zip_test_avec_executable(tmp_path)
    monkeypatch.setattr(
        urllib.request,
        "urlretrieve",
        lambda url, filename: shutil.copy(chemin_zip, filename),
    )

    maj.appliquer_maj(_info())

    assert (maj.CHEMIN_RACINE / "Tamponne.command").stat().st_mode & 0o111


def test_appliquer_maj_ne_touche_pas_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """data/ n'est jamais dans l'archive (gitignore) — doit survivre intact."""
    dossier_data = maj.CHEMIN_RACINE / "data"
    dossier_data.mkdir()
    fichier_utilisateur = dossier_data / "profils.json"
    fichier_utilisateur.write_text('{"conserve": true}', encoding="utf-8")

    chemin_zip = _construire_zip_test(tmp_path)
    monkeypatch.setattr(
        urllib.request,
        "urlretrieve",
        lambda url, filename: shutil.copy(chemin_zip, filename),
    )

    maj.appliquer_maj(_info())

    assert fichier_utilisateur.read_text(encoding="utf-8") == '{"conserve": true}'


def test_appliquer_maj_url_manquante_leve_erreur_explicite() -> None:
    with pytest.raises(RuntimeError):
        maj.appliquer_maj(_info(""))


def test_appliquer_maj_echec_telechargement_leve_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _leve(url: str, filename: str) -> None:
        raise URLError("hors ligne")

    monkeypatch.setattr(urllib.request, "urlretrieve", _leve)
    with pytest.raises(RuntimeError):
        maj.appliquer_maj(_info())


# --- installer_archive : purge et remplacement ---


def _publication(tmp_path: Path, fichiers: dict[str, str]) -> Path:
    dossier = tmp_path / "extrait" / "tamponne-abc123"
    for relatif, contenu in fichiers.items():
        chemin = dossier / relatif
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(contenu, encoding="utf-8")
    return dossier


def _installation(racine: Path, fichiers: dict[str, str]) -> None:
    for relatif, contenu in fichiers.items():
        chemin = racine / relatif
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text(contenu, encoding="utf-8")


def test_installer_archive_purge_src_seulement(tmp_path: Path) -> None:
    racine = tmp_path / "installation"
    _installation(
        racine,
        {
            "src/garde.py": "ancien",
            "src/gui/vues/accueil.py": "obsolète",
            "src/gui/vues/__pycache__/accueil.cpython-314.pyc": "",
            "tests/test_ancien.py": "obsolète",
            "data/profils.json": "{}",
            "notes-perso.md": "à garder",
        },
    )
    publication = _publication(tmp_path, {"src/garde.py": "nouveau"})

    maj.installer_archive(publication, racine)

    assert (racine / "src/garde.py").read_text(encoding="utf-8") == "nouveau"
    assert not (racine / "src/gui").exists()
    assert (racine / "tests/test_ancien.py").exists()
    assert (racine / "data/profils.json").read_text(encoding="utf-8") == "{}"
    assert (racine / "notes-perso.md").exists()


def test_installer_archive_ne_purge_rien_dans_un_clone_git(tmp_path: Path) -> None:
    racine = tmp_path / "clone"
    _installation(racine, {".git/HEAD": "ref", "src/local.py": "en cours"})
    maj.installer_archive(_publication(tmp_path, {"src/autre.py": ""}), racine)
    assert (racine / "src/local.py").exists()


def test_installer_archive_remplace_sans_reecrire_le_fichier_ouvert(
    tmp_path: Path,
) -> None:
    """bash lit Tamponne.command au fil de l'exécution : le remplacer par
    renommage laisse au processus en cours l'ancien contenu."""
    racine = tmp_path / "installation"
    _installation(racine, {"Tamponne.command": "ancien contenu\n"})
    with (racine / "Tamponne.command").open(encoding="utf-8") as ouvert:
        maj.installer_archive(_publication(tmp_path, {"Tamponne.command": "nouveau\n"}), racine)
        assert ouvert.read() == "ancien contenu\n"
    assert (racine / "Tamponne.command").read_text(encoding="utf-8") == "nouveau\n"
    assert not list(racine.glob("*.maj"))


# --- retour arrière ---


def _installation_1_0(racine: Path) -> None:
    """Version installée : un module, des données, un environnement Python."""
    (racine / "src").mkdir()
    (racine / "src" / "ancien.py").write_text("# 1.0\n", encoding="utf-8")
    (racine / "data").mkdir()
    (racine / "data" / "profils.json").write_text("{}", encoding="utf-8")
    (racine / ".venv").mkdir()
    (racine / ".venv" / "pyvenv.cfg").write_text("", encoding="utf-8")


def test_appliquer_maj_sauvegarde_la_version_actuelle_hors_donnees_et_venv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _installation_1_0(maj.CHEMIN_RACINE)
    chemin_zip = _construire_zip_test(tmp_path)
    monkeypatch.setattr(
        urllib.request,
        "urlretrieve",
        lambda url, filename: shutil.copy(chemin_zip, filename),
    )

    maj.appliquer_maj(_info())

    sauvegarde = maj.dossier_precedente()
    assert (sauvegarde / "src" / "ancien.py").exists()
    assert 'version = "1.0.0"' in (sauvegarde / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert not (sauvegarde / "data").exists()
    assert not (sauvegarde / ".venv").exists()


def test_restaurer_version_precedente_remet_l_ancienne_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _installation_1_0(maj.CHEMIN_RACINE)
    chemin_zip = _construire_zip_test(tmp_path)
    monkeypatch.setattr(
        urllib.request,
        "urlretrieve",
        lambda url, filename: shutil.copy(chemin_zip, filename),
    )
    maj.appliquer_maj(_info())

    assert maj.restaurer_version_precedente()

    assert maj.version_locale() == "1.0.0"
    assert (maj.CHEMIN_RACINE / "src" / "ancien.py").exists()
    assert not (maj.CHEMIN_RACINE / "src" / "nouveau.py").exists()
    assert (maj.CHEMIN_RACINE / "data" / "profils.json").exists()
    assert not maj.dossier_precedente().exists()


def test_restaurer_version_precedente_sans_sauvegarde_retourne_faux() -> None:
    assert not maj.restaurer_version_precedente()


def test_valider_maj_supprime_la_sauvegarde_et_l_echec() -> None:
    maj.dossier_precedente().mkdir()
    maj.enregistrer_echec("1.1.0", "motif")

    maj.valider_maj()

    assert not maj.dossier_precedente().exists()
    assert maj.lire_echec() is None


def test_valider_maj_sans_sauvegarde_garde_l_echec() -> None:
    """Version précédente relancée après une annulation : l'échec reste
    mémorisé, la version annulée n'est pas reprogrammée."""
    maj.enregistrer_echec("1.1.0", "motif")

    maj.valider_maj()

    assert maj.maj_en_echec("1.1.0")


def test_maj_en_echec_seulement_pour_la_version_annulee() -> None:
    maj.enregistrer_echec("1.1.0", "motif")

    assert maj.maj_en_echec("1.1.0")
    assert not maj.maj_en_echec("1.1.1")
