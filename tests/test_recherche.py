"""Tests de l'orchestration de recherche multi-source (src/recherche.py)."""

import threading
from collections.abc import Callable
from functools import partialmethod
from pathlib import Path

import pytest

from src import cache, parametres_sources, profils
from src.recherche import (
    RechercheImpossible,
    lignes_resume,
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
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2", "Territorial")], 1, False),
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
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1", "Territorial")], 1, False),
    )
    resultats, _, _ = _executer({})
    offres = resultats[0][0]
    assert len(offres) == 1
    assert offres[0]["source"] == ""  # version choisirleservicepublic conservée


def test_rechercher_avertissement_sur_echec_partiel_sans_bloquer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )

    def _echec(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
    ) -> None:
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echec)
    resultats, avertissements, erreurs = _executer({})
    assert erreurs == []
    assert len(avertissements) == 1
    assert "indisponible" in avertissements[0]
    assert resultats[0][0][0]["reference"] == "O1"


def test_rechercher_erreur_si_toutes_les_sources_echouent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _echec(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
    ) -> None:
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _echec)
    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echec)
    resultats, avertissements, erreurs = _executer({})
    assert resultats == []
    assert len(erreurs) == 1


def test_rechercher_erreur_si_aucune_source_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )

    def _echoue_si_appelee(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
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
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    # Passerelles/MEF est elle-même mono-versant État : doit rester interrogée.
    monkeypatch.setattr(
        PasserellesMef,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2", "MEF")], 1, False),
    )

    def _echoue_si_appelee(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
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
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2", "Territorial")], 1, False),
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
            lambda self, filtres, on_page=None, ref=ref: ([_offre(ref)], 1, False),
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
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
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
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        PasserellesMef,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2", "MEF")], 1, False),
    )
    monkeypatch.setattr(
        Fhf,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("FHF_1", "FHF")], 1, False),
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
        lambda self, filtres, on_page=None: ([offre_csp], 1, False),
    )
    monkeypatch.setattr(
        Fhf,
        "rechercher",
        lambda self, filtres, on_page=None: ([offre_fhf], 1, False),
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
    ) -> tuple[list[Offre], int, bool]:
        territoriale_finie.wait(timeout=5)
        return [_offre("REF", "CSP")], 1, False

    def _territorial(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
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
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2", "Territorial")], 1, False),
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
    ) -> tuple[list[Offre], int, bool]:
        assert on_page is not None
        on_page(1, 2)
        on_page(2, 2)
        return [_offre("O1")], 2, False

    def _echec(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
    ) -> None:
        raise RuntimeError("HTTP 503")

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _csp)
    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echec)
    progressions: list[tuple[str, int, int]] = []
    terminees: list[str] = []
    offres, nb_pages, _ = rechercher_toutes_sources(
        {},
        {},
        on_progression=lambda nom, page, total: progressions.append(
            (nom, page, total)
        ),
        on_source_terminee=terminees.append,
    )

    nom_csp = parametres_sources.SOURCES_DISPONIBLES["choisirleservicepublic"]
    assert progressions == [(nom_csp, 1, 2), (nom_csp, 2, 2)]
    # Une source en échec est elle aussi signalée terminée.
    assert sorted(terminees) == sorted(
        [nom_csp, parametres_sources.SOURCES_DISPONIBLES["emploiterritorial"]]
    )
    assert nb_pages == 2
    assert [o["reference"] for o in offres] == ["O1"]


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


def test_post_traiter_avec_profil_marque_les_nouvelles_et_les_stats() -> None:
    profils.ajouter_profil("p", {"label": "p"})
    premiere = post_traiter_resultats([_offre("O1")], [], False, "p")
    assert premiere["nouvelles"] == {"O1"}
    assert profils.charger_profils()["p"].get("nb_nouvelles") == 1

    # O1 reste « nouvelle » : vue pour la première fois il y a moins de 24 h.
    seconde = post_traiter_resultats([_offre("O1"), _offre("O2")], [], False, "p")
    assert seconde["nouvelles"] == {"O1", "O2"}
    assert profils.charger_profils()["p"].get("nb_nouvelles") == 2


# --- Résumé ---


def test_lignes_resume_cas_nominal() -> None:
    resultat = post_traiter_resultats([_offre("O1")], [], False, None)
    lignes = lignes_resume({}, resultat, 1, False, [])
    assert lignes == ["Filtres : tous versants", "1 offre(s)"]


def test_lignes_resume_detaille_pages_exclusions_et_avertissements() -> None:
    lignes = lignes_resume(
        {},
        {"offres": [_offre("O1")], "nb_exclus": 2, "nouvelles": {"O1"}},
        3,
        True,
        ["FHF indisponible : HTTP 503"],
    )
    assert lignes[1] == "1 offre(s) · 3 page(s)"
    assert "1 nouvelle(s) offre(s) depuis la dernière recherche" in lignes
    assert "2 offre(s) IDiv/IP exclue(s) (filtre de titre)" in lignes
    assert "Arrêt à la page 3 (page vide)" in lignes
    assert lignes[-1] == "FHF indisponible : HTTP 503"


def test_lignes_resume_aucune_offre() -> None:
    lignes = lignes_resume(
        {}, {"offres": [], "nb_exclus": 0, "nouvelles": set()}, 1, False, []
    )
    assert lignes[-1] == "Aucune offre trouvée."
