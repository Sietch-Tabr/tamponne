"""Tests de src/releve.py et du travailleur `ReleveFiches` : relevé
quotidien des nouvelles des fiches, sans réseau."""

from datetime import date
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from src import cache, parametres_sources, profils, releve
from src.gui import travailleurs
from src.gui.travailleurs import ReleveFiches
from src.recherche import RechercheImpossible, RechercheInterrompue
from src.types import FiltresRecherche, Offre, Organisations, Profil

AUJOURD_HUI = date(2026, 10, 5)


@pytest.fixture(autouse=True)
def _donnees(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    monkeypatch.setattr(cache, "CHEMIN_OFFRES", tmp_path / "offres.json")


def _offre(reference: str) -> Offre:
    return {
        "titre": f"Offre {reference}",
        "url": f"https://example.org/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": "",
        "localisation": "",
        "versant": "",
        "date": "",
        "source": "",
    }


def test_fiches_a_relever_ignore_celles_comptees_aujourd_hui() -> None:
    fiches: dict[str, Profil] = {
        "jamais": {"label": "jamais"},
        "hier": {"nouvelles_le": "2026-10-04"},
        "aujourd-hui": {"nouvelles_le": "2026-10-05"},
    }
    assert releve.fiches_a_relever(fiches, AUJOURD_HUI) == ["jamais", "hier"]


def test_filtres_de_la_fiche_sans_metadonnees_et_versant_historique() -> None:
    fiche: Profil = {
        "label": "Attaché",
        "categories": ["A"],
        "query": "chef",
        "nb_nouvelles": 3,
        "versant": "hospitalier",  # type: ignore[typeddict-unknown-key]
    }
    assert releve.filtres_de_la_fiche(fiche) == {
        "categories": ["A"],
        "query": "chef",
        "versants": ["hospitalier"],
    }


def test_relever_fiche_compte_sans_consulter(monkeypatch: pytest.MonkeyPatch) -> None:
    profils.ajouter_profil("p", {"label": "p", "grades": []})
    recus: list[FiltresRecherche] = []

    def rechercher(
        filtres: FiltresRecherche, orgas: Organisations, **_options: object
    ) -> tuple[list[Offre], int, bool]:
        recus.append(filtres)
        return [_offre("O1"), _offre("O2")], 1, False

    monkeypatch.setattr(releve, "rechercher_toutes_sources", rechercher)
    assert releve.relever_fiche("p", profils.charger_profils()["p"], {}, lambda: False) == 2
    assert recus[0].get("versants") == ["etat"]
    assert profils.charger_profils()["p"].get("nb_nouvelles") == 2
    # Toujours non consultées au relevé suivant.
    assert releve.relever_fiche("p", profils.charger_profils()["p"], {}, lambda: False) == 2


def _executer(releve_fiches: ReleveFiches, qtbot: QtBot) -> list[str]:
    relevees: list[str] = []
    releve_fiches.fiche_relevee.connect(relevees.append)
    with qtbot.waitSignal(releve_fiches.termine, timeout=2000):
        releve_fiches.executer()
    return relevees


def test_releve_fiches_parcourt_les_fiches_du_jour(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    profils.sauvegarder_profils(
        {"a": {"label": "a"}, "b": {"label": "b", "nouvelles_le": "2026-10-05"}, "c": {}}
    )
    monkeypatch.setattr(travailleurs, "relever_fiche", lambda nom, *_args: 1)
    assert _executer(ReleveFiches({}, AUJOURD_HUI), qtbot) == ["a", "c"]


def test_releve_fiches_continue_apres_une_fiche_en_echec(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    profils.sauvegarder_profils({"a": {}, "b": {}})

    def relever(nom: str, *_args: object) -> int:
        if nom == "a":
            raise RechercheImpossible("sources indisponibles")
        return 1

    monkeypatch.setattr(travailleurs, "relever_fiche", relever)
    assert _executer(ReleveFiches({}, AUJOURD_HUI), qtbot) == ["b"]


def test_releve_fiches_s_arrete_sans_source_active(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    profils.sauvegarder_profils({"a": {}, "b": {}})
    parametres_sources.sauvegarder_sources_actives(
        {cle: False for cle in parametres_sources.SOURCES_DISPONIBLES}
    )
    appels: list[str] = []

    def relever(nom: str, *_args: object) -> int:
        appels.append(nom)
        raise RechercheImpossible("Aucune source cochée")

    monkeypatch.setattr(travailleurs, "relever_fiche", relever)
    assert _executer(ReleveFiches({}, AUJOURD_HUI), qtbot) == []
    assert appels == ["a"]


def test_releve_fiches_interrompu(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    profils.sauvegarder_profils({"a": {}, "b": {}})
    releve_fiches = ReleveFiches({}, AUJOURD_HUI)

    def relever(nom: str, _profil: Profil, _orgas: Organisations, doit_arreter: object) -> int:
        releve_fiches.arreter()
        assert callable(doit_arreter) and doit_arreter()
        raise RechercheInterrompue

    monkeypatch.setattr(travailleurs, "relever_fiche", relever)
    assert _executer(releve_fiches, qtbot) == []


def test_relever_fiche_respecte_les_grades_superieurs(monkeypatch: pytest.MonkeyPatch) -> None:
    idiv = {**_offre("O1"), "titre": "IDIV Chef de service"}
    monkeypatch.setattr(
        releve, "rechercher_toutes_sources", lambda *_a, **_k: ([idiv], 1, False)
    )
    profils.ajouter_profil("exclus", {"label": "e"})
    profils.ajouter_profil("inclus", {"label": "i", "grades_superieurs": True})
    fiches = profils.charger_profils()
    assert releve.relever_fiche("exclus", fiches["exclus"], {}, lambda: False) == 0
    assert releve.relever_fiche("inclus", fiches["inclus"], {}, lambda: False) == 1
