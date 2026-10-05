"""Interface commune à toutes les sources d'offres."""

from collections.abc import Callable
from typing import Protocol

from src.types import FiltresRecherche, Offre

# Sites sans WAF : User-Agent identifiant l'application et son dépôt.
USER_AGENT_IDENTIFIE = "tamponne (+https://codeberg.org/Kwaite/tamponne)"


def deduplique_offres(offres: list[Offre]) -> list[Offre]:
    """Retire les doublons par référence (insensible à la casse), garde
    la première occurrence — appeler avec choisirleservicepublic en
    premier pour conserver sa version (détail enrichi, PDF archivé)
    quand une offre territoriale déjà syndiquée apparaît aussi côté
    choisirleservicepublic (même référence sur les deux sites)."""
    vues: set[str] = set()
    resultat: list[Offre] = []
    for offre in offres:
        ref = offre["reference"].upper()
        if ref and ref in vues:
            continue
        vues.add(ref)
        resultat.append(offre)
    return resultat


class SourceOffres(Protocol):
    """Contrat qu'une source de données doit respecter pour être branchée
    sur le moteur de recherche.

    Convertit des filtres génériques (indépendants de la source) en
    offres, en gérant elle-même la pagination propre à son API/site.
    Ne filtre pas les grades supérieurs (IDIV/IP*/AFIPA) : ça reste un
    post-traitement appliqué par l'appelant, pour permettre de les
    afficher ponctuellement (bouton dédié dans la TUI).
    """

    def rechercher(
        self,
        filtres: FiltresRecherche,
        on_page: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Offre], int, bool]:
        """Retourne (offres de toutes les pages chargées, nb_pages, arret_anticipe).

        Args:
            filtres: Filtres génériques du wizard/TUI.
            on_page: Callback optionnel appelé après chaque page chargée
                avec (page_courante, nb_pages_a_charger), pour permettre
                à l'appelant d'afficher une progression sans coupler
                cette méthode à une bibliothèque d'UI particulière.

        Returns:
            Tuple ``(offres, nb_pages, arret_anticipe)`` où ``nb_pages``
            est le nombre de pages annoncé par la source (peut dépasser
            le nombre de pages effectivement chargées si la source plafonne),
            et ``arret_anticipe`` indique un arrêt avant la fin (page vide
            ou boucle détectée).
        """
        ...
