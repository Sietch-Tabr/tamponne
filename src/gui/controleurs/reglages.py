"""Contrôleur de l'écran Réglages : sources consultées, préférences
d'affichage, avis de mise à jour, cache des organisations, raccourci,
sauvegarde des données et exports de recherche."""

import html
import logging
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import cast

from PySide6.QtCore import Property, QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from src.donnees import sauvegarde
from src.donnees.cache import date_cache_organisations, obtenir_organisations
from src.donnees.parametres_affichage import (
    charger_reduire_animations,
    sauvegarder_reduire_animations,
)
from src.donnees.parametres_sources import (
    SOURCES_DISPONIBLES,
    charger_sources_actives,
    sauvegarder_sources_actives,
)
from src.gui.presentation import (
    TEXTES_RACCOURCI,
    notes_en_html,
    texte_avis_sans_publication,
    texte_confirmation_exports,
    texte_confirmation_import,
    texte_date_cache,
    texte_exports,
)
from src.gui.travailleurs import TacheReseau, VerificateurMiseAJour
from src.maj import ecrire_maj_disponible, lire_echec, version_locale
from src.recherche import export
from src.systeme import raccourci
from src.types import InfoMaj, Organisations

journal = logging.getLogger(__name__)

MESSAGE_EXPORTS_NON_SUPPRIMES = (
    "Certains exports n'ont pas pu être supprimés. Fermez-les s'ils sont "
    "ouverts, puis réessayez.\nDétail\u00a0: {erreur}"
)

MESSAGE_CACHE_INDISPONIBLE = (
    "Le site choisirleservicepublic.gouv.fr est inaccessible. Réessayer plus tard."
)


def date_avis() -> date:
    """Date portée sur l'avis de mise à jour, celle de la vérification
    (remplaçable pour les captures de comparaison avec la maquette)."""
    return date.today()


