"""Tests de src/gui/controleurs/reglages.py : sources, préférences,
avis de mise à jour et rafraîchissement du cache des organisations."""

from datetime import date, datetime
from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from src import maj
from src.donnees import parametres_affichage, parametres_sources, profils
from src.gui import travailleurs
from src.gui.controleurs import reglages as controleur_reglages
from src.gui.controleurs.reglages import (
    MESSAGE_CACHE_INDISPONIBLE,
    MESSAGE_EXPORTS_NON_SUPPRIMES,
    ControleurReglages,
)
from src.gui.pont import Pont
from src.gui.presentation import texte_date_cache
from src.recherche import export
from src.systeme import raccourci
from src.types import InfoMaj, Organisations

INFO: InfoMaj = {
    "version": "2.0.1",
    "notes": "- Correctifs",
    "url_zip": "https://api.github.com/repos/Sietch-Tabr/tamponne/zipball/v2.0.1",
    "url_publication": "https://github.com/Sietch-Tabr/tamponne/releases/tag/v2.0.1",
}


@pytest.fixture(autouse=True)
def _environnement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    monkeypatch.setattr(controleur_reglages, "version_locale", lambda: "2.0.0")
    monkeypatch.setattr(controleur_reglages, "date_avis", lambda: date(2026, 10, 4))


@pytest.mark.usefixtures("qapp")
def test_sources_toutes_actives_par_defaut_dans_l_ordre() -> None:
    reglages = ControleurReglages()
    cles = [s["cle"] for s in reglages.property("sources")]
    assert cles == list(parametres_sources.SOURCES_DISPONIBLES)
    assert all(reglages.property("sources_actives")[cle] for cle in cles)


@pytest.mark.usefixtures("qapp")
def test_basculer_source_enregistre_aussitot() -> None:
    reglages = ControleurReglages()
    reglages.basculer_source("fhf")
    assert parametres_sources.charger_sources_actives()["fhf"] is False
    assert reglages.property("sources_actives")["fhf"] is False


@pytest.mark.usefixtures("qapp")
def test_basculer_source_inconnue_ignoree() -> None:
    reglages = ControleurReglages()
    reglages.basculer_source("inconnue")
    assert not parametres_sources.CHEMIN_SOURCES.exists()


@pytest.mark.usefixtures("qapp")
def test_definir_reduire_animations_persiste() -> None:
    reglages = ControleurReglages()
    reglages.definir_reduire_animations(True)
    assert parametres_affichage.charger_reduire_animations() is True
    assert ControleurReglages().property("reduire_animations") is True


@pytest.mark.usefixtures("qapp")
def test_avis_sans_publication_annonce_version_a_jour() -> None:
    reglages = ControleurReglages()
    assert reglages.property("avis") == {
        "disponible": False,
        "a_jour": True,
        "objet": "version 2.0.0 installée, rien de plus récent.",
    }
    assert reglages.property("pastille") is False


@pytest.mark.usefixtures("qapp")
def test_afficher_avis_reprend_version_date_et_notes() -> None:
    reglages = ControleurReglages()
    reglages.afficher_avis(INFO)
    assert reglages.property("avis") == {
        "disponible": True,
        "numero": "Avis n° 2.0.1",
        "date": "04/10/2026",
        "objet": "version 2.0.1 disponible (installée\u00a0: 2.0.0).",
        "notes": '<ul style="margin-top:4px;margin-bottom:0"><li>Correctifs</li></ul>',
    }
    assert reglages.property("pastille") is True


@pytest.mark.usefixtures("qapp")
def test_afficher_avis_sans_notes_le_signale() -> None:
    reglages = ControleurReglages()
    reglages.afficher_avis({**INFO, "notes": ""})
    assert "Pas de notes de version." in reglages.property("avis")["notes"]


@pytest.mark.usefixtures("qapp")
def test_reporter_maj_efface_la_pastille() -> None:
    reglages = ControleurReglages()
    reglages.afficher_avis(INFO)
    reglages.reporter_maj()
    assert reglages.property("pastille") is False
    assert reglages.property("avis")["disponible"] is True


