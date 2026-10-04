"""Écran Suivi côté Python : dossiers de candidature exposés au QML,
vérification des offres en arrière-plan et actions sur un dossier."""

from datetime import date
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QThread,
    QUrl,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices

from src.candidatures import (
    TYPES_EVENEMENT,
    ajouter_evenement,
    charger_candidatures,
    chemin_archive_pdf,
    marquer_disponibilite,
    source_candidature,
    supprimer_candidature,
)
from src.gui.presentation import ContenuDossier, contenu_detail, contenu_dossier
from src.gui.travailleurs import VerificateurDisponibilite

type _Index = QModelIndex | QPersistentModelIndex

_ROLES: dict[int, bytes] = {
    Qt.ItemDataRole.UserRole + 1: b"reference",
    Qt.ItemDataRole.UserRole + 2: b"titre",
    Qt.ItemDataRole.UserRole + 3: b"employeurLieu",
    Qt.ItemDataRole.UserRole + 4: b"statut",
    Qt.ItemDataRole.UserRole + 5: b"tampons",
    Qt.ItemDataRole.UserRole + 6: b"joursSansNouvelles",
    Qt.ItemDataRole.UserRole + 7: b"disponible",
}

LIBELLE_VERIFIER = "Vérifier les offres"


def date_du_jour() -> date:
    """Date de référence des jours sans nouvelles (remplaçable pour les
    captures de comparaison avec la maquette, datée du 04/10/2026)."""
    return date.today()


def nombre_dossiers(total: int) -> str:
    """Texte du compteur sous le titre « Dossiers en cours »."""
    return f"{total} candidature{'s' if total > 1 else ''} suivie{'s' if total > 1 else ''}"