class ControleurReglages(QObject):
    """Réglages persistés dans `data/` et tâches d'arrière-plan associées
    (vérification de version, rafraîchissement du cache)."""

    etat_change = Signal()
    organisations_rafraichies = Signal(dict)
    """Nouveau cache des organisations, à transmettre à la recherche."""
    quitter_demande = Signal()
    """Quitter pour redémarrer (« Installer et redémarrer », import de
    données) : `src.lanceur` relance l'application."""
    question_raccourci = Signal(str)
    """Question à poser au démarrage : `premier_lancement` ou `deplace`."""
    erreur_signalee = Signal(str)
    """Message d'une opération impossible, affiché tel quel."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.erreur_signalee.connect(self._journaliser_erreur)
        self._sources = charger_sources_actives()
        self._reduire_animations = charger_reduire_animations()
        self._info_maj: InfoMaj | None = None
        self._verification_en_cours = False
        self._erreur_verification = ""
        self._date_avis = ""
        self._avis_lu = False
        self._redemarrage_demande = False
        self._cache_en_cours = False
        self._message_cache = ""
        self._date_cache = texte_date_cache(date_cache_organisations())
        self._thread_maj: QThread | None = None
        self._verificateur: VerificateurMiseAJour | None = None
        self._thread_cache: QThread | None = None
        self._tache_cache: TacheReseau | None = None
        self._etat_exports = export.etat_exports()
        self._etat_raccourci = raccourci.etat()
        self._raccourci_en_cours = False
        self._thread_raccourci: QThread | None = None
        self._tache_raccourci: TacheReseau | None = None

    # --- Sources ---

    def _lire_sources(self) -> list[dict[str, str]]:
        return [
            {"cle": cle, "libelle": libelle}
            for cle, libelle in SOURCES_DISPONIBLES.items()
        ]

    # Liste constante : réémise, elle ferait recréer les cases par le
    # Repeater et la case cliquée perdrait le focus clavier.
    sources = Property(list, _lire_sources, constant=True)
    """Sources dans l'ordre de `SOURCES_DISPONIBLES` : clé et libellé."""

    def _lire_sources_actives(self) -> dict[str, bool]:
        return dict(self._sources)

    sources_actives = Property(dict, _lire_sources_actives, notify=etat_change)
    """État coché de chaque source, par clé."""

    @Slot(str)
    def basculer_source(self, cle: str) -> None:
        """Coche ou décoche une source et l'enregistre aussitôt."""
        if cle not in self._sources:
            return
        self._sources[cle] = not self._sources[cle]
        sauvegarder_sources_actives(self._sources)
        self.etat_change.emit()

    # --- Affichage ---

    def _lire_reduire_animations(self) -> bool:
        return self._reduire_animations

    reduire_animations = Property(bool, _lire_reduire_animations, notify=etat_change)
    """Préférence « Réduire les animations » enregistrée."""

    @Slot(bool)
    def definir_reduire_animations(self, actif: bool) -> None:
        """Enregistre la préférence « Réduire les animations »."""
        self._reduire_animations = actif
        sauvegarder_reduire_animations(actif)
        self.etat_change.emit()

    # --- Mise à jour ---

    def verifier_mise_a_jour(self) -> None:
        """Interroge Codeberg une fois, en arrière-plan. Appelée par
        `main()` une fois la fenêtre chargée, jamais par le constructeur :
        les tests construisent l'interface sans boucle d'événements."""
        if self._thread_maj is not None:
            return
        self._thread_maj = QThread()
        self._verificateur = VerificateurMiseAJour()
        self._verificateur.moveToThread(self._thread_maj)
        self._thread_maj.started.connect(self._verificateur.executer)
        self._verificateur.resultat.connect(self.afficher_avis)
        self._verificateur.resultat.connect(self._thread_maj.quit)
        self._verificateur.echec.connect(self.afficher_echec_verification)
        self._verificateur.echec.connect(self._thread_maj.quit)
        self._verification_en_cours = True
        self.etat_change.emit()
        self._thread_maj.start()

    def afficher_avis(self, info: InfoMaj | None) -> None:
        """Résultat de la vérification : avis de la publication `info`,
        ou état « À jour » si `None`."""
        self._info_maj = info
        self._verification_en_cours = False
        self._erreur_verification = ""
        self._date_avis = date_avis().strftime("%d/%m/%Y")
        self.etat_change.emit()

    def afficher_echec_verification(self, detail: str) -> None:
        """Codeberg injoignable : l'avis le dit au lieu d'annoncer « rien
        de plus récent », avec le détail technique `detail`."""
        self._verification_en_cours = False
        self._erreur_verification = detail
        self.etat_change.emit()

    def _lire_avis(self) -> dict[str, object]:
        installee = version_locale()
        info = self._info_maj
        if info is None:
            objet = texte_avis_sans_publication(
                installee, self._verification_en_cours, self._erreur_verification
            )
            return {
                "disponible": False,
                "a_jour": not (
                    self._verification_en_cours or self._erreur_verification
                ),
                # Affiché en texte riche : un détail comme « <urlopen error …> »
                # serait pris pour une balise.
                "objet": html.escape(objet, quote=False),
            }
        objet = f"version {info['version']} disponible (installée\u00a0: {installee})."
        echec = lire_echec()
        if echec is not None and echec["version"] == info["version"]:
            objet = (
                f"version {info['version']} non installée au dernier essai\u00a0: "
                f"{echec['motif']} (installée\u00a0: {installee})."
            )
        return {
            "disponible": True,
            "numero": f"Avis n° {info['version']}",
            "date": self._date_avis,
            "objet": html.escape(objet, quote=False),
            "notes": notes_en_html(info["notes"] or "Pas de notes de version."),
        }

    avis = Property(dict, _lire_avis, notify=etat_change)
    """Contenu de l'avis de mise à jour : `disponible` faux sans publication
    proposée, `a_jour` vrai seulement si Codeberg a confirmé (tampon
    « À jour ») ; `objet` échappé pour le texte riche."""

    def _lire_pastille(self) -> bool:
        return self._info_maj is not None and not self._avis_lu

    pastille = Property(bool, _lire_pastille, notify=etat_change)
    """Pastille de l'onglet Réglages : avis disponible et pas encore reporté."""

    @Slot()
    def installer_maj(self) -> None:
        """Quitte avec le code dédié : le lanceur applique la mise à jour et
        relance aussitôt. Le marqueur est reposé ici : la vérification ne le
        pose pas pour une version déjà annulée (nouvel essai à la demande)."""
        if self._info_maj is None:
            return
        ecrire_maj_disponible(self._info_maj)
        self._redemarrage_demande = True
        self.quitter_demande.emit()

    @Slot()
    def reporter_maj(self) -> None:
        """« Au prochain lancement » : le lanceur appliquera la mise à jour au
        démarrage suivant (marqueur reposé, même pour une version annulée) ;
        la pastille s'efface."""
        if self._info_maj is not None:
            ecrire_maj_disponible(self._info_maj)
        self._avis_lu = True
        self.etat_change.emit()

    @property
    def redemarrage_demande(self) -> bool:
        """Vrai si l'utilisateur a demandé un redémarrage (mise à jour ou
        import de données)."""
        return self._redemarrage_demande

    # --- Cache des organisations ---

    def _lire_cache_en_cours(self) -> bool:
        return self._cache_en_cours

    cache_en_cours = Property(bool, _lire_cache_en_cours, notify=etat_change)
    """Vrai pendant le rafraîchissement du cache des organisations."""

    def _lire_message_cache(self) -> str:
        return self._message_cache

    message_cache = Property(str, _lire_message_cache, notify=etat_change)
    """Erreur du dernier rafraîchissement du cache, vide sinon."""

    def _lire_date_cache(self) -> str:
        return self._date_cache

    date_cache = Property(str, _lire_date_cache, notify=etat_change)
    """Date de mise en cache des organisations (`texte_date_cache`), vide
    sans cache."""

    @Slot()
    def rafraichir_cache(self) -> None:
        """Recharge les organisations depuis le site, sans figer l'interface."""
        if self._cache_en_cours:
            return
        self._cache_en_cours = True
        self._message_cache = ""
        thread = QThread()
        tache = TacheReseau(lambda: obtenir_organisations(forcer=True))
        tache.moveToThread(thread)
        thread.started.connect(tache.executer)
        tache.termine.connect(self._on_cache_rafraichi)
        tache.echec.connect(self._on_cache_echoue)
        tache.termine.connect(thread.quit)
        tache.echec.connect(thread.quit)
        self._thread_cache = thread
        self._tache_cache = tache
        thread.start()
        self.etat_change.emit()

    def _on_cache_rafraichi(self, organisations: object) -> None:
        self._cache_en_cours = False
        self._date_cache = texte_date_cache(date_cache_organisations())
        self.organisations_rafraichies.emit(cast(Organisations, organisations))
        self.etat_change.emit()

    @staticmethod
    def _journaliser_erreur(message: str) -> None:
        journal.error("%s", message)

    def _on_cache_echoue(self, message: str) -> None:
        journal.warning("Liste des organisations non rafraîchie\u00a0: %s", message)
        self._cache_en_cours = False
        self._message_cache = MESSAGE_CACHE_INDISPONIBLE
        self.etat_change.emit()

    # --- Raccourci ---

    def _lire_raccourci(self) -> dict[str, object]:
        etat = self._etat_raccourci
        return {
            "disponible": etat != "indisponible",
            "etat": etat,
            "texte": TEXTES_RACCOURCI.get(etat, ""),
        }

    raccourci = Property(dict, _lire_raccourci, notify=etat_change)
    """Feuille Raccourci : `disponible`, `etat` (`src.systeme.raccourci.etat`), `texte`."""

    def verifier_raccourci(self) -> None:
        """Pose, si besoin, la question du raccourci. Appelée par `main()`
        une fois la fenêtre chargée, jamais par le constructeur (tests)."""
        question = raccourci.question_au_lancement()
        if question != "aucune":
            self.question_raccourci.emit(question)

    def _actualiser_raccourci(self) -> None:
        self._etat_raccourci = raccourci.etat()
        self.etat_change.emit()

    def _lire_raccourci_en_cours(self) -> bool:
        return self._raccourci_en_cours

    raccourci_en_cours = Property(bool, _lire_raccourci_en_cours, notify=etat_change)
    """Vrai pendant la création ou le retrait du raccourci."""

    def _lancer_operation_raccourci(self, operation: Callable[[], None]) -> None:
        """Exécute `operation` hors du fil de l'interface : sous Windows,
        PowerShell met plusieurs secondes à démarrer."""
        if self._raccourci_en_cours:
            return
        self._raccourci_en_cours = True
        thread = QThread()
        tache = TacheReseau(operation)
        tache.moveToThread(thread)
        thread.started.connect(tache.executer)
        tache.termine.connect(self._on_raccourci_termine)
        tache.echec.connect(self._on_raccourci_echoue)
        tache.termine.connect(thread.quit)
        tache.echec.connect(thread.quit)
        self._thread_raccourci = thread
        self._tache_raccourci = tache
        thread.start()
        self.etat_change.emit()

    def _on_raccourci_termine(self, _resultat: object) -> None:
        self._raccourci_en_cours = False
        self._actualiser_raccourci()

    def _on_raccourci_echoue(self, message: str) -> None:
        self._raccourci_en_cours = False
        self.erreur_signalee.emit(message)
        self._actualiser_raccourci()

    @Slot()
    def ajouter_raccourci(self) -> None:
        """Crée le raccourci, ou le met à jour après un déplacement."""
        self._lancer_operation_raccourci(raccourci.creer)

    @Slot()
    def retirer_raccourci(self) -> None:
        """Supprime le raccourci du menu des applications."""
        self._lancer_operation_raccourci(raccourci.retirer)

    @Slot()
    def refuser_raccourci(self) -> None:
        """« Non » à la question du premier lancement : ne plus la poser.
        Après un déplacement, « Non » ne note rien : la question revient."""
        if raccourci.question_au_lancement() == "premier_lancement":
            raccourci.refuser_premiere_question()

    # --- Sauvegarde ---

    def _lire_nom_export(self) -> str:
        return sauvegarde.nom_export()

    nom_export = Property(str, _lire_nom_export, constant=True)
    """Nom de fichier proposé à l'export des données."""

    @Slot(str, result=str)
    def exporter_donnees(self, url: str) -> str:
        """Exporte les données vers le fichier choisi (`url` du sélecteur).

        Returns:
            Chemin du fichier écrit, vide en cas d'échec (`erreur_signalee`).
        """
        destination = Path(QUrl(url).toLocalFile())
        try:
            sauvegarde.exporter_donnees(destination)
        except sauvegarde.ErreurSauvegarde as erreur:
            self.erreur_signalee.emit(str(erreur))
            return ""
        return str(destination)

    @Slot(str, result=str)
    def confirmation_import(self, url: str) -> str:
        """Question posée avant d'importer le fichier choisi."""
        return texte_confirmation_import(Path(QUrl(url).toLocalFile()).name)

    @Slot(str)
    def importer_donnees(self, url: str) -> None:
        """Remplace les données par la sauvegarde choisie puis redémarre :
        les écrans relisent tout au lancement."""
        try:
            sauvegarde.importer_donnees(Path(QUrl(url).toLocalFile()))
        except sauvegarde.ErreurSauvegarde as erreur:
            self.erreur_signalee.emit(str(erreur))
            return
        self._redemarrage_demande = True
        self.quitter_demande.emit()

    # --- Exports de recherche ---

    def _lire_exports(self) -> dict[str, object]:
        nombre, octets = self._etat_exports
        return {"nombre": nombre, "texte": texte_exports(nombre, octets)}

    exports = Property(dict, _lire_exports, notify=etat_change)
    """Exports HTML de la recherche : `nombre` et `texte` (`texte_exports`)."""

    @Slot()
    def actualiser_exports(self) -> None:
        """Relit le dossier des exports (un export a pu être fait depuis
        l'écran Recherche)."""
        self._etat_exports = export.etat_exports()
        self.etat_change.emit()

    @Slot(result=str)
    def confirmation_suppression_exports(self) -> str:
        """Question posée avant de supprimer les exports."""
        return texte_confirmation_exports(self._etat_exports[0])

    @Slot()
    def supprimer_exports(self) -> None:
        """Supprime les exports HTML ; un échec est signalé (`erreur_signalee`)."""
        try:
            export.supprimer_exports()
        except OSError as erreur:
            self.erreur_signalee.emit(
                MESSAGE_EXPORTS_NON_SUPPRIMES.format(erreur=erreur)
            )
        self.actualiser_exports()

    @Slot()
    def ouvrir_dossier_exports(self) -> None:
        """Affiche le dossier des exports dans le gestionnaire de fichiers."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(export.DOSSIER_EXPORTS)))

    @Slot(str)
    def ouvrir_dossier(self, chemin: str) -> None:
        """Affiche le dossier qui contient `chemin` dans le gestionnaire de fichiers."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(chemin).parent)))

    def arreter(self) -> None:
        """Attend la fin des tâches en cours : détruire un `QThread` actif
        fait planter le processus."""
        for thread in (self._thread_maj, self._thread_cache, self._thread_raccourci):
            if thread is not None and thread.isRunning():
                thread.quit()
                thread.wait()
