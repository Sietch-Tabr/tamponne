"""Tests de src/profils.py : modification, date de lancement et lecture
des fiches enregistrées sous d'anciens formats."""

from datetime import date
from typing import Any, cast

from src import profils
from src.types import Profil


def test_modifier_profil_garde_intitule_et_dates_retire_les_anciens_comptes() -> None:
    # Compte de nouvelles écrit par une version de développement, abandonné depuis.
    ancien_format: dict[str, Any] = {
        "f": {
            "label": "Attaché, Paris",
            "cree_le": "2026-01-02",
            "dernier_lancement": "2026-10-01",
            "nb_nouvelles": 4,
            "nouvelles_le": "2026-10-04",
            "categories": ["A"],
            "query": "ancien",
        }
    }
    profils.sauvegarder_profils(cast(dict[str, Profil], ancien_format))
    profils.modifier_profil("f", {"categories": ["B"]})
    assert profils.charger_profils()["f"] == {
        "label": "Attaché, Paris",
        "cree_le": "2026-01-02",
        "dernier_lancement": "2026-10-01",
        "categories": ["B"],
    }


def test_modifier_profil_inexistant_le_cree_date_du_jour() -> None:
    profils.modifier_profil("neuf", {"categories": ["A"]})
    assert profils.charger_profils()["neuf"] == {
        "cree_le": date.today().isoformat(),
        "categories": ["A"],
    }


def test_noter_lancement_date_du_jour_et_fiche_supprimee_ignoree() -> None:
    profils.sauvegarder_profils({"f": {"label": "F"}})
    profils.noter_lancement("f")
    profils.noter_lancement("absente")
    assert profils.charger_profils() == {
        "f": {"label": "F", "dernier_lancement": date.today().isoformat()}
    }


def test_categories_compatibles_cle_et_libelle_court_sans_doublon() -> None:
    assert profils.categories_compatibles(
        {"categories": ["A+ (autres)", "A+ (autres emplois fonctionnels)", "C"]}
    ) == ["A+ (autres emplois fonctionnels)", "C"]
