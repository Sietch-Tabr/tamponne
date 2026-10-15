"""Tests du filtrage côté client de Passerelles/MEF (pas de réseau)."""

from datetime import date

import pytest

from src.sources import passerellesmef
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.passerellesmef.filtrage import (
    date_dans_fenetre,
    fiche_correspond,
    libelle_lieu,
    lieu_correspond,
    numero_depuis_fiche,
    organisations_de_bercy,
)
from src.types import DetailOffre, FiltresRecherche, Offre


def _fiche(**champs: str) -> DetailOffre:
    secteur = champs.pop("secteur", "")
    return {
        **DETAIL_VIDE,
        "secteur": secteur,
        "page_html": "<html>",
        "sections_complementaires": {
            cle.replace("_", " "): valeur for cle, valeur in champs.items()
        },
    }


def test_lieu_correspond_departement_region_et_inconnu() -> None:
    assert lieu_correspond("75", ["Paris"])
    assert not lieu_correspond("52", ["Paris", "Hauts-de-Seine"])
    assert lieu_correspond("93", ["Ile-de-France"])
    assert lieu_correspond(None, ["Paris"])


def test_numero_depuis_fiche_prefere_la_localisation_puis_le_code_postal() -> None:
    avec_numero = _fiche(
        **{"Localisation_du_poste": "France, Pays de Loire, Loire Atlantique (44)"}
    )
    assert numero_depuis_fiche(avec_numero) == "44"
    region_seule = _fiche(
        **{
            "Localisation_du_poste": "France, Ile-de-France",
            "Lieu_d'affectation": "86-92 Allée de Bercy - 75012 PARIS",
        }
    )
    assert numero_depuis_fiche(region_seule) == "75"
    assert numero_depuis_fiche(_fiche()) is None


def test_libelle_lieu() -> None:
    assert libelle_lieu("75") == "Paris (75)"
    assert libelle_lieu("21") == ""


@pytest.mark.parametrize(
    ("texte", "cle", "attendu"),
    [
        ("14/10/2026", "Dernières 48 heures", True),
        ("10/10/2026", "Dernières 48 heures", False),
        ("10/10/2026", "7 derniers jours", True),
        ("illisible", "7 derniers jours", True),
        ("01/01/2020", "", True),
    ],
)
def test_date_dans_fenetre(texte: str, cle: str, attendu: bool) -> None:
    assert date_dans_fenetre(texte, cle, date(2026, 10, 15)) is attendu


def test_fiche_correspond_categorie_et_domaine() -> None:
    fiche = _fiche(Catégorie="Catégorie A (cadre)", secteur="Numérique - Développeuse")
    assert fiche_correspond(fiche, {"categories": ["A"], "domaines": ["Numérique"]})
    assert not fiche_correspond(fiche, {"categories": ["B"]})
    assert not fiche_correspond(fiche, {"domaines": ["Finances Publiques"]})


def test_fiche_correspond_domaine_ecrit_differemment_sur_les_deux_sites() -> None:
    fiche = _fiche(secteur="Intervention technique et logistique - Imprimeur")
    assert fiche_correspond(
        fiche, {"domaines": ["Interventions techniques et logistiques"]}
    )


def test_fiche_correspond_organisation_management_et_teletravail() -> None:
    fiche = _fiche(
        Directions_et_Services="Direction générale des finances publiques (DGFiP)",
        Management="Non",
        **{"Télétravail_possible": "Oui"},
    )
    bercy = "Ministères Economiques et Financiers - DGFiP"
    assert fiche_correspond(fiche, {"organisations": [bercy]})
    assert not fiche_correspond(
        fiche, {"organisations": ["Ministères Economiques et Financiers - Douane"]}
    )
    assert not fiche_correspond(fiche, {"management": True})
    assert fiche_correspond(fiche, {"teletravail": True})


def test_fiche_illisible_est_gardee() -> None:
    assert fiche_correspond(DETAIL_VIDE, {"categories": ["A"]})


