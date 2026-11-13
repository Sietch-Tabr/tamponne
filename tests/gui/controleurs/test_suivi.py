"""Tests de src/gui/controleurs/suivi.py : dossiers exposés au QML,
vérification en arrière-plan (QThread) et actions."""

from datetime import date
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from src.donnees import candidatures
from src.gui import travailleurs
from src.gui.controleurs.suivi import (
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
    monkeypatch.setattr(
        travailleurs, "verifier_disponibilite", Mock(return_value=False)
    )
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
    monkeypatch.setattr(travailleurs, "verifier_disponibilite", Mock(return_value=True))
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


def _sauver(*dossiers: Candidature) -> None:
    candidatures.sauvegarder_candidatures({c["offre_reference"]: c for c in dossiers})


def _attendre_fin(qtbot: QtBot, controleur: ControleurSuivi) -> None:
    qtbot.waitUntil(
        lambda: not controleur.property("verification_en_cours"), timeout=5000
    )


def test_verification_automatique_ne_regarde_que_les_dossiers_ouverts_non_verifies(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    ouvert = _candidature("OUVERT", "https://example.org/ouvert")
    clos = _candidature("CLOS", "https://example.org/clos")
    clos["historique"].append({"date": "2026-09-20", "type": "refus", "note": ""})
    deja = _candidature("DEJA", "https://example.org/deja")
    deja["derniere_verification"] = date.today().isoformat()
    _sauver(ouvert, clos, deja)
    verifiees: list[str] = []

    def verifier(url: str) -> bool:
        verifiees.append(url)
        return False

    monkeypatch.setattr(travailleurs, "verifier_disponibilite", verifier)
    controleur = ControleurSuivi(qapp)

    controleur.verifier_si_necessaire()
    _attendre_fin(qtbot, controleur)

    assert verifiees == ["https://example.org/ouvert"]
    toutes = candidatures.charger_candidatures()
    assert toutes["OUVERT"]["disponible"] is False
    assert toutes["OUVERT"].get("depubliee_le") == date.today().isoformat()
    assert toutes["CLOS"]["disponible"] is True
    assert _valeur(controleur, 2, b"depublicationASignaler") is True


def test_verification_automatique_une_seule_fois_par_jour(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    _sauver(_candidature("A", "https://example.org/a"))
    verifiees: list[str] = []

    def injoignable(url: str) -> bool:
        verifiees.append(url)
        raise RuntimeError("hors ligne")

    monkeypatch.setattr(travailleurs, "verifier_disponibilite", injoignable)
    controleur = ControleurSuivi(qapp)

    controleur.verifier_si_necessaire()
    _attendre_fin(qtbot, controleur)
    controleur.verifier_si_necessaire()
    controleur.verifier_si_necessaire()

    assert verifiees == ["https://example.org/a"]


def test_verification_automatique_sans_dossier_ne_lance_rien(
    qapp: QApplication,
) -> None:
    controleur = ControleurSuivi(qapp)
    controleur.verifier_si_necessaire()
    assert controleur.property("verification_en_cours") is False


def test_verification_automatique_revoit_une_depublication_recente_et_l_efface(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidature = _candidature("A", "https://example.org/a")
    candidature["disponible"] = False
    candidature["depubliee_le"] = date.today().isoformat()
    candidature["derniere_verification"] = "2020-01-01"
    _sauver(candidature)
    monkeypatch.setattr(travailleurs, "verifier_disponibilite", Mock(return_value=True))
    controleur = ControleurSuivi(qapp)

    controleur.verifier_si_necessaire()
    _attendre_fin(qtbot, controleur)

    revue = candidatures.charger_candidatures()["A"]
    assert revue["disponible"] is True
    assert "depubliee_le" not in revue
    assert _valeur(controleur, 0, b"depublicationASignaler") is False


@pytest.mark.usefixtures("deux_dossiers")
def test_verifier_offres_revoit_aussi_les_dossiers_ouverts_marques_depublies(
    qapp: QApplication, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidatures.marquer_disponibilite("REF-A", False)
    verifiees: list[str] = []

    def verifier(url: str) -> bool:
        verifiees.append(url)
        return True

    monkeypatch.setattr(travailleurs, "verifier_disponibilite", verifier)
    controleur = ControleurSuivi(qapp)
    controleur.verifier_offres()
    _attendre_fin(qtbot, controleur)

    assert len(verifiees) == 2
    assert candidatures.charger_candidatures()["REF-A"]["disponible"] is True