@pytest.mark.usefixtures("qapp")
def test_installer_maj_demande_a_quitter(qtbot: QtBot) -> None:
    reglages = ControleurReglages()
    reglages.afficher_avis(INFO)
    with qtbot.waitSignal(reglages.quitter_demande, timeout=1000):
        reglages.installer_maj()
    assert reglages.redemarrage_demande is True


@pytest.mark.usefixtures("qapp")
def test_installer_maj_repose_le_marqueur() -> None:
    """La vérification ne pose pas le marqueur d'une version annulée : le
    clic le repose, c'est le nouvel essai à la demande."""
    reglages = ControleurReglages()
    reglages.afficher_avis(INFO)
    reglages.installer_maj()
    assert maj.lire_maj_disponible() == INFO


@pytest.mark.usefixtures("qapp")
def test_reporter_maj_repose_le_marqueur() -> None:
    reglages = ControleurReglages()
    reglages.afficher_avis(INFO)
    reglages.reporter_maj()
    assert maj.lire_maj_disponible() == INFO


@pytest.mark.usefixtures("qapp")
def test_avis_d_une_version_annulee_donne_le_motif() -> None:
    maj.enregistrer_echec("2.0.1", "l'application ne démarrait pas")
    reglages = ControleurReglages()
    reglages.afficher_avis(INFO)
    assert reglages.property("avis")["objet"] == (
        "version 2.0.1 non installée au dernier essai\u00a0: l'application ne "
        "démarrait pas (installée\u00a0: 2.0.0)."
    )


@pytest.mark.usefixtures("qapp")
def test_avis_d_une_version_plus_recente_que_l_annulee_reste_normal() -> None:
    maj.enregistrer_echec("2.0.0", "motif")
    reglages = ControleurReglages()
    reglages.afficher_avis(INFO)
    assert reglages.property("avis")["objet"].startswith("version 2.0.1 disponible")


