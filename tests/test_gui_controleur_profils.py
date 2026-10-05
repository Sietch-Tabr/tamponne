"""Tests de src/gui/controleur_profils.py : fiches exposées au QML et
actions de l'écran Profils."""

import threading
from datetime import date

import pytest
from PySide6.QtCore import QModelIndex
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from src import profils
from src.gui import travailleurs
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
                "nouvelles_le": "2026-10-04",
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
    assert _valeur(controleur, 0, b"dateNouvelles") == "04/10/26"
    assert _valeur(controleur, 1, b"intitule") == "hospitalier-achats"
    assert _valeur(controleur, 1, b"nouvelles") == ""
    assert _valeur(controleur, 1, b"lignes") == [
        "Cat. A · tous versants",
        "Toute la France",
        "mot-clé «\u00a0achat\u00a0»",
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


@pytest.mark.usefixtures("deux_fiches")
def test_rafraichir_memes_fiches_met_a_jour_sans_reinitialiser(
    qapp: QApplication, qtbot: QtBot
) -> None:
    controleur = ControleurProfils(qapp)
    modele = _modele(controleur)
    profils.mettre_a_jour_stats("hospitalier-achats", 4, consultation=False)
    with qtbot.assertNotEmitted(modele.modelReset):
        with qtbot.waitSignal(modele.dataChanged, timeout=1000):
            controleur.rafraichir()
    assert _valeur(controleur, 1, b"nouvelles") == "4 nouvelles"


@pytest.mark.usefixtures("deux_fiches")
def test_lancer_releve_rafraichit_chaque_fiche_relevee(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    def relever(nom: str, *_args: object) -> int:
        profils.mettre_a_jour_stats(nom, 5, consultation=False)
        return 5

    monkeypatch.setattr(travailleurs, "relever_fiche", relever)
    controleur = ControleurProfils(qapp)
    controleur.lancer_releve({}, date.today())
    qtbot.waitUntil(
        lambda: _valeur(controleur, 1, b"nouvelles") == "5 nouvelles", timeout=3000
    )
    controleur.arreter()
    assert _valeur(controleur, 0, b"nouvelles") == "5 nouvelles"


def test_ecritures_concurrentes_des_profils_sans_perte(qapp: QApplication) -> None:
    profils.sauvegarder_profils({"base": {"label": "base"}})

    def ajouter(rang: int) -> None:
        profils.ajouter_profil(f"fiche-{rang}", {"label": str(rang)})
        profils.mettre_a_jour_stats("base", rang, consultation=False)

    fils = [threading.Thread(target=ajouter, args=(rang,)) for rang in range(20)]
    for fil in fils:
        fil.start()
    for fil in fils:
        fil.join()
    assert len(profils.charger_profils()) == 21
