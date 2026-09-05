"""Tests de la vue Recherche + Résultats (src/gui/vues/recherche_resultats.py)."""

import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from src import cache, candidatures, export, parametres_sources
from src.gui.vues.recherche_resultats import VueRechercheResultats
from src.sources.choisirleservicepublic import ChoisirLeServicePublic
from src.sources.emploiterritorial import EmploiTerritorial
from src.types import Offre


@pytest.fixture(autouse=True)
def _rediriger_stockage_vers_tmp(tmp_path, monkeypatch):
    """Isole cache.py, export.py et candidatures.py de data/ réel, même
    pattern que test_cache.py."""
    monkeypatch.setattr(cache, "CHEMIN_CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(cache, "CHEMIN_OFFRES", tmp_path / "offres.json")
    monkeypatch.setattr(export, "DOSSIER_EXPORTS", tmp_path / "exports")
    monkeypatch.setattr(
        candidatures, "CHEMIN_CANDIDATURES", tmp_path / "candidatures.json"
    )
    monkeypatch.setattr(candidatures, "DOSSIER_ARCHIVES", tmp_path / "archives")
    # Seule choisirleservicepublic active par défaut dans les tests : évite
    # un vrai appel réseau vers les autres sources à chaque recherche.
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    parametres_sources.sauvegarder_sources_actives(
        {"emploiterritorial": False, "passerellesmef": False, "fhf": False}
    )


_OFFRE_TEST: Offre = {
    "titre": "Attaché principal — Responsable RH",
    "url": "https://choisirleservicepublic.gouv.fr/offre-emploi/reference-O1/",
    "reference": "O1",
    "domaine": "Ressources Humaines",
    "employeur": "DGFiP Hérault",
    "localisation": "Montpellier (34)",
    "versant": "Fonction publique de l'État",
    "date": "il y a 6 j",
}

_OFFRE_GRADE_SUPERIEUR: Offre = {
    "titre": "IDIV HC / AP Adjoint du Service de Gestion Comptable Métropole (34) H/F",
    "url": "https://choisirleservicepublic.gouv.fr/offre-emploi/reference-O2/",
    "reference": "O2",
    "domaine": "Finances Publiques",
    "employeur": "DGFiP Hérault",
    "localisation": "Montpellier (34)",
    "versant": "Fonction publique de l'État",
    "date": "il y a 6 j",
}


def test_construire_filtres_sans_selection_retourne_les_defauts(qtbot):
    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    filtres = vue.construire_filtres()
    assert filtres == {
        "categories": [],
        "domaines": [],
        "localisations": [],
        "organisations": [],
        "grades": [],
        "versants": ["etat"],
        "types_poste": None,
        "experience": "",
        "date_publication": "",
        "management": False,
        "teletravail": False,
        "query": "",
    }
    assert vue.afficher_grades_superieurs() is False


def test_construire_filtres_reflete_les_selections(qtbot):
    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    vue.show()  # geometrie reelle necessaire pour un clic precis sur la case

    qtbot.mouseClick(vue._categories_cases[2][0], Qt.MouseButton.LeftButton)  # "A"
    vue._management_case.setChecked(True)
    vue._grades_superieurs_case.setChecked(True)
    vue._mot_cle_champ.setText("  IDIV  ")

    filtres = vue.construire_filtres()
    assert filtres["categories"] == ["A"]
    assert filtres["management"] is True
    assert filtres["query"] == "IDIV"
    assert vue.afficher_grades_superieurs() is True


def test_versant_fpe_seul_par_defaut(qtbot):
    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    assert vue.construire_filtres()["versants"] == ["etat"]
    valeurs = {cle: case.isChecked() for case, cle in vue._versants_cases}
    assert valeurs == {"etat": True, "hospitalier": False, "territorial": False}


def test_versant_case_a_une_infobulle_avec_le_nom_complet(qtbot):
    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    for case, cle in vue._versants_cases:
        assert case.toolTip()  # non vide
        assert case.text() in ("FPE", "FPH", "FPT")


def test_versant_multi_selection(qtbot):
    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    for case, cle in vue._versants_cases:
        case.setChecked(cle in ("hospitalier", "territorial"))
    assert set(vue.construire_filtres()["versants"]) == {"hospitalier", "territorial"}


def test_versant_compat_ancien_format_singulier(qtbot):
    """Anciens profils sauvegardés avant le passage aux cases à cocher
    (`"versant": "territorial"`, singulier) — la sélection initiale doit
    quand même refléter la valeur, pas retomber sur le défaut FPE."""
    vue = VueRechercheResultats(filtres_existants={"versant": "territorial"})
    qtbot.addWidget(vue)
    assert vue.construire_filtres()["versants"] == ["territorial"]


def test_versant_compat_ancien_tous_devient_liste_vide(qtbot):
    vue = VueRechercheResultats(filtres_existants={"versant": "__tous__"})
    qtbot.addWidget(vue)
    assert vue.construire_filtres()["versants"] == []


def test_raz_reinitialise_versant_a_fpe_seul(qtbot):
    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    for case, cle in vue._versants_cases:
        case.setChecked(cle == "hospitalier")

    vue._reinitialiser_filtres()

    assert vue.construire_filtres()["versants"] == ["etat"]


def test_bouton_domaines_affiche_tous_par_defaut(qtbot):
    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    assert vue.bouton_domaines.text() == "Domaine(s)\nTous"
    assert vue.bouton_localisations.text() == "Localisation(s)\nTous"
    assert vue.bouton_organisations.text() == "Organisation(s)\nTous"
    assert vue.bouton_grades.text() == "Grade(s)\nTous"


def test_panneau_filtres_ne_peut_pas_etre_reduit_a_zero(qtbot):
    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    splitter = vue.findChild(QSplitter)
    assert splitter is not None

    splitter.setSizes([0, 1000])

    assert splitter.sizes()[0] >= 280


def test_selection_domaines_via_dialogue_met_a_jour_le_bouton(qtbot, monkeypatch):
    from PySide6.QtWidgets import QDialog

    from src.gui.widgets.dialogue_selection import DialogueSelectionListe

    monkeypatch.setattr(
        DialogueSelectionListe, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    monkeypatch.setattr(DialogueSelectionListe, "selection", lambda self: ["Numérique"])

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    vue._ouvrir_selection_domaines()

    assert vue._domaines_selection == ["Numérique"]
    assert vue.bouton_domaines.text() == "Domaine(s)\n1 sélectionné"
    assert vue.construire_filtres()["domaines"] == ["Numérique"]


def test_selection_domaines_annulee_ne_change_rien(qtbot, monkeypatch):
    from PySide6.QtWidgets import QDialog

    from src.gui.widgets.dialogue_selection import DialogueSelectionListe

    monkeypatch.setattr(
        DialogueSelectionListe, "exec", lambda self: QDialog.DialogCode.Rejected
    )

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    vue._ouvrir_selection_domaines()

    assert vue._domaines_selection == []
    assert vue.bouton_domaines.text() == "Domaine(s)\nTous"


def test_selection_grades_via_dialogue_met_a_jour_le_bouton(qtbot, monkeypatch):
    from PySide6.QtWidgets import QDialog

    from src.gui.widgets.dialogue_selection import DialogueSelectionListe

    monkeypatch.setattr(
        DialogueSelectionListe, "exec", lambda self: QDialog.DialogCode.Accepted
    )
    monkeypatch.setattr(
        DialogueSelectionListe, "selection", lambda self: ["Attaché principal"]
    )

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    vue._ouvrir_selection_grades()

    assert vue._grades_selection == ["Attaché principal"]
    assert vue.bouton_grades.text() == "Grade(s)\n1 sélectionné"
    assert vue.construire_filtres()["grades"] == ["Attaché principal"]


def test_selection_organisations_via_dialogue(qtbot, monkeypatch):
    from PySide6.QtWidgets import QDialog

    from src.gui.widgets.dialogue_selection import DialogueSelectionOrganisations

    monkeypatch.setattr(
        DialogueSelectionOrganisations,
        "exec",
        lambda self: QDialog.DialogCode.Accepted,
    )
    monkeypatch.setattr(
        DialogueSelectionOrganisations,
        "selection",
        lambda self: ["Ministère de test - Sous-org A"],
    )

    vue = VueRechercheResultats(orgas_cache={"Ministère de test": {"Sous-org A": 1}})
    qtbot.addWidget(vue)
    vue._ouvrir_selection_organisations()

    assert vue._organisations_selection == ["Ministère de test - Sous-org A"]
    assert vue.bouton_organisations.text() == "Organisation(s)\n1 sélectionné"


def test_raz_reinitialise_les_selections_domaines_localisations_organisations_grades(
    qtbot,
):
    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    vue._domaines_selection = ["Numérique"]
    vue._localisations_selection = ["Hérault"]
    vue._organisations_selection = ["Ministère - Sous-org"]
    vue._grades_selection = ["Attaché principal"]

    vue._reinitialiser_filtres()

    assert vue._domaines_selection == []
    assert vue._localisations_selection == []
    assert vue._organisations_selection == []
    assert vue._grades_selection == []
    assert vue.bouton_domaines.text() == "Domaine(s)\nTous"
    assert vue.bouton_grades.text() == "Grade(s)\nTous"


def test_bouton_porte_le_bon_libelle_selon_le_mode(qtbot):
    vue_recherche = VueRechercheResultats()
    qtbot.addWidget(vue_recherche)
    assert vue_recherche.bouton_lancer.text() == "Lancer la recherche"

    vue_edition = VueRechercheResultats(mode_edition=True, nom_profil="test")
    qtbot.addWidget(vue_edition)
    assert vue_edition.bouton_lancer.text() == "Enregistrer les modifications"


def test_filtres_existants_prerempliss_les_widgets(qtbot):
    orgas_cache = {"Ministère de test": {"Sous-org A": 1, "Sous-org B": 2}}
    filtres: dict = {
        "categories": ["A"],
        "domaines": ["Numérique"],
        "localisations": ["Hérault"],
        "organisations": ["Ministère de test - Sous-org A"],
        "versants": ["territorial"],
        "types_poste": ["titulaire"],
        "experience": "Confirmé",
        "date_publication": "7 derniers jours",
        "management": True,
        "teletravail": True,
        "query": "IDIV",
    }
    vue = VueRechercheResultats(orgas_cache, filtres_existants=filtres)
    qtbot.addWidget(vue)

    reconstruits = vue.construire_filtres()
    assert reconstruits["categories"] == ["A"]
    assert reconstruits["domaines"] == ["Numérique"]
    assert reconstruits["localisations"] == ["Hérault"]
    assert reconstruits["organisations"] == ["Ministère de test - Sous-org A"]
    assert reconstruits["versants"] == ["territorial"]
    assert reconstruits["types_poste"] == ["titulaire"]
    assert reconstruits["experience"] == "Confirmé"
    assert reconstruits["date_publication"] == "7 derniers jours"
    assert reconstruits["management"] is True
    assert reconstruits["teletravail"] is True
    assert reconstruits["query"] == "IDIV"


def test_lancer_recherche_peuple_la_table(qtbot, monkeypatch):
    """Le bouton déclenche la recherche (mockée, pas d'appel réseau réel)
    dans un QThread, et peuple le tableau une fois le résultat reçu."""

    def _rechercher_factice(self, filtres, on_page=None):
        if on_page:
            on_page(1, 1)
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)


def test_barre_progression_visible_pendant_recherche_puis_cachee(qtbot, monkeypatch):
    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    assert vue.barre_progression.isVisible() is False

    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)
    qtbot.waitUntil(lambda: vue._thread is None, timeout=2000)

    assert vue.barre_progression.isVisible() is False


