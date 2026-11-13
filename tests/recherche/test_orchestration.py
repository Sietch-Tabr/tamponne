"""Tests de l'orchestration de recherche multi-source (src/recherche/orchestration.py)."""

import threading
from collections.abc import Callable
from datetime import date
from functools import partialmethod
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.donnees import cache, parametres_sources, profils
from src.recherche import orchestration
from src.recherche.orchestration import (
    RechercheImpossible,
    criteres_ignores,
    post_traiter_resultats,
    rechercher_toutes_sources,
)
from src.sources import emploiterritorial as emploiterritorial_module
from src.sources.choisirleservicepublic import ChoisirLeServicePublic
from src.sources.emploiterritorial import EmploiTerritorial
from src.sources.fhf import Fhf
from src.sources.passerellesmef import PasserellesMef
from src.types import FiltresRecherche, Offre, PageAPI


@pytest.fixture(autouse=True)
def _rediriger_donnees_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    monkeypatch.setattr(cache, "CHEMIN_OFFRES", tmp_path / "offres.json")
    monkeypatch.setattr(profils, "CHEMIN_PROFILS", tmp_path / "profils.json")
    # passerellesmef/fhf désactivées par défaut : évite un vrai appel réseau
    # dans les tests qui ne mockent que choisirleservicepublic/territorial.
    parametres_sources.sauvegarder_sources_actives(
        {"passerellesmef": False, "fhf": False}
    )


@pytest.fixture(autouse=True)
def _site_en_bon_etat(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Le contrôle du site (accueil) ne joint jamais le réseau ; renvoie les
    sites contrôlés. Les tests de panne le remplacent."""
    controles: list[str] = []
    monkeypatch.setattr(orchestration, "controler_site", controles.append)
    return controles


def _offre(reference: str, source: str = "") -> Offre:
    return {
        "titre": f"Offre {reference}",
        "url": f"https://example.org/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": "",
        "localisation": "",
        "versant": "",
        "date": "",
        "source": source,
    }


type _Resultat = tuple[list[Offre], int, bool]


def _executer(
    filtres: FiltresRecherche,
) -> tuple[list[_Resultat], list[str], list[str]]:
    """Lance `rechercher_toutes_sources` et collecte (résultats,
    avertissements, erreurs) — au plus un résultat ou une erreur."""
    avertissements: list[str] = []
    try:
        resultat = rechercher_toutes_sources(
            filtres, {}, on_avertissement=avertissements.append
        )
    except RechercheImpossible as erreur:
        return [], avertissements, [str(erreur)]
    return [resultat], avertissements, []


def test_rechercher_fusionne_les_resultats_de_deux_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        Mock(
            return_value=(
                [_offre("O2", "Territorial")],
                1,
                False,
            )
        ),
    )
    resultats, avertissements, erreurs = _executer({})
    assert avertissements == []
    assert erreurs == []
    offres, nb_pages, arret_anticipe = resultats[0]
    assert {o["reference"] for o in offres} == {"O1", "O2"}


def test_rechercher_dedoublonne_les_offres_communes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        Mock(
            return_value=(
                [_offre("O1", "Territorial")],
                1,
                False,
            )
        ),
    )
    resultats, _, _ = _executer({})
    offres = resultats[0][0]
    assert len(offres) == 1
    assert offres[0]["source"] == ""  # version choisirleservicepublic conservée


def test_rechercher_avertissement_sur_echec_partiel_sans_bloquer(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )

    def _echec(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> None:
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echec)
    resultats, avertissements, erreurs = _executer({})
    assert erreurs == []
    assert len(avertissements) == 1
    assert "indisponible" in avertissements[0]
    assert resultats[0][0][0]["reference"] == "O1"
    assert "indisponible\u00a0: Erreur réseau" in caplog.text


def test_rechercher_source_au_format_imprevu_n_arrete_pas_les_autres(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )

    def _format_imprevu(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> None:
        raise AttributeError("'NoneType' object has no attribute 'find'")

    monkeypatch.setattr(EmploiTerritorial, "rechercher", _format_imprevu)
    resultats, avertissements, erreurs = _executer({})
    assert erreurs == []
    assert resultats[0][0][0]["reference"] == "O1"
    assert "réponse inattendue du site (AttributeError" in avertissements[0]
    # Journal : la trace complète, pour retrouver la ligne qui a cédé.
    assert "Traceback" in caplog.text and "_format_imprevu" in caplog.text


def test_rechercher_erreur_si_toutes_les_sources_echouent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _echec(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> None:
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _echec)
    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echec)
    resultats, avertissements, erreurs = _executer({})
    assert resultats == []
    assert len(erreurs) == 1


@pytest.mark.usefixtures("monkeypatch")
def test_rechercher_erreur_si_aucune_source_active() -> None:
    parametres_sources.sauvegarder_sources_actives(
        {
            "choisirleservicepublic": False,
            "emploiterritorial": False,
            "passerellesmef": False,
            "fhf": False,
        }
    )
    resultats, avertissements, erreurs = _executer({})
    assert resultats == []
    assert len(erreurs) == 1


def test_rechercher_source_desactivee_nest_pas_interrogee(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parametres_sources.sauvegarder_sources_actives(
        {"emploiterritorial": False, "passerellesmef": False, "fhf": False}
    )
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )

    def _echoue_si_appelee(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> None:
        raise AssertionError("emploiterritorial ne doit pas être interrogée")

    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echoue_si_appelee)
    resultats, _, _ = _executer({})
    assert resultats[0][0][0]["reference"] == "O1"


def test_rechercher_versant_etat_seul_exclut_territorial_et_hospitaliere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Régression : emploi-territorial.fr (FPT) et emploi.fhf.fr (FPH),
    mono-versant, étaient interrogées quel que soit le filtre Versant — une
    recherche restreinte à l'État renvoyait quand même de la FPT/FPH."""
    parametres_sources.sauvegarder_sources_actives(
        {"passerellesmef": True, "fhf": True}
    )
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )
    # Passerelles/MEF est elle-même mono-versant État : doit rester interrogée.
    monkeypatch.setattr(
        PasserellesMef,
        "rechercher",
        Mock(
            return_value=(
                [_offre("O2", "MEF")],
                1,
                False,
            )
        ),
    )

    def _echoue_si_appelee(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> None:
        raise AssertionError("source mono-versant exclue par le filtre appelée")

    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echoue_si_appelee)
    monkeypatch.setattr(Fhf, "rechercher", _echoue_si_appelee)

    resultats, _, _ = _executer({"versants": ["etat"]})
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2"}


