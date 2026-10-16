"""Tests du filtre de grade (client, cross-source) — src/filtres.py."""

from datetime import date

import pytest

from src.filtres import (
    CORPS_GRADES,
    GRADES,
    LOCALISATIONS,
    NUMEROS_DEPARTEMENTS,
    NUMEROS_REGIONS,
    RE_GRADE_SUPERIEUR,
    cle_categorie,
    date_dans_fenetre,
    filtrer_par_grades,
    libelle_lieu,
    lieu_correspond,
    numero_departement_texte,
    numeros_departements,
)
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


# --- départements, régions, catégories ---


def test_tous_les_departements_de_localisations_ont_un_numero() -> None:
    sans_numero = set(LOCALISATIONS) - set(NUMEROS_DEPARTEMENTS)
    assert sans_numero == set(NUMEROS_REGIONS)


def test_numeros_departements_departement_et_region() -> None:
    assert numeros_departements(["Paris", "Hauts-de-Seine"]) == {"75", "92"}
    assert numeros_departements(["Ile-de-France"]) == {
        "75", "77", "78", "91", "92", "93", "94", "95",
    }  # fmt: skip
    assert numeros_departements(["Inconnu"]) == set()


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ("Paris (75)", "75"),
        ("Corrèze (19 )", "19"),
        ("Haute Corse (2b)", "2B"),
        ("Réunion (974)", "974"),
        ("86-92 Allée de Bercy - 75012 PARIS", "75"),
        ("10 rue Auguste Blanqui 93186 Montreuil Cedex", "93"),
        ("20190 Ajaccio", "2A"),
        ("20600 Bastia", "2B"),
        ("97400 Saint-Denis", "974"),
        ("France, Ile-de-France", None),
        ("", None),
    ],
)
def test_numero_departement_texte(texte: str, attendu: str | None) -> None:
    assert numero_departement_texte(texte) == attendu


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ("Catégorie A (cadre)", "A"),
        ("Catégorie B (profession intermédiaire)", "B"),
        ("Catégorie C (employé)", "C"),
        (
            "Catégorie A+ (Encadrement Supérieur - Autres emplois fonctionnels)",
            "A+ (autres emplois fonctionnels)",
        ),
        ("Catégorie A+ (Direction)", "A+ (direction)"),
        ("Contractuel", None),
    ],
)
def test_cle_categorie(texte: str, attendu: str | None) -> None:
    assert cle_categorie(texte) == attendu


@pytest.mark.parametrize(
    "titre",
    ["IP/AP - Chef de secteur", "IP/IDIV HC/AP - Responsable", "IPFIP / IDIV HC"],
)
def test_grade_superieur_reconnait_ip_suivi_d_une_barre(titre: str) -> None:
    assert RE_GRADE_SUPERIEUR.match(titre)


def test_grade_superieur_ne_prend_pas_ifip_ni_ipsum() -> None:
    assert not RE_GRADE_SUPERIEUR.match("IFIP/ATT - Développeur")
    assert not RE_GRADE_SUPERIEUR.match("Ipsum lorem")


def test_lieu_correspond_departement_region_et_inconnu() -> None:
    assert lieu_correspond("75", ["Paris"])
    assert not lieu_correspond("52", ["Paris", "Hauts-de-Seine"])
    assert lieu_correspond("93", ["Ile-de-France"])
    assert lieu_correspond("", ["Paris"])


def test_libelle_lieu() -> None:
    assert libelle_lieu("75") == "Paris (75)"
    assert libelle_lieu("21") == ""


@pytest.mark.parametrize(
    ("texte", "fenetre", "attendu"),
    [
        ("14/10/2026", "Dernières 48 heures", True),
        ("10/10/2026", "Dernières 48 heures", False),
        ("10/10/2026", "7 derniers jours", True),
        ("illisible", "7 derniers jours", True),
        ("01/01/2020", "", True),
    ],
)
def test_date_dans_fenetre(texte: str, fenetre: str, attendu: bool) -> None:
    assert date_dans_fenetre(texte, fenetre, date(2026, 10, 15)) is attendu
