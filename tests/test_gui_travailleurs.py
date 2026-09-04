"""Tests des utilitaires GUI de recherche réseau (src/gui/travailleurs.py)."""

import pytest

from src import parametres_sources
from src.gui.travailleurs import (
    TravailleurRecherche,
    VerificateurMiseAJour,
    _reformater_date,
    offre_vers_ligne,
)
from src.sources import emploiterritorial as emploiterritorial_module
from src.sources.choisirleservicepublic import ChoisirLeServicePublic
from src.sources.emploiterritorial import EmploiTerritorial
from src.sources.fhf import Fhf
from src.sources.passerellesmef import PasserellesMef
from src.types import InfoMaj, Offre


@pytest.fixture(autouse=True)
def _rediriger_sources_vers_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(parametres_sources, "CHEMIN_SOURCES", tmp_path / "sources.json")
    # passerellesmef/fhf désactivées par défaut : évite un vrai appel réseau
    # dans les tests qui ne mockent que choisirleservicepublic/territorial.
    parametres_sources.sauvegarder_sources_actives(
        {"passerellesmef": False, "fhf": False}
    )


def test_reformater_date_format_reel_du_site():
    assert _reformater_date("26 août 2026") == "26/08/2026"


def test_reformater_date_jour_sur_un_chiffre():
    assert _reformater_date("5 mars 2026") == "05/03/2026"


def test_reformater_date_premier_du_mois_avec_suffixe_er():
    assert _reformater_date("1er janvier 2026") == "01/01/2026"


def test_reformater_date_format_non_reconnu_retourne_tel_quel():
    assert _reformater_date("il y a 6 jours") == "il y a 6 jours"


def test_reformater_date_chaine_vide_retourne_tel_quel():
    assert _reformater_date("") == ""


_OFFRE_TEST: Offre = {
    "titre": "Attaché principal",
    "url": "https://example.org/1",
    "reference": "O1",
    "domaine": "RH",
    "employeur": "DGFiP Hérault",
    "localisation": "Montpellier (34)",
    "versant": "Fonction publique de l'État",
    "date": "26 août 2026",
    "source": "",
}


def test_offre_vers_ligne_reformate_la_date():
    assert offre_vers_ligne(_OFFRE_TEST) == (
        "Attaché principal",
        "DGFiP Hérault",
        "Montpellier (34)",
        "26/08/2026",
        "Choisir le service public",
    )


def test_offre_vers_ligne_date_absente():
    offre = {**_OFFRE_TEST, "date": ""}
    assert offre_vers_ligne(offre)[3] == "—"


def test_offre_vers_ligne_source_territoriale():
    offre = {**_OFFRE_TEST, "source": "Fonction publique territoriale"}
    assert offre_vers_ligne(offre)[4] == "Fonction publique territoriale"


def _offre(reference: str, source: str = "") -> Offre:
    return {
        "titre": f"Offre {reference}",
        "url": f"https://example.org/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": "",
        "localisation": "",
        "versant": "",
        "date": "",
        "source": source,
    }


def _executer(travailleur: TravailleurRecherche) -> tuple[list, list, list]:
    """Exécute `travailleur.executer()` directement (hors QThread) et
    collecte les émissions des signaux pertinents."""
    resultats, avertissements, erreurs = [], [], []
    travailleur.resultat.connect(lambda *a: resultats.append(a))
    travailleur.avertissement.connect(avertissements.append)
    travailleur.erreur.connect(erreurs.append)
    travailleur.executer()
    return resultats, avertissements, erreurs


def test_executer_fusionne_les_resultats_de_deux_sources(monkeypatch):
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2", "Territorial")], 1, False),
    )
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert avertissements == []
    assert erreurs == []
    offres, nb_pages, arret_anticipe = resultats[0]
    assert {o["reference"] for o in offres} == {"O1", "O2"}


def test_executer_dedoublonne_les_offres_communes(monkeypatch):
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1", "Territorial")], 1, False),
    )
    resultats, _, _ = _executer(TravailleurRecherche({}, {}))
    offres = resultats[0][0]
    assert len(offres) == 1
    assert offres[0]["source"] == ""  # version choisirleservicepublic conservée


