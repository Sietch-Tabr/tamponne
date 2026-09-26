"""Tests des utilitaires GUI de recherche réseau (src/gui/travailleurs.py)."""

import threading
from collections.abc import Callable
from functools import partialmethod
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication
from pytestqt.qtbot import QtBot

from src import parametres_sources
from src.gui.travailleurs import (
    _reformater_date,
    offre_vers_ligne,
    TravailleurRecherche,
    VerificateurMiseAJour,
)
from src.sources import emploiterritorial as emploiterritorial_module
from src.sources.choisirleservicepublic import ChoisirLeServicePublic
from src.sources.emploiterritorial import EmploiTerritorial
from src.sources.fhf import Fhf
from src.sources.passerellesmef import PasserellesMef
from src.types import FiltresRecherche, InfoMaj, Offre, PageAPI


@pytest.fixture(autouse=True)
def _rediriger_sources_vers_tmp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    # passerellesmef/fhf désactivées par défaut : évite un vrai appel réseau
    # dans les tests qui ne mockent que choisirleservicepublic/territorial.
    parametres_sources.sauvegarder_sources_actives(
        {"passerellesmef": False, "fhf": False}
    )


def test_reformater_date_format_reel_du_site() -> None:
    assert _reformater_date("26 août 2026") == "26/08/2026"


def test_reformater_date_jour_sur_un_chiffre() -> None:
    assert _reformater_date("5 mars 2026") == "05/03/2026"


def test_reformater_date_premier_du_mois_avec_suffixe_er() -> None:
    assert _reformater_date("1er janvier 2026") == "01/01/2026"


def test_reformater_date_format_non_reconnu_retourne_tel_quel() -> None:
    assert _reformater_date("il y a 6 jours") == "il y a 6 jours"


def test_reformater_date_chaine_vide_retourne_tel_quel() -> None:
    assert _reformater_date("") == ""


_OFFRE_TEST: Offre = {
    "titre": "Attaché principal",
    "url": "https://example.org/1",
    "reference": "O1",
    "domaine": "RH",
    "employeur": "DGFiP Hérault",
    "localisation": "Montpellier (34)",
    "versant": "Fonction publique de l'État",
    "date": "26 août 2026",
    "source": "",
}


def test_offre_vers_ligne_reformate_la_date() -> None:
    assert offre_vers_ligne(_OFFRE_TEST) == (
        "Attaché principal",
        "DGFiP Hérault",
        "Montpellier (34)",
        "26/08/2026",
        "Choisir le service public",
    )


def test_offre_vers_ligne_date_absente() -> None:
    offre: Offre = {**_OFFRE_TEST, "date": ""}
    assert offre_vers_ligne(offre)[3] == "—"


def test_offre_vers_ligne_source_territoriale() -> None:
    offre: Offre = {**_OFFRE_TEST, "source": "Fonction publique territoriale"}
    assert offre_vers_ligne(offre)[4] == "Fonction publique territoriale"


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
"""Émission du signal `resultat` : (offres, nb_pages, arret_anticipe)."""


def _executer(
    travailleur: TravailleurRecherche,
) -> tuple[list[_Resultat], list[str], list[str]]:
    """Exécute `travailleur.executer()` directement (hors QThread) et
    collecte les émissions des signaux pertinents."""
    resultats: list[_Resultat] = []
    avertissements: list[str] = []
    erreurs: list[str] = []
    travailleur.resultat.connect(lambda *a: resultats.append(a))
    travailleur.avertissement.connect(avertissements.append)
    travailleur.erreur.connect(erreurs.append)
    travailleur.executer()
    return resultats, avertissements, erreurs


