"""Tests du filtre de grade (client, cross-source) — src/filtres.py."""

from src.filtres import CORPS_GRADES, GRADES, filtrer_par_grades
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


def test_attache_ne_matche_pas_attache_principal() -> None:
    assert not GRADES["Attaché"].search("Attaché principal - Chef de service RH")


def test_attache_ne_matche_pas_attache_hors_classe() -> None:
    assert not GRADES["Attaché"].search("Un poste d'Attaché hors classe (H/F)")


def test_attache_matche_grade_de_base() -> None:
    assert GRADES["Attaché"].search("Attaché - Gestionnaire RH (H/F)")


def test_attache_principal_matche_toutes_versants() -> None:
    # Les intitulés longs par versant embarquent le nom court en sous-chaîne.
    assert GRADES["Attaché principal"].search(
        "Attaché principal d'administration de l'État"
    )
    assert GRADES["Attaché principal"].search(
        "Attaché principal d'administration hospitalière"
    )
    assert GRADES["Attaché principal"].search("Attaché principal territorial")


def test_attache_hors_classe_matche() -> None:
    assert GRADES["Attaché hors classe"].search("Attaché hors classe territorial")


def test_filtrer_par_grades_liste_vide_ne_filtre_rien() -> None:
    offres = [_offre("Attaché principal"), _offre("Technicien informatique")]
    assert filtrer_par_grades(offres, []) == offres


def test_filtrer_par_grades_un_seul_grade() -> None:
    offres = [
        _offre("Attaché principal - Chef de service"),
        _offre("Attaché - Gestionnaire"),
        _offre("Technicien informatique"),
    ]
    filtrees = filtrer_par_grades(offres, ["Attaché principal"])
    assert [o["titre"] for o in filtrees] == ["Attaché principal - Chef de service"]


def test_filtrer_par_grades_plusieurs_grades_en_or() -> None:
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


def test_filtrer_par_grades_ignore_cle_inconnue() -> None:
    offres = [_offre("Attaché principal")]
    assert filtrer_par_grades(offres, ["Grade inexistant"]) == []


# --- Adjoint administratif — variantes réelles vérifiées sur le site ---


def test_adjoint_administratif_matche_grade_de_base() -> None:
    assert GRADES["Adjoint administratif"].search(
        "Adjoint administratif H/F 50% au sein du Secrétariat"
    )
    assert GRADES["Adjoint administratif"].search(
        "ADJOINT ADMINISTRATIF - FRAIS DE JUSTICE OU RH"
    )


def test_adjoint_administratif_ne_matche_pas_principal() -> None:
    assert not GRADES["Adjoint administratif"].search(
        "Adjoint administratif principal 2ème classe"
    )
    # Cas piège corrigé : le "s" optionnel du pluriel ne doit pas
    # permettre de contourner la négation.
    assert not GRADES["Adjoint administratif"].search(
        "épreuves d'adjoints administratifs principal 2è classe"
    )


def test_adjoint_administratif_principal_2e_classe_matche_variantes_orthographiques() -> (
    None
):
    grade = GRADES["Adjoint administratif principal de 2e classe"]
    assert grade.search("Adjoint administratif principal 2ème classe")
    assert grade.search("Adjoint administratif principal de 2ème classe")
    assert grade.search("Adjoint Administratif principal de 2éme classe")
    assert grade.search("adjoints administratifs principal 2è classe")


def test_adjoint_administratif_principal_1re_classe_matche_variantes_orthographiques() -> (
    None
):
    grade = GRADES["Adjoint administratif principal de 1re classe"]
    assert grade.search("Adjoint administratif principal de 1re classe")
    assert grade.search("Adjoint administratif principal de 1ère classe")


def test_corps_grades_regroupe_les_memes_grades_que_grades_a_plat() -> None:
    """CORPS_GRADES (structure pour l'UI) et GRADES (lookup à plat pour le
    filtrage) doivent rester synchronisés."""
    grades_via_corps = {
        grade for grades_du_corps in CORPS_GRADES.values() for grade in grades_du_corps
    }
    assert grades_via_corps == set(GRADES.keys())