def test_statut_recherche_visible_puis_retabli_apres_resultat(qtbot, monkeypatch):
    """Le texte « Recherche en cours… » doit être visuellement marqué
    (role="statut", accent) pendant la recherche, pas confondu avec le
    role="sousTexte" discret utilisé au repos — signalé par l'utilisateur
    comme donnant une impression de blocage sans aucun indice visuel."""

    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    assert vue.label_entete.property("role") == "sousTexte"

    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue._thread is None, timeout=2000)

    assert vue.label_entete.property("role") == "sousTexte"


def test_fenetre_reste_reactive_pendant_une_recherche_lente(qtbot, monkeypatch):
    """Vérifie noir sur blanc que la fenêtre n'est pas bloquée pendant
    une recherche (le QThread ne bloque que le worker, pas le thread
    principal) : un autre widget doit rester cliquable et réagir
    immédiatement pendant que le réseau (mocké ici par un délai) tourne
    encore en arrière-plan."""

    def _rechercher_lente(self, filtres, on_page=None):
        time.sleep(0.3)
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_lente)

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    vue._mot_cle_champ.setText("IDIV")

    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    assert vue._thread is not None and vue._thread.isRunning()

    # La recherche tourne encore (délai de 0.3s) : le clic sur RAZ doit
    # être traité immédiatement par le thread principal, sans attendre
    # la fin de la recherche.
    qtbot.mouseClick(vue.bouton_raz, Qt.MouseButton.LeftButton)
    assert vue._mot_cle_champ.text() == ""
    assert vue._thread is not None and vue._thread.isRunning()  # toujours en cours

    qtbot.waitUntil(lambda: vue._thread is None, timeout=2000)

    assert vue.table_resultats.item(0, 0).text() == _OFFRE_TEST["titre"]
    assert vue.table_resultats.item(0, 1).text() == "DGFiP Hérault"
    assert "1 offre(s)" in vue.label_entete.text()
    assert vue.bouton_lancer.text() == "Lancer la recherche"
    assert vue.bouton_lancer.isEnabled()