def test_organisations_de_bercy() -> None:
    assert organisations_de_bercy(
        ["Ministères Economiques et Financiers - DGFiP", "Mairie de Paris - X"]
    ) == ["DGFiP"]


# --- rechercher : filtrage branché sur la source ---


def _offre(reference: str, localisation: str, date_offre: str = "") -> Offre:
    return {
        "titre": f"Offre {reference}",
        "url": f"https://exemple.test/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": "",
        "localisation": localisation,
        "versant": "",
        "date": date_offre,
        "source": "MEF",
    }


@pytest.fixture
def _site(monkeypatch: pytest.MonkeyPatch) -> dict[str, DetailOffre]:
    """Liste de trois offres et leurs fiches ; renvoie le dictionnaire des
    fiches, à compléter par chaque test."""
    fiches: dict[str, DetailOffre] = {}
    offres = [
        _offre("paris", "Paris (75)"),
        _offre("marne", "Haute-Marne (52)"),
        _offre("sans-lieu", ""),
    ]
    monkeypatch.setattr(passerellesmef.time, "sleep", lambda _s: None)
    monkeypatch.setattr(passerellesmef, "nouvelle_session", lambda: None)
    monkeypatch.setattr(
        passerellesmef,
        "obtenir_page_recherche",
        lambda _o, _u: {"html": "", "title": ""},
    )
    monkeypatch.setattr(passerellesmef, "extraire_offres", lambda _h: list(offres))
    monkeypatch.setattr(
        passerellesmef,
        "recuperer_detail_offre",
        lambda url: fiches.get(url.rsplit("/", 1)[1], DETAIL_VIDE),
    )
    return fiches


def _references(filtres: FiltresRecherche) -> list[str]:
    offres, _, _ = passerellesmef.PasserellesMef().rechercher(filtres)
    return [o["reference"] for o in offres]


def test_rechercher_sans_critere_local_ne_lit_aucune_fiche(
    _site: dict[str, DetailOffre],
) -> None:
    assert _references({}) == ["paris", "marne", "sans-lieu"]


def test_rechercher_localisation_lit_le_lieu_manquant_sur_la_fiche(
    _site: dict[str, DetailOffre],
) -> None:
    _site["sans-lieu"] = _fiche(
        **{"Lieu_d'affectation": "86-92 Allée de Bercy - 75012 PARIS"}
    )
    offres, _, _ = passerellesmef.PasserellesMef().rechercher(
        {"localisations": ["Paris"]}
    )
    assert [o["reference"] for o in offres] == ["paris", "sans-lieu"]
    assert offres[1]["localisation"] == "Paris (75)"


def test_rechercher_localisation_ecarte_une_fiche_d_un_autre_departement(
    _site: dict[str, DetailOffre],
) -> None:
    _site["sans-lieu"] = _fiche(**{"Localisation_du_poste": "France, Somme (80)"})
    assert _references({"localisations": ["Paris"]}) == ["paris"]


def test_rechercher_categorie_filtre_sur_la_fiche(
    _site: dict[str, DetailOffre],
) -> None:
    _site["paris"] = _fiche(Catégorie="Catégorie A (cadre)")
    _site["marne"] = _fiche(Catégorie="Catégorie B (profession intermédiaire)")
    _site["sans-lieu"] = _fiche(Catégorie="Catégorie B (profession intermédiaire)")
    assert _references({"categories": ["A"]}) == ["paris"]


def test_rechercher_fiche_illisible_est_gardee(
    _site: dict[str, DetailOffre],
) -> None:
    assert _references({"categories": ["A"], "localisations": ["Paris"]}) == [
        "paris",
        "sans-lieu",
    ]


def test_rechercher_organisation_hors_bercy_ne_renvoie_rien(
    _site: dict[str, DetailOffre],
) -> None:
    assert _references({"organisations": ["Mairie de Paris - Crédit municipal"]}) == []
