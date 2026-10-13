"""Tests de src/gui/controleur_suivi.py : dossiers exposés au QML,
vérification en arrière-plan (QThread) et actions."""

import pytest
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from src import candidatures
from src.gui import travailleurs
from src.gui.controleur_suivi import (
    LIBELLE_VERIFIER,
    ControleurSuivi,
    ModeleDossiers,
    nombre_dossiers,
    titre_ecran,
)
from src.types import Candidature


def _candidature(titre: str, url: str = "https://example.org/offre") -> Candidature:
    return {
        "offre_titre": titre,
        "offre_employeur": "Préfecture de région",
        "offre_url": url,
        "offre_reference": titre,
        "offre_domaine": "",
        "offre_localisation": "Paris 75",
        "offre_versant": "",
        "offre_date": "",
        "date_candidature": "2026-09-11",
        "historique": [
            {"date": "2026-09-11", "type": "candidature_envoyee", "note": ""}
        ],
        "disponible": True,
        "derniere_verification": "",
        "detail": {
            "description": "",
            "salaire": "",
            "experience_requise": "",
            "formation_requise": "",
            "secteur": "",
            "date_publication": "",
            "a_propos_employeur": "",
            "sections_complementaires": {},
            "page_html": "",
            "lien_postuler": "",
            "date_limite": "",
        },
    }


def _modele(controleur: ControleurSuivi) -> ModeleDossiers:
    modele = controleur.property("modele")
    assert isinstance(modele, ModeleDossiers)
    return modele


def _valeur(controleur: ControleurSuivi, ligne: int, nom: bytes) -> object:
    modele = _modele(controleur)
    role = next(r for r, n in modele.roleNames().items() if n.data() == nom)
    return modele.data(modele.index(ligne, 0, QModelIndex()), role)


@pytest.fixture
def deux_dossiers() -> None:
    candidatures.sauvegarder_candidatures(
        {"REF-A": _candidature("Premier suivi"), "REF-B": _candidature("Dernier suivi")}
    )


def test_nombre_dossiers_accorde_au_pluriel() -> None:
    assert nombre_dossiers(1) == "1 candidature suivie"
    assert nombre_dossiers(3) == "3 candidatures suivies"


@pytest.mark.usefixtures("deux_dossiers")
def test_rafraichir_expose_dossier_le_plus_recent_en_premier(
    qapp: QApplication,
) -> None:
    controleur = ControleurSuivi(qapp)
    assert controleur.property("nombre") == 2
    assert _valeur(controleur, 0, b"titre") == "Dernier suivi"
    assert _valeur(controleur, 0, b"statut") == "candidature envoyée le 11/09/2026"
    tampons = _valeur(controleur, 0, b"tampons")
    assert isinstance(tampons, list) and tampons[0]["libelle"] == "Envoyée"


