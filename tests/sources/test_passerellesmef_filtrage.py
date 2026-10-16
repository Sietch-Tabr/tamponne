"""Tests du filtrage côté client de Passerelles/MEF (pas de réseau)."""

import pytest

from src.sources import passerellesmef
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.passerellesmef.filtrage import (
    extraire_fiche,
    fiche_correspond,
    organisations_de_bercy,
)
from src.types import DetailOffre, FicheFiltrage, FiltresRecherche, Offre

BERCY = "Ministères Economiques et Financiers"


def _detail(secteur: str = "", experience: str = "", **champs: str) -> DetailOffre:
    return {
        **DETAIL_VIDE,
        "secteur": secteur,
        "experience_requise": experience,
        "page_html": "<html>",
        "sections_complementaires": {
            cle.replace("_", " "): valeur for cle, valeur in champs.items()
        },
    }


def _fiche(**modifs: object) -> FicheFiltrage:
    base: FicheFiltrage = {
        "numero": "75",
        "categorie": "A",
        "secteur": "Numérique - Développeuse",
        "direction": "Direction générale des finances publiques (DGFiP)",
        "experience": "Confirmé",
        "management": False,
        "teletravail": True,
    }
    return {**base, **modifs}  # type: ignore[typeddict-item]


# --- extraire_fiche ---


def test_extraire_fiche_prefere_la_localisation_puis_le_code_postal() -> None:
    avec_numero = _detail(
        **{"Localisation_du_poste": "France, Pays de Loire, Loire Atlantique (44)"}
    )
    extrait = extraire_fiche(avec_numero)
    assert extrait is not None
    assert extrait["numero"] == "44"
    region_seule = _detail(
        **{
            "Localisation_du_poste": "France, Ile-de-France",
            "Lieu_d'affectation": "86-92 Allée de Bercy - 75012 PARIS",
        }
    )
    extrait = extraire_fiche(region_seule)
    assert extrait is not None
    assert extrait["numero"] == "75"


def test_extraire_fiche_lit_categorie_domaine_et_options() -> None:
    fiche = extraire_fiche(
        _detail(
            "Numérique - Développeuse / Développeur",
            "Confirmé",
            Catégorie="Catégorie A (cadre)",
            Directions_et_Services="DGFiP",
            Management="Oui",
            **{"Télétravail_possible": "Non"},
        )
    )
    assert fiche == {
        "numero": "",
        "categorie": "A",
        "secteur": "Numérique - Développeuse / Développeur",
        "direction": "DGFiP",
        "experience": "Confirmé",
        "management": True,
        "teletravail": False,
    }


def test_extraire_fiche_illisible_retourne_none() -> None:
    assert extraire_fiche(DETAIL_VIDE) is None


# --- fiche_correspond ---


def test_fiche_correspond_categorie_et_domaine() -> None:
    assert fiche_correspond(_fiche(), {"categories": ["A"], "domaines": ["Numérique"]})
    assert not fiche_correspond(_fiche(), {"categories": ["B"]})
    assert not fiche_correspond(_fiche(), {"domaines": ["Finances Publiques"]})


def test_fiche_correspond_domaine_ecrit_differemment_sur_les_deux_sites() -> None:
    fiche = _fiche(secteur="Intervention technique et logistique - Imprimeur")
    assert fiche_correspond(
        fiche, {"domaines": ["Interventions techniques et logistiques"]}
    )


def test_fiche_correspond_organisation() -> None:
    assert fiche_correspond(_fiche(), {"organisations": [f"{BERCY} - DGFiP"]})
    assert not fiche_correspond(_fiche(), {"organisations": [f"{BERCY} - Douane"]})


def test_fiche_correspond_experience_management_et_teletravail() -> None:
    assert fiche_correspond(_fiche(), {"experience": "Confirmé"})
    assert not fiche_correspond(_fiche(), {"experience": "Expert"})
    assert not fiche_correspond(_fiche(), {"management": True})
    assert fiche_correspond(_fiche(), {"teletravail": True})
    assert not fiche_correspond(_fiche(teletravail=False), {"teletravail": True})


