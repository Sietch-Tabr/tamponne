"""Tests du formulaire de recherche de Passerelles/MEF (pas de réseau)."""

import pytest
from unittest.mock import Mock

from src.sources import passerellesmef
from src.sources.choisirleservicepublic.extraction import DETAIL_VIDE
from src.sources.passerellesmef.formulaire import (
    analyser_formulaire,
    construire_recherche,
)
from src.types import DetailOffre, FiltresRecherche, Offre, PageAPI

BERCY = "Ministères Economiques et Financiers"
P = "ctl00$ctl00$moteurRapideOffre$"


def _case(nom: str, valeur: str, libelle: str, parents: int = 1) -> str:
    ids = " ".join(f"i{n}" for n in range(parents))
    return (
        f'<input aria-label="{libelle}" id="c{valeur}" aria-labelledby="{ids}" '
        f'type="checkbox" value="{valeur}" name="{P}{nom}" />'
    )


FORMULAIRE = f"""
<form name="aspnetForm" method="post" id="aspnetForm">
<input type="hidden" name="__VIEWSTATE" value="vs" />
<input type="hidden" name="__EVENTVALIDATION" value="ev" />
<input name="{P}ctl00$OfferCriteria_Keywords" type="text" />
<select name="{P}ctl00$Categorie">
<option value="0">Sélection</option>
<option value="3754">Catégorie A+ (Encadrement Supérieur - Emplois de Direction) (12)</option>
<option value="2309">Catégorie A+ (Encadrement Supérieur - Autres emplois fonctionnels) (93)</option>
<option value="2310">Catégorie A (cadre) (501)</option>
<option value="2311">Catégorie B (profession intermédiaire) (106)</option>
</select>
{_case("ctl01$GeographicalAreaCollection$79", "79", "France (737)")}
{_case("ctl01$GeographicalAreaCollection$208", "208", "Ile-de-France (493)", 2)}
{_case("ctl01$GeographicalAreaCollection$205", "205", "DROM (4)", 2)}
{_case("ctl01$GeographicalAreaCollection$217", "217", "Provence-Cote d&#39;Azur (23)", 2)}
{_case("ctl02$PrimaryProfile$3043", "3043", "Numérique (147)")}
{_case("ctl02$PrimaryProfile$3059", "3059", "Administratrice d&#39;outils (20)", 2)}
{_case("ctl02$PrimaryProfile$3044", "3044", "Organisation, Contrôle et Evaluation (73)")}
{_case("ctl02$Entity$101", "101", "DGFIP (320)")}
{_case("ctl02$Entity$20", "20", "Direction générale des entreprises (DGE) (75)")}
{_case("ctl02$Entity$106", "106", "DGE - DIRECTION DES GRANDES ENTREPRISES (1)")}
<input type="submit" name="{P}BT_recherche" value="Lancer ma recherche" />
</form>
"""

DGFIP = f"{BERCY} - Direction générale des Finances publiques (DGFiP)"


def test_analyser_formulaire_lit_les_champs_de_la_page() -> None:
    formulaire = analyser_formulaire(FORMULAIRE)
    assert formulaire.exploitable()
    assert formulaire.caches == {"__VIEWSTATE": "vs", "__EVENTVALIDATION": "ev"}
    assert formulaire.bouton == (f"{P}BT_recherche", "Lancer ma recherche")
    assert formulaire.mots_cles == f"{P}ctl00$OfferCriteria_Keywords"
    assert formulaire.categories["A"] == "2310"
    assert formulaire.categories["A+ (direction)"] == "3754"
    assert formulaire.categories["A+ (autres emplois fonctionnels)"] == "2309"
    assert [c.libelle for c in formulaire.domaines] == [
        "Numérique",
        "Organisation, Contrôle et Evaluation",
    ]
    assert "Provence-Cote d'Azur" in [c.libelle for c in formulaire.regions]


def test_analyser_formulaire_page_sans_formulaire_est_inexploitable() -> None:
    assert not analyser_formulaire(
        "<html><body>Maintenance</body></html>"
    ).exploitable()


def _champs(
    filtres: FiltresRecherche,
) -> tuple[dict[str, str], frozenset[str]]:
    sous = [
        o.removeprefix(f"{BERCY} - ")
        for o in filtres.get("organisations", [])
        if o.startswith(f"{BERCY} - ")
    ]
    return construire_recherche(analyser_formulaire(FORMULAIRE), filtres, sous)


def test_construire_recherche_demande_au_site_ce_qu_il_sait_filtrer() -> None:
    champs, appliques = _champs(
        {
            "categories": ["A"],
            "domaines": ["Numérique"],
            "organisations": [DGFIP],
            "localisations": ["Paris", "Seine Saint-Denis"],
            "query": "réseau",
        }
    )
    assert champs == {
        f"{P}ctl00$Categorie": "2310",
        f"{P}ctl02$PrimaryProfile$3043": "3043",
        f"{P}ctl02$Entity$101": "101",
        f"{P}ctl01$GeographicalAreaCollection$208": "208",
        f"{P}ctl00$OfferCriteria_Keywords": "réseau",
    }
    assert appliques == {"categories", "domaines", "organisations"}


def test_construire_recherche_region_seule_ne_dispense_pas_du_departement() -> None:
    champs, appliques = _champs({"localisations": ["Paris"]})
    assert list(champs.values()) == ["208"]
    assert appliques == frozenset()


