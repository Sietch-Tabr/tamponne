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
from src.parametres_sources import (
    SOURCES_DISPONIBLES,
    VERSANT_SOURCE,
    charger_sources_actives,
)
from src.sources.base import SourceOffres, deduplique_offres
from src.sources.choisirleservicepublic import ChoisirLeServicePublic
from src.sources.emploiterritorial import EmploiTerritorial
from src.sources.fhf import Fhf
from src.sources.fhf.dedoublonnage import filtrer_doublons_fhf
from src.sources.passerellesmef import PasserellesMef
from src.types import Candidature, FiltresRecherche, Offre, Organisations


class TravailleurRecherche(QObject):
    """Interroge les sources actives (`parametres_sources`), fusionne et
    dédoublonne les résultats — à déplacer dans un `QThread` avant de
    démarrer (`moveToThread`)."""

    progression = Signal(int, int)
    resultat = Signal(list, int, bool)
    erreur = Signal(str)
    avertissement = Signal(str)
    """Émis pour chaque source active en échec, sans interrompre les autres."""
    source_en_cours = Signal(str)
    """Nom affiché de la source en cours d'interrogation."""

    def __init__(self, filtres: FiltresRecherche, orgas_cache: Organisations) -> None:
        super().__init__()
        self._filtres = filtres
        self._orgas_cache = orgas_cache

    def _construire_source(self, cle: str) -> SourceOffres | None:
        if cle == "choisirleservicepublic":
            return ChoisirLeServicePublic(self._orgas_cache)
        if cle == "emploiterritorial":
            return EmploiTerritorial()
        if cle == "passerellesmef":
            return PasserellesMef()
        if cle == "fhf":
            return Fhf()
        return None

    def executer(self) -> None:
        """Slot à connecter à `QThread.started` — tourne dans le thread
        du worker une fois `moveToThread` appelé."""
        sources_actives = charger_sources_actives()
        versants_filtres = self._filtres.get("versants") or []
        toutes_offres: list[Offre] = []
        nb_pages_reference = 1
        arret_anticipe_reference = False
        nb_interrogees = 0
        nb_echecs = 0

        def _on_page(page: int, total: int) -> None:
            self.progression.emit(page, total)

        for cle, nom_affiche in SOURCES_DISPONIBLES.items():
            if not sources_actives.get(cle, True):
                continue
            versant_source = VERSANT_SOURCE.get(cle)
            if (
                versant_source is not None
                and versants_filtres
                and versant_source not in versants_filtres
            ):
                continue  # source mono-versant exclue par le filtre Versant
            source = self._construire_source(cle)
            if source is None:
                continue
            nb_interrogees += 1
            self.source_en_cours.emit(nom_affiche)
            try:
                offres, nb_pages, arret_anticipe = source.rechercher(
                    self._filtres, on_page=_on_page
                )
            except RuntimeError as erreur:
                nb_echecs += 1
                self.avertissement.emit(f"{nom_affiche} indisponible : {erreur}")
                continue

            if cle == "fhf":
                offres = filtrer_doublons_fhf(offres, toutes_offres)
            toutes_offres.extend(offres)
            if cle == "choisirleservicepublic":
                nb_pages_reference = nb_pages
                arret_anticipe_reference = arret_anticipe

        if nb_interrogees == 0:
            self.erreur.emit("Aucune source active — voir l'onglet Sources.")
            return
        if nb_echecs == nb_interrogees:
            self.erreur.emit("Toutes les sources actives sont indisponibles.")
            return

        self.resultat.emit(
            deduplique_offres(toutes_offres),
            nb_pages_reference,
            arret_anticipe_reference,
        )


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


_MOIS_FR = {
    "janvier": 1,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
}


def _reformater_date(date_str: str) -> str:
    """Reformate une date française textuelle (ex. « 26 août 2026 »,
    format réel renvoyé par le site) en format compact JJ/MM/AAAA.
    Retourne la chaîne d'origine si le format n'est pas reconnu."""
    parties = date_str.strip().split()
    if len(parties) != 3:
        return date_str
    jour, mois_nom, annee = parties
    if jour.endswith("er"):
        jour = jour[:-2]
    mois = _MOIS_FR.get(mois_nom.lower())
    if mois is None or not jour.isdigit() or not annee.isdigit():
        return date_str
    return f"{int(jour):02d}/{mois:02d}/{annee}"


def offre_vers_ligne(offre: Offre) -> tuple[str, str, str, str, str]:
    """Extrait les 5 colonnes affichées dans le tableau de résultats."""
    return (
        offre["titre"],
        offre["employeur"] or "—",
        offre["localisation"] or "—",
        _reformater_date(offre["date"]) if offre["date"] else "—",
        offre.get("source") or "Choisir le service public",
    )
