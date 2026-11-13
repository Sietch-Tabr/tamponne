"""Tests de src/utils.py : écriture atomique et nouvel essai sous Windows."""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from src import utils


@pytest.fixture(autouse=True)
def _sans_attente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils.time, "sleep", Mock(return_value=None))


def test_ecriture_atomique_ecrit_le_json(tmp_path: Path) -> None:
    utils.ecriture_atomique(tmp_path / "a.json", {"cle": "valeur é"})
    assert (tmp_path / "a.json").read_text(encoding="utf-8").count("valeur é") == 1


def test_ecriture_atomique_retente_si_le_fichier_est_tenu(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vrai_remplacement = os.replace
    essais: list[int] = []

    def remplacer(source: str, destination: Path) -> None:
        essais.append(1)
        if len(essais) < 3:
            raise PermissionError("tenu par l'antivirus")
        vrai_remplacement(source, destination)

    monkeypatch.setattr(utils.os, "replace", remplacer)
    utils.ecriture_atomique(tmp_path / "a.json", {"a": 1})

    assert len(essais) == 3
    assert (tmp_path / "a.json").exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_ecriture_atomique_abandonne_apres_les_essais_et_nettoie(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(_source: str, _destination: Path) -> None:
        raise PermissionError("tenu")

    monkeypatch.setattr(utils.os, "replace", refuse)
    with pytest.raises(PermissionError):
        utils.ecriture_atomique(tmp_path / "a.json", {"a": 1})

    assert not (tmp_path / "a.json").exists()
    assert not list(tmp_path.glob("*.tmp"))
