"""Tests de src/gui/controleur_profils.py : fiches exposées au QML et
actions de l'écran Profils."""

import pytest
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication

from src import profils
from src.gui.controleur_profils import ControleurProfils, ModeleFiches


@pytest.fixture
def deux_fiches() -> None:
    profils.sauvegarder_profils(
        {
            "attache-paris": {
                "label": "Attaché, Paris et petite couronne",
                "categories": ["A"],
                "versants": ["etat"],
                "nb_nouvelles": 2,
            },
            "hospitalier-achats": {"categories": ["A"], "query": "achat"},
        }
    )


def _modele(controleur: ControleurProfils) -> ModeleFiches:
    modele = controleur.property("modele")
    assert isinstance(modele, ModeleFiches)
    return modele


def _valeur(controleur: ControleurProfils, ligne: int, nom: bytes) -> object:
    modele = _modele(controleur)
    role = next(r for r, n in modele.roleNames().items() if n.data() == nom)
    return modele.data(modele.index(ligne, 0, QModelIndex()), role)


@pytest.mark.usefixtures("deux_fiches")
def test_fiches_exposent_intitule_resume_et_nouvelles(qapp: QApplication) -> None:
    controleur = ControleurProfils(qapp)
    assert controleur.property("texte_nombre") == "2 fiches classées"
    assert _valeur(controleur, 0, b"intitule") == "Attaché, Paris et petite couronne"
    assert _valeur(controleur, 0, b"nouvelles") == "2 nouvelles"
    assert _valeur(controleur, 1, b"intitule") == "hospitalier-achats"
    assert _valeur(controleur, 1, b"nouvelles") == ""
    assert _valeur(controleur, 1, b"lignes") == [
        "Cat. A · tous versants",
        "Toute la France",
        "mot-clé « achat »",
    ]


@pytest.mark.usefixtures("deux_fiches")
def test_dupliquer_refuse_nom_vide_ou_existant(qapp: QApplication) -> None:
    controleur = ControleurProfils(qapp)
    assert (
        controleur.dupliquer("attache-paris", "  ", "")
        == "Donner un nom à la nouvelle fiche."
    )
    assert controleur.dupliquer("attache-paris", "hospitalier-achats", "") == (
        "Une fiche porte déjà ce nom."
    )
    assert (
        controleur.dupliquer("absente", "copie", "") == "La fiche d'origine n'existe plus."
    )
    assert controleur.dupliquer("attache-paris", " attache-copie ", "") == ""
    assert "attache-copie" in profils.charger_profils()
    assert controleur.property("nombre") == 3


@pytest.mark.usefixtures("deux_fiches")
def test_supprimer_retire_la_fiche(qapp: QApplication) -> None:
    controleur = ControleurProfils(qapp)
    controleur.supprimer("attache-paris")
    assert list(profils.charger_profils()) == ["hospitalier-achats"]
    assert controleur.property("nombre") == 1


@pytest.mark.usefixtures("deux_fiches")
def test_lancer_et_modifier_emettent_le_nom_si_la_fiche_existe(
    qapp: QApplication,
) -> None:
    controleur = ControleurProfils(qapp)
    lances: list[str] = []
    modifies: list[str] = []
    controleur.lancement_demande.connect(lances.append)
    controleur.modification_demandee.connect(modifies.append)
    controleur.lancer("attache-paris")
    controleur.lancer("absente")
    controleur.modifier("hospitalier-achats")
    assert lances == ["attache-paris"]
    assert modifies == ["hospitalier-achats"]
    assert controleur.intitule("attache-paris") == "Attaché, Paris et petite couronne"
    assert controleur.intitule("absente") == ""