def test_executer_fusionne_les_resultats_de_deux_sources(
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
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert avertissements == []
    assert erreurs == []
    offres, nb_pages, arret_anticipe = resultats[0]
    assert {o["reference"] for o in offres} == {"O1", "O2"}


def test_executer_dedoublonne_les_offres_communes(
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
    resultats, _, _ = _executer(TravailleurRecherche({}, {}))
    offres = resultats[0][0]
    assert len(offres) == 1
    assert offres[0]["source"] == ""  # version choisirleservicepublic conservée


def test_executer_avertissement_sur_echec_partiel_sans_bloquer(
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
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert erreurs == []
    assert len(avertissements) == 1
    assert "indisponible" in avertissements[0]
    assert resultats[0][0][0]["reference"] == "O1"


def test_executer_erreur_si_toutes_les_sources_echouent(
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
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert resultats == []
    assert len(erreurs) == 1


def test_executer_erreur_si_aucune_source_active(
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
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert resultats == []
    assert len(erreurs) == 1


def test_executer_source_desactivee_nest_pas_interrogee(
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
    resultats, _, _ = _executer(TravailleurRecherche({}, {}))
    assert resultats[0][0][0]["reference"] == "O1"


def test_executer_versant_etat_seul_exclut_territorial_et_hospitaliere(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Régression : emploi-territorial.fr (FPT) et emploi.fhf.fr (FPH) sont
    # mono-versant et étaient interrogées quel que soit le filtre Versant —
    # une recherche restreinte à l'État renvoyait quand même de la FPT/FPH.
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

    resultats, _, _ = _executer(TravailleurRecherche({"versants": ["etat"]}, {}))
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2"}


def test_executer_versant_territorial_seul_interroge_emploiterritorial(
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
    resultats, _, _ = _executer(TravailleurRecherche({"versants": ["territorial"]}, {}))
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2"}


def test_executer_sans_filtre_versant_interroge_toutes_les_sources_actives(
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
    resultats, _, _ = _executer(TravailleurRecherche({}, {}))
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2", "O3", "O4"}


def test_executer_traduit_categorie_et_departement_vers_emploiterritorial(
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
    _executer(TravailleurRecherche(filtres, {}))

    assert len(urls_appelees) == 1
    assert "search_offre_form%5Bsearchcat%5D%5B%5D=A" in urls_appelees[0]
    assert "search_offre_form%5Bsearchdept%5D%5B%5D=034" in urls_appelees[0]


def test_executer_emet_source_en_cours(monkeypatch: pytest.MonkeyPatch) -> None:
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
    travailleur = TravailleurRecherche({}, {})
    sources_vues: list[str] = []
    travailleur.source_en_cours.connect(sources_vues.append)
    travailleur.executer()
    assert sources_vues == [
        parametres_sources.SOURCES_DISPONIBLES["choisirleservicepublic"],
        parametres_sources.SOURCES_DISPONIBLES["emploiterritorial"],
    ]


def test_executer_interroge_passerellesmef_et_fhf_quand_actives(
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
    resultats, avertissements, _ = _executer(TravailleurRecherche({}, {}))
    assert avertissements == []
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2", "FHF_1"}


def test_executer_fhf_dedoublonnee_contre_les_autres_sources(
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
    resultats, _, _ = _executer(TravailleurRecherche({}, {}))
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1"}


def test_executer_interroge_les_sources_en_parallele(
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
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert avertissements == [] and erreurs == []
    assert {o["reference"] for o in resultats[0][0]} == {"O1", "O2"}


def test_executer_fusion_dans_lordre_des_sources_meme_si_csp_finit_derniere(
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
    resultats, _, _ = _executer(TravailleurRecherche({}, {}))
    offres = resultats[0][0]
    assert [o["source"] for o in offres] == ["CSP"]


def test_executer_emet_progression_nommee_et_source_terminee(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
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

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _csp)
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None: ([], 1, False),
    )
    travailleur = TravailleurRecherche({}, {})
    progressions: list[tuple[object, ...]] = []
    terminees: list[str] = []
    travailleur.progression.connect(lambda *a: progressions.append(a))
    travailleur.source_terminee.connect(terminees.append)
    travailleur.executer()
    # Émis depuis les threads du pool : livrés via la boucle d'événements.
    QCoreApplication.processEvents()

    nom_csp = parametres_sources.SOURCES_DISPONIBLES["choisirleservicepublic"]
    assert progressions == [(nom_csp, 1, 2), (nom_csp, 2, 2)]
    assert sorted(terminees) == sorted(
        [nom_csp, parametres_sources.SOURCES_DISPONIBLES["emploiterritorial"]]
    )


def test_executer_source_en_echec_est_aussi_signalee_terminee(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _echec(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
    ) -> None:
        raise RuntimeError("HTTP 503")

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _echec)
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2")], 1, False),
    )
    travailleur = TravailleurRecherche({}, {})
    terminees: list[str] = []
    travailleur.source_terminee.connect(terminees.append)
    resultats, avertissements, _ = _executer(travailleur)
    QCoreApplication.processEvents()
    assert len(terminees) == 2
    assert len(avertissements) == 1
    assert {o["reference"] for o in resultats[0][0]} == {"O2"}


_INFO_MAJ_TEST: InfoMaj = {
    "version": "1.1.0",
    "notes": "notes",
    "url_zip": "https://codeberg.org/x.zip",
    "url_publication": "https://codeberg.org/x",
}


def test_verificateur_maj_emet_linfo_si_disponible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.gui import travailleurs as travailleurs_module

    monkeypatch.setattr(
        travailleurs_module, "verifier_derniere_publication", lambda: _INFO_MAJ_TEST
    )
    marqueurs_ecrits: list[InfoMaj] = []
    monkeypatch.setattr(
        travailleurs_module, "ecrire_maj_disponible", marqueurs_ecrits.append
    )

    resultats: list[InfoMaj | None] = []
    verificateur = VerificateurMiseAJour()
    verificateur.resultat.connect(resultats.append)
    verificateur.executer()

    assert resultats == [_INFO_MAJ_TEST]
    assert marqueurs_ecrits == [_INFO_MAJ_TEST]


def test_verificateur_maj_emet_none_si_a_jour_ou_hors_ligne(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.gui import travailleurs as travailleurs_module

    monkeypatch.setattr(
        travailleurs_module, "verifier_derniere_publication", lambda: None
    )
    marqueurs_ecrits: list[InfoMaj] = []
    monkeypatch.setattr(
        travailleurs_module, "ecrire_maj_disponible", marqueurs_ecrits.append
    )

    resultats: list[InfoMaj | None] = []
    verificateur = VerificateurMiseAJour()
    verificateur.resultat.connect(resultats.append)
    verificateur.executer()

    assert resultats == [None]
    assert marqueurs_ecrits == []
