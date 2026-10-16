"""Tests des boucles de recherche et de la fiche détaillée de chaque source,
sites simulés : pagination, page vide, plafond `MAX_PAGES`, échec réseau."""

from collections.abc import Callable
from types import ModuleType

import pytest

from src.sources import choisirleservicepublic as csp
from src.sources import emploiterritorial, fhf, passerellesmef
from src.types import Offre


def _offre(reference: str) -> Offre:
    return {
        "titre": f"Offre {reference}",
        "url": f"https://exemple.test/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": "",
        "localisation": "",
        "versant": "",
        "date": "",
        "source": "",
    }


def _offres_de_page(html: str) -> list[Offre]:
    """Page simulée : `"p3:a,b"` → offres `a` et `b` ; `"p3:"` → page vide."""
    _, _, references = html.partition(":")
    return [_offre(r) for r in references.split(",") if r]


@pytest.fixture(autouse=True)
def _sans_attente(monkeypatch: pytest.MonkeyPatch) -> None:
    for module in (csp, emploiterritorial, fhf, passerellesmef):
        monkeypatch.setattr(module.time, "sleep", lambda _s: None)


def _progression() -> tuple[list[tuple[int, int]], Callable[[int, int], None]]:
    pages: list[tuple[int, int]] = []
    return pages, lambda page, total: pages.append((page, total))


# --- choisirleservicepublic ---


def _csp_pages(monkeypatch: pytest.MonkeyPatch, pages: dict[int, str], nb: int) -> None:
    def obtenir(url: str) -> dict[str, str]:
        numero = int(url.rsplit("page/", 1)[1].strip("/")) if "page/" in url else 1
        return {"html": pages.get(numero, ""), "title": f"Page 1 sur {nb}"}

    monkeypatch.setattr(csp, "obtenir_page_offres", obtenir)
    monkeypatch.setattr(csp, "extraire_offres", _offres_de_page)
    monkeypatch.setattr(csp, "extraire_pagination", lambda _t: (1, nb))


def test_csp_une_seule_page(monkeypatch: pytest.MonkeyPatch) -> None:
    _csp_pages(monkeypatch, {1: "p1:a,b"}, 1)
    pages, on_page = _progression()
    offres, nb, arret = csp.ChoisirLeServicePublic().rechercher({}, on_page)
    assert [o["reference"] for o in offres] == ["a", "b"]
    assert (nb, arret, pages) == (1, False, [(1, 1)])


def test_csp_charge_les_pages_suivantes(monkeypatch: pytest.MonkeyPatch) -> None:
    _csp_pages(monkeypatch, {1: "p1:a", 2: "p2:b", 3: "p3:c"}, 3)
    offres, nb, arret = csp.ChoisirLeServicePublic().rechercher({})
    assert [o["reference"] for o in offres] == ["a", "b", "c"]
    assert (nb, arret) == (3, False)


def test_csp_s_arrete_sur_une_page_vide(monkeypatch: pytest.MonkeyPatch) -> None:
    _csp_pages(monkeypatch, {1: "p1:a", 2: "p2:"}, 5)
    offres, nb, arret = csp.ChoisirLeServicePublic().rechercher({})
    assert [o["reference"] for o in offres] == ["a"]
    assert (nb, arret) == (1, True)


def test_csp_s_arrete_quand_l_api_reboucle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Après la dernière page réelle, l'API renvoie des offres déjà vues."""
    _csp_pages(monkeypatch, {1: "p1:a,b", 2: "p2:c", 3: "p3:a,b"}, 4)
    offres, nb, arret = csp.ChoisirLeServicePublic().rechercher({})
    assert [o["reference"] for o in offres] == ["a", "b", "c"]
    assert (nb, arret) == (2, True)


def test_csp_plafonne_a_max_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    total = csp.MAX_PAGES + 5
    _csp_pages(monkeypatch, {n: f"p{n}:r{n}" for n in range(1, total + 1)}, total)
    offres, nb, _ = csp.ChoisirLeServicePublic().rechercher({})
    assert len(offres) == csp.MAX_PAGES
    assert nb == total


def test_csp_resout_les_organisations_du_cache() -> None:
    cache = {"Ministère": {"Direction": 12, "Service": 34}}
    assert csp._resoudre_ids_organisations(
        ["Ministère - Direction", "Service", "Inconnue"], cache
    ) == [12, 34]


# --- FHF et Passerelles : une requête par page ---


def _pages_par_requete(
    monkeypatch: pytest.MonkeyPatch, module: ModuleType, pages: list[str], titre: str
) -> None:
    reponses = iter(pages)
    monkeypatch.setattr(module, "nouvelle_session", lambda: None)
    monkeypatch.setattr(
        module,
        "obtenir_page_recherche",
        lambda _opener, _url: {"html": next(reponses, "fin:"), "title": titre},
    )
    monkeypatch.setattr(module, "extraire_offres", _offres_de_page)


def test_fhf_boucle_jusqu_a_une_page_vide(monkeypatch: pytest.MonkeyPatch) -> None:
    _pages_par_requete(monkeypatch, fhf, ["p0:a", "p1:b", "p2:"], "")
    pages, on_page = _progression()
    offres, nb, arret = fhf.Fhf().rechercher({}, on_page)
    assert [o["reference"] for o in offres] == ["a", "b"]
    assert (nb, arret) == (3, False)
    assert pages[-1] == (3, 3)


def test_fhf_plafonne_a_max_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    _pages_par_requete(
        monkeypatch, fhf, [f"p{n}:r{n}" for n in range(fhf.MAX_PAGES + 3)], ""
    )
    offres, nb, arret = fhf.Fhf().rechercher({})
    assert len(offres) == fhf.MAX_PAGES
    assert (nb, arret) == (fhf.MAX_PAGES, True)


