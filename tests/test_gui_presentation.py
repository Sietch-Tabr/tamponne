"""Tests de src/gui/presentation.py : textes des dossiers de suivi."""

from datetime import date

from src.gui.presentation import contenu_dossier, reformater_date_iso
from src.types import Candidature, EvenementCandidature


def _candidature(
    historique: list[EvenementCandidature], disponible: bool = True
) -> Candidature:
    return {
        "offre_titre": "Attaché(e) d'administration RH",
        "offre_employeur": "Préfecture de région",
        "offre_url": "https://example.org/offre",
        "offre_reference": "MINT_2026-31544",
        "offre_domaine": "",
        "offre_localisation": "Paris 75",
        "offre_versant": "",
        "offre_date": "",
        "date_candidature": "2026-09-11",
        "historique": historique,
        "disponible": disponible,
        "derniere_verification": "",
        "detail": {
            "description": "",
            "salaire": "",
            "experience_requise": "",
            "formation_requise": "",
            "secteur": "",
            "date_publication": "",
            "a_propos_employeur": "",
            "sections_complementaires": {},
            "page_html": "",
            "lien_postuler": "",
            "date_limite": "",
        },
    }


def _evt(jour: str, type_evt: str, note: str = "") -> EvenementCandidature:
    return {"date": jour, "type": type_evt, "note": note}


def test_reformater_date_iso_annee_courte_retourne_jj_mm_aa() -> None:
    assert reformater_date_iso("2026-09-11") == "11/09/2026"
    assert reformater_date_iso("2026-09-11", annee_courte=True) == "11/09/26"
    assert reformater_date_iso("inconnue") == "inconnue"


def test_contenu_dossier_statut_reprend_dernier_evenement_et_sa_note() -> None:
    contenu = contenu_dossier(
        "2026-30871",
        _candidature(
            [
                _evt("2026-09-24", "accuse_reception"),
                _evt("2026-09-20", "candidature_envoyee"),
                _evt("2026-10-01", "entretien_planifie", "visio, 14 h"),
            ]
        ),
        aujourd_hui=date(2026, 10, 4),
        archive_presente=True,
    )
    assert contenu.statut == "entretien planifié le 01/10/2026 (visio, 14 h)"
    assert contenu.employeur_lieu == "Préfecture de région · Paris 75"
    assert [t.libelle for t in contenu.tampons] == [
        "Envoyée",
        "Accusé de réception",
        "Entretien",
    ]
    assert [t.courant for t in contenu.tampons] == [False, False, True]
    assert contenu.tampons[2].date == "01/10/26"
    assert contenu.jours_sans_nouvelles is None


def test_contenu_dossier_relance_suggeree_donne_jours_sans_nouvelles() -> None:
    contenu = contenu_dossier(
        "MINT_2026-31544",
        _candidature([_evt("2026-09-11", "candidature_envoyee")]),
        aujourd_hui=date(2026, 10, 4),
        archive_presente=True,
    )
    assert contenu.jours_sans_nouvelles == 23


def test_contenu_dossier_refus_depublie_signale_archive_et_encre_rouge() -> None:
    contenu = contenu_dossier(
        "FHF_48213",
        _candidature(
            [_evt("2026-09-05", "candidature_envoyee"), _evt("2026-09-26", "refus")],
            disponible=False,
        ),
        aujourd_hui=date(2026, 10, 4),
        archive_presente=True,
    )
    assert contenu.statut == (
        "refus le 26/09/2026 · offre dépubliée, archive PDF conservée"
    )
    assert contenu.tampons[-1].refus is True
    assert contenu.disponible is False


def test_contenu_dossier_depublie_sans_archive_ne_promet_pas_de_copie() -> None:
    contenu = contenu_dossier(
        "FHF_48213",
        _candidature([_evt("2026-09-26", "refus")], disponible=False),
        aujourd_hui=date(2026, 10, 4),
        archive_presente=False,
    )
    assert contenu.statut == "refus le 26/09/2026 · offre dépubliée"


def test_contenu_dossier_sans_historique_indique_aucun_evenement() -> None:
    contenu = contenu_dossier(
        "REF", _candidature([]), aujourd_hui=date(2026, 10, 4), archive_presente=False
    )
    assert contenu.statut == "aucun événement"
    assert contenu.tampons == ()
