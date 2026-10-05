"""Tests de src/profils.py : modification, statistiques et lecture des
fiches enregistrées sous d'anciens formats."""

from datetime import date

from src import profils


def test_modifier_profil_garde_intitule_et_dates_efface_le_compte() -> None:
    profils.sauvegarder_profils(
        {
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
    )
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


def test_mettre_a_jour_stats_profil_supprime_ignore() -> None:
    profils.mettre_a_jour_stats("absent", 3)
    assert profils.charger_profils() == {}


def test_categories_compatibles_cle_et_libelle_court_sans_doublon() -> None:
    assert profils.categories_compatibles(
        {"categories": ["A+ (autres)", "A+ (autres emplois fonctionnels)", "C"]}
    ) == ["A+ (autres emplois fonctionnels)", "C"]
