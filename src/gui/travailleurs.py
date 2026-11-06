"""Exécution de la recherche réseau en arrière-plan (QThread + Signal).

Les signaux de ce worker ne doivent être connectés qu'à des
méthodes liées d'objets `QObject` créés dans le thread principal — une
connexion à une fonction/lambda ordinaire ne garantit pas l'exécution
sur le bon thread.
"""

import logging
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal

from src.maj import (
    VerificationImpossible,
    ecrire_maj_disponible,
    maj_en_echec,
    verifier_derniere_publication,
)
from src.recherche.orchestration import RechercheImpossible, rechercher_toutes_sources
from src.sources.detail import verifier_disponibilite
from src.types import Candidature, FiltresRecherche, Organisations

journal = logging.getLogger(__name__)

MESSAGE_INATTENDU = "Erreur inattendue, le détail est dans le journal de Tamponné."
"""Montré quand un traitement d'arrière-plan échoue autrement que prévu : sans
cela le thread ne se terminerait pas et l'écran resterait « en cours »."""


class TravailleurRecherche(QObject):
    """Adaptateur Qt de `src.recherche.orchestration.rechercher_toutes_sources` (sources
    actives interrogées en parallèle, fusion, dédoublonnage) — à déplacer
    dans un `QThread` avant de démarrer (`moveToThread`).

    Chaque source tourne dans un thread du pool : les signaux peuvent
    donc être émis depuis ces threads, d'où l'obligation de ne les
    connecter qu'à des méthodes liées de `QObject` (connexion en file).
    """

    progression = Signal(str, int, int)
    """(nom affiché de la source, page chargée, nb pages à charger)."""
    fiches = Signal(str, int, int)
    """(nom affiché de la source, fiches lues, nb fiches à lire)."""
    resultat = Signal(list, int, bool)
    erreur = Signal(str)
    avertissement = Signal(str)
    """Émis pour chaque source active en échec, sans interrompre les autres."""
    echec_source = Signal(str)
    """Nom affiché d'une source en échec (en plus de son avertissement)."""
    source_en_cours = Signal(str)
    """Nom affiché d'une source dont l'interrogation démarre."""
    source_terminee = Signal(str)
    """Nom affiché d'une source dont l'interrogation est finie (succès ou échec)."""
    offres_source = Signal(str, int)
    """(nom affiché, nombre d'offres trouvées) d'une source qui a réussi."""

    def __init__(self, filtres: FiltresRecherche, orgas_cache: Organisations) -> None:
        super().__init__()
        self._filtres = filtres
        self._orgas_cache = orgas_cache

    def executer(self) -> None:
        """Slot à connecter à `QThread.started` — tourne dans le thread
        du worker une fois `moveToThread` appelé. Relaie en signaux les
        callbacks de `src.recherche.orchestration.rechercher_toutes_sources`."""
        try:
            offres, nb_pages, arret_anticipe = rechercher_toutes_sources(
                self._filtres,
                self._orgas_cache,
                on_source_en_cours=self.source_en_cours.emit,
                on_progression=self.progression.emit,
                on_fiches=self.fiches.emit,
                on_source_terminee=self.source_terminee.emit,
                on_avertissement=self.avertissement.emit,
                on_echec_source=self.echec_source.emit,
                on_offres_source=self.offres_source.emit,
            )
        except RechercheImpossible as erreur:
            journal.error("Recherche impossible\u00a0: %s", erreur)
            self.erreur.emit(str(erreur))
            return
        except Exception:  # noqa: BLE001 - tout échec doit terminer le thread
            journal.exception("Recherche interrompue par une erreur inattendue")
            self.erreur.emit(MESSAGE_INATTENDU)
            return
        self.resultat.emit(offres, nb_pages, arret_anticipe)


