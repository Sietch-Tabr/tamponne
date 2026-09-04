"""Tests de la fenêtre principale (src/gui/app.py) — navigation entre écrans."""

import pytest

from src import parametres_sources, profils
from src.gui.app import FenetrePrincipale
from src.gui.vues.accueil import VueAccueil
from src.gui.vues.aide import VueAide
from src.gui.vues.parametres import VueParametres
from src.gui.vues.recherche_resultats import VueRechercheResultats
from src.sources.choisirleservicepublic import ChoisirLeServicePublic
from src.types import InfoMaj


@pytest.fixture(autouse=True)
def _rediriger_profils_vers_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(profils, "CHEMIN_PROFILS", tmp_path / "profils.json")
    # Seule choisirleservicepublic active par défaut : évite un vrai appel
    # réseau vers les autres sources dans ces tests.
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    parametres_sources.sauvegarder_sources_actives(
        {"emploiterritorial": False, "passerellesmef": False, "fhf": False}
    )


def test_ecran_initial_est_laccueil(qtbot):
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    assert isinstance(fenetre._pile.currentWidget(), VueAccueil)


def test_nouvelle_recherche_ouvre_une_vue_recherche_vierge(qtbot):
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    fenetre.bouton_nav_recherche.click()
    assert isinstance(fenetre._pile.currentWidget(), VueRechercheResultats)
    assert fenetre._pile.currentWidget().construire_filtres()["query"] == ""


def test_lancer_profil_ouvre_une_vue_prereplie_et_lance_seul_la_recherche(
    qtbot, monkeypatch
):
    def _rechercher_factice(self, filtres, on_page=None):
        return [], 1, False

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _rechercher_factice)

    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    fenetre._vue_accueil.demande_lancer_profil.emit(
        "mon-profil", {"query": "IDIV", "label": "test"}
    )
    vue = fenetre._pile.currentWidget()
    assert isinstance(vue, VueRechercheResultats)
    assert vue.mode_edition is False
    assert vue.construire_filtres()["query"] == "IDIV"

    # Ouvrir depuis un profil lance la recherche seul, sans clic
    # supplémentaire sur le bouton.
    qtbot.waitUntil(
        lambda: "Aucune recherche" not in vue.label_entete.text(), timeout=2000
    )
    qtbot.waitUntil(lambda: vue._thread is None, timeout=2000)


def test_modifier_profil_ouvre_une_vue_en_mode_edition(qtbot):
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    fenetre._vue_accueil.demande_modifier_profil.emit(
        "mon-profil", {"query": "IDIV", "label": "test"}
    )
    vue = fenetre._pile.currentWidget()
    assert isinstance(vue, VueRechercheResultats)
    assert vue.mode_edition is True


def test_retour_depuis_recherche_revient_a_laccueil(qtbot):
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    fenetre.bouton_nav_recherche.click()
    vue_recherche = fenetre._pile.currentWidget()
    vue_recherche.demande_retour.emit()
    assert isinstance(fenetre._pile.currentWidget(), VueAccueil)


def test_navigation_vers_aide_et_parametres_via_le_bandeau(qtbot):
    """Navigation par le bandeau persistant, pas par les écrans eux-mêmes
    (Aide/Paramètres n'ont plus de bouton retour propre)."""
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)

    fenetre.bouton_nav_aide.click()
    assert isinstance(fenetre._pile.currentWidget(), VueAide)
    assert fenetre.bouton_nav_aide.isChecked()

    fenetre.bouton_nav_accueil.click()
    assert isinstance(fenetre._pile.currentWidget(), VueAccueil)
    assert fenetre.bouton_nav_accueil.isChecked()

    fenetre.bouton_nav_parametres.click()
    assert isinstance(fenetre._pile.currentWidget(), VueParametres)
    assert fenetre.bouton_nav_parametres.isChecked()

    fenetre.bouton_nav_accueil.click()
    assert isinstance(fenetre._pile.currentWidget(), VueAccueil)


def test_nav_recherche_se_coche_et_accueil_se_decoche_quand_on_ouvre_une_recherche(
    qtbot,
):
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    assert fenetre.bouton_nav_accueil.isChecked()

    fenetre.bouton_nav_recherche.click()
    assert fenetre.bouton_nav_recherche.isChecked() is True
    assert fenetre.bouton_nav_accueil.isChecked() is False