def test_executer_avertissement_sur_echec_partiel_sans_bloquer(monkeypatch):
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )

    def _echec(self, filtres, on_page=None):
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echec)
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert erreurs == []
    assert len(avertissements) == 1
    assert "indisponible" in avertissements[0]
    assert resultats[0][0][0]["reference"] == "O1"


def test_executer_erreur_si_toutes_les_sources_echouent(monkeypatch):
    def _echec(self, filtres, on_page=None):
        raise RuntimeError("Erreur réseau")

    monkeypatch.setattr(ChoisirLeServicePublic, "rechercher", _echec)
    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echec)
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert resultats == []
    assert len(erreurs) == 1


def test_executer_erreur_si_aucune_source_active(monkeypatch):
    parametres_sources.sauvegarder_sources_actives(
        {
            "choisirleservicepublic": False,
            "emploiterritorial": False,
            "passerellesmef": False,
            "fhf": False,
        }
    )
    resultats, avertissements, erreurs = _executer(TravailleurRecherche({}, {}))
    assert resultats == []
    assert len(erreurs) == 1


def test_executer_source_desactivee_nest_pas_interrogee(monkeypatch):
    parametres_sources.sauvegarder_sources_actives(
        {"emploiterritorial": False, "passerellesmef": False, "fhf": False}
    )
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )

    def _echoue_si_appelee(self, filtres, on_page=None):
        raise AssertionError("emploiterritorial ne doit pas être interrogée")

    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echoue_si_appelee)
    resultats, _, _ = _executer(TravailleurRecherche({}, {}))
    assert resultats[0][0][0]["reference"] == "O1"


def test_executer_versant_etat_seul_exclut_territorial_et_hospitaliere(monkeypatch):
    # Régression : emploi-territorial.fr (FPT) et emploi.fhf.fr (FPH) sont
    # mono-versant et étaient interrogées quel que soit le filtre Versant —
    # une recherche restreinte à l'État renvoyait quand même de la FPT/FPH.
    parametres_sources.sauvegarder_sources_actives(
        {"passerellesmef": True, "fhf": True}
    )
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    # Passerelles/MEF est elle-même mono-versant État : doit rester interrogée.
    monkeypatch.setattr(
        PasserellesMef,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2", "MEF")], 1, False),
    )

    def _echoue_si_appelee(self, filtres, on_page=None):
        raise AssertionError("source mono-versant exclue par le filtre appelée")

    monkeypatch.setattr(EmploiTerritorial, "rechercher", _echoue_si_appelee)
    monkeypatch.setattr(Fhf, "rechercher", _echoue_si_appelee)

    resultats, _, _ = _executer(TravailleurRecherche({"versants": ["etat"]}, {}))
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2"}


def test_executer_versant_territorial_seul_interroge_emploiterritorial(monkeypatch):
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2", "Territorial")], 1, False),
    )
    resultats, _, _ = _executer(TravailleurRecherche({"versants": ["territorial"]}, {}))
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2"}


def test_executer_sans_filtre_versant_interroge_toutes_les_sources_actives(
    monkeypatch,
):
    parametres_sources.sauvegarder_sources_actives(
        {"passerellesmef": True, "fhf": True}
    )
    for classe, ref in [
        (ChoisirLeServicePublic, "O1"),
        (EmploiTerritorial, "O2"),
        (PasserellesMef, "O3"),
        (Fhf, "O4"),
    ]:
        monkeypatch.setattr(
            classe,
            "rechercher",
            lambda self, filtres, on_page=None, ref=ref: ([_offre(ref)], 1, False),
        )
    resultats, _, _ = _executer(TravailleurRecherche({}, {}))
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2", "O3", "O4"}


def test_executer_traduit_categorie_et_departement_vers_emploiterritorial(
    monkeypatch,
):
    """Test d'intégration : FiltresRecherche -> URL réelle envoyée à ET,
    en passant par la vraie traduction de emploiterritorial/__init__.py
    (pas un mock de EmploiTerritorial.rechercher qui la court-circuiterait)."""
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    urls_appelees = []

    def _obtenir_page_recherche_factice(opener, url):
        urls_appelees.append(url)
        return {"html": "<html></html>", "title": ""}

    monkeypatch.setattr(
        emploiterritorial_module,
        "obtenir_page_recherche",
        _obtenir_page_recherche_factice,
    )

    filtres = {"categories": ["A"], "localisations": ["Hérault"]}
    _executer(TravailleurRecherche(filtres, {}))

    assert len(urls_appelees) == 1
    assert "search_offre_form%5Bsearchcat%5D%5B%5D=A" in urls_appelees[0]
    assert "search_offre_form%5Bsearchdept%5D%5B%5D=034" in urls_appelees[0]


