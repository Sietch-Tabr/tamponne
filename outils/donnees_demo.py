"""Données de démonstration identiques à celles de la maquette, écrites
dans un dossier temporaire pour les captures de comparaison (jamais dans
data/)."""

from pathlib import Path
from typing import cast

from PySide6.QtCore import QObject

from src import candidatures, profils
from src.gui.controleur_recherche import ControleurRecherche
from src.types import Candidature, DetailOffre, EvenementCandidature, Offre

_DETAIL_VIDE: DetailOffre = {
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
}


def _dossier(
    titre: str,
    employeur: str,
    lieu: str,
    historique: list[EvenementCandidature],
    disponible: bool = True,
) -> Candidature:
    return {
        "offre_titre": titre,
        "offre_employeur": employeur,
        "offre_url": "https://example.org/offre",
        "offre_reference": "",
        "offre_domaine": "",
        "offre_localisation": lieu,
        "offre_versant": "",
        "offre_date": "",
        "date_candidature": historique[0]["date"],
        "historique": historique,
        "disponible": disponible,
        "derniere_verification": "",
        "detail": dict(_DETAIL_VIDE),  # type: ignore[typeddict-item]
    }


def _avec_fiche(candidature: Candidature) -> Candidature:
    """Fiche de poste de la maquette (textes entre crochets)."""
    candidature["detail"].update(
        {
            "description": "[Description reprise de l'offre]",
            "salaire": "[selon l'offre]",
            "experience_requise": "[selon l'offre]",
            "formation_requise": "[selon l'offre]",
            "secteur": "[selon l'offre]",
            "date_publication": "01/10/2026",
            "date_limite": "[selon l'offre]",
            "a_propos_employeur": "[Présentation de l'employeur reprise de l'offre]",
            "lien_postuler": "https://example.org/postuler",
        }
    )
    candidature["offre_source"] = "Ministère de l'Intérieur"
    return candidature


def installer(dossier: Path) -> None:
    """Redirige les données vers `dossier` et y écrit les fiches et les
    trois dossiers de la maquette (le plus récemment suivi en dernier)."""
    profils.CHEMIN_PROFILS = dossier / "profils.json"
    dossier.mkdir(parents=True, exist_ok=True)
    profils.sauvegarder_profils(
        {
            "attache-paris": {
                "label": "Attaché, Paris et petite couronne",
                "categories": ["A+ (direction)", "A"],
                "versants": ["etat", "territorial"],
                "localisations": ["Île-de-France"],
                "teletravail": True,
                "nb_nouvelles": 2,
            },
            "hospitalier-achats": {
                "label": "Hospitalier, achats",
                "categories": ["A"],
                "versants": ["hospitalier"],
                "query": "achat",
            },
        }
    )
    candidatures.CHEMIN_CANDIDATURES = dossier / "candidatures.json"
    candidatures.DOSSIER_ARCHIVES = dossier / "archives"
    candidatures.DOSSIER_ARCHIVES.mkdir(parents=True, exist_ok=True)
    for reference in ("FHF_48213", "MINT_2026-31544"):
        (candidatures.DOSSIER_ARCHIVES / f"{reference}.pdf").write_bytes(b"%PDF-1.4\n")
    candidatures.sauvegarder_candidatures(
        {
            "FHF_48213": _dossier(
                "Acheteur(se) public(que)",
                "Centre hospitalier [exemple]",
                "Créteil 94",
                [
                    {"date": "2026-09-05", "type": "candidature_envoyee", "note": ""},
                    {"date": "2026-09-26", "type": "refus", "note": ""},
                ],
                disponible=False,
            ),
            "2026-30871": _dossier(
                "Chargé(e) de mission politiques agricoles",
                "DRAAF Île-de-France",
                "Paris 75",
                [
                    {"date": "2026-09-20", "type": "candidature_envoyee", "note": ""},
                    {"date": "2026-09-24", "type": "accuse_reception", "note": ""},
                    {
                        "date": "2026-10-01",
                        "type": "entretien_planifie",
                        "note": "visio, 14 h",
                    },
                ],
            ),
            "MINT_2026-31544": _avec_fiche(
                _dossier(
                    "Attaché(e) d'administration RH",
                    "Préfecture de région",
                    "Paris 75",
                    [{"date": "2026-09-11", "type": "candidature_envoyee", "note": ""}],
                )
            ),
        }
    )


def _offre(reference: str, titre: str, employeur: str, lieu: str, date: str, source: str) -> Offre:
    return {
        "titre": titre,
        "url": f"https://example.org/{reference}",
        "reference": reference,
        "domaine": "",
        "employeur": employeur,
        "localisation": lieu,
        "versant": "",
        "date": date,
        "source": source,
    }


def remplir_registre(recherche: QObject) -> None:
    """Formulaire et registre de la maquette dans l'écran Recherche, sans
    lancer de vraie recherche (outil de comparaison uniquement)."""
    controleur = cast(ControleurRecherche, recherche)
    controleur.definir("categories", ["A"])
    controleur.definir("versants", ["etat", "territorial"])
    controleur.definir("domaines", ["Achats", "Finances"])
    controleur.definir("localisations", ["Île-de-France"])
    controleur.definir("teletravail", True)
    offres = [
        _offre("AGRI_1", "Chargé(e) de mission politiques agricoles", "DRAAF Île-de-France", "Paris 75", "02/10/2026", "Ministère de l'Agriculture"),
        _offre("MINT_2", "Attaché(e) d'administration RH", "Préfecture de région", "Paris 75", "01/10/2026", "Ministère de l'Intérieur"),
        _offre("T3", "Responsable du service finances", "Commune [exemple]", "Versailles 78", "30/09/2026", "Fonction publique territoriale"),
        _offre("FHF_4", "Acheteur(se) public(que)", "Centre hospitalier [exemple]", "Créteil 94", "29/09/2026", "FHF"),
        _offre("MEF_5", "Chef(fe) de bureau budget", "Direction ministérielle [exemple]", "Paris 75", "28/09/2026", "MEF"),
        _offre("2026-6", "Chargé(e) d'études statistiques", "Service statistique [exemple]", "Montrouge 92", "27/09/2026", ""),
    ]
    controleur._modele.definir_offres(offres, {"AGRI_1", "MINT_2"})
    controleur._nb_nouvelles = 2
    controleur._resume = "6 inscrites · 2 nouvelles · 1 écartée (grades supérieurs) · 04/10/2026 10:12"
    controleur._phase = "resultats"
    controleur.selectionner(1)
