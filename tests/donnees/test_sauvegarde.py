"""Tests de src/donnees/sauvegarde.py : export, import par remplacement et refus des
fichiers qui ne sont pas des sauvegardes intactes."""

import json
import zipfile
from pathlib import Path

import pytest

from src.donnees import cache, candidatures, parametres_sources, profils, sauvegarde
from src.donnees.sauvegarde import ErreurSauvegarde, exporter_donnees, importer_donnees


@pytest.fixture(autouse=True)
def _sources_vers_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")


def _ecrire(chemin: Path, contenu: object) -> None:
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(contenu), encoding="utf-8")


def _zip(chemin: Path, membres: dict[str, str | bytes]) -> Path:
    with zipfile.ZipFile(chemin, "w") as archive:
        for nom, contenu in membres.items():
            archive.writestr(nom, contenu)
    return chemin


MANIFESTE = json.dumps({"application": "Tamponné", "format": 1, "version": "1.2.0"})


def test_exporter_donnees_contient_donnees_et_manifeste_sans_cache(
    tmp_path: Path,
) -> None:
    _ecrire(profils.CHEMIN_PROFILS, {"Attaché Paris": {}})
    _ecrire(candidatures.CHEMIN_CANDIDATURES, [])
    _ecrire(cache.CHEMIN_CACHE, {"organisations": {}})
    candidatures.DOSSIER_ARCHIVES.mkdir()
    (candidatures.DOSSIER_ARCHIVES / "MINT_2026-1.pdf").write_bytes(b"%PDF")

    destination = tmp_path / "export" / sauvegarde.nom_export()
    exporter_donnees(destination)

    with zipfile.ZipFile(destination) as archive:
        noms = set(archive.namelist())
        manifeste = json.loads(archive.read("manifeste.json"))
    assert noms == {
        "manifeste.json",
        "profils.json",
        "candidatures.json",
        "archives/MINT_2026-1.pdf",
    }
    assert manifeste["application"] == "Tamponné" and manifeste["format"] == 1
    assert not list(destination.parent.glob("*.tmp"))


def test_importer_donnees_aller_retour_remplace_tout(tmp_path: Path) -> None:
    _ecrire(profils.CHEMIN_PROFILS, {"Exportée": {}})
    candidatures.DOSSIER_ARCHIVES.mkdir()
    (candidatures.DOSSIER_ARCHIVES / "A.pdf").write_bytes(b"A")
    export = tmp_path / "export.zip"
    exporter_donnees(export)

    _ecrire(profils.CHEMIN_PROFILS, {"Locale": {}})
    _ecrire(cache.CHEMIN_OFFRES, {"Locale": {}})
    (candidatures.DOSSIER_ARCHIVES / "B.pdf").write_bytes(b"B")

    importer_donnees(export)

    assert json.loads(profils.CHEMIN_PROFILS.read_text(encoding="utf-8")) == {
        "Exportée": {}
    }
    assert not cache.CHEMIN_OFFRES.exists()
    assert sorted(p.name for p in candidatures.DOSSIER_ARCHIVES.iterdir()) == ["A.pdf"]
    with zipfile.ZipFile(sauvegarde.chemin_copie_securite()) as copie:
        assert "archives/B.pdf" in copie.namelist()
        assert json.loads(copie.read("profils.json")) == {"Locale": {}}


@pytest.mark.parametrize(
    "membres",
    [
        {"profils.json": "{}"},
        {"manifeste.json": "pas du json"},
        {"manifeste.json": json.dumps({"application": "Autre", "format": 1})},
        {"manifeste.json": MANIFESTE, "../evasion.json": "{}"},
        {"manifeste.json": MANIFESTE, "/etc/passwd": "x"},
        {"manifeste.json": MANIFESTE, "archives/../profils.pdf": "x"},
        {"manifeste.json": MANIFESTE, "archives/sous/dossier.pdf": "x"},
        {"manifeste.json": MANIFESTE, "cache.json": "{}"},
    ],
    ids=[
        "sans-manifeste",
        "manifeste-illisible",
        "autre-application",
        "chemin-parent",
        "chemin-absolu",
        "pdf-hors-archives",
        "pdf-sous-dossier",
        "fichier-non-exporte",
    ],
)
def test_importer_donnees_refuse_un_fichier_douteux_sans_rien_toucher(
    tmp_path: Path, membres: dict[str, str | bytes]
) -> None:
    _ecrire(profils.CHEMIN_PROFILS, {"Locale": {}})
    with pytest.raises(ErreurSauvegarde, match="pas une sauvegarde"):
        importer_donnees(_zip(tmp_path / "douteux.zip", membres))
    assert json.loads(profils.CHEMIN_PROFILS.read_text(encoding="utf-8")) == {
        "Locale": {}
    }
    assert not sauvegarde.chemin_copie_securite().exists()


def test_importer_donnees_refuse_un_fichier_qui_n_est_pas_un_zip(
    tmp_path: Path,
) -> None:
    faux = tmp_path / "faux.zip"
    faux.write_text("bonjour", encoding="utf-8")
    with pytest.raises(ErreurSauvegarde, match="pas une sauvegarde"):
        importer_donnees(faux)


def test_importer_donnees_refuse_un_json_endommage(tmp_path: Path) -> None:
    membres: dict[str, str | bytes] = {"manifeste.json": MANIFESTE, "profils.json": "{"}
    with pytest.raises(ErreurSauvegarde, match="endommagée"):
        importer_donnees(_zip(tmp_path / "abime.zip", membres))


def test_importer_donnees_refuse_un_format_plus_recent(tmp_path: Path) -> None:
    manifeste = json.dumps({"application": "Tamponné", "format": 2})
    with pytest.raises(ErreurSauvegarde, match="plus récente"):
        importer_donnees(_zip(tmp_path / "futur.zip", {"manifeste.json": manifeste}))


def test_importer_donnees_refuse_une_taille_excessive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sauvegarde, "TAILLE_MAX", 10)
    membres: dict[str, str | bytes] = {
        "manifeste.json": MANIFESTE,
        "profils.json": json.dumps({"x" * 20: {}}),
    }
    with pytest.raises(ErreurSauvegarde, match="trop volumineuse"):
        importer_donnees(_zip(tmp_path / "gros.zip", membres))


def test_exporter_donnees_emplacement_impossible_message_en_francais(
    tmp_path: Path,
) -> None:
    bloque = tmp_path / "fichier"
    bloque.write_text("", encoding="utf-8")
    with pytest.raises(ErreurSauvegarde, match="Impossible d'écrire"):
        exporter_donnees(bloque / "export.zip")