def test_bouton_suivre_desactive_sans_selection_puis_active(qtbot, monkeypatch):
    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)
    assert vue.bouton_suivre.isEnabled() is False

    vue.table_resultats.selectRow(0)
    assert vue.bouton_suivre.isEnabled() is True


def test_bouton_voir_detail_desactive_sans_selection_puis_active(qtbot, monkeypatch):
    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)
    assert vue.bouton_voir_detail.isEnabled() is False

    vue.table_resultats.selectRow(0)
    assert vue.bouton_voir_detail.isEnabled() is True


def test_voir_detail_offre_ouvre_la_dialogue_avec_le_detail(qtbot, monkeypatch):
    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)
    detail_factice = {
        "description": "Missions du poste",
        "salaire": "Non renseigné",
        "experience_requise": "Confirmé",
        "formation_requise": "",
        "secteur": "Numérique",
        "date_publication": "31/08/2026",
        "a_propos_employeur": "Présentation du service",
        "sections_complementaires": {"Statut du poste": "Vacant"},
        "page_html": "<html></html>",
    }
    monkeypatch.setattr(
        "src.gui.vues.recherche_resultats.recuperer_detail_offre",
        lambda url: detail_factice,
    )

    appels = []

    class _DialogueFactice:
        def __init__(self, titre_offre, employeur, detail, url, reference, parent=None):
            appels.append((titre_offre, employeur, detail, url, reference))

        def exec(self):
            return None

    monkeypatch.setattr(
        "src.gui.vues.recherche_resultats.DialogueDetailOffre", _DialogueFactice
    )

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)

    vue.table_resultats.selectRow(0)
    qtbot.mouseClick(vue.bouton_voir_detail, Qt.MouseButton.LeftButton)

    assert appels == [
        (
            _OFFRE_TEST["titre"],
            _OFFRE_TEST["employeur"],
            detail_factice,
            _OFFRE_TEST["url"],
            _OFFRE_TEST["reference"],
        )
    ]


