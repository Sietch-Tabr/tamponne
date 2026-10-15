"""Tests des correspondances de filtres emploi-territorial.fr (pas de réseau)."""

from src.filtres import LOCALISATIONS
from src.sources.emploiterritorial.api import construire_url_recherche
from src.sources.emploiterritorial.filtres import CATEGORIES, DEPARTEMENTS


def test_departements_couvre_uniquement_les_departements_pas_les_regions() -> None:
    assert DEPARTEMENTS["Hérault"] == "034"
    assert DEPARTEMENTS["Belfort"] == "090"
    assert DEPARTEMENTS["Réunion"] == "974"
    assert DEPARTEMENTS["Alpes Hte Provence"] == "004"
    assert "Occitanie" not in DEPARTEMENTS
    assert "DOM" not in DEPARTEMENTS


def test_departements_toutes_les_cles_existent_dans_localisations() -> None:
    assert set(DEPARTEMENTS).issubset(set(LOCALISATIONS))


def test_categories_collapse_les_deux_variantes_a_plus() -> None:
    assert CATEGORIES["A+ (direction)"] == "A+"
    assert CATEGORIES["A+ (autres emplois fonctionnels)"] == "A+"


def test_construire_url_recherche_avec_departement() -> None:
    url = construire_url_recherche(departements=["034"])
    assert "search_offre_form%5Bsearchdept%5D%5B%5D=034" in url


def test_construire_url_recherche_avec_categorie() -> None:
    url = construire_url_recherche(categories=["A"])
    assert "search_offre_form%5Bsearchcat%5D%5B%5D=A" in url


def test_construire_url_recherche_avec_experience() -> None:
    url = construire_url_recherche(experience="2")
    assert "search_offre_form%5Bexperience%5D%5B%5D=2" in url


def test_construire_url_recherche_management_absent_si_false() -> None:
    url = construire_url_recherche(management=False)
    assert "management" not in url


def test_construire_url_recherche_management_present_si_true() -> None:
    url = construire_url_recherche(management=True)
    assert "search_offre_form%5Bmanagement%5D=2" in url


def test_construire_url_recherche_teletravail_present_si_true() -> None:
    url = construire_url_recherche(teletravail=True)
    assert "search_offre_form%5Bteletravail%5D=2" in url


def test_construire_url_recherche_type_contrat() -> None:
    url = construire_url_recherche(type_contrat="99")
    assert "search_offre_form%5Bsearchtypecontrat%5D%5B%5D=99" in url


def test_construire_url_recherche_combine_tous_les_filtres() -> None:
    url = construire_url_recherche(
        query="rh",
        categories=["A"],
        departements=["034"],
        experience="2",
        management=True,
        teletravail=True,
        type_contrat="99",
    )
    for segment in [
        "search_offre_form%5Badvsearch%5D=rh",
        "search_offre_form%5Bsearchdept%5D%5B%5D=034",
        "search_offre_form%5Bsearchcat%5D%5B%5D=A",
        "search_offre_form%5Bexperience%5D%5B%5D=2",
        "search_offre_form%5Bmanagement%5D=2",
        "search_offre_form%5Bteletravail%5D=2",
        "search_offre_form%5Bsearchtypecontrat%5D%5B%5D=99",
    ]:
        assert segment in url


def test_construire_url_recherche_sans_filtre_retourne_url_nue() -> None:
    from src.sources.emploiterritorial.api import URL_RECHERCHE

    assert construire_url_recherche() == URL_RECHERCHE
