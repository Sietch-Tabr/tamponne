"""Tests du suivi de candidature (src/donnees/candidatures.py)."""

from datetime import date, timedelta
from pathlib import Path
from typing import cast

import pytest

from src.donnees import candidatures
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.types import Candidature, DetailOffre, Offre


@pytest.fixture(autouse=True)
def _rediriger_candidatures_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        candidatures, "CHEMIN_CANDIDATURES", tmp_path / "candidatures.json"
    )
    monkeypatch.setattr(candidatures, "DOSSIER_ARCHIVES", tmp_path / "archives")


def test_charger_candidatures_absent_retourne_dict_vide() -> None:
    assert candidatures.charger_candidatures() == {}


def test_charger_candidatures_corrompu_retourne_dict_vide(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chemin = tmp_path / "candidatures.json"
    chemin.write_text("{ceci n'est pas du json", encoding="utf-8")
    monkeypatch.setattr(candidatures, "CHEMIN_CANDIDATURES", chemin)
    assert candidatures.charger_candidatures() == {}


def test_ajouter_candidature_ne_prerempli_pas_lhistorique() -> None:
    """Démarrer le suivi (« Suivre cette offre ») ne signifie pas que la
    candidature a été envoyée : l'historique reste vide tant que
    l'utilisateur n'a rien confirmé via « Ajouter un événement »."""
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    toutes = candidatures.charger_candidatures()
    assert "ref-1" in toutes
    assert toutes["ref-1"]["offre_titre"] == "Attaché"
    assert toutes["ref-1"]["historique"] == []


def test_ajouter_candidature_date_explicite() -> None:
    candidatures.ajouter_candidature(
        "ref-1",
        "Attaché",
        "DGFiP",
        "https://example.org/1",
        date_candidature="2026-01-15",
    )
    toutes = candidatures.charger_candidatures()
    assert toutes["ref-1"]["date_candidature"] == "2026-01-15"


def test_ajouter_candidature_ecrase_une_candidature_existante() -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    candidatures.ajouter_evenement("ref-1", "entretien_passe")
    candidatures.ajouter_candidature(
        "ref-1", "Attaché v2", "DGFiP", "https://example.org/1"
    )
    toutes = candidatures.charger_candidatures()
    assert toutes["ref-1"]["offre_titre"] == "Attaché v2"
    assert toutes["ref-1"]["historique"] == []


def test_ajouter_evenement_sur_candidature_introuvable_leve_keyerror() -> None:
    with pytest.raises(KeyError):
        candidatures.ajouter_evenement("inconnue", "relance")


def test_ajouter_evenement_empile_dans_lhistorique() -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    candidatures.ajouter_evenement("ref-1", "accuse_reception", note="Reçu par mail")
    toutes = candidatures.charger_candidatures()
    assert len(toutes["ref-1"]["historique"]) == 1
    assert toutes["ref-1"]["historique"][0]["type"] == "accuse_reception"
    assert toutes["ref-1"]["historique"][0]["note"] == "Reçu par mail"


def test_supprimer_candidature() -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    candidatures.supprimer_candidature("ref-1")
    assert "ref-1" not in candidatures.charger_candidatures()


def test_supprimer_candidature_inconnue_ne_leve_pas() -> None:
    candidatures.supprimer_candidature("inconnue")  # pas d'exception


def test_supprimer_candidature_supprime_larchive_pdf() -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    chemin_pdf = candidatures.chemin_archive_pdf("ref-1")
    chemin_pdf.parent.mkdir(parents=True, exist_ok=True)
    chemin_pdf.write_bytes(b"%PDF-1.4 factice")

    candidatures.supprimer_candidature("ref-1")

    assert not chemin_pdf.exists()


def test_supprimer_candidature_sans_archive_ne_leve_pas() -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    candidatures.supprimer_candidature("ref-1")  # pas d'exception


_PAGE_AVEC_LIEN_PDF = (
    '<a class="fr-link--download" href='
    '"https://choisirleservicepublic.gouv.fr/wp-content/uploads/pdf-offers/x.pdf">'
    "Télécharger</a>"
)


def test_extraire_url_pdf_trouve_le_lien() -> None:
    assert candidatures._extraire_url_pdf(_PAGE_AVEC_LIEN_PDF) == (
        "https://choisirleservicepublic.gouv.fr/wp-content/uploads/pdf-offers/x.pdf"
    )


def test_extraire_url_pdf_absent_retourne_vide() -> None:
    assert candidatures._extraire_url_pdf("<html></html>") == ""


def test_extraire_url_pdf_domaine_externe_rejete() -> None:
    page = '<a class="fr-link--download" href="https://evil.example.com/x.pdf">Dl</a>'
    assert candidatures._extraire_url_pdf(page) == ""


def test_generer_archive_pdf_reussi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        candidatures, "telecharger_binaire", lambda url: b"%PDF-1.4 contenu"
    )
    reussi = candidatures.generer_archive_pdf("ref-1", _PAGE_AVEC_LIEN_PDF)

    assert reussi is True
    chemin = candidatures.chemin_archive_pdf("ref-1")
    assert chemin.read_bytes() == b"%PDF-1.4 contenu"