def test_fiche_correspond_information_absente_n_ecarte_pas() -> None:
    vide = _fiche(categorie="", secteur="", direction="", experience="")
    filtres: FiltresRecherche = {
        "categories": ["A"],
        "domaines": ["Numérique"],
        "organisations": [f"{BERCY} - DGFiP"],
        "experience": "Expert",
    }
    assert fiche_correspond(vide, filtres)


def test_organisations_de_bercy() -> None:
    assert organisations_de_bercy([f"{BERCY} - DGFiP", "Mairie de Paris - X"]) == [
        "DGFiP"
    ]


# --- rechercher : filtrage branché sur la source ---


def _offre(reference: str, localisation: str) -> Offre:
    return {
        "titre": f"Offre {reference}",
        "url": f"https://exemple.test/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": "",
        "localisation": localisation,
        "versant": "",
        "date": "",
        "source": "MEF",
    }


class _CacheMemoire:
    def __init__(self) -> None:
        self.fiches: dict[str, FicheFiltrage] = {}

    def lire(self, url: str) -> FicheFiltrage | None:
        return self.fiches.get(url)

    def ecrire(self, url: str, fiche: FicheFiltrage) -> None:
        self.fiches[url] = fiche


@pytest.fixture
def _site(monkeypatch: pytest.MonkeyPatch) -> dict[str, DetailOffre]:
    """Liste de trois offres ; renvoie le dictionnaire de leurs fiches, à
    compléter par chaque test."""
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
    monkeypatch.setattr(
        passerellesmef, "extraire_offres", lambda _h: [dict(o) for o in offres]
    )
    monkeypatch.setattr(
        passerellesmef,
        "recuperer_detail_offre",
        lambda url: fiches.get(url.rsplit("/", 1)[1], DETAIL_VIDE),
    )
    return fiches


def _references(
    filtres: FiltresRecherche, cache: _CacheMemoire | None = None
) -> list[str]:
    source = passerellesmef.PasserellesMef(cache)
    offres, _, _ = source.rechercher(filtres)
    return [o["reference"] for o in offres]


def test_rechercher_sans_critere_local_ne_lit_aucune_fiche(
    _site: dict[str, DetailOffre],
) -> None:
    assert _references({}) == ["paris", "marne", "sans-lieu"]


def test_rechercher_localisation_lit_le_lieu_manquant_sur_la_fiche(
    _site: dict[str, DetailOffre],
) -> None:
    _site["sans-lieu"] = _detail(
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
    _site["sans-lieu"] = _detail(**{"Localisation_du_poste": "France, Somme (80)"})
    assert _references({"localisations": ["Paris"]}) == ["paris"]


def test_rechercher_categorie_filtre_sur_la_fiche(
    _site: dict[str, DetailOffre],
) -> None:
    _site["paris"] = _detail(Catégorie="Catégorie A (cadre)")
    _site["marne"] = _detail(Catégorie="Catégorie B (profession intermédiaire)")
    _site["sans-lieu"] = _detail(Catégorie="Catégorie B (profession intermédiaire)")
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


def test_rechercher_ne_relit_pas_une_fiche_en_cache(
    _site: dict[str, DetailOffre], monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = _CacheMemoire()
    _site["paris"] = _detail(Catégorie="Catégorie A (cadre)")
    _site["marne"] = _detail(Catégorie="Catégorie B (profession intermédiaire)")
    _site["sans-lieu"] = _detail(Catégorie="Catégorie A (cadre)")
    assert _references({"categories": ["A"]}, cache) == ["paris", "sans-lieu"]

    lectures: list[str] = []

    def _detail_espion(url: str) -> DetailOffre:
        lectures.append(url)
        return DETAIL_VIDE

    monkeypatch.setattr(passerellesmef, "recuperer_detail_offre", _detail_espion)
    assert _references({"categories": ["A"]}, cache) == ["paris", "sans-lieu"]
    assert lectures == []
