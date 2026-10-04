"""Données de démonstration identiques à celles de la maquette, écrites
dans un dossier temporaire pour les captures de comparaison (jamais dans
data/)."""

from pathlib import Path

from src import candidatures
from src.types import Candidature, DetailOffre, EvenementCandidature

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


def installer(dossier: Path) -> None:
    """Redirige les données du Suivi vers `dossier` et y écrit les trois
    dossiers de la maquette (le plus récemment suivi en dernier)."""
    candidatures.CHEMIN_CANDIDATURES = dossier / "candidatures.json"
    candidatures.DOSSIER_ARCHIVES = dossier / "archives"
    candidatures.DOSSIER_ARCHIVES.mkdir(parents=True, exist_ok=True)
    (candidatures.DOSSIER_ARCHIVES / "FHF_48213.pdf").write_bytes(b"%PDF-1.4\n")
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
            "MINT_2026-31544": _dossier(
                "Attaché(e) d'administration RH",
                "Préfecture de région",
                "Paris 75",
                [{"date": "2026-09-11", "type": "candidature_envoyee", "note": ""}],
            ),
        }
    )