def test_construire_recherche_region_hors_table_et_alias() -> None:
    champs, _ = _champs({"localisations": ["Var", "Guadeloupe"]})
    assert sorted(champs.values()) == ["205", "217"]


def test_construire_recherche_plusieurs_categories_restent_cote_client() -> None:
    champs, appliques = _champs({"categories": ["A", "B"]})
    assert champs == {}
    assert appliques == frozenset()


def test_construire_recherche_domaine_inconnu_du_site_reste_cote_client() -> None:
    champs, appliques = _champs({"domaines": ["Numérique", "Défense"]})
    assert champs == {}
    assert appliques == frozenset()


def test_construire_recherche_organisation_ambigue_ou_inconnue_reste_cote_client() -> (
    None
):
    dge = f"{BERCY} - Direction générale des entreprises (DGE)"
    assert _champs({"organisations": [dge]})[1] == {"organisations"}
    inconnue = f"{BERCY} - Direction imaginaire (DI)"
    assert _champs({"organisations": [inconnue]}) == ({}, frozenset())


def test_construire_recherche_departement_sans_region_connue_n_est_pas_demande() -> (
    None
):
    champs, _ = _champs({"localisations": ["Nouvelle Calédonie"]})
    assert champs == {}


# --- rechercher : le site filtre, les fiches ne sont lues que pour le reste ---


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


@pytest.fixture
def _site(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[object]]:
    """Site simulé ; renvoie le journal de ses échanges."""
    echanges: dict[str, list[object]] = {"envois": [], "fiches": [], "pages": []}
    monkeypatch.setattr(passerellesmef.time, "sleep", Mock(return_value=None))
    monkeypatch.setattr(passerellesmef, "nouvelle_session", lambda: None)
    monkeypatch.setattr(
        passerellesmef, "obtenir_formulaire", Mock(return_value=FORMULAIRE)
    )

    def envoyer(_: object, champs: dict[str, str]) -> PageAPI:
        echanges["envois"].append(champs)
        return {"html": "p1", "title": "(30 offres, page 1) / Catégorie : A"}

    def page(_: object, url: str) -> PageAPI:
        echanges["pages"].append(url)
        numero = url.rsplit("page=", 1)[1] if "page=" in url else "1"
        return {"html": f"p{numero}", "title": "(30 offres, page 1)"}

    def offres_de(html: str) -> list[Offre]:
        return [_offre(f"{html}-{n}", "Paris (75)") for n in (1, 2)]

    def fiche(url: str) -> DetailOffre:
        echanges["fiches"].append(url)
        return DETAIL_VIDE

    monkeypatch.setattr(passerellesmef, "envoyer_recherche", envoyer)
    monkeypatch.setattr(passerellesmef, "obtenir_page_recherche", page)
    monkeypatch.setattr(passerellesmef, "extraire_offres", offres_de)
    monkeypatch.setattr(passerellesmef, "recuperer_detail_offre", fiche)
    return echanges


def test_rechercher_envoie_le_formulaire_et_lit_les_pages_de_resultats(
    _site: dict[str, list[object]],
) -> None:
    offres, nb_pages, _ = passerellesmef.PasserellesMef().rechercher(
        {"categories": ["A"], "localisations": ["Paris"]}
    )
    assert nb_pages == 2
    assert [o["reference"] for o in offres] == ["p1-1", "p1-2", "p2-1", "p2-2"]
    (envoi,) = _site["envois"]
    assert isinstance(envoi, dict)
    assert envoi["__VIEWSTATE"] == "vs"
    assert envoi[f"{P}ctl00$Categorie"] == "2310"
    assert envoi[f"{P}BT_recherche"] == "Lancer ma recherche"
    assert _site["pages"] == [
        "https://www.passerelles.economie.gouv.fr/offre-de-emploi/liste-offres.aspx?LCID=1036&page=2"
    ]


def test_rechercher_ne_lit_pas_les_fiches_d_un_critere_que_le_site_a_applique(
    _site: dict[str, list[object]],
) -> None:
    passerellesmef.PasserellesMef().rechercher(
        {"categories": ["A"], "domaines": ["Numérique"]}
    )
    assert _site["fiches"] == []


def test_rechercher_lit_les_fiches_des_criteres_que_le_site_ne_filtre_pas(
    _site: dict[str, list[object]],
) -> None:
    passerellesmef.PasserellesMef().rechercher(
        {"categories": ["A"], "management": True}
    )
    assert len(_site["fiches"]) == 4


def test_rechercher_sans_critere_pour_le_site_ne_charge_pas_le_formulaire(
    _site: dict[str, list[object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    interdit = Mock(side_effect=AssertionError("formulaire inutile"))

    monkeypatch.setattr(passerellesmef, "obtenir_formulaire", interdit)
    passerellesmef.PasserellesMef().rechercher({"query": "réseau"})
    assert _site["envois"] == []


def test_rechercher_site_qui_ignore_les_criteres_retombe_sur_le_filtrage_local(
    _site: dict[str, list[object]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        passerellesmef,
        "envoyer_recherche",
        Mock(
            return_value={"html": "p1", "title": "(30 offres, page 1) / Tout afficher"}
        ),
    )
    passerellesmef.PasserellesMef().rechercher({"categories": ["A"]})
    assert len(_site["fiches"]) == 4