def test_suivre_cette_offre_demarre_le_suivi_de_candidature(qtbot, monkeypatch):
    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)
    monkeypatch.setattr(
        "src.gui.vues.recherche_resultats.QMessageBox.information",
        lambda *a, **k: None,
    )
    detail_factice = {
        "description": "Missions du poste",
        "salaire": "Non renseigné",
        "experience_requise": "Confirmé",
        "formation_requise": "",
        "secteur": "Numérique",
        "date_publication": "31/08/2026",
        "a_propos_employeur": "Présentation du service",
        "sections_complementaires": {"Statut du poste": "Vacant"},
        "page_html": "<html></html>",
    }
    monkeypatch.setattr(
        "src.gui.vues.recherche_resultats.recuperer_detail_offre",
        lambda url: detail_factice,
    )

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)

    vue.table_resultats.selectRow(0)
    qtbot.mouseClick(vue.bouton_suivre, Qt.MouseButton.LeftButton)

    toutes = candidatures.charger_candidatures()
    assert "O1" in toutes
    assert toutes["O1"]["offre_titre"] == _OFFRE_TEST["titre"]
    assert toutes["O1"]["offre_domaine"] == _OFFRE_TEST["domaine"]
    assert toutes["O1"]["detail"] == detail_factice
    assert toutes["O1"]["offre_employeur"] == "DGFiP Hérault"


