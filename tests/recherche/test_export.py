"""Tests de src/recherche/export.py : export HTML du registre."""

from pathlib import Path

import pytest

from src.recherche import export
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


def test_etat_exports_sans_dossier_est_vide() -> None:
    assert export.etat_exports() == (0, 0)


def test_etat_exports_compte_les_fichiers_html() -> None:
    export.DOSSIER_EXPORTS.mkdir(parents=True)
    (export.DOSSIER_EXPORTS / "a.html").write_text("abc", encoding="utf-8")
    (export.DOSSIER_EXPORTS / "b.html").write_text("de", encoding="utf-8")
    (export.DOSSIER_EXPORTS / "notes.txt").write_text("ignoré", encoding="utf-8")
    assert export.etat_exports() == (2, 5)


def test_supprimer_exports_ne_garde_que_les_autres_fichiers() -> None:
    export.exporter_html([_offre()], "A", 1)
    (export.DOSSIER_EXPORTS / "notes.txt").write_text("gardé", encoding="utf-8")
    export.supprimer_exports()
    assert export.etat_exports() == (0, 0)
    assert (export.DOSSIER_EXPORTS / "notes.txt").exists()


def test_supprimer_exports_sans_dossier_ne_fait_rien() -> None:
    export.supprimer_exports()
    assert not export.DOSSIER_EXPORTS.exists()


def test_supprimer_exports_en_echec_supprime_les_autres_puis_leve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    export.DOSSIER_EXPORTS.mkdir(parents=True)
    bloque = export.DOSSIER_EXPORTS / "a.html"
    libre = export.DOSSIER_EXPORTS / "b.html"
    bloque.write_text("x", encoding="utf-8")
    libre.write_text("x", encoding="utf-8")
    unlink = Path.unlink

    def unlink_bloque(chemin: Path, missing_ok: bool = False) -> None:
        if chemin.name == "a.html":
            raise PermissionError("fichier ouvert")
        unlink(chemin, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", unlink_bloque)
    with pytest.raises(PermissionError):
        export.supprimer_exports()
    assert bloque.exists() and not libre.exists()