def test_ouvrir_une_deuxieme_recherche_remplace_la_premiere(qtbot):
    """Pas d'accumulation de vues fantômes dans le QStackedWidget."""
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    fenetre.bouton_nav_recherche.click()
    fenetre.bouton_nav_recherche.click()
    nb_vues_recherche = sum(
        1
        for i in range(fenetre._pile.count())
        if isinstance(fenetre._pile.widget(i), VueRechercheResultats)
    )
    assert nb_vues_recherche == 1


_INFO_MAJ_TEST: InfoMaj = {
    "version": "1.1.0",
    "notes": "notes",
    "url_zip": "https://codeberg.org/x.zip",
    "url_publication": "https://codeberg.org/x",
}


def test_on_maj_verifiee_affiche_indicateur_et_carte(qtbot):
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    fenetre.show()  # isVisible() dépend du mappage réel à l'écran, cf. doc Qt
    # carte_maj vit dans l'écran Paramètres — un QStackedWidget ne rend
    # visible que sa page courante, il faut y naviguer pour la tester.
    fenetre.bouton_nav_parametres.click()

    fenetre._on_maj_verifiee(_INFO_MAJ_TEST)

    assert fenetre.point_maj.isVisible() is True
    assert fenetre._vue_parametres.carte_maj.isVisible() is True
    assert "1.1.0" in fenetre._vue_parametres.label_maj_version.text()


def test_on_maj_verifiee_none_cache_indicateur_mais_pas_la_carte(qtbot):
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    fenetre.show()
    fenetre.bouton_nav_parametres.click()

    fenetre._on_maj_verifiee(None)

    assert fenetre.point_maj.isVisible() is False
    assert fenetre._vue_parametres.carte_maj.isVisible() is True
    assert fenetre._vue_parametres.bouton_maj.isEnabled() is False


def test_demander_maj_immediate_marque_le_redemarrage(qtbot):
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    assert fenetre._redemarrage_demande is False

    fenetre._demander_maj_immediate()

    assert fenetre._redemarrage_demande is True


def test_lancer_verification_maj_nest_pas_appelee_a_la_construction(qtbot):
    """Volontaire (voir docstring de `_lancer_verification_maj`) : sinon un
    QThread démarré dans `__init__` peut planter le process au teardown
    des tests (destruction pendant qu'il tourne encore)."""
    fenetre = FenetrePrincipale()
    qtbot.addWidget(fenetre)
    assert fenetre._thread_maj is None


@pytest.fixture
def _main_prepare(monkeypatch):
    """Prépare `main()` pour un test isolé : pas de vrai `QApplication`
    (un seul singleton toléré par processus, déjà pris par pytest-qt), pas
    de réseau, capture l'instance `FenetrePrincipale` construite."""
    import src.gui.app as app_module

    monkeypatch.setattr(app_module, "obtenir_organisations", lambda: {})
    monkeypatch.setattr(
        app_module.FenetrePrincipale, "_lancer_verification_maj", lambda self: None
    )
    monkeypatch.setattr(app_module.FenetrePrincipale, "show", lambda self: None)

    instances = []
    init_original = app_module.FenetrePrincipale.__init__

    def _init_traqueur(self, *args, **kwargs):
        init_original(self, *args, **kwargs)
        instances.append(self)

    monkeypatch.setattr(app_module.FenetrePrincipale, "__init__", _init_traqueur)

    classe_qapp_reelle = app_module.QApplication
    monkeypatch.setattr(
        app_module, "QApplication", lambda args=None: classe_qapp_reelle.instance()
    )
    return app_module, instances, classe_qapp_reelle


def test_main_retourne_le_code_maj_si_redemarrage_demande(_main_prepare, monkeypatch):
    app_module, instances, classe_qapp_reelle = _main_prepare

    def _exec_avec_demande_maj(self):
        instances[0]._redemarrage_demande = True

    monkeypatch.setattr(classe_qapp_reelle, "exec", _exec_avec_demande_maj)

    assert app_module.main() == app_module.CODE_RETOUR_MAJ


def test_main_retourne_zero_si_fermeture_normale(_main_prepare, monkeypatch):
    app_module, _instances, classe_qapp_reelle = _main_prepare
    monkeypatch.setattr(classe_qapp_reelle, "exec", lambda self: None)

    assert app_module.main() == 0
