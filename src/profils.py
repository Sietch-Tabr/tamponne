"""Gestion des profils de recherche sauvegardés."""

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, cast

from src.filtres import categorie_normalisee, resumer_filtres
from src.types import FiltresRecherche, Profil
from src.utils import ecriture_atomique

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
            f"Avertissement\u00a0: {CHEMIN_PROFILS.name} illisible ou corrompu, "
            "aucun profil chargé.",
            file=sys.stderr,
        )
        return {}


def sauvegarder_profils(profils: dict[str, Profil]) -> None:
    """Écrit profils.json sur le disque."""
    ecriture_atomique(CHEMIN_PROFILS, profils)


def ajouter_profil(nom: str, filtres: Profil) -> None:
    """Crée ou remplace un profil."""
    profils = charger_profils()
    profils[nom] = {**filtres, "cree_le": date.today().isoformat()}
    sauvegarder_profils(profils)


_METADONNEES_CONSERVEES = ("label", "cree_le", "dernier_lancement")


def modifier_profil(nom: str, filtres: FiltresRecherche) -> None:
    """Remplace les critères d'un profil en gardant son intitulé, sa date
    de création et celle du dernier lancement."""
    profils = charger_profils()
    ancien = cast(dict[str, Any], profils.get(nom, {}))
    conserve = {cle: ancien[cle] for cle in _METADONNEES_CONSERVEES if cle in ancien}
    profils[nom] = cast(
        Profil, {"cree_le": date.today().isoformat(), **conserve, **filtres}
    )
    sauvegarder_profils(profils)


def supprimer_profil(nom: str) -> None:
    """Supprime un profil."""
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
    profils = charger_profils()
    if nom_source not in profils:
        raise KeyError(f"Profil introuvable\u00a0: {nom_source}")
    profils[nouveau_nom] = {
        **profils[nom_source],
        "cree_le": date.today().isoformat(),
    }
    if label:
        profils[nouveau_nom]["label"] = label
    sauvegarder_profils(profils)


def noter_lancement(nom: str) -> None:
    """Enregistre la date du dernier lancement d'une fiche (ignorée si elle
    n'existe plus)."""
    profils = charger_profils()
    if nom not in profils:
        return
    profils[nom]["dernier_lancement"] = date.today().isoformat()
    sauvegarder_profils(profils)


def categories_compatibles(profil: FiltresRecherche) -> list[str]:
    """Catégories d'un profil en clés de `src.filtres.CATEGORIES`, y compris
    celles enregistrées sous leur libellé court, sans doublon."""
    return list(dict.fromkeys(categorie_normalisee(c) for c in profil.get("categories") or []))


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