def test_erreur_reseau_affichee_sans_planter(qtbot, monkeypatch):
    def _rechercher_en_erreur(self, filtres, on_page=None):
        raise RuntimeError("Erreur réseau lors du chargement")

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_en_erreur)

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: "Erreur" in vue.label_entete.text(), timeout=2000)

    assert vue.bouton_lancer.isEnabled()


def test_avertissement_source_en_echec_affiche_sans_bloquer_les_autres(
    qtbot, monkeypatch
):
    parametres_sources.sauvegarder_sources_actives(
        {"emploiterritorial": True, "passerellesmef": False, "fhf": False}
    )

    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    def _echec(self, filtres, on_page=None):
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)
    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echec)

    # "versants": [] (tous les versants) — sinon le filtre Versant par
    # défaut (État seul) exclurait emploi-territorial.fr avant même
    # l'appel, et ne testerait plus la résilience à un échec partiel.
    vue = VueRechercheResultats(filtres_existants={"versants": []})
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)

    assert "indisponible" in vue.label_entete.text()


def test_mode_edition_enregistre_et_emet_demande_retour(qtbot, monkeypatch):
    profils_enregistres = {}

    def _modifier_profil_factice(nom, filtres):
        profils_enregistres[nom] = filtres

    monkeypatch.setattr(
        "src.gui.vues.recherche_resultats.modifier_profil", _modifier_profil_factice
    )

    vue = VueRechercheResultats(
        filtres_existants={"query": "IDIV"},
        nom_profil="mon-profil",
        mode_edition=True,
    )
    qtbot.addWidget(vue)

    with qtbot.waitSignal(vue.demande_retour, timeout=1000):
        qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)

    assert profils_enregistres["mon-profil"]["query"] == "IDIV"


def test_double_clic_ouvre_loffre_dans_le_navigateur(qtbot, monkeypatch):
    ouvertes = []
    monkeypatch.setattr("webbrowser.open", lambda url: ouvertes.append(url))

    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)

    vue._ouvrir_offre(vue.table_resultats.item(0, 0))
    assert ouvertes == [_OFFRE_TEST["url"]]


def test_grades_superieurs_exclus_par_defaut_et_reaffiches_sur_demande(
    qtbot, monkeypatch
):
    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST, _OFFRE_GRADE_SUPERIEUR], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() >= 1, timeout=2000)
    assert vue.table_resultats.rowCount() == 1  # l'offre IDIV est exclue
    assert "1 offre(s) IDiv/IP exclue" in vue.label_entete.text()

    vue._grades_superieurs_case.setChecked(True)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 2, timeout=2000)


def test_exporter_html_genere_un_fichier(qtbot, monkeypatch):
    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    monkeypatch.setattr(
        "src.gui.vues.recherche_resultats.question_oui_non",
        lambda *a, **k: False,
    )

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    assert vue.bouton_exporter.isEnabled() is False

    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)
    assert vue.bouton_exporter.isEnabled() is True

    vue._exporter_html()
    fichiers = list(export.DOSSIER_EXPORTS.glob("*.html"))
    assert len(fichiers) == 1
    assert _OFFRE_TEST["titre"] in fichiers[0].read_text(encoding="utf-8")


