"""Tests de src/gui/presentation.py : textes des dossiers de suivi."""

from datetime import UTC, date, datetime

import pytest

from src.gui import presentation
from src.gui.presentation import (
    contenu_detail,
    contenu_dossier,
    date_courte,
    evenement_propose,
    libelle_selection,
    lignes_fiche,
    notes_en_html,
    reformater_date_iso,
    resume_registre,
    texte_confirmation_exports,
    texte_date_cache,
    texte_exports,
    texte_nombre_fiches,
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
        ("Qui sommes-nous\u00a0?", "Préfecture de région."),
        ("Profil recherché", "Rigueur."),
    )
    assert contenu.lien_postuler == "https://portail.example.org"


def test_contenu_detail_refuse_liens_non_https() -> None:
    detail = _candidature([])["detail"]
    detail["lien_postuler"] = "http://portail.example.org"
    contenu = contenu_detail("R", "T", [], detail, "javascript:alert(1)", False)
    assert contenu.lien_postuler == ""
    assert contenu.url == ""


@pytest.mark.parametrize(
    "lien",
    [
        "https://example.org/offre",
        "https://EXAMPLE.org/offre/",
        "https://example.org/offre#postuler",
        "",
    ],
)
def test_contenu_detail_ecarte_un_lien_de_candidature_identique_a_l_offre(
    lien: str,
) -> None:
    detail = _candidature([])["detail"]
    detail["lien_postuler"] = lien
    contenu = contenu_detail(
        "R", "T", [], detail, "https://example.org/offre", archive_presente=False
    )
    assert contenu.lien_postuler == ""
    assert contenu.url == "https://example.org/offre"


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
        "grades supérieurs exclus",
    ]


def test_lignes_fiche_grades_superieurs_inclus() -> None:
    profil: Profil = {"categories": ["A+ (direction)"], "grades_superieurs": True}
    assert lignes_fiche(profil)[2] == "grades supérieurs inclus"


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
        "Achats +1 · Direction des achats · mot-clé «\u00a0achat\u00a0»",
    ]


def test_lignes_fiche_profil_vide() -> None:
    assert lignes_fiche({}) == [
        "Toutes catégories · tous versants",
        "Toute la France",
        "grades supérieurs exclus",
    ]


def test_texte_nombre_de_fiches_accorde() -> None:
    assert texte_nombre_fiches(1) == "1 demande classée"
    assert texte_nombre_fiches(2) == "2 demandes classées"


def test_libelle_selection_tous_unique_ou_nombre() -> None:
    assert libelle_selection([]) == "tous"
    assert libelle_selection(["Île-de-France"]) == "Île-de-France"
    assert (
        libelle_selection(["Ministère - Direction des achats"])
        == "Direction des achats"
    )
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
            [
                _evt("2026-09-24", "accuse_reception"),
                _evt("2026-09-20", "candidature_envoyee"),
            ]
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
            [
                _evt("2026-10-01", "entretien_planifie"),
                _evt("2026-09-20", "candidature_envoyee"),
            ]
        ),
        date(2026, 10, 4),
    ) == ("entretien_passe", "2026-10-01")
    assert evenement_propose(
        _candidature([_evt("2026-09-26", "autre")]), date(2026, 10, 4)
    ) == ("autre", "2026-09-26")


def test_notes_en_html_titres_et_listes_sans_marge_avant_le_premier_bloc() -> None:
    notes = "### Recherche\n\n- Plus rapide\n- Tri des colonnes\n\n### Corrections\n\n- Titres rognés"
    assert notes_en_html(notes) == (
        '<p style="margin-top:0px;margin-bottom:0"><b>Recherche</b></p>'
        '<ul style="margin-top:4px;margin-bottom:0"><li>Plus rapide</li>'
        "<li>Tri des colonnes</li></ul>"
        '<p style="margin-top:12px;margin-bottom:0"><b>Corrections</b></p>'
        '<ul style="margin-top:4px;margin-bottom:0"><li>Titres rognés</li></ul>'
    )


def test_notes_en_html_paragraphe_sur_plusieurs_lignes() -> None:
    assert notes_en_html("Migration vers Python 3.14.\r\nCorrectif.") == (
        '<p style="margin-top:0px;margin-bottom:0">Migration vers Python 3.14. Correctif.</p>'
    )


def test_notes_en_html_puce_continuee_sur_la_ligne_suivante() -> None:
    assert "<li>Premier point suite</li>" in notes_en_html("- Premier point\n  suite")


def test_notes_en_html_code_gras_et_echappement() -> None:
    html = notes_en_html("- `chmod +x lancer.sh` **avant** <script> & co")
    assert '<span style="font-weight:600">chmod +x lancer.sh</span>' in html
    assert "<b>avant</b>" in html
    assert "&lt;script&gt; &amp; co" in html


def test_notes_en_html_liens_https_seulement() -> None:
    html = notes_en_html("[README](https://github.com/r) et [local](file:///etc)")
    assert '<a href="https://github.com/r">README</a>' in html
    assert "local" in html and "file://" not in html


def test_lignes_fiche_categories_en_libelle_court() -> None:
    lignes = lignes_fiche(
        {"categories": ["A+ (autres emplois fonctionnels)", "A+ (autres)", "A"]}
    )
    assert lignes[0].startswith("Cat. A+ (autres), A ·")


