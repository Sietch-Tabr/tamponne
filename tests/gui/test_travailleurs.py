"""Tests des adaptateurs Qt de src/gui/travailleurs.py : relais des callbacks
de `src.recherche.orchestration` en signaux. L'orchestration est testée dans test_recherche.py.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication
from pytestqt.qtbot import QtBot

from src.donnees import parametres_sources
from src.gui.travailleurs import TravailleurRecherche, VerificateurMiseAJour
from src.sources.choisirleservicepublic import ChoisirLeServicePublic
from src.sources.emploiterritorial import EmploiTerritorial
from src.types import FiltresRecherche, InfoMaj, Offre


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
        lambda self, filtres, on_page=None, on_fiche=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None, on_fiche=None: (
            [_offre("O2", "Territorial")],
            1,
            False,
        ),
    )
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert avertissements == []
    assert erreurs == []
    offres, nb_pages, arret_anticipe = resultats[0]
    assert {o["reference"] for o in offres} == {"O1", "O2"}


def test_executer_avertissement_sur_echec_partiel_sans_bloquer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None, on_fiche=None: ([_offre("O1")], 1, False),
    )

    def _echec(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> None:
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echec)
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert erreurs == []
    assert len(avertissements) == 1
    assert "indisponible" in avertissements[0]
    assert resultats[0][0][0]["reference"] == "O1"


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


def test_executer_emet_source_en_cours(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None, on_fiche=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None, on_fiche=None: (
            [_offre("O2", "Territorial")],
            1,
            False,
        ),
    )
    travailleur = TravailleurRecherche({}, {})
    sources_vues: list[str] = []
    travailleur.source_en_cours.connect(sources_vues.append)
    travailleur.executer()
    assert sources_vues == [
        parametres_sources.SOURCES_DISPONIBLES["choisirleservicepublic"],
        parametres_sources.SOURCES_DISPONIBLES["emploiterritorial"],
    ]


def test_executer_emet_progression_nommee_et_source_terminee(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
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

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _csp)
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None, on_fiche=None: ([], 1, False),
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
        on_fiche: Callable[[int, int], None] | None = None,
    ) -> None:
        raise RuntimeError("HTTP 503")

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _echec)
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None, on_fiche=None: ([_offre("O2")], 1, False),
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


# --- exceptions inattendues : le thread doit toujours se terminer ---


def test_recherche_exception_inattendue_emet_une_erreur(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.gui import travailleurs as travailleurs_module

    def casse(*_args: object, **_kwargs: object) -> None:
        raise KeyError("imprévu")

    monkeypatch.setattr(travailleurs_module, "rechercher_toutes_sources", casse)
    erreurs: list[str] = []
    travailleur = TravailleurRecherche({}, {})
    travailleur.erreur.connect(erreurs.append)
    travailleur.executer()

    assert erreurs == [travailleurs_module.MESSAGE_INATTENDU]


def test_verificateur_disponibilite_une_offre_inattendue_ne_bloque_pas_les_autres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.gui import travailleurs as travailleurs_module

    def verifier(url: str) -> bool:
        if url.endswith("/mauvaise"):
            raise ValueError("adresse invalide")
        return True

    monkeypatch.setattr(travailleurs_module, "verifier_disponibilite", verifier)
    candidatures = {
        "A": {"offre_url": "https://exemple.test/bonne"},
        "B": {"offre_url": "https://exemple.test/mauvaise"},
    }
    resultats: list[tuple[dict[str, bool], dict[str, str]]] = []
    verificateur = travailleurs_module.VerificateurDisponibilite(
        candidatures  # type: ignore[arg-type]
    )
    verificateur.resultat.connect(lambda ok, ko: resultats.append((ok, ko)))
    verificateur.executer()

    assert resultats == [({"A": True}, {"B": "ValueError"})]


def test_verificateur_maj_exception_inattendue_emet_un_echec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.gui import travailleurs as travailleurs_module

    def casse() -> None:
        raise TypeError("imprévu")

    monkeypatch.setattr(travailleurs_module, "verifier_derniere_publication", casse)
    echecs: list[str] = []
    verificateur = VerificateurMiseAJour()
    verificateur.echec.connect(echecs.append)
    verificateur.executer()

    assert echecs == [travailleurs_module.MESSAGE_INATTENDU]


def test_verificateur_maj_marqueur_non_ecrit_n_empeche_pas_l_annonce(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.gui import travailleurs as travailleurs_module

    def refuse(_info: InfoMaj) -> None:
        raise PermissionError("fichier tenu")

    monkeypatch.setattr(
        travailleurs_module, "verifier_derniere_publication", lambda: _INFO_MAJ_TEST
    )
    monkeypatch.setattr(travailleurs_module, "ecrire_maj_disponible", refuse)
    resultats: list[InfoMaj | None] = []
    verificateur = VerificateurMiseAJour()
    verificateur.resultat.connect(resultats.append)
    verificateur.executer()

    assert resultats == [_INFO_MAJ_TEST]


def test_tache_reseau_exception_inattendue_emet_un_echec() -> None:
    from src.gui import travailleurs as travailleurs_module

    def casse() -> None:
        raise AttributeError("imprévu")

    echecs: list[str] = []
    tache = travailleurs_module.TacheReseau(casse)
    tache.echec.connect(echecs.append)
    tache.executer()

    assert echecs == [travailleurs_module.MESSAGE_INATTENDU]