class ModeleDossiers(QAbstractListModel):
    """Dossiers de suivi, le plus récemment suivi en premier."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._dossiers: list[ContenuDossier] = []

    def definir(self, dossiers: list[ContenuDossier]) -> None:
        """Remplace tous les dossiers affichés."""
        self.beginResetModel()
        self._dossiers = dossiers
        self.endResetModel()

    def rowCount(self, parent: _Index = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._dossiers)

    def roleNames(self) -> dict[int, QByteArray]:
        return {role: QByteArray(nom) for role, nom in _ROLES.items()}

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role not in _ROLES:
            return None
        dossier = self._dossiers[index.row()]
        nom = _ROLES[role]
        if nom == b"tampons":
            return [
                {
                    "libelle": t.libelle,
                    "date": t.date,
                    "courant": t.courant,
                    "refus": t.refus,
                }
                for t in dossier.tampons
            ]
        if nom == b"joursSansNouvelles":
            return (
                -1
                if dossier.jours_sans_nouvelles is None
                else dossier.jours_sans_nouvelles
            )
        return {
            b"reference": dossier.reference,
            b"titre": dossier.titre,
            b"employeurLieu": dossier.employeur_lieu,
            b"statut": dossier.statut,
            b"disponible": dossier.disponible,
        }[nom]


class ControleurSuivi(QObject):
    """Actions et états de l'écran Suivi (objet `pont.suivi` côté QML)."""

    etat_change = Signal()
    """Nombre de dossiers ou état de la vérification modifié."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._modele = ModeleDossiers(self)
        self._nombre = 0
        self._texte_verification = LIBELLE_VERIFIER
        self._thread: QThread | None = None
        self._verificateur: VerificateurDisponibilite | None = None
        self.rafraichir()

    def _lire_modele(self) -> QObject:
        return self._modele

    def _lire_nombre(self) -> int:
        return self._nombre

    def _lire_texte_nombre(self) -> str:
        return nombre_dossiers(self._nombre)

    def _lire_verification_en_cours(self) -> bool:
        return self._thread is not None

    def _lire_texte_verification(self) -> str:
        return self._texte_verification

    def _lire_types_evenement(self) -> list[dict[str, str]]:
        return [
            {"cle": cle, "libelle": libelle} for cle, libelle in TYPES_EVENEMENT.items()
        ]

    modele = Property(QObject, _lire_modele, constant=True)
    nombre = Property(int, _lire_nombre, notify=etat_change)
    texte_nombre = Property(str, _lire_texte_nombre, notify=etat_change)
    verification_en_cours = Property(
        bool, _lire_verification_en_cours, notify=etat_change
    )
    texte_verification = Property(str, _lire_texte_verification, notify=etat_change)
    types_evenement = Property(list, _lire_types_evenement, constant=True)
    """Types d'événement proposés dans « Ajouter un événement »."""

    @Slot()
    def rafraichir(self) -> None:
        """Recharge les dossiers depuis `data/candidatures.json`."""
        candidatures = charger_candidatures()
        aujourd_hui = date_du_jour()
        dossiers = [
            contenu_dossier(
                reference,
                candidature,
                aujourd_hui,
                chemin_archive_pdf(reference).exists(),
            )
            for reference, candidature in reversed(list(candidatures.items()))
        ]
        self._modele.definir(dossiers)
        self._nombre = len(dossiers)
        self.etat_change.emit()

    @Slot()
    def verifier_offres(self) -> None:
        """Vérifie en arrière-plan si les offres suivies sont toujours en
        ligne ; sans effet si une vérification tourne déjà ou s'il n'y a
        rien à vérifier."""
        if self._thread is not None:
            return
        candidatures = charger_candidatures()
        if not candidatures:
            return
        self._thread = QThread()
        self._verificateur = VerificateurDisponibilite(candidatures)
        self._verificateur.moveToThread(self._thread)
        self._thread.started.connect(self._verificateur.executer)
        self._verificateur.progression.connect(self._on_progression)
        self._verificateur.resultat.connect(self._on_resultat)
        self._verificateur.resultat.connect(self._thread.quit)
        self._thread.finished.connect(self._on_termine)
        self._texte_verification = "Vérification…"
        self.etat_change.emit()
        self._thread.start()

    def _on_progression(self, rang: int, total: int) -> None:
        self._texte_verification = f"Vérification… {rang}/{total}"
        self.etat_change.emit()

    def _on_resultat(self, resultats: dict[str, bool | None]) -> None:
        for reference, disponible in resultats.items():
            if disponible is not None:
                marquer_disponibilite(reference, disponible)
        self.rafraichir()

    def _on_termine(self) -> None:
        self._thread = None
        self._verificateur = None
        self._texte_verification = LIBELLE_VERIFIER
        self.etat_change.emit()

    def arreter(self) -> None:
        """Attend la fin d'une vérification en cours : détruire un
        `QThread` encore actif fait planter le processus."""
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

    @Slot(str)
    def voir_offre(self, reference: str) -> None:
        """Ouvre l'offre en ligne dans le navigateur (liens https uniquement)."""
        candidature = charger_candidatures().get(reference)
        if candidature and candidature["offre_url"].startswith("https://"):
            QDesktopServices.openUrl(QUrl(candidature["offre_url"]))

    @Slot(str, result="QVariantMap")
    def detail(self, reference: str) -> dict[str, Any]:
        """Contenu de la fiche de poste archivée au moment du suivi (aucun
        appel réseau) ; dictionnaire vide si le dossier n'existe plus."""
        candidature = charger_candidatures().get(reference)
        if candidature is None:
            return {}
        contenu = contenu_detail(
            reference,
            candidature["offre_titre"],
            [
                candidature["offre_employeur"],
                candidature["offre_localisation"],
                source_candidature(candidature),
            ],
            candidature["detail"],
            candidature["offre_url"],
            chemin_archive_pdf(reference).exists(),
        )
        return {
            "reference": contenu.reference,
            "titre": contenu.titre,
            "sousTitre": contenu.sous_titre,
            "description": contenu.description,
            "informations": [
                {
                    "libelle": libelle,
                    "valeur": valeur,
                    "date": libelle in ("Publiée le", "Date limite"),
                }
                for libelle, valeur in contenu.informations
            ],
            "rubriques": [
                {"titre": titre, "texte": texte} for titre, texte in contenu.rubriques
            ],
            "peutPostuler": bool(contenu.lien_postuler),
            "enLigne": bool(contenu.url),
            "archivePresente": contenu.archive_presente,
        }

    @Slot(str)
    def postuler(self, reference: str) -> None:
        """Ouvre le portail de candidature de l'offre (liens https uniquement)."""
        candidature = charger_candidatures().get(reference)
        if candidature is None:
            return
        lien = candidature["detail"].get("lien_postuler") or ""
        if lien.startswith("https://"):
            QDesktopServices.openUrl(QUrl(lien))

    @Slot(str)
    def voir_archive(self, reference: str) -> None:
        """Ouvre la copie PDF archivée de la fiche, si elle existe."""
        chemin = chemin_archive_pdf(reference)
        if chemin.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(chemin)))

    @Slot(str, str, str, str)
    def ajouter_evenement(
        self, reference: str, type_evenement: str, date_iso: str, note: str
    ) -> None:
        """Tamponne un nouvel événement dans l'historique du dossier."""
        if type_evenement not in TYPES_EVENEMENT:
            return
        if reference not in charger_candidatures():
            return  # dossier supprimé entre-temps
        ajouter_evenement(reference, type_evenement, date_iso, note.strip())
        self.rafraichir()

    @Slot(str)
    def supprimer(self, reference: str) -> None:
        """Arrête le suivi (historique et archive PDF supprimés)."""
        supprimer_candidature(reference)
        self.rafraichir()
