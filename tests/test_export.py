"""Tests de src/export.py : export HTML du registre."""

from pathlib import Path

import pytest

from src import export
from src.types import Offre


def _offre(**champs: str) -> Offre:
    offre: Offre = {
        "titre": "Attaché(e) RH",
        "url": "https://choisirleservicepublic.gouv.fr/offre-emploi/x/",
        "reference": "MINT_2026-1",
        "domaine": "",
        "employeur": "Préfecture",
        "localisation": "Paris 75",
        "versant": "",
        "date": "11/09/2026",
        "source": "",
    }
    offre.update(champs)  # type: ignore[typeddict-item]
    return offre


@pytest.fixture(autouse=True)
def _exports_vers_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export, "DOSSIER_EXPORTS", tmp_path / "exports")


def test_exporter_html_ecrit_une_ligne_par_offre() -> None:
    chemin = export.exporter_html([_offre(), _offre(reference="MINT_2026-2")], "A", 3)
    page = chemin.read_text(encoding="utf-8")
    assert page.count("<tr><td>") == 2
    assert "2 offres affichées" in page
    assert "~60 au total, 3 page(s)" in page
    assert "de la fonction publique — Tamponné" in page


def test_exporter_html_echappe_le_texte_des_sites() -> None:
    piege = "<script>alert(1)</script>"
    chemin = export.exporter_html(
        [_offre(titre=piege, employeur='"><img src=x>', localisation="O'Neil")],
        piege,
        1,
    )
    page = chemin.read_text(encoding="utf-8")
    assert "<script>" not in page and "<img" not in page
    assert "&lt;script&gt;" in page and "&#x27;" in page


def test_exporter_html_nom_de_fichier_tire_du_profil() -> None:
    chemin = export.exporter_html([], "", 1, nom_profil="Fiche Paris / RH")
    assert chemin.parent == export.DOSSIER_EXPORTS
    assert chemin.name.startswith("fiche-paris---rh_")
    assert chemin.suffix == ".html"