def test_generer_archive_pdf_sans_lien_echoue_sans_lever(
    caplog: pytest.LogCaptureFixture,
) -> None:
    reussi = candidatures.generer_archive_pdf("ref-1", "<html></html>")

    assert reussi is False
    assert not candidatures.chemin_archive_pdf("ref-1").exists()
    assert "Lien PDF introuvable" in caplog.text


def test_generer_archive_pdf_echec_reseau_echoue_sans_lever(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def _leve_erreur(url: str) -> None:
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(candidatures, "telecharger_binaire", _leve_erreur)
    reussi = candidatures.generer_archive_pdf("ref-1", _PAGE_AVEC_LIEN_PDF)

    assert reussi is False
    assert "Échec de téléchargement" in caplog.text


def test_suivre_offre_enregistre_detail_et_archive_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detail: DetailOffre = {**DETAIL_VIDE, "page_html": _PAGE_AVEC_LIEN_PDF}
    monkeypatch.setattr(candidatures, "recuperer_detail_offre", lambda url: detail)
    monkeypatch.setattr(
        candidatures, "telecharger_binaire", lambda url: b"%PDF-1.4 contenu"
    )
    offre: Offre = {
        "titre": "Attaché",
        "url": "https://example.org/1",
        "reference": "ref-1",
        "domaine": "RH",
        "employeur": "DGFiP",
        "localisation": "Montpellier (34)",
        "versant": "Fonction publique de l'État",
        "date": "26 août 2026",
        "source": "",
    }

    candidatures.suivre_offre(offre)

    suivie = candidatures.charger_candidatures()["ref-1"]
    assert suivie["offre_titre"] == "Attaché"
    assert suivie["offre_localisation"] == "Montpellier (34)"
    assert suivie["detail"] == detail
    assert candidatures.chemin_archive_pdf("ref-1").exists()


def test_suivre_offre_sans_detail_ni_archive_suit_quand_meme(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fiche injoignable : le suivi basique reste utile (titre/url)."""
    monkeypatch.setattr(candidatures, "recuperer_detail_offre", lambda url: DETAIL_VIDE)
    offre: Offre = {
        "titre": "Attaché",
        "url": "https://example.org/1",
        "reference": "ref-1",
        "domaine": "",
        "employeur": "DGFiP",
        "localisation": "",
        "versant": "",
        "date": "",
        "source": "",
    }

    candidatures.suivre_offre(offre)

    assert "ref-1" in candidatures.charger_candidatures()
    assert not candidatures.chemin_archive_pdf("ref-1").exists()


def test_dernier_evenement_retourne_le_plus_recent_par_date() -> None:
    # Candidature partielle : seuls les champs lus par dernier_evenement.
    candidature = cast(
        Candidature,
        {
            "offre_titre": "x",
            "offre_employeur": "x",
            "offre_url": "x",
            "date_candidature": "2026-01-01",
            "historique": [
                {"date": "2026-01-01", "type": "candidature_envoyee", "note": ""},
                {"date": "2026-01-20", "type": "entretien_passe", "note": ""},
                {"date": "2026-01-10", "type": "accuse_reception", "note": ""},
            ],
        },
    )
    dernier = candidatures.dernier_evenement(candidature)
    assert dernier is not None
    assert dernier["type"] == "entretien_passe"


def test_dernier_evenement_historique_vide_retourne_none() -> None:
    candidature = cast(
        Candidature,
        {
            "offre_titre": "x",
            "offre_employeur": "x",
            "offre_url": "x",
            "date_candidature": "2026-01-01",
            "historique": [],
        },
    )
    assert candidatures.dernier_evenement(candidature) is None


def test_statut_libelle_derive_du_dernier_evenement() -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    candidatures.ajouter_evenement("ref-1", "entretien_planifie")
    toutes = candidatures.charger_candidatures()
    assert candidatures.statut_libelle(toutes["ref-1"]) == "Entretien planifié"


def test_relance_suggeree_false_si_recent() -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    candidatures.ajouter_evenement("ref-1", "candidature_envoyee")
    toutes = candidatures.charger_candidatures()
    assert candidatures.relance_suggeree(toutes["ref-1"]) is False


def test_relance_suggeree_true_apres_le_seuil() -> None:
    ancienne = (
        date.today() - timedelta(days=candidatures.SEUIL_RELANCE_JOURS + 1)
    ).isoformat()
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1", date_candidature=ancienne
    )
    candidatures.ajouter_evenement("ref-1", "candidature_envoyee", ancienne)
    toutes = candidatures.charger_candidatures()
    assert candidatures.relance_suggeree(toutes["ref-1"]) is True


def test_relance_suggeree_false_si_pas_devenement() -> None:
    # Suivi démarré mais aucun événement confirmé : rien à relancer,
    # on ne sait même pas si la candidature a été envoyée.
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    toutes = candidatures.charger_candidatures()
    assert candidatures.relance_suggeree(toutes["ref-1"]) is False


def test_relance_suggeree_false_si_candidature_close() -> None:
    ancienne = (
        date.today() - timedelta(days=candidatures.SEUIL_RELANCE_JOURS + 1)
    ).isoformat()
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1", date_candidature=ancienne
    )
    candidatures.ajouter_evenement("ref-1", "refus")
    toutes = candidatures.charger_candidatures()
    assert candidatures.relance_suggeree(toutes["ref-1"]) is False


def test_marquer_disponibilite_persiste_le_resultat() -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    candidatures.marquer_disponibilite("ref-1", False)
    toutes = candidatures.charger_candidatures()
    assert toutes["ref-1"]["disponible"] is False
    assert toutes["ref-1"]["derniere_verification"] == date.today().isoformat()


def test_marquer_disponibilite_candidature_inconnue_ne_leve_pas() -> None:
    candidatures.marquer_disponibilite("inconnue", False)  # pas d'exception


def test_nouvelle_candidature_disponible_par_defaut() -> None:
    candidatures.ajouter_candidature(
        "ref-1", "Attaché", "DGFiP", "https://example.org/1"
    )
    toutes = candidatures.charger_candidatures()
    assert toutes["ref-1"]["disponible"] is True
    assert toutes["ref-1"]["derniere_verification"] == ""


def test_source_candidature_memorisee_puis_deduite_du_prefixe() -> None:
    candidatures.ajouter_candidature(
        "2026-1", "Titre", "Employeur", "https://example.org", offre_source="FHF"
    )
    assert (
        candidatures.source_candidature(candidatures.charger_candidatures()["2026-1"])
        == "FHF"
    )
    ancienne = candidatures.charger_candidatures()["2026-1"]
    del ancienne["offre_source"]
    ancienne["offre_reference"] = "MINT_2026-31544"
    assert candidatures.source_candidature(ancienne) == "Ministère de l'Intérieur"
    ancienne["offre_reference"] = "2026-30871"
    assert candidatures.source_candidature(ancienne) == ""


def test_evenements_doublon_modification_et_suppression() -> None:
    candidatures.ajouter_candidature("R", "Titre", "Employeur", "https://example.org")
    candidatures.ajouter_evenement("R", "relance", "2026-10-01", "")
    candidatures.ajouter_evenement("R", "entretien_planifie", "2026-10-03", "visio")
    dossier = candidatures.charger_candidatures()["R"]
    assert candidatures.evenement_en_double(dossier, "relance", "2026-10-01")
    assert not candidatures.evenement_en_double(
        dossier, "relance", "2026-10-01", sauf_indice=0
    )
    assert not candidatures.evenement_en_double(dossier, "relance", "2026-10-02")

    candidatures.modifier_evenement("R", 1, "entretien_passe", "2026-10-03", "fait")
    candidatures.supprimer_evenement("R", 0)
    assert candidatures.charger_candidatures()["R"]["historique"] == [
        {"date": "2026-10-03", "type": "entretien_passe", "note": "fait"}
    ]
    with pytest.raises(IndexError):
        candidatures.supprimer_evenement("R", 5)


@pytest.mark.parametrize(
    "reference", ["MINT_2026-31544", "2026-30871", "FHF_48213", "o001261013000295"]
)
def test_chemin_archive_pdf_garde_les_references_reelles(reference: str) -> None:
    assert candidatures.chemin_archive_pdf(reference) == (
        candidatures.DOSSIER_ARCHIVES / f"{reference}.pdf"
    )


@pytest.mark.parametrize(
    "reference", ["../../evil", "..\\..\\evil", "/etc/evil", "C:\\evil", ".", ""]
)
def test_chemin_archive_pdf_reste_dans_le_dossier_des_archives(reference: str) -> None:
    chemin = candidatures.chemin_archive_pdf(reference)
    assert chemin.parent == candidatures.DOSSIER_ARCHIVES
    assert chemin.suffix == ".pdf" and not chemin.name.startswith(".")
