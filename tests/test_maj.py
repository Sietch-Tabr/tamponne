"""Tests pour src/maj.py — vérification et application des mises à jour."""

import json
import shutil
import zipfile
from urllib.error import URLError

import pytest

from src import maj
from src.types import InfoMaj


@pytest.fixture(autouse=True)
def _rediriger_maj_vers_tmp(tmp_path, monkeypatch):
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


def test_version_plus_recente_patch_superieur():
    assert maj.version_plus_recente("1.0.1", "1.0.0")


def test_version_plus_recente_egale_nest_pas_plus_recente():
    assert not maj.version_plus_recente("1.0.0", "1.0.0")


def test_version_plus_recente_inferieure():
    assert not maj.version_plus_recente("0.9.0", "1.0.0")


def test_version_plus_recente_tolere_prefixe_v():
    assert maj.version_plus_recente("v2.0.0", "1.0.0")


def test_version_plus_recente_major_superieur():
    assert maj.version_plus_recente("2.0.0", "1.9.9")


# --- version_locale ---


def test_version_locale_lit_pyproject():
    assert maj.version_locale() == "1.0.0"


# --- marqueur ---


def test_marqueur_absent_par_defaut():
    assert maj.lire_maj_disponible() is None


def test_marqueur_ecriture_puis_lecture():
    maj.ecrire_maj_disponible(_info())
    assert maj.lire_maj_disponible() == _info()


def test_marqueur_effacement():
    maj.ecrire_maj_disponible(_info())
    maj.effacer_maj_disponible()
    assert maj.lire_maj_disponible() is None


def test_marqueur_effacement_sans_marqueur_ne_leve_pas():
    maj.effacer_maj_disponible()  # ne doit pas lever


# --- verifier_derniere_publication ---


def test_verifier_derniere_publication_version_plus_recente(monkeypatch):
    reponse = json.dumps(
        {
            "tag_name": "v1.1.0",
            "body": "notes",
            "zipball_url": "https://codeberg.org/x.zip",
            "html_url": "https://codeberg.org/x",
        }
    ).encode("utf-8")
    monkeypatch.setattr(maj.urllib.request, "urlopen", _urlopen_factice(reponse))
    info = maj.verifier_derniere_publication()
    assert info == {
        "version": "1.1.0",
        "notes": "notes",
        "url_zip": "https://codeberg.org/x.zip",
        "url_publication": "https://codeberg.org/x",
    }


def test_verifier_derniere_publication_deja_a_jour_retourne_none(monkeypatch):
    reponse = json.dumps({"tag_name": "v1.0.0", "body": "", "zipball_url": ""}).encode(
        "utf-8"
    )
    monkeypatch.setattr(maj.urllib.request, "urlopen", _urlopen_factice(reponse))
    assert maj.verifier_derniere_publication() is None


def test_verifier_derniere_publication_erreur_reseau_retourne_none(monkeypatch):
    def _leve(*args, **kwargs):
        raise URLError("hors ligne")

    monkeypatch.setattr(maj.urllib.request, "urlopen", _leve)
    assert maj.verifier_derniere_publication() is None


def test_verifier_derniere_publication_json_invalide_retourne_none(monkeypatch):
    monkeypatch.setattr(maj.urllib.request, "urlopen", _urlopen_factice(b"pas du json"))
    assert maj.verifier_derniere_publication() is None


def _urlopen_factice(contenu: bytes):
    class _ReponseFactice:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return contenu

    return lambda *args, **kwargs: _ReponseFactice()


# --- appliquer_maj ---


def _construire_zip_test(tmp_path) -> str:
    """Zip avec un unique dossier racine (comme les archives Gitea/Forgejo)
    contenant un fichier modifié et un fichier nouveau."""
    chemin_zip = tmp_path / "source.zip"
    with zipfile.ZipFile(chemin_zip, "w") as archive:
        archive.writestr(
            "tamponne-abc123/pyproject.toml", '[project]\nversion = "1.1.0"\n'
        )
        archive.writestr("tamponne-abc123/src/nouveau.py", "# nouveau fichier\n")
    return str(chemin_zip)


def test_appliquer_maj_copie_les_fichiers_de_larchive(tmp_path, monkeypatch):
    chemin_zip = _construire_zip_test(tmp_path)
    monkeypatch.setattr(
        maj.urllib.request,
        "urlretrieve",
        lambda url, filename: shutil.copy(chemin_zip, filename),
    )

    maj.appliquer_maj(_info())

    assert (maj.CHEMIN_RACINE / "pyproject.toml").read_text(
        encoding="utf-8"
    ) == '[project]\nversion = "1.1.0"\n'
    assert (maj.CHEMIN_RACINE / "src" / "nouveau.py").exists()


def test_appliquer_maj_ne_touche_pas_data(tmp_path, monkeypatch):
    """data/ n'est jamais dans l'archive (gitignore) — doit survivre intact."""
    dossier_data = maj.CHEMIN_RACINE / "data"
    dossier_data.mkdir()
    fichier_utilisateur = dossier_data / "profils.json"
    fichier_utilisateur.write_text('{"conserve": true}', encoding="utf-8")

    chemin_zip = _construire_zip_test(tmp_path)
    monkeypatch.setattr(
        maj.urllib.request,
        "urlretrieve",
        lambda url, filename: shutil.copy(chemin_zip, filename),
    )

    maj.appliquer_maj(_info())

    assert fichier_utilisateur.read_text(encoding="utf-8") == '{"conserve": true}'


def test_appliquer_maj_url_manquante_leve_erreur_explicite():
    with pytest.raises(RuntimeError):
        maj.appliquer_maj(_info(""))


def test_appliquer_maj_echec_telechargement_leve_runtime_error(monkeypatch):
    def _leve(url, filename):
        raise URLError("hors ligne")

    monkeypatch.setattr(maj.urllib.request, "urlretrieve", _leve)
    with pytest.raises(RuntimeError):
        maj.appliquer_maj(_info())
