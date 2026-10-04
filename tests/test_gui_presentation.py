"""Tests de src/gui/presentation.py : textes des dossiers de suivi."""

from datetime import date, datetime

from src.gui.presentation import (
    contenu_detail,
    contenu_dossier,
    date_courte,
    evenement_propose,
    libelle_selection,
    lignes_fiche,
    reformater_date_iso,
    resume_registre,
    texte_nombre_fiches,
    texte_nouvelles,
)
from src.types import Candidature, EvenementCandidature, Profil


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


def test_contenu_detail_ordonne_rubriques_et_ignore_valeurs_vides() -> None:
    detail = _candidature([])["detail"]
    detail.update(
        {
            "description": "Gérer la paie.",
            "salaire": "",
            "secteur": "Administration",
            "date_publication": "01/10/2026",
            "a_propos_employeur": "Préfecture de région.",
            "sections_complementaires": {"Profil recherché": "Rigueur."},
            "lien_postuler": "https://portail.example.org",
        }
    )
    contenu = contenu_detail(
        "MINT_2026-31544",
        "Attaché(e) d'administration RH",
        ["Préfecture de région", "", "Paris 75"],
        detail,
        "https://example.org/offre",
        archive_presente=True,
    )
    assert contenu.sous_titre == "Préfecture de région · Paris 75"
    assert contenu.description == "Gérer la paie."
    assert contenu.informations == (
        ("Secteur", "Administration"),
        ("Publiée le", "01/10/2026"),
    )
    assert contenu.rubriques == (
        ("Qui sommes-nous ?", "Préfecture de région."),
        ("Profil recherché", "Rigueur."),
    )
    assert contenu.lien_postuler == "https://portail.example.org"


def test_contenu_detail_refuse_liens_non_https() -> None:
    detail = _candidature([])["detail"]
    detail["lien_postuler"] = "http://portail.example.org"
    contenu = contenu_detail("R", "T", [], detail, "javascript:alert(1)", False)
    assert contenu.lien_postuler == ""
    assert contenu.url == ""


def test_lignes_fiche_regroupe_comme_la_maquette() -> None:
    profil: Profil = {
        "categories": ["A+ (direction)", "A"],
        "versants": ["etat", "territorial"],
        "localisations": ["Île-de-France"],
        "teletravail": True,
    }
    assert lignes_fiche(profil) == [
        "Cat. A+ (direction), A · État, Territorial",
        "Île-de-France · télétravail",
    ]


def test_lignes_fiche_troisieme_ligne_pour_les_autres_criteres() -> None:
    profil: Profil = {
        "categories": ["A"],
        "versants": ["hospitalier"],
        "domaines": ["Achats", "Finances"],
        "organisations": ["Ministère - Direction des achats"],
        "query": "achat",
    }
    assert lignes_fiche(profil) == [
        "Cat. A · Hospitalier",
        "Toute la France",
        "Achats +1 · Direction des achats · mot-clé « achat »",
    ]


def test_lignes_fiche_profil_vide() -> None:
    assert lignes_fiche({}) == ["Toutes catégories · tous versants", "Toute la France"]


def test_textes_nouvelles_et_nombre_de_fiches_accordes() -> None:
    assert texte_nouvelles(0) == ""
    assert texte_nouvelles(1) == "1 nouvelle"
    assert texte_nouvelles(2) == "2 nouvelles"
    assert texte_nombre_fiches(1) == "1 fiche classée"
    assert texte_nombre_fiches(2) == "2 fiches classées"


def test_libelle_selection_tous_unique_ou_nombre() -> None:
    assert libelle_selection([]) == "tous"
    assert libelle_selection(["Île-de-France"]) == "Île-de-France"
    assert libelle_selection(["Ministère - Direction des achats"]) == "Direction des achats"
    assert libelle_selection(["A", "B"]) == "2 cochés"


def test_resume_registre_omet_les_compteurs_nuls() -> None:
    quand = datetime(2026, 10, 4, 10, 12)
    assert resume_registre(6, 2, 1, quand) == (
        "6 inscrites · 2 nouvelles · 1 écartée (grades supérieurs) · 04/10/2026 10:12"
    )
    assert resume_registre(0, 0, 0, quand) == "0 inscrite · 04/10/2026 10:12"


def test_date_courte_raccourcit_l_annee() -> None:
    assert date_courte("02/10/2026") == "02/10/26"
    assert date_courte("—") == "—"


def test_tampons_gardent_la_position_d_origine_dans_l_historique() -> None:
    contenu = contenu_dossier(
        "R",
        _candidature(
            [_evt("2026-09-24", "accuse_reception"), _evt("2026-09-20", "candidature_envoyee")]
        ),
        aujourd_hui=date(2026, 10, 4),
        archive_presente=False,
    )
    assert [(t.libelle, t.indice) for t in contenu.tampons] == [
        ("Envoyée", 1),
        ("Accusé de réception", 0),
    ]


def test_evenement_propose_suit_le_dernier_evenement() -> None:
    assert evenement_propose(_candidature([]), date(2026, 10, 4)) == (
        "candidature_envoyee",
        "2026-10-04",
    )
    assert evenement_propose(
        _candidature(
            [_evt("2026-10-01", "entretien_planifie"), _evt("2026-09-20", "candidature_envoyee")]
        ),
        date(2026, 10, 4),
    ) == ("entretien_passe", "2026-10-01")
    assert evenement_propose(
        _candidature([_evt("2026-09-26", "autre")]), date(2026, 10, 4)
    ) == ("autre", "2026-09-26")
