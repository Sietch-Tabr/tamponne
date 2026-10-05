"""Tests de src/gui/controleur_recherche.py avec des sources factices
(aucun appel réseau) : formulaire, recherche en QThread, registre,
classement en profil, mode édition et actions sur une offre."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from src import parametres_sources, profils
from src.gui import controleur_recherche
from src.filtres import CATEGORIES
from src.gui.controleur_recherche import ControleurRecherche
from src.gui.modele_offres import ProxyOffres
from src.profils import versants_compatibles
from src.sources.choisirleservicepublic import ChoisirLeServicePublic
from src.sources.emploiterritorial import EmploiTerritorial
from src.types import FiltresRecherche, Offre


def _offre(
    reference: str, titre: str, date: str = "02/10/2026", source: str = ""
) -> Offre:
    return {
        "titre": titre,
        "url": f"https://example.org/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": "Préfecture de région",
        "localisation": "Paris (75)",
        "versant": "",
        "date": date,
        "source": source,
    }


@pytest.fixture(autouse=True)
def _sources_factices(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    parametres_sources.sauvegarder_sources_actives(
        {"passerellesmef": False, "fhf": False}
    )

    def _csp(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        assert on_page is not None
        on_page(1, 2)
        on_page(2, 2)
        return (
            [
                _offre("MINT_2026-1", "Attaché(e) d'administration RH", "01/10/2026"),
                _offre("2026-2", "IDIV adjoint"),
            ],
            2,
            False,
        )

    def _territorial(
        self: object,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        return (
            [
                _offre(
                    "T3",
                    "Responsable du service finances",
                    "30/09/2026",
                    "Fonction publique territoriale",
                )
            ],
            1,
            False,
        )

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _csp)
    monkeypatch.setattr(EmploiTerritorial, "rechercher", _territorial)


@pytest.fixture
def controleur(qapp: QApplication) -> Iterator[ControleurRecherche]:
    resultat = ControleurRecherche({"Ministère": {"Direction des achats": 1}}, qapp)
    yield resultat
    resultat.arreter()


def _attendre(controleur: ControleurRecherche, qtbot: QtBot) -> None:
    qtbot.waitUntil(lambda: controleur.property("phase") != "en_cours", timeout=5000)
    qtbot.waitUntil(
        lambda: controleur.property("texte_bouton") == "Lancer la recherche",
        timeout=5000,
    )


def _cellule(controleur: ControleurRecherche, ligne: int, colonne: int) -> object:
    modele = controleur.property("modele")
    assert isinstance(modele, ProxyOffres)
    return modele.data(
        modele.index(ligne, colonne, QModelIndex()), Qt.ItemDataRole.DisplayRole
    )


def test_formulaire_par_defaut_et_libelles_de_selection(
    controleur: ControleurRecherche,
) -> None:
    etat = controleur.property("etat")
    assert etat["versants"] == ["etat"]
    assert etat["libelle_domaines"] == "tous"
    controleur.definir("localisations", ["Île-de-France"])
    controleur.definir("domaines", ["Achats", "Finances"])
    etat = controleur.property("etat")
    assert etat["libelle_localisations"] == "Île-de-France"
    assert etat["libelle_domaines"] == "2 cochés"
    controleur.basculer("categories", "A", True)
    controleur.basculer("versants", "etat", False)
    filtres = controleur.construire_filtres()
    assert filtres.get("categories") == ["A"]
    assert filtres.get("versants") == []
    controleur.reinitialiser()
    assert controleur.property("etat")["categories"] == []


def test_groupes_selection_des_organisations_et_des_grades(
    controleur: ControleurRecherche,
) -> None:
    organisations = controleur.groupes_selection("organisations")
    assert organisations == [
        {
            "groupe": "Ministère",
            "elements": [
                {
                    "valeur": "Ministère - Direction des achats",
                    "libelle": "Direction des achats",
                }
            ],
        }
    ]
    grades = controleur.groupes_selection("grades")
    assert grades[0]["groupe"] == "Attaché"
    assert controleur.groupes_selection("inconnue") == []


def test_recherche_remplit_le_registre_et_le_resume(
    controleur: ControleurRecherche, qtbot: QtBot
) -> None:
    # Le versant par défaut (État seul) exclut la source territoriale.
    controleur.definir("versants", ["etat", "territorial"])
    controleur.lancer()
    assert controleur.property("phase") == "en_cours"
    _attendre(controleur, qtbot)

    assert controleur.property("phase") == "resultats"
    resume = controleur.property("resume")
    assert resume.startswith("2 inscrites · 1 écartée (grades supérieurs) · ")
    avancement = {a["nom"]: a["etat"] for a in controleur.property("avancement")}
    assert set(avancement.values()) == {"terminé · 2 offres", "terminé · 1 offre"}
    assert _cellule(controleur, 0, 0) == "001"
    assert _cellule(controleur, 0, 1) == "Attaché(e) d'administration RH"
    assert _cellule(controleur, 0, 4) == "01/10/26"
    assert _cellule(controleur, 1, 5) == "Fonction publique territoriale"


def test_tri_puis_filtre_du_registre(
    controleur: ControleurRecherche, qtbot: QtBot
) -> None:
    # Le versant par défaut (État seul) exclut la source territoriale.
    controleur.definir("versants", ["etat", "territorial"])
    controleur.lancer()
    _attendre(controleur, qtbot)
    controleur.trier(4)
    assert controleur.property("tri") == {"colonne": 4, "ordre": 0}
    assert _cellule(controleur, 0, 1) == "Responsable du service finances"
    controleur.trier(4)
    assert controleur.property("tri") == {"colonne": 4, "ordre": 1}
    controleur.filtrer("finances")
    modele = controleur.property("modele")
    assert isinstance(modele, ProxyOffres)
    assert modele.rowCount() == 1


def test_classer_en_profil_refuse_nom_vide_ou_existant(
    controleur: ControleurRecherche,
) -> None:
    profils.sauvegarder_profils({"existante": {}})
    assert controleur.classer("  ", "") == "Donner un nom à la fiche."
    assert controleur.classer("existante", "") == "Une fiche porte déjà ce nom."
    controleur.basculer("categories", "A", True)
    assert controleur.classer("nouvelle", "Mon intitulé") == ""
    fiche = profils.charger_profils()["nouvelle"]
    assert fiche.get("label") == "Mon intitulé"
    assert fiche.get("categories") == ["A"]


def test_edition_enregistre_la_fiche_et_retourne_aux_profils(
    controleur: ControleurRecherche,
) -> None:
    profils.sauvegarder_profils(
        {"fiche": {"label": "Ma fiche", "versant": "__tous__"}}  # type: ignore[typeddict-unknown-key]
    )
    retours: list[bool] = []
    controleur.retour_profils.connect(lambda: retours.append(True))
    controleur.modifier_profil("fiche")
    assert controleur.property("edition") is True
    assert controleur.property("texte_bouton") == "Enregistrer la fiche"
    assert controleur.property("intitule_edition") == "Ma fiche"
    assert controleur.property("etat")["versants"] == []
    controleur.basculer("categories", "B", True)
    controleur.valider()
    assert profils.charger_profils()["fiche"].get("categories") == ["B"]
    assert controleur.property("edition") is False
    assert retours == [True]


def test_consulter_et_tamponner_passent_par_un_thread(
    controleur: ControleurRecherche, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    detail = dict.fromkeys(
        (
            "description",
            "salaire",
            "experience_requise",
            "formation_requise",
            "secteur",
            "date_publication",
            "a_propos_employeur",
            "page_html",
            "lien_postuler",
            "date_limite",
        ),
        "",
    )
    detail["description"] = "Missions."
    monkeypatch.setattr(
        controleur_recherche, "recuperer_detail_offre", lambda url: detail
    )
    suivis: list[str] = []
    monkeypatch.setattr(
        controleur_recherche,
        "suivre_offre",
        lambda offre: suivis.append(offre["reference"]),
    )

    controleur.lancer()
    _attendre(controleur, qtbot)
    controleur.selectionner(0)
    with qtbot.waitSignal(controleur.detail_pret, timeout=5000) as signal:
        controleur.consulter()
    assert signal.args is not None and signal.args[0]["description"] == "Missions."
    with qtbot.waitSignal(controleur.suivi_termine, timeout=5000) as signal:
        controleur.tamponner_pour_suivi()
    assert signal.args == ["Attaché(e) d'administration RH"]
    assert suivis == ["MINT_2026-1"]


def test_versants_compatibles_lit_l_ancien_format_singulier() -> None:
    assert versants_compatibles({}) == ["etat"]
    assert versants_compatibles({"versants": ["territorial"]}) == ["territorial"]
    ancien: FiltresRecherche = {}
    ancien["versant"] = "hospitalier"  # type: ignore[typeddict-unknown-key]
    assert versants_compatibles(ancien) == ["hospitalier"]


def test_numero_de_selection_suit_le_registre_apres_tri(
    controleur: ControleurRecherche, qtbot: QtBot
) -> None:
    controleur.definir("versants", ["etat", "territorial"])
    controleur.lancer()
    _attendre(controleur, qtbot)
    assert controleur.property("numero_selection") == ""
    controleur.trier(4)
    controleur.selectionner(0)
    assert controleur.property("numero_selection") == "002"


def test_categorie_a_plus_autres_envoie_la_cle_connue_des_sources(
    qapp: QApplication,
) -> None:
    controleur = ControleurRecherche({}, qapp)
    choix = controleur.property("choix")["categories"]
    assert {"cle": "A+ (autres emplois fonctionnels)", "libelle": "A+ (autres)"} in choix
    assert all(c["cle"] in CATEGORIES for c in choix)
    controleur.basculer("categories", "A+ (autres emplois fonctionnels)", True)
    assert controleur.construire_filtres().get("categories") == [
        "A+ (autres emplois fonctionnels)"
    ]


def test_fiche_classee_avec_le_libelle_court_relue_avec_la_cle(qapp: QApplication) -> None:
    profils.sauvegarder_profils({"f": {"categories": ["A+ (autres)", "A"]}})
    controleur = ControleurRecherche({}, qapp)
    controleur.modifier_profil("f")
    assert controleur.construire_filtres().get("categories") == [
        "A+ (autres emplois fonctionnels)",
        "A",
    ]


def test_enregistrer_une_fiche_modifiee_garde_son_intitule(qapp: QApplication) -> None:
    profils.sauvegarder_profils(
        {"f": {"label": "Attaché, Paris", "cree_le": "2026-01-02", "categories": ["A"]}}
    )
    controleur = ControleurRecherche({}, qapp)
    controleur.modifier_profil("f")
    controleur.basculer("categories", "B", True)
    controleur.valider()
    fiche = profils.charger_profils()["f"]
    assert fiche.get("label") == "Attaché, Paris"
    assert fiche.get("categories") == ["A", "B"]


def test_grades_superieurs_enregistres_avec_la_fiche_et_relus(qapp: QApplication) -> None:
    controleur = ControleurRecherche({}, qapp)
    controleur.definir("grades_superieurs", True)
    assert controleur.classer("f", "Fiche") == ""
    assert profils.charger_profils()["f"].get("grades_superieurs") is True
    autre = ControleurRecherche({}, qapp)
    autre.modifier_profil("f")
    assert autre.property("etat")["grades_superieurs"] is True