def test_rechercher_versant_territorial_seul_interroge_emploiterritorial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        Mock(
            return_value=(
                [_offre("O2", "Territorial")],
                1,
                False,
            )
        ),
    )
    resultats, _, _ = _executer({"versants": ["territorial"]})
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2"}


def test_rechercher_sans_filtre_versant_interroge_toutes_les_sources_actives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parametres_sources.sauvegarder_sources_actives(
        {"passerellesmef": True, "fhf": True}
    )
    for classe, ref in [
        (ChoisirLeServicePublic, "O1"),
        (EmploiTerritorial, "O2"),
        (PasserellesMef, "O3"),
        (Fhf, "O4"),
    ]:
        monkeypatch.setattr(
            classe,
            "rechercher",
            lambda self, filtres, on_page=None, on_fiche=None, ref=ref: (
                [_offre(ref)],
                1,
                False,
            ),
        )
    resultats, _, _ = _executer({})
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2", "O3", "O4"}


def test_rechercher_traduit_categorie_et_departement_vers_emploiterritorial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test d'intégration : FiltresRecherche -> URL réelle envoyée à ET,
    en passant par la vraie traduction de emploiterritorial/__init__.py
    (pas un mock de EmploiTerritorial.rechercher qui la court-circuiterait)."""
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )
    urls_appelees: list[str] = []

    def _obtenir_page_recherche_factice(opener: object, url: str) -> PageAPI:
        urls_appelees.append(url)
        return {"html": "<html></html>", "title": ""}

    monkeypatch.setattr(
        emploiterritorial_module,
        "obtenir_page_recherche",
        _obtenir_page_recherche_factice,
    )

    filtres: FiltresRecherche = {"categories": ["A"], "localisations": ["Hérault"]}
    _executer(filtres)

    assert len(urls_appelees) == 1
    assert "search_offre_form%5Bsearchcat%5D%5B%5D=A" in urls_appelees[0]
    assert "search_offre_form%5Bsearchdept%5D%5B%5D=034" in urls_appelees[0]


def test_rechercher_interroge_passerellesmef_et_fhf_quand_actives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parametres_sources.sauvegarder_sources_actives(
        {"emploiterritorial": False, "passerellesmef": True, "fhf": True}
    )
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )
    monkeypatch.setattr(
        PasserellesMef,
        "rechercher",
        Mock(
            return_value=(
                [_offre("O2", "MEF")],
                1,
                False,
            )
        ),
    )
    monkeypatch.setattr(
        Fhf,
        "rechercher",
        Mock(
            return_value=(
                [_offre("FHF_1", "FHF")],
                1,
                False,
            )
        ),
    )
    resultats, avertissements, _ = _executer({})
    assert avertissements == []
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2", "FHF_1"}


def test_rechercher_fhf_dedoublonnee_contre_les_autres_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # "Un(e) Infirmier(ère)" au même employeur que O1 : doit être filtrée
    # par filtrer_doublons_fhf avant fusion, même titre + employeur lié.
    parametres_sources.sauvegarder_sources_actives(
        {"emploiterritorial": False, "passerellesmef": False, "fhf": True}
    )
    offre_csp = {
        **_offre("O1"),
        "titre": "Infirmier de nuit",
        "employeur": "Centre Hospitalier Epsylan",
    }
    offre_fhf = {
        **_offre("FHF_1", "FHF"),
        "titre": "Infirmier de nuit",
        "employeur": "EPSYLAN (Établissement Psychiatrique)",
    }
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None, on_fiche=None: ([offre_csp], 1, False),
    )
    monkeypatch.setattr(
        Fhf,
        "rechercher",
        lambda self, filtres, on_page=None, on_fiche=None: ([offre_fhf], 1, False),
    )
    resultats, _, _ = _executer({})
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1"}


def test_rechercher_interroge_les_sources_en_parallele(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # La barrière ne se franchit que si les deux sources tournent en même
    # temps : en série, la première attendrait indéfiniment (timeout).
    barriere = threading.Barrier(2, timeout=5)

    def _rechercher(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
        ref: str = "",
    ) -> tuple[list[Offre], int, bool]:
        barriere.wait()
        return [_offre(ref)], 1, False

    monkeypatch.setattr(
        ChoisirLeServicePublic, "rechercher", partialmethod(_rechercher, ref="O1")
    )
    monkeypatch.setattr(
        EmploiTerritorial, "rechercher", partialmethod(_rechercher, ref="O2")
    )
    resultats, avertissements, erreurs = _executer({})
    assert avertissements == [] and erreurs == []
    assert {o["reference"] for o in resultats[0][0]} == {"O1", "O2"}


def test_rechercher_fusion_dans_lordre_des_sources_meme_si_csp_finit_derniere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Même référence des deux côtés : la version choisirleservicepublic doit
    # gagner au dédoublonnage, même si elle arrive après la territoriale.
    territoriale_finie = threading.Event()

    def _csp(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        territoriale_finie.wait(timeout=5)
        return [_offre("REF", "CSP")], 1, False

    def _territorial(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        territoriale_finie.set()
        return [_offre("REF", "Territorial")], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _csp)
    monkeypatch.setattr(EmploiTerritorial, "rechercher", _territorial)
    resultats, _, _ = _executer({})
    offres = resultats[0][0]
    assert [o["source"] for o in offres] == ["CSP"]


def test_rechercher_signale_chaque_source_en_cours_dans_lordre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        Mock(
            return_value=(
                [_offre("O2", "Territorial")],
                1,
                False,
            )
        ),
    )
    sources_vues: list[str] = []
    rechercher_toutes_sources({}, {}, on_source_en_cours=sources_vues.append)
    assert sources_vues == [
        parametres_sources.SOURCES_DISPONIBLES["choisirleservicepublic"],
        parametres_sources.SOURCES_DISPONIBLES["emploiterritorial"],
    ]


def test_rechercher_remonte_progression_et_sources_terminees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _csp(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        assert on_page is not None
        on_page(1, 2)
        on_page(2, 2)
        return [_offre("O1")], 2, False

    def _echec(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> None:
        raise RuntimeError("HTTP 503")

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _csp)
    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echec)
    progressions: list[tuple[str, int, int]] = []
    terminees: list[str] = []
    comptes: list[tuple[str, int]] = []
    offres, nb_pages, _ = rechercher_toutes_sources(
        {},
        {},
        on_progression=lambda nom, page, total: progressions.append((nom, page, total)),
        on_source_terminee=terminees.append,
        on_offres_source=lambda nom, nombre: comptes.append((nom, nombre)),
    )

    nom_csp = parametres_sources.SOURCES_DISPONIBLES["choisirleservicepublic"]
    assert progressions == [(nom_csp, 1, 2), (nom_csp, 2, 2)]
    # Une source en échec est elle aussi signalée terminée.
    assert sorted(terminees) == sorted(
        [nom_csp, parametres_sources.SOURCES_DISPONIBLES["emploiterritorial"]]
    )
    assert nb_pages == 2
    assert [o["reference"] for o in offres] == ["O1"]
    # Seule la source qui a réussi annonce son nombre d'offres.
    assert comptes == [(nom_csp, 1)]


# --- Post-traitement ---


def _offre_titre(reference: str, titre: str) -> Offre:
    return {**_offre(reference), "titre": titre}


def test_post_traiter_exclut_les_grades_superieurs_par_defaut() -> None:
    offres = [_offre_titre("O1", "Attaché"), _offre_titre("O2", "IDIV adjoint")]
    resultat = post_traiter_resultats(offres, [], False, None)
    assert [o["reference"] for o in resultat["offres"]] == ["O1"]
    assert resultat["nb_exclus"] == 1


def test_post_traiter_conserve_les_grades_superieurs_si_demande() -> None:
    offres = [_offre_titre("O1", "Attaché"), _offre_titre("O2", "IDIV adjoint")]
    resultat = post_traiter_resultats(offres, [], True, None)
    assert len(resultat["offres"]) == 2
    assert resultat["nb_exclus"] == 0


def test_post_traiter_filtre_par_grade_selectionne() -> None:
    offres = [
        _offre_titre("O1", "Attaché principal"),
        _offre_titre("O2", "Secrétaire administratif"),
    ]
    resultat = post_traiter_resultats(offres, ["Attaché principal"], False, None)
    assert [o["reference"] for o in resultat["offres"]] == ["O1"]


def test_post_traiter_sans_profil_ne_marque_aucune_nouvelle() -> None:
    resultat = post_traiter_resultats([_offre("O1")], [], False, None)
    assert resultat["nouvelles"] == set()
    assert cache._charger_offres() == {}


def test_post_traiter_avec_profil_marque_les_nouvelles_et_la_date() -> None:
    profils.ajouter_profil("p", {"label": "p"})
    premiere = post_traiter_resultats([_offre("O1")], [], False, "p")
    assert premiere["nouvelles"] == {"O1"}
    assert (
        profils.charger_profils()["p"].get("dernier_lancement")
        == date.today().isoformat()
    )

    seconde = post_traiter_resultats([_offre("O1"), _offre("O2")], [], False, "p")
    assert seconde["nouvelles"] == {"O2"}


# --- critères qu'une source ne peut pas appliquer : prévenir, ne pas exclure ---


def test_criteres_ignores_ignore_les_criteres_vides() -> None:
    assert criteres_ignores("fhf", {"categories": [], "management": False}) == []
    assert criteres_ignores("fhf", {"categories": ["A"], "teletravail": True}) == [
        "la catégorie",
        "le télétravail",
    ]
    assert criteres_ignores("emploiterritorial", {"domaines": ["Numérique"]}) == [
        "le domaine"
    ]
    assert criteres_ignores("passerellesmef", {"domaines": ["X"]}) == []
    assert criteres_ignores("choisirleservicepublic", {"domaines": ["X"]}) == []


def test_rechercher_previent_sans_exclure_une_source_qui_ignore_un_critere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parametres_sources.sauvegarder_sources_actives(
        {
            "choisirleservicepublic": False,
            "emploiterritorial": False,
            "passerellesmef": False,
            "fhf": True,
        }
    )
    interrogees: list[str] = []

    def _fhf_espion(
        self: Fhf,
        filtres: FiltresRecherche,
        on_page: object = None,
        on_fiche: object = None,
    ) -> _Resultat:
        interrogees.append("fhf")
        return [_offre("F1", "FHF")], 1, False

    monkeypatch.setattr(Fhf, "rechercher", _fhf_espion)
    avertissements: list[str] = []
    offres, _, _ = rechercher_toutes_sources(
        {"categories": ["A"]}, {}, on_avertissement=avertissements.append
    )
    assert interrogees == ["fhf"]
    assert [o["reference"] for o in offres] == ["F1"]
    assert len(avertissements) == 1
    assert "la catégorie" in avertissements[0]


def test_rechercher_ecarte_les_offres_hors_fenetre_de_date_des_sources_sans_filtre(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parametres_sources.sauvegarder_sources_actives(
        {
            "choisirleservicepublic": False,
            "emploiterritorial": False,
            "passerellesmef": True,
            "fhf": False,
        }
    )
    recente = _offre("R", "MEF")
    recente["date"] = date.today().strftime("%d/%m/%Y")
    ancienne = _offre("A", "MEF")
    ancienne["date"] = "01/01/2020"
    monkeypatch.setattr(
        PasserellesMef,
        "rechercher",
        lambda self, filtres, on_page=None, on_fiche=None: (
            [recente, ancienne],
            1,
            False,
        ),
    )
    offres, _, _ = rechercher_toutes_sources(
        {"date_publication": "7 derniers jours"}, {}
    )
    assert [o["reference"] for o in offres] == ["R"]


def test_rechercher_remonte_la_lecture_des_fiches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _csp(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        assert on_fiche is not None
        on_fiche(1, 2)
        on_fiche(2, 2)
        return [_offre("O1")], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _csp)
    monkeypatch.setattr(
        EmploiTerritorial, "rechercher", Mock(return_value=([], 1, False))
    )
    lectures: list[tuple[str, int, int]] = []
    rechercher_toutes_sources(
        {}, {}, on_fiches=lambda nom, lues, total: lectures.append((nom, lues, total))
    )

    nom_csp = parametres_sources.SOURCES_DISPONIBLES["choisirleservicepublic"]
    assert lectures == [(nom_csp, 1, 2), (nom_csp, 2, 2)]


def test_une_source_sans_offre_dont_le_site_va_bien_est_une_recherche_vide(
    monkeypatch: pytest.MonkeyPatch, _site_en_bon_etat: list[str]
) -> None:
    monkeypatch.setattr(
        ChoisirLeServicePublic, "rechercher", Mock(return_value=([], 1, False))
    )
    monkeypatch.setattr(
        EmploiTerritorial, "rechercher", Mock(return_value=([_offre("T1")], 1, False))
    )
    resultats, avertissements, erreurs = _executer({})

    assert (avertissements, erreurs) == ([], [])
    assert [o["reference"] for o in resultats[0][0]] == ["T1"]
    # Seule la source sans offre est contrôlée : un résultat prouve que le site répond.
    assert _site_en_bon_etat == [orchestration.SITES["choisirleservicepublic"]]


def test_une_source_sans_offre_dont_le_site_est_en_panne_est_signalee(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def panne(url: str) -> None:
        raise RuntimeError(f"Le site {url} annonce une panne (Maintenance)")

    monkeypatch.setattr(orchestration, "controler_site", panne)
    monkeypatch.setattr(
        ChoisirLeServicePublic, "rechercher", Mock(return_value=([], 1, False))
    )
    monkeypatch.setattr(
        EmploiTerritorial, "rechercher", Mock(return_value=([_offre("T1")], 1, False))
    )
    resultats, avertissements, erreurs = _executer({})

    assert erreurs == []
    assert [o["reference"] for o in resultats[0][0]] == ["T1"]
    assert len(avertissements) == 1
    assert "indisponible" in avertissements[0] and "panne" in avertissements[0]


def test_toutes_les_sources_vides_et_en_panne_la_recherche_est_impossible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def panne(_url: str) -> None:
        raise RuntimeError("Le site annonce une panne")

    monkeypatch.setattr(orchestration, "controler_site", panne)
    monkeypatch.setattr(
        ChoisirLeServicePublic, "rechercher", Mock(return_value=([], 1, False))
    )
    monkeypatch.setattr(
        EmploiTerritorial, "rechercher", Mock(return_value=([], 1, False))
    )
    _, _, erreurs = _executer({})
    assert erreurs and "indisponibles" in erreurs[0]


def test_source_en_echec_est_signalee_par_son_nom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def echec(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("HTTP 503")

    monkeypatch.setattr(EmploiTerritorial, "rechercher", echec)
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        Mock(return_value=([_offre("O1")], 1, False)),
    )
    noms: list[str] = []
    rechercher_toutes_sources({}, {}, on_echec_source=noms.append)
    assert noms == [parametres_sources.SOURCES_DISPONIBLES["emploiterritorial"]]


def test_date_de_lancement_non_enregistree_ne_fait_pas_echouer_le_traitement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(_nom: str) -> None:
        raise PermissionError("tenu")

    monkeypatch.setattr(orchestration, "noter_lancement", refuse)
    resultat = post_traiter_resultats([_offre("O1")], [], False, "fiche")
    assert [o["reference"] for o in resultat["offres"]] == ["O1"]
    assert resultat["nouvelles"] == {"O1"}
