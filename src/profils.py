"""Gestion des profils de recherche sauvegardés."""

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, cast

from src.filtres import resumer_filtres
from src.types import FiltresRecherche, Profil
from src.utils import VERROU_DONNEES, ecriture_atomique

CHEMIN_PROFILS = Path(__file__).parent.parent / "data" / "profils.json"


def charger_profils() -> dict[str, Profil]:
    """Charge les profils depuis profils.json."""
    if not CHEMIN_PROFILS.exists():
        return {}
    try:
        return json.loads(CHEMIN_PROFILS.read_text(encoding="utf-8"))
    except json.JSONDecodeError, OSError:
        # stderr, pas de bibliothèque d'UI : ce module n'est lié à
        # aucune interface particulière.
        print(
            f"Avertissement : {CHEMIN_PROFILS.name} illisible ou corrompu, "
            "aucun profil chargé.",
            file=sys.stderr,
        )
        return {}


def sauvegarder_profils(profils: dict[str, Profil]) -> None:
    """Écrit profils.json sur le disque."""
    ecriture_atomique(CHEMIN_PROFILS, profils)


def ajouter_profil(nom: str, filtres: Profil) -> None:
    """Crée ou remplace un profil."""
    with VERROU_DONNEES:
        profils = charger_profils()
        profils[nom] = {**filtres, "cree_le": date.today().isoformat()}
        sauvegarder_profils(profils)


def modifier_profil(nom: str, filtres: FiltresRecherche) -> None:
    """Met à jour un profil existant (conserve cree_le original)."""
    with VERROU_DONNEES:
        profils = charger_profils()
        cree_le = profils.get(nom, {}).get("cree_le", date.today().isoformat())
        profils[nom] = {**filtres, "cree_le": cree_le}
        sauvegarder_profils(profils)


def supprimer_profil(nom: str) -> None:
    """Supprime un profil."""
    with VERROU_DONNEES:
        profils = charger_profils()
        profils.pop(nom, None)
        sauvegarder_profils(profils)


def dupliquer_profil(
    nom_source: str, nouveau_nom: str, label: str | None = None
) -> None:
    """Copie un profil sous un nouveau nom.

    Args:
        nom_source: Profil à copier.
        nouveau_nom: Nom de la copie.
        label: Intitulé de la copie ; `None` garde celui du profil source.
    """
    with VERROU_DONNEES:
        profils = charger_profils()
        if nom_source not in profils:
            raise KeyError(f"Profil introuvable : {nom_source}")
        profils[nouveau_nom] = {
            **profils[nom_source],
            "cree_le": date.today().isoformat(),
        }
        if label:
            profils[nouveau_nom]["label"] = label
        sauvegarder_profils(profils)


def mettre_a_jour_stats(nom: str, nb_nouvelles: int, consultation: bool = True) -> None:
    """Enregistre le nombre d'offres pas encore consultées et sa date.

    Args:
        nom: Profil concerné (ignoré s'il n'existe plus).
        nb_nouvelles: Offres pas encore consultées dans le registre.
        consultation: Vrai pour un lancement depuis l'interface (date du
            dernier lancement aussi mise à jour), faux pour un relevé.
    """
    with VERROU_DONNEES:
        profils = charger_profils()
        if nom not in profils:
            return
        aujourd_hui = date.today().isoformat()
        if consultation:
            profils[nom]["dernier_lancement"] = aujourd_hui
        profils[nom]["nb_nouvelles"] = nb_nouvelles
        profils[nom]["nouvelles_le"] = aujourd_hui
        sauvegarder_profils(profils)


def versants_compatibles(profil: FiltresRecherche) -> list[str]:
    """Versants d'un profil, y compris au format singulier historique
    (`"versant": "etat"|"hospitalier"|"territorial"|"__tous__"`)."""
    versants = profil.get("versants")
    if versants is not None:
        return list(versants)
    ancien = cast(dict[str, Any], profil).get("versant")
    if ancien is None or ancien == "etat":
        return ["etat"]
    if ancien == "__tous__":
        return []
    return [str(ancien)]


def resume_profil(profil: Profil) -> str:
    """Retourne une ligne de résumé lisible pour l'affichage dans les menus.

    `Profil` étend `FiltresRecherche` : délègue à `resumer_filtres`,
    seule implémentation (avant, une copie légèrement divergente
    existait ici — sans le versant notamment).
    """
    return resumer_filtres(profil)
