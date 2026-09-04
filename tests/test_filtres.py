"""Tests du filtre de grade (client, cross-source) — src/filtres.py."""

from src.filtres import GRADES, filtrer_par_grades
from src.types import Offre


def _offre(titre: str) -> Offre:
    return {
        "titre": titre,
        "url": "",
        "reference": "",
        "domaine": "",
        "employeur": "",
        "localisation": "",
        "versant": "",
        "date": "",
        "source": "",
    }


def test_attache_ne_matche_pas_attache_principal():
    assert not GRADES["Attaché"].search("Attaché principal - Chef de service RH")


def test_attache_ne_matche_pas_attache_hors_classe():
    assert not GRADES["Attaché"].search("Un poste d'Attaché hors classe (H/F)")


def test_attache_matche_grade_de_base():
    assert GRADES["Attaché"].search("Attaché - Gestionnaire RH (H/F)")


def test_attache_principal_matche_toutes_versants():
    # Les intitulés longs par versant embarquent le nom court en sous-chaîne.
    assert GRADES["Attaché principal"].search(
        "Attaché principal d'administration de l'État"
    )
    assert GRADES["Attaché principal"].search(
        "Attaché principal d'administration hospitalière"
    )
    assert GRADES["Attaché principal"].search("Attaché principal territorial")


def test_attache_hors_classe_matche():
    assert GRADES["Attaché hors classe"].search("Attaché hors classe territorial")


def test_filtrer_par_grades_liste_vide_ne_filtre_rien():
    offres = [_offre("Attaché principal"), _offre("Technicien informatique")]
    assert filtrer_par_grades(offres, []) == offres


def test_filtrer_par_grades_un_seul_grade():
    offres = [
        _offre("Attaché principal - Chef de service"),
        _offre("Attaché - Gestionnaire"),
        _offre("Technicien informatique"),
    ]
    filtrees = filtrer_par_grades(offres, ["Attaché principal"])
    assert [o["titre"] for o in filtrees] == ["Attaché principal - Chef de service"]


def test_filtrer_par_grades_plusieurs_grades_en_or():
    offres = [
        _offre("Attaché principal - Chef de service"),
        _offre("Attaché hors classe - Directeur adjoint"),
        _offre("Attaché - Gestionnaire"),
    ]
    filtrees = filtrer_par_grades(offres, ["Attaché principal", "Attaché hors classe"])
    assert [o["titre"] for o in filtrees] == [
        "Attaché principal - Chef de service",
        "Attaché hors classe - Directeur adjoint",
    ]


def test_filtrer_par_grades_ignore_cle_inconnue():
    offres = [_offre("Attaché principal")]
    assert filtrer_par_grades(offres, ["Grade inexistant"]) == []
