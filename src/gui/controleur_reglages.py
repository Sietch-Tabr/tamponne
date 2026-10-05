"""Contrôleur de l'écran Réglages : sources consultées, préférences
d'affichage, avis de mise à jour, cache des organisations, raccourci et
sauvegarde des données."""

from datetime import date
from pathlib import Path
from typing import cast

from PySide6.QtCore import Property, QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from src import raccourci, sauvegarde
from src.cache import obtenir_organisations
from src.gui.presentation import (
    TEXTES_RACCOURCI,
    notes_en_html,
    texte_confirmation_import,
)
from src.gui.travailleurs import TacheReseau, VerificateurMiseAJour
from src.maj import version_locale
from src.parametres_affichage import (
    charger_reduire_animations,
    sauvegarder_reduire_animations,
)
from src.parametres_sources import (
    SOURCES_DISPONIBLES,
    charger_sources_actives,
    sauvegarder_sources_actives,
)
from src.types import InfoMaj, Organisations

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
        self._sources = charger_sources_actives()
        self._reduire_animations = charger_reduire_animations()
        self._info_maj: InfoMaj | None = None
        self._date_avis = ""
        self._avis_lu = False
        self._redemarrage_demande = False
        self._cache_en_cours = False
        self._message_cache = ""
        self._thread_maj: QThread | None = None
        self._verificateur: VerificateurMiseAJour | None = None
        self._thread_cache: QThread | None = None
        self._tache_cache: TacheReseau | None = None
        self._etat_raccourci = raccourci.etat()

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
        self._thread_maj.start()

    def afficher_avis(self, info: InfoMaj | None) -> None:
        """Résultat de la vérification : avis de la publication `info`,
        ou état « À jour » si `None`."""
        self._info_maj = info
        self._date_avis = date_avis().strftime("%d/%m/%Y")
        self.etat_change.emit()

    def _lire_avis(self) -> dict[str, object]:
        installee = version_locale()
        info = self._info_maj
        if info is None:
            return {
                "disponible": False,
                "objet": f"version {installee} installée, rien de plus récent.",
            }
        return {
            "disponible": True,
            "numero": f"Avis n° {info['version']}",
            "date": self._date_avis,
            "objet": f"version {info['version']} disponible (installée\u00a0: {installee}).",
            "notes": notes_en_html(info["notes"] or "Pas de notes de version."),
        }

    avis = Property(dict, _lire_avis, notify=etat_change)
    """Contenu de l'avis de mise à jour (`disponible` faux : déjà à jour)."""

    def _lire_pastille(self) -> bool:
        return self._info_maj is not None and not self._avis_lu

    pastille = Property(bool, _lire_pastille, notify=etat_change)
    """Pastille de l'onglet Réglages : avis disponible et pas encore reporté."""

    @Slot()
    def installer_maj(self) -> None:
        """Quitte avec le code dédié : le lanceur applique la mise à jour
        (marqueur déjà posé par la vérification) et relance aussitôt."""
        if self._info_maj is None:
            return
        self._redemarrage_demande = True
        self.quitter_demande.emit()

    @Slot()
    def reporter_maj(self) -> None:
        """« Au prochain lancement » : le marqueur reste posé, le lanceur
        l'appliquera au démarrage suivant ; seule la pastille s'efface."""
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
        self.organisations_rafraichies.emit(cast(Organisations, organisations))
        self.etat_change.emit()

    def _on_cache_echoue(self, _message: str) -> None:
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
    """Feuille Raccourci : `disponible`, `etat` (`src.raccourci.etat`), `texte`."""

    def verifier_raccourci(self) -> None:
        """Pose, si besoin, la question du raccourci. Appelée par `main()`
        une fois la fenêtre chargée, jamais par le constructeur (tests)."""
        question = raccourci.question_au_lancement()
        if question != "aucune":
            self.question_raccourci.emit(question)

    def _actualiser_raccourci(self) -> None:
        self._etat_raccourci = raccourci.etat()
        self.etat_change.emit()

    @Slot()
    def ajouter_raccourci(self) -> None:
        """Crée le raccourci, ou le met à jour après un déplacement."""
        try:
            raccourci.creer()
        except raccourci.ErreurRaccourci as erreur:
            self.erreur_signalee.emit(str(erreur))
        self._actualiser_raccourci()

    @Slot()
    def retirer_raccourci(self) -> None:
        """Supprime le raccourci du menu des applications."""
        try:
            raccourci.retirer()
        except raccourci.ErreurRaccourci as erreur:
            self.erreur_signalee.emit(str(erreur))
        self._actualiser_raccourci()

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

    @Slot(str)
    def ouvrir_dossier(self, chemin: str) -> None:
        """Affiche le dossier qui contient `chemin` dans le gestionnaire de fichiers."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(chemin).parent)))

    def arreter(self) -> None:
        """Attend la fin des tâches en cours : détruire un `QThread` actif
        fait planter le processus."""
        for thread in (self._thread_maj, self._thread_cache):
            if thread is not None and thread.isRunning():
                thread.quit()
                thread.wait()