def test_badge_nouvelles_offres_pour_une_recherche_liee_a_un_profil(qtbot, monkeypatch):
    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats(nom_profil="mon-profil")
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)
    # attend la fin réelle du thread (pas juste le résultat affiché) avant
    # de relancer une recherche — détruire un QThread encore en cours fait
    # planter Qt, cf. `arreter_recherche_en_cours`.
    qtbot.waitUntil(lambda: vue._thread is None, timeout=2000)

    assert vue._nouvelles == {"O1"}
    assert "★" in vue.table_resultats.item(0, 0).text()
    assert "1 nouvelle(s) offre(s)" in vue.label_entete.text()
    # toutes les offres sont nouvelles : rien à filtrer, la case reste
    # cachée (même règle que le CLI historique).
    assert vue.case_nouvelles_seulement.isVisible() is False

    # deuxième lancement, quelques instants après : l'offre reste
    # "nouvelle" pendant TTL_NOUVELLES (24h, cf. CLAUDE.md) — un badge
    # qui disparaîtrait au lancement suivant serait une régression, pas
    # le comportement voulu.
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)
    qtbot.waitUntil(lambda: vue._thread is None, timeout=2000)
    assert vue._nouvelles == {"O1"}
    assert "★" in vue.table_resultats.item(0, 0).text()


def test_case_nouvelles_seulement_filtre_le_tableau_sans_relancer(qtbot, monkeypatch):
    """Équivalent du choix « Afficher nouvelles seulement » du CLI
    historique — visible seulement s'il reste des offres à exclure."""
    offre_ancienne: Offre = {**_OFFRE_TEST, "reference": "O3"}
    vu_le_ancien = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    cache.CHEMIN_OFFRES.write_text(
        json.dumps(
            {
                "mon-profil": {
                    "O3": {
                        **offre_ancienne,
                        "vu_le": vu_le_ancien,
                        "derniere_vue": vu_le_ancien,
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST, offre_ancienne], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats(nom_profil="mon-profil")
    qtbot.addWidget(vue)
    vue.show()  # isVisible() dépend du mappage réel à l'écran, cf. doc Qt
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 2, timeout=2000)
    qtbot.waitUntil(lambda: vue._thread is None, timeout=2000)

    assert vue._nouvelles == {"O1"}
    assert vue.case_nouvelles_seulement.isVisible() is True
    assert vue.case_nouvelles_seulement.isChecked() is False

    vue.case_nouvelles_seulement.setChecked(True)
    assert vue.table_resultats.rowCount() == 1
    assert vue.table_resultats.item(0, 0).text() == f"★ {_OFFRE_TEST['titre']}"
    assert vue._offres_visibles == [_OFFRE_TEST]

    vue.case_nouvelles_seulement.setChecked(False)
    assert vue.table_resultats.rowCount() == 2
    assert vue._offres_visibles == [_OFFRE_TEST, offre_ancienne]


def test_pas_de_badge_nouvelles_offres_pour_une_recherche_vierge(qtbot, monkeypatch):
    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats()  # pas de nom_profil
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: vue.table_resultats.rowCount() == 1, timeout=2000)

    assert vue._nouvelles == set()
    assert "nouvelle(s) offre(s)" not in vue.label_entete.text()


def test_arreter_recherche_en_cours_ne_plante_pas_sans_recherche_active(qtbot):
    """Ne fait rien si aucun thread n'est en cours — sûr à appeler même
    quand la vue n'a jamais lancé de recherche."""
    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    vue.arreter_recherche_en_cours()  # ne doit pas lever d'exception


def test_arreter_recherche_en_cours_attend_la_fin_du_thread(qtbot, monkeypatch):
    """Empêche le crash Qt (QThread détruit alors qu'il tourne encore) —
    régression trouvée en pratique en enchaînant deux recherches vite."""

    def _rechercher_factice(self, filtres, on_page=None):
        return [_OFFRE_TEST], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    vue = VueRechercheResultats()
    qtbot.addWidget(vue)
    qtbot.mouseClick(vue.bouton_lancer, Qt.MouseButton.LeftButton)

    vue.arreter_recherche_en_cours()
    assert vue._thread is None or not vue._thread.isRunning()