class VerificateurDisponibilite(QObject):
    """Vérifie séquentiellement la disponibilité (toujours en ligne ou
    dépubliée) des offres des candidatures données — l'appelant choisit
    lesquelles — même pattern QThread que `TravailleurRecherche`."""

    progression = Signal(int, int)
    resultat = Signal(dict, dict)
    """`dict[reference, bool]` des offres vérifiées, puis
    `dict[reference, str]` des offres non vérifiées (site injoignable) avec
    le détail de l'erreur : rien n'est conclu pour celles-ci."""

    def __init__(self, candidatures: dict[str, Candidature]) -> None:
        super().__init__()
        self._candidatures = candidatures

    def executer(self) -> None:
        """Slot à connecter à `QThread.started`."""
        a_verifier = list(self._candidatures)
        resultats: dict[str, bool] = {}
        echecs: dict[str, str] = {}
        total = len(a_verifier)
        for i, reference in enumerate(a_verifier, 1):
            url = self._candidatures[reference]["offre_url"]
            try:
                resultats[reference] = verifier_disponibilite(url)
            except RuntimeError as erreur:
                journal.warning("Offre %s non vérifiée\u00a0: %s", reference, erreur)
                echecs[reference] = str(erreur)
            # Une offre en erreur ne bloque pas les autres.
            except Exception as erreur:  # noqa: BLE001
                journal.exception(
                    "Offre %s non vérifiée (erreur inattendue)", reference
                )
                echecs[reference] = type(erreur).__name__
            self.progression.emit(i, total)
        self.resultat.emit(resultats, echecs)


class VerificateurMiseAJour(QObject):
    """Vérifie une fois s'il existe une publication Codeberg plus récente —
    même pattern QThread que `TravailleurRecherche`/`VerificateurDisponibilite`."""

    resultat = Signal(object)
    """`InfoMaj | None` — `None` si aucune mise à jour (rien de publié,
    déjà à jour)."""
    echec = Signal(str)
    """Codeberg injoignable : détail technique de l'erreur."""

    def executer(self) -> None:
        """Slot à connecter à `QThread.started`. Pose le marqueur de mise
        à jour disponible si une publication plus récente est trouvée —
        c'est ce marqueur qui déclenche l'application automatique au
        prochain lancement (`src.lanceur`), indépendamment
        d'un clic utilisateur. Pas pour une version déjà annulée par le
        lanceur : seul « Installer et redémarrer » la retente."""
        try:
            info = verifier_derniere_publication()
        except VerificationImpossible as erreur:
            journal.warning("Vérification de mise à jour impossible\u00a0: %s", erreur)
            self.echec.emit(str(erreur))
            return
        except Exception:  # noqa: BLE001 - tout échec doit terminer le thread
            journal.exception("Vérification de mise à jour : erreur inattendue")
            self.echec.emit(MESSAGE_INATTENDU)
            return
        if info is not None and not maj_en_echec(info["version"]):
            try:
                ecrire_maj_disponible(info)
            except OSError as erreur:
                # La publication reste annoncée à l'utilisateur, qui peut l'installer.
                journal.warning("Marqueur de mise à jour non écrit\u00a0: %s", erreur)
        self.resultat.emit(info)


class TacheReseau(QObject):
    """Appel réseau ponctuel (détail d'une offre, suivi) exécuté dans un
    `QThread`, pour ne pas figer l'interface pendant l'attente."""

    termine = Signal(object)
    """Valeur renvoyée par la fonction."""
    echec = Signal(str)
    """Message d'erreur si la fonction a levé une exception attendue."""

    def __init__(self, fonction: Callable[[], object]) -> None:
        super().__init__()
        self._fonction = fonction

    def executer(self) -> None:
        """Slot à connecter à `QThread.started`."""
        try:
            resultat = self._fonction()
        except (RuntimeError, OSError) as erreur:
            self.echec.emit(str(erreur))
            return
        except Exception:  # noqa: BLE001 - tout échec doit terminer le thread
            journal.exception("Tâche réseau : erreur inattendue")
            self.echec.emit(MESSAGE_INATTENDU)
            return
        self.termine.emit(resultat)
