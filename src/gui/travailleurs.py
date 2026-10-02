"""Exécution de la recherche réseau en arrière-plan (QThread + Signal).

Pattern vérifié concrètement avant écriture (REFONTE.md §8, Lot GUI
étape 2) : les signaux de ce worker ne doivent être connectés qu'à des
méthodes liées d'objets `QObject` créés dans le thread principal — une
connexion à une fonction/lambda ordinaire ne garantit pas l'exécution
sur le bon thread.
"""

from PySide6.QtCore import QObject, Signal

from src.candidatures import verifier_disponibilite
from src.maj import ecrire_maj_disponible, verifier_derniere_publication
from src.recherche import RechercheImpossible, rechercher_toutes_sources
from src.types import Candidature, FiltresRecherche, Organisations


class TravailleurRecherche(QObject):
    """Adaptateur Qt de `src.recherche.rechercher_toutes_sources` (sources
    actives interrogées en parallèle, fusion, dédoublonnage) — à déplacer
    dans un `QThread` avant de démarrer (`moveToThread`).

    Chaque source tourne dans un thread du pool : les signaux peuvent
    donc être émis depuis ces threads, d'où l'obligation de ne les
    connecter qu'à des méthodes liées de `QObject` (connexion en file).
    """

    progression = Signal(str, int, int)
    """(nom affiché de la source, page chargée, nb pages à charger)."""
    resultat = Signal(list, int, bool)
    erreur = Signal(str)
    avertissement = Signal(str)
    """Émis pour chaque source active en échec, sans interrompre les autres."""
    source_en_cours = Signal(str)
    """Nom affiché d'une source dont l'interrogation démarre."""
    source_terminee = Signal(str)
    """Nom affiché d'une source dont l'interrogation est finie (succès ou échec)."""

    def __init__(self, filtres: FiltresRecherche, orgas_cache: Organisations) -> None:
        super().__init__()
        self._filtres = filtres
        self._orgas_cache = orgas_cache

    def executer(self) -> None:
        """Slot à connecter à `QThread.started` — tourne dans le thread
        du worker une fois `moveToThread` appelé. Relaie en signaux les
        callbacks de `src.recherche.rechercher_toutes_sources`."""
        try:
            offres, nb_pages, arret_anticipe = rechercher_toutes_sources(
                self._filtres,
                self._orgas_cache,
                on_source_en_cours=self.source_en_cours.emit,
                on_progression=self.progression.emit,
                on_source_terminee=self.source_terminee.emit,
                on_avertissement=self.avertissement.emit,
            )
        except RechercheImpossible as erreur:
            self.erreur.emit(str(erreur))
            return
        self.resultat.emit(offres, nb_pages, arret_anticipe)


class VerificateurDisponibilite(QObject):
    """Vérifie séquentiellement la disponibilité (toujours en ligne ou
    dépubliée) des offres suivies dont le statut n'est pas déjà connu
    comme dépublié — même pattern QThread que `TravailleurRecherche`."""

    progression = Signal(int, int)
    resultat = Signal(dict)
    """dict[reference, bool | None] — None si la vérification a échoué
    (erreur réseau), à ne pas interpréter comme une réponse."""

    def __init__(self, candidatures: dict[str, Candidature]) -> None:
        super().__init__()
        self._candidatures = candidatures

    def executer(self) -> None:
        """Slot à connecter à `QThread.started`."""
        a_verifier = [
            ref
            for ref, candidature in self._candidatures.items()
            if candidature.get("disponible", True)
        ]
        resultats: dict[str, bool | None] = {}
        total = len(a_verifier)
        for i, reference in enumerate(a_verifier, 1):
            url = self._candidatures[reference]["offre_url"]
            resultats[reference] = verifier_disponibilite(url)
            self.progression.emit(i, total)
        self.resultat.emit(resultats)


class VerificateurMiseAJour(QObject):
    """Vérifie une fois s'il existe une publication Codeberg plus récente —
    même pattern QThread que `TravailleurRecherche`/`VerificateurDisponibilite`."""

    resultat = Signal(object)
    """`InfoMaj | None` — `None` si aucune mise à jour (rien de publié,
    déjà à jour, ou échec réseau silencieux, voir `src.maj`)."""

    def executer(self) -> None:
        """Slot à connecter à `QThread.started`. Pose le marqueur de mise
        à jour disponible si une publication plus récente est trouvée —
        c'est ce marqueur qui déclenche l'application automatique au
        prochain lancement (`lancer.sh`/`lancer.bat`), indépendamment
        d'un clic utilisateur."""
        info = verifier_derniere_publication()
        if info is not None:
            ecrire_maj_disponible(info)
        self.resultat.emit(info)