def test_executer_emet_source_en_cours(monkeypatch):
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        EmploiTerritorial,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2", "Territorial")], 1, False),
    )
    travailleur = TravailleurRecherche({}, {})
    sources_vues = []
    travailleur.source_en_cours.connect(sources_vues.append)
    travailleur.executer()
    assert sources_vues == [
        parametres_sources.SOURCES_DISPONIBLES["choisirleservicepublic"],
        parametres_sources.SOURCES_DISPONIBLES["emploiterritorial"],
    ]


def test_executer_interroge_passerellesmef_et_fhf_quand_actives(monkeypatch):
    parametres_sources.sauvegarder_sources_actives(
        {"emploiterritorial": False, "passerellesmef": True, "fhf": True}
    )
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O1")], 1, False),
    )
    monkeypatch.setattr(
        PasserellesMef,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("O2", "MEF")], 1, False),
    )
    monkeypatch.setattr(
        Fhf,
        "rechercher",
        lambda self, filtres, on_page=None: ([_offre("FHF_1", "FHF")], 1, False),
    )
    resultats, avertissements, _ = _executer(TravailleurRecherche({}, {}))
    assert avertissements == []
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1", "O2", "FHF_1"}


def test_executer_fhf_dedoublonnee_contre_les_autres_sources(monkeypatch):
    # "Un(e) Infirmier(ère)" au même employeur que O1 : doit être filtrée
    # par filtrer_doublons_fhf avant fusion, même titre + employeur lié.
    parametres_sources.sauvegarder_sources_actives(
        {"emploiterritorial": False, "passerellesmef": False, "fhf": True}
    )
    offre_csp = {
        **_offre("O1"),
        "titre": "Infirmier de nuit",
        "employeur": "Centre Hospitalier Epsylan",
    }
    offre_fhf = {
        **_offre("FHF_1", "FHF"),
        "titre": "Infirmier de nuit",
        "employeur": "EPSYLAN (Établissement Psychiatrique)",
    }
    monkeypatch.setattr(
        ChoisirLeServicePublic,
        "rechercher",
        lambda self, filtres, on_page=None: ([offre_csp], 1, False),
    )
    monkeypatch.setattr(
        Fhf,
        "rechercher",
        lambda self, filtres, on_page=None: ([offre_fhf], 1, False),
    )
    resultats, _, _ = _executer(TravailleurRecherche({}, {}))
    offres = resultats[0][0]
    assert {o["reference"] for o in offres} == {"O1"}


_INFO_MAJ_TEST: InfoMaj = {
    "version": "1.1.0",
    "notes": "notes",
    "url_zip": "https://codeberg.org/x.zip",
    "url_publication": "https://codeberg.org/x",
}


def test_verificateur_maj_emet_linfo_si_disponible(monkeypatch):
    from src.gui import travailleurs as travailleurs_module

    monkeypatch.setattr(
        travailleurs_module, "verifier_derniere_publication", lambda: _INFO_MAJ_TEST
    )
    marqueurs_ecrits = []
    monkeypatch.setattr(
        travailleurs_module, "ecrire_maj_disponible", marqueurs_ecrits.append
    )

    resultats = []
    verificateur = VerificateurMiseAJour()
    verificateur.resultat.connect(resultats.append)
    verificateur.executer()

    assert resultats == [_INFO_MAJ_TEST]
    assert marqueurs_ecrits == [_INFO_MAJ_TEST]


def test_verificateur_maj_emet_none_si_a_jour_ou_hors_ligne(monkeypatch):
    from src.gui import travailleurs as travailleurs_module

    monkeypatch.setattr(
        travailleurs_module, "verifier_derniere_publication", lambda: None
    )
    marqueurs_ecrits = []
    monkeypatch.setattr(
        travailleurs_module, "ecrire_maj_disponible", marqueurs_ecrits.append
    )

    resultats = []
    verificateur = VerificateurMiseAJour()
    verificateur.resultat.connect(resultats.append)
    verificateur.executer()

    assert resultats == [None]
    assert marqueurs_ecrits == []