def test_texte_offres_non_verifiees_accorde_et_donne_le_detail() -> None:
    assert presentation.texte_offres_non_verifiees(0, "") == ""
    assert presentation.texte_offres_non_verifiees(1, "délai dépassé").startswith(
        "1 offre non vérifiée : le site de l'offre ne répond pas"
    )
    texte = presentation.texte_offres_non_verifiees(3, "délai dépassé")
    assert texte.startswith("3 offres non vérifiées :")
    assert texte.endswith("Détail : délai dépassé")


def test_texte_avis_sans_publication_distingue_en_cours_echec_et_a_jour() -> None:
    assert presentation.texte_avis_sans_publication("1.3.2", True, "") == (
        "version 1.3.2 installée, recherche d'une mise à jour…"
    )
    assert presentation.texte_avis_sans_publication("1.3.2", False, "") == (
        "version 1.3.2 installée, rien de plus récent."
    )
    echec = presentation.texte_avis_sans_publication("1.3.2", False, "timed out")
    assert "GitHub ne répond pas (connexion internet ou proxy)" in echec
    assert echec.endswith("Détail : timed out")


def test_texte_date_cache_absent_est_vide() -> None:
    assert texte_date_cache(None) == ""


def test_texte_date_cache_en_heure_locale() -> None:
    moment = datetime(2026, 10, 12, 14, 5).astimezone()
    assert texte_date_cache(moment.astimezone(UTC)) == (
        "En cache depuis le 12\u00a0octobre\u00a02026 à\u00a014\u00a0h\u00a005"
    )


def test_texte_date_cache_premier_du_mois() -> None:
    moment = datetime(2026, 3, 1, 9, 30).astimezone()
    assert texte_date_cache(moment).startswith("En cache depuis le 1er\u00a0mars")


def test_texte_exports_aucun() -> None:
    assert texte_exports(0, 0) == "Aucun export de recherche."


def test_texte_exports_en_ko_jamais_zero() -> None:
    assert texte_exports(1, 120) == "1\u00a0fichier, 1\u00a0Ko"
    assert texte_exports(3, 45_600) == "3\u00a0fichiers, 46\u00a0Ko"


def test_texte_exports_en_mo_virgule_decimale() -> None:
    assert texte_exports(12, 1_440_000) == "12\u00a0fichiers, 1,4\u00a0Mo"


def test_texte_confirmation_exports_singulier_et_pluriel() -> None:
    assert "l'export de recherche\u00a0?" in texte_confirmation_exports(1)
    assert "les 12\u00a0exports de recherche\u00a0?" in texte_confirmation_exports(12)


def test_contenu_dossier_depublie_date_la_depublication_sans_toucher_au_statut() -> (
    None
):
    candidature = _candidature(
        [
            _evt("2026-09-05", "candidature_envoyee"),
            _evt("2026-09-26", "entretien_planifie"),
        ],
        disponible=False,
    )
    candidature["depubliee_le"] = "2026-10-01"
    contenu = contenu_dossier(
        "REF", candidature, aujourd_hui=date(2026, 10, 4), archive_presente=False
    )

    assert contenu.statut == (
        "entretien planifié le 26/09/2026 · offre dépubliée le 01/10/2026"
    )
    assert contenu.depubliee_le == "01/10/26"
    assert contenu.depublication_a_signaler is True
    libelles = [
        (t.libelle, t.courant, t.information, t.indice) for t in contenu.tampons
    ]
    assert libelles == [
        ("Envoyée", False, False, 0),
        ("Entretien", True, False, 1),
        ("Offre dépubliée", False, True, -1),
    ]


def test_contenu_dossier_depublication_se_range_a_sa_date_parmi_les_evenements() -> (
    None
):
    candidature = _candidature(
        [_evt("2026-09-05", "candidature_envoyee"), _evt("2026-10-03", "relance")],
        disponible=False,
    )
    candidature["depubliee_le"] = "2026-09-20"
    contenu = contenu_dossier(
        "REF", candidature, aujourd_hui=date(2026, 10, 4), archive_presente=False
    )
    assert [t.libelle for t in contenu.tampons] == [
        "Envoyée",
        "Offre dépubliée",
        "Relance",
    ]
    assert [t.courant for t in contenu.tampons] == [False, False, True]


def test_contenu_dossier_clos_depublie_n_est_pas_a_signaler() -> None:
    candidature = _candidature([_evt("2026-09-26", "refus")], disponible=False)
    candidature["depubliee_le"] = "2026-10-01"
    contenu = contenu_dossier(
        "REF", candidature, aujourd_hui=date(2026, 10, 4), archive_presente=False
    )
    assert contenu.depublication_a_signaler is False
    assert contenu.tampons[-1].information is True


def test_contenu_dossier_en_ligne_n_a_pas_de_tampon_de_depublication() -> None:
    contenu = contenu_dossier(
        "REF",
        _candidature([_evt("2026-09-26", "relance")]),
        aujourd_hui=date(2026, 10, 4),
        archive_presente=False,
    )
    assert contenu.depubliee_le == ""
    assert all(not t.information for t in contenu.tampons)