def _passerelles_pages(monkeypatch: pytest.MonkeyPatch, pages: dict[int, str]) -> None:
    """Pages de Passerelles par numéro (lues en parallèle : ordre libre)."""

    def obtenir(_opener: object, url: str) -> dict[str, str]:
        numero = int(url.rsplit("page=", 1)[1]) if "page=" in url else 1
        return {"html": pages.get(numero, ""), "title": ""}

    monkeypatch.setattr(passerellesmef, "nouvelle_session", lambda: None)
    monkeypatch.setattr(passerellesmef, "obtenir_page_recherche", obtenir)
    monkeypatch.setattr(passerellesmef, "extraire_offres", _offres_de_page)


def test_passerelles_pages_selon_le_total_annonce(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _passerelles_pages(monkeypatch, {1: "p1:a", 2: "p2:b"})
    monkeypatch.setattr(passerellesmef, "extraire_totaux", lambda _t: (20, 2))
    pages, on_page = _progression()
    offres, nb, arret = passerellesmef.PasserellesMef().rechercher({}, on_page)
    assert [o["reference"] for o in offres] == ["a", "b"]
    assert (nb, arret) == (2, False)
    assert sorted(pages) == [(1, 2), (2, 2)]


def test_passerelles_page_vide_avant_la_fin(monkeypatch: pytest.MonkeyPatch) -> None:
    _passerelles_pages(monkeypatch, {1: "p1:a", 2: "p2:", 3: "p3:c"})
    monkeypatch.setattr(passerellesmef, "extraire_totaux", lambda _t: (45, 3))
    offres, nb, arret = passerellesmef.PasserellesMef().rechercher({})
    assert [o["reference"] for o in offres] == ["a"]
    assert (nb, arret) == (3, True)


def test_passerelles_plafonne_les_pages_sans_filtre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    total = passerellesmef.MAX_PAGES + 5
    _passerelles_pages(monkeypatch, {n: f"p{n}:r{n}" for n in range(1, total + 1)})
    monkeypatch.setattr(passerellesmef, "extraire_totaux", lambda _t: (total * 15, 1))
    offres, nb, arret = passerellesmef.PasserellesMef().rechercher({})
    assert len(offres) == passerellesmef.MAX_PAGES
    assert (nb, arret) == (total, True)


# --- emploi-territorial : une seule requête cumulative ---


def _territorial(
    monkeypatch: pytest.MonkeyPatch, total: int, premiere: str, cumul: str
) -> list[int]:
    demandes: list[int] = []
    monkeypatch.setattr(emploiterritorial, "nouvelle_session", lambda: None)
    monkeypatch.setattr(
        emploiterritorial,
        "obtenir_page_recherche",
        lambda _opener, _url: {"html": premiere, "title": ""},
    )

    def suivante(_opener: object, page: int) -> str:
        demandes.append(page)
        return cumul

    monkeypatch.setattr(emploiterritorial, "obtenir_page_suivante", suivante)
    monkeypatch.setattr(emploiterritorial, "extraire_offres", _offres_de_page)
    monkeypatch.setattr(emploiterritorial, "extraire_totaux", lambda _h: (total, 2))
    return demandes


def test_territorial_une_seule_page(monkeypatch: pytest.MonkeyPatch) -> None:
    demandes = _territorial(monkeypatch, 2, "p1:a,b", "")
    offres, nb, arret = emploiterritorial.EmploiTerritorial().rechercher({})
    assert [o["reference"] for o in offres] == ["a", "b"]
    assert (nb, arret, demandes) == (1, False, [])


def test_territorial_demande_toutes_les_pages_en_une_fois(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demandes = _territorial(monkeypatch, 6, "p1:a,b", "cumul:a,b,c,d,e,f")
    offres, nb, arret = emploiterritorial.EmploiTerritorial().rechercher({})
    assert len(offres) == 6
    assert (nb, arret, demandes) == (3, False, [3])


def test_territorial_signale_des_offres_manquantes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _territorial(monkeypatch, 6, "p1:a,b", "cumul:a,b,c")
    _, _, arret = emploiterritorial.EmploiTerritorial().rechercher({})
    assert arret is True


# --- fiche détaillée : échec réseau → fiche vide ---


@pytest.mark.parametrize("module", [emploiterritorial, fhf, passerellesmef])
def test_recuperer_detail_offre_echec_reseau_fiche_vide(
    monkeypatch: pytest.MonkeyPatch, module: ModuleType
) -> None:
    def injoignable(_opener: object, _url: str) -> str:
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(module, "nouvelle_session", lambda: None)
    monkeypatch.setattr(module, "obtenir_fiche_offre", injoignable)
    assert module.recuperer_detail_offre("https://exemple.test/x") == csp.DETAIL_VIDE


@pytest.mark.parametrize("module", [emploiterritorial, fhf, passerellesmef])
def test_recuperer_detail_offre_extrait_la_page(
    monkeypatch: pytest.MonkeyPatch, module: ModuleType
) -> None:
    monkeypatch.setattr(module, "nouvelle_session", lambda: None)
    monkeypatch.setattr(module, "obtenir_fiche_offre", lambda _o, _u: "<html>x</html>")
    monkeypatch.setattr(module, "extraire_detail_offre", lambda html: {"page": html})
    assert module.recuperer_detail_offre("https://exemple.test/x") == {
        "page": "<html>x</html>"
    }


def test_csp_recuperer_detail_offre_echec_reseau_fiche_vide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def injoignable(_url: str) -> None:
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(csp, "obtenir_page_offres", injoignable)
    assert csp.recuperer_detail_offre("https://exemple.test/x") == csp.DETAIL_VIDE