@pytest.mark.usefixtures("deux_dossiers")
def test_verifier_offres_relaie_progression_et_marque_depubliee(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    textes: list[str] = []
    monkeypatch.setattr(travailleurs, "verifier_disponibilite", lambda _url: False)
    controleur = ControleurSuivi(qapp)
    controleur.etat_change.connect(
        lambda: textes.append(controleur.property("texte_verification"))
    )

    controleur.verifier_offres()
    assert controleur.property("verification_en_cours") is True
    qtbot.waitUntil(
        lambda: not controleur.property("verification_en_cours"), timeout=5000
    )

    assert "Vérification… 2/2" in textes
    assert controleur.property("texte_verification") == LIBELLE_VERIFIER
    assert all(
        not c["disponible"] for c in candidatures.charger_candidatures().values()
    )
    assert _valeur(controleur, 0, b"disponible") is False


@pytest.mark.usefixtures("deux_dossiers")
def test_verifier_offres_echec_reseau_signale_sans_rien_conclure(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    def injoignable(_url: str) -> bool:
        raise RuntimeError("Erreur réseau lors du chargement")

    monkeypatch.setattr(travailleurs, "verifier_disponibilite", injoignable)
    controleur = ControleurSuivi(qapp)
    controleur.verifier_offres()
    qtbot.waitUntil(
        lambda: not controleur.property("verification_en_cours"), timeout=5000
    )
    assert all(c["disponible"] for c in candidatures.charger_candidatures().values())
    assert controleur.property("avertissement").startswith("2 offres non vérifiées")
    assert controleur.property("avertissement").endswith(
        "Détail\u00a0: Erreur réseau lors du chargement"
    )


@pytest.mark.usefixtures("deux_dossiers")
def test_verifier_offres_sans_echec_sans_avertissement(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(travailleurs, "verifier_disponibilite", lambda _url: True)
    controleur = ControleurSuivi(qapp)
    controleur.verifier_offres()
    qtbot.waitUntil(
        lambda: not controleur.property("verification_en_cours"), timeout=5000
    )
    assert controleur.property("avertissement") == ""


@pytest.mark.usefixtures("deux_dossiers")
def test_ajouter_evenement_met_a_jour_le_statut(qapp: QApplication) -> None:
    controleur = ControleurSuivi(qapp)
    controleur.ajouter_evenement("REF-B", "entretien_planifie", "2026-10-01", " visio ")
    assert (
        _valeur(controleur, 0, b"statut") == "entretien planifié le 01/10/2026 (visio)"
    )


@pytest.mark.usefixtures("deux_dossiers")
def test_ajouter_evenement_ignore_type_inconnu_et_dossier_absent(
    qapp: QApplication,
) -> None:
    controleur = ControleurSuivi(qapp)
    controleur.ajouter_evenement("REF-B", "inconnu", "2026-10-01", "")
    controleur.ajouter_evenement("REF-ABSENTE", "relance", "2026-10-01", "")
    assert len(candidatures.charger_candidatures()["REF-B"]["historique"]) == 1


@pytest.mark.usefixtures("deux_dossiers")
def test_supprimer_retire_le_dossier(qapp: QApplication) -> None:
    controleur = ControleurSuivi(qapp)
    controleur.supprimer("REF-A")
    assert controleur.property("nombre") == 1
    assert "REF-A" not in candidatures.charger_candidatures()


def test_types_evenement_reprennent_les_huit_types(qapp: QApplication) -> None:
    types = ControleurSuivi(qapp).property("types_evenement")
    assert [t["cle"] for t in types] == list(candidatures.TYPES_EVENEMENT)


def test_modele_ignore_role_inconnu(qapp: QApplication) -> None:
    modele = _modele(ControleurSuivi(qapp))
    index = modele.index(0, 0, QModelIndex())
    assert modele.data(index, Qt.ItemDataRole.DisplayRole) is None


@pytest.mark.usefixtures("deux_dossiers")
def test_detail_renvoie_fiche_archivee_et_vide_si_absent(qapp: QApplication) -> None:
    controleur = ControleurSuivi(qapp)
    fiche = controleur.detail("REF-A")
    assert fiche["titre"] == "Premier suivi"
    assert fiche["sousTitre"] == "Préfecture de région · Paris 75"
    assert fiche["peutPostuler"] is False
    assert fiche["enLigne"] is True
    assert controleur.detail("REF-ABSENTE") == {}


def test_titre_au_pluriel_seulement_s_il_y_a_plusieurs_dossiers() -> None:
    assert titre_ecran(0) == "Dossier en cours"
    assert titre_ecran(1) == "Dossier en cours"
    assert titre_ecran(2) == "Dossiers en cours"


@pytest.mark.usefixtures("deux_dossiers")
def test_ajout_d_un_evenement_en_double_est_refuse(qapp: QApplication) -> None:
    controleur = ControleurSuivi(qapp)
    erreur = controleur.ajouter_evenement(
        "REF-B", "candidature_envoyee", "2026-09-11", ""
    )
    assert erreur == (
        "Déjà tamponné\u00a0: un événement «\u00a0Candidature envoyée\u00a0» existe à cette date."
    )
    assert len(candidatures.charger_candidatures()["REF-B"]["historique"]) == 1


@pytest.mark.usefixtures("deux_dossiers")
def test_modifier_puis_supprimer_un_evenement(qapp: QApplication) -> None:
    controleur = ControleurSuivi(qapp)
    assert controleur.ajouter_evenement("REF-B", "relance", "2026-09-30", "") == ""
    assert controleur.evenement("REF-B", 1)["libelle"] == "Relance"
    assert controleur.modifier_evenement(
        "REF-B", 1, "candidature_envoyee", "2026-09-11", ""
    ) == (
        "Déjà tamponné\u00a0: un événement «\u00a0Candidature envoyée\u00a0» existe à cette date."
    )
    assert (
        controleur.modifier_evenement(
            "REF-B", 1, "accuse_reception", "2026-09-30", "ok"
        )
        == ""
    )
    assert (
        candidatures.charger_candidatures()["REF-B"]["historique"][1]["type"]
        == "accuse_reception"
    )
    controleur.supprimer_evenement("REF-B", 1)
    assert len(candidatures.charger_candidatures()["REF-B"]["historique"]) == 1
    assert controleur.evenement("REF-B", 7) == {}


@pytest.mark.usefixtures("deux_dossiers")
def test_proposition_suit_le_dernier_evenement(qapp: QApplication) -> None:
    controleur = ControleurSuivi(qapp)
    assert controleur.proposition("REF-B") == {
        "type": "accuse_reception",
        "date": "2026-09-11",
    }
    assert controleur.proposition("REF-ABSENTE") == {}