def test_verification_ne_reprogramme_pas_une_version_annulee(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maj.enregistrer_echec("2.0.1", "motif")
    monkeypatch.setattr(travailleurs, "verifier_derniere_publication", lambda: INFO)
    travailleurs.VerificateurMiseAJour().executer()
    assert maj.lire_maj_disponible() is None


def test_verification_programme_une_version_plus_recente_que_l_annulee(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maj.enregistrer_echec("2.0.0", "motif")
    monkeypatch.setattr(travailleurs, "verifier_derniere_publication", lambda: INFO)
    travailleurs.VerificateurMiseAJour().executer()
    assert maj.lire_maj_disponible() == INFO


@pytest.mark.usefixtures("qapp")
def test_installer_maj_sans_avis_ne_fait_rien(qtbot: QtBot) -> None:
    reglages = ControleurReglages()
    with qtbot.assertNotEmitted(reglages.quitter_demande):
        reglages.installer_maj()
    assert reglages.redemarrage_demande is False


@pytest.mark.usefixtures("qapp")
def test_verifier_mise_a_jour_affiche_l_avis_trouve(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(travailleurs, "verifier_derniere_publication", lambda: INFO)
    monkeypatch.setattr(travailleurs, "ecrire_maj_disponible", lambda _info: None)
    reglages = ControleurReglages()
    reglages.verifier_mise_a_jour()
    assert "recherche d'une mise à jour" in reglages.property("avis")["objet"]
    assert reglages.property("avis")["a_jour"] is False
    qtbot.waitUntil(lambda: reglages.property("avis")["disponible"], timeout=5000)
    reglages.arreter()


@pytest.mark.usefixtures("qapp")
def test_verifier_mise_a_jour_github_injoignable_le_dit(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    def injoignable() -> None:
        raise maj.VerificationImpossible("<urlopen error timed out>")

    monkeypatch.setattr(travailleurs, "verifier_derniere_publication", injoignable)
    reglages = ControleurReglages()
    reglages.verifier_mise_a_jour()
    qtbot.waitUntil(
        lambda: "GitHub ne répond pas" in reglages.property("avis")["objet"],
        timeout=5000,
    )
    reglages.arreter()
    avis = reglages.property("avis")
    assert avis["a_jour"] is False
    assert "rien de plus récent" not in avis["objet"]
    assert avis["objet"].endswith("Détail\u00a0: &lt;urlopen error timed out&gt;")


@pytest.mark.usefixtures("qapp")
def test_rafraichir_cache_transmet_les_organisations(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    orgas: Organisations = {"Ministère": {"Direction": 12}}
    monkeypatch.setattr(
        controleur_reglages, "obtenir_organisations", lambda forcer=False: orgas
    )
    moment = datetime(2026, 10, 12, 14, 5).astimezone()
    monkeypatch.setattr(controleur_reglages, "date_cache_organisations", lambda: None)
    reglages = ControleurReglages()
    assert reglages.property("date_cache") == ""
    monkeypatch.setattr(controleur_reglages, "date_cache_organisations", lambda: moment)
    with qtbot.waitSignal(reglages.organisations_rafraichies, timeout=5000) as signal:
        reglages.rafraichir_cache()
        assert reglages.property("cache_en_cours") is True
    reglages.arreter()
    assert signal.args == [orgas]
    assert reglages.property("cache_en_cours") is False
    assert reglages.property("message_cache") == ""
    assert reglages.property("date_cache") == texte_date_cache(moment)


@pytest.mark.usefixtures("qapp")
def test_rafraichir_cache_en_echec_affiche_un_message(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    def echouer(forcer: bool = False) -> Organisations:
        raise RuntimeError("site inaccessible")

    monkeypatch.setattr(controleur_reglages, "obtenir_organisations", echouer)
    reglages = ControleurReglages()
    with qtbot.waitSignal(reglages.etat_change, timeout=5000):
        reglages.rafraichir_cache()
    qtbot.waitUntil(lambda: not reglages.property("cache_en_cours"), timeout=5000)
    reglages.arreter()
    assert reglages.property("message_cache") == MESSAGE_CACHE_INDISPONIBLE


@pytest.mark.usefixtures("qapp")
def test_pont_transmet_le_cache_rafraichi_a_la_recherche() -> None:
    pont = Pont()
    orgas: Organisations = {"Ministère": {"Direction": 12}}
    pont.reglages_controleur.organisations_rafraichies.emit(orgas)
    groupes = pont.property("recherche").groupes_selection("organisations")
    assert groupes[0]["elements"][0]["valeur"] == "Ministère - Direction"


@pytest.mark.usefixtures("qapp")
def test_pont_relaie_le_chargement_des_organisations_a_la_recherche(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    orgas: Organisations = {"Ministère": {"Direction": 12}}
    monkeypatch.setattr(
        controleur_reglages, "obtenir_organisations", lambda forcer=False: orgas
    )
    pont = Pont()
    recherche = pont.property("recherche")
    assert recherche.property("etat_organisations") == "indisponible"
    with qtbot.waitSignal(
        pont.reglages_controleur.organisations_rafraichies, timeout=5000
    ):
        pont.reglages_controleur.rafraichir_cache()
        assert recherche.property("etat_organisations") == "chargement…"
    pont.arreter()
    assert recherche.property("etat_organisations") == ""


@pytest.mark.usefixtures("qapp")
def test_pont_pastille_suit_l_avis() -> None:
    pont = Pont()
    assert pont.property("mise_a_jour_disponible") is False
    pont.reglages_controleur.afficher_avis(INFO)
    assert pont.property("mise_a_jour_disponible") is True
    pont.reglages_controleur.reporter_maj()
    assert pont.property("mise_a_jour_disponible") is False


@pytest.fixture
def sous_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raccourci `.desktop` dans le profil redirigé par `conftest.py`."""
    monkeypatch.setattr(raccourci, "systeme_courant", lambda: "linux")


@pytest.mark.usefixtures("qapp", "sous_linux")
def test_raccourci_premier_lancement_pose_la_question_puis_la_retient(
    qtbot: QtBot,
) -> None:
    reglages = ControleurReglages()
    assert reglages.property("raccourci")["etat"] == "absent"
    with qtbot.waitSignal(reglages.question_raccourci) as signal:
        reglages.verifier_raccourci()
    assert signal.args == ["premier_lancement"]
    reglages.refuser_raccourci()
    with qtbot.assertNotEmitted(reglages.question_raccourci):
        reglages.verifier_raccourci()


@pytest.mark.usefixtures("qapp", "sous_linux")
def test_ajouter_puis_retirer_raccourci_en_arriere_plan(qtbot: QtBot) -> None:
    reglages = ControleurReglages()
    reglages.ajouter_raccourci()
    assert reglages.property("raccourci_en_cours") is True
    qtbot.waitUntil(lambda: not reglages.property("raccourci_en_cours"))
    etat = reglages.property("raccourci")
    assert etat["etat"] == "a_jour"
    assert etat["texte"] == "Tamponné figure dans le menu des applications."
    reglages.retirer_raccourci()
    qtbot.waitUntil(lambda: not reglages.property("raccourci_en_cours"))
    assert reglages.property("raccourci")["etat"] == "absent"
    reglages.arreter()


@pytest.mark.usefixtures("qapp")
def test_raccourci_indisponible_masque_la_feuille(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(raccourci, "systeme_courant", lambda: None)
    reglages = ControleurReglages()
    assert reglages.property("raccourci")["disponible"] is False
    with qtbot.waitSignal(reglages.erreur_signalee) as signal:
        reglages.ajouter_raccourci()
    assert signal.args == ["Raccourci indisponible sur ce système."]
    # Toute erreur montrée à l'utilisateur laisse sa ligne dans le journal.
    assert "ERROR" in caplog.text
    assert "Raccourci indisponible sur ce système." in caplog.text
    reglages.arreter()


@pytest.mark.usefixtures("qapp")
def test_exporter_puis_importer_donnees_redemarre(qtbot: QtBot, tmp_path: Path) -> None:
    profils.CHEMIN_PROFILS.write_text('{"Exportée": {}}', encoding="utf-8")
    reglages = ControleurReglages()
    url = (tmp_path / "export.zip").as_uri()
    assert reglages.exporter_donnees(url) == str(tmp_path / "export.zip")

    profils.CHEMIN_PROFILS.write_text('{"Locale": {}}', encoding="utf-8")
    assert "«\u00a0export.zip\u00a0»" in reglages.confirmation_import(url)
    with qtbot.waitSignal(reglages.quitter_demande):
        reglages.importer_donnees(url)
    assert reglages.redemarrage_demande is True
    assert profils.CHEMIN_PROFILS.read_text(encoding="utf-8") == '{"Exportée": {}}'


@pytest.mark.usefixtures("qapp")
def test_importer_un_fichier_douteux_signale_l_erreur_sans_redemarrer(
    qtbot: QtBot, tmp_path: Path
) -> None:
    faux = tmp_path / "faux.zip"
    faux.write_text("bonjour", encoding="utf-8")
    reglages = ControleurReglages()
    with qtbot.waitSignal(reglages.erreur_signalee) as signal:
        reglages.importer_donnees(faux.as_uri())
    assert signal.args == ["Ce fichier n'est pas une sauvegarde de Tamponné."]
    assert reglages.redemarrage_demande is False


def test_exports_relus_a_l_actualisation() -> None:
    reglages = ControleurReglages()
    assert reglages.property("exports") == {
        "nombre": 0,
        "texte": "Aucun export de recherche.",
    }
    export.DOSSIER_EXPORTS.mkdir(parents=True)
    (export.DOSSIER_EXPORTS / "a.html").write_bytes(b"x" * 2500)
    reglages.actualiser_exports()
    assert reglages.property("exports") == {
        "nombre": 1,
        "texte": "1\u00a0fichier, 2\u00a0Ko",
    }
    assert "l'export de recherche" in reglages.confirmation_suppression_exports()


def test_supprimer_exports_vide_le_dossier() -> None:
    export.DOSSIER_EXPORTS.mkdir(parents=True)
    (export.DOSSIER_EXPORTS / "a.html").write_text("x", encoding="utf-8")
    reglages = ControleurReglages()
    reglages.supprimer_exports()
    assert reglages.property("exports")["nombre"] == 0
    assert not (export.DOSSIER_EXPORTS / "a.html").exists()


def test_supprimer_exports_en_echec_signale_l_erreur(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    def echouer() -> None:
        raise PermissionError("fichier ouvert")

    monkeypatch.setattr(export, "supprimer_exports", echouer)
    reglages = ControleurReglages()
    with qtbot.waitSignal(reglages.erreur_signalee) as signal:
        reglages.supprimer_exports()
    assert signal.args == [
        MESSAGE_EXPORTS_NON_SUPPRIMES.format(erreur="fichier ouvert")
    ]
