"""Écran Profils côté Python : fiches de recherche exposées au QML,
suppression, duplication, demande de lancement et relevé quotidien des
nouvelles."""

from datetime import date
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    QThread,
    Signal,
    Slot,
)

from src.gui.presentation import lignes_fiche, tampon_nouvelles, texte_nombre_fiches
from src.gui.travailleurs import ReleveFiches
from src.profils import charger_profils, dupliquer_profil, supprimer_profil
from src.types import Organisations, Profil

type _Index = QModelIndex | QPersistentModelIndex

_ROLES: dict[int, bytes] = {
    Qt.ItemDataRole.UserRole + 1: b"nom",
    Qt.ItemDataRole.UserRole + 2: b"intitule",
    Qt.ItemDataRole.UserRole + 3: b"lignes",
    Qt.ItemDataRole.UserRole + 4: b"nouvelles",
    Qt.ItemDataRole.UserRole + 5: b"dateNouvelles",
}


class ModeleFiches(QAbstractListModel):
    """Fiches de recherche, dans l'ordre d'enregistrement des profils."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._profils: list[tuple[str, Profil]] = []

    def definir(self, profils: dict[str, Profil]) -> None:
        """Remplace les fiches affichées ; mêmes fiches dans le même ordre :
        contenu mis à jour sur place (le focus clavier reste sur sa fiche)."""
        nouvelles = list(profils.items())
        if [nom for nom, _ in nouvelles] == [nom for nom, _ in self._profils]:
            self._profils = nouvelles
            if nouvelles:
                self.dataChanged.emit(self.index(0), self.index(len(nouvelles) - 1))
            return
        self.beginResetModel()
        self._profils = nouvelles
        self.endResetModel()

    def rowCount(self, parent: _Index = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._profils)

    def roleNames(self) -> dict[int, QByteArray]:
        return {role: QByteArray(nom) for role, nom in _ROLES.items()}

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role not in _ROLES:
            return None
        nom, profil = self._profils[index.row()]
        texte, date_comptage = tampon_nouvelles(profil)
        return {
            b"nom": nom,
            b"intitule": profil.get("label") or nom,
            b"lignes": lignes_fiche(profil),
            b"nouvelles": texte,
            b"dateNouvelles": date_comptage,
        }[_ROLES[role]]


class ControleurProfils(QObject):
    """Actions et états de l'écran Profils (objet `pont.profils` côté QML)."""

    etat_change = Signal()
    lancement_demande = Signal(str)
    """Nom du profil à lancer dans l'écran Recherche."""
    modification_demandee = Signal(str)
    """Nom du profil à ouvrir en édition dans l'écran Recherche."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._modele = ModeleFiches(self)
        self._nombre = 0
        self._thread_releve: QThread | None = None
        self._releve: ReleveFiches | None = None
        self.rafraichir()

    def _lire_modele(self) -> QObject:
        return self._modele

    def _lire_nombre(self) -> int:
        return self._nombre

    def _lire_texte_nombre(self) -> str:
        return texte_nombre_fiches(self._nombre)

    modele = Property(QObject, _lire_modele, constant=True)
    nombre = Property(int, _lire_nombre, notify=etat_change)
    texte_nombre = Property(str, _lire_texte_nombre, notify=etat_change)

    @Slot()
    def rafraichir(self) -> None:
        """Recharge les fiches depuis `data/profils.json`."""
        profils = charger_profils()
        self._modele.definir(profils)
        self._nombre = len(profils)
        self.etat_change.emit()

    @Slot(str, result=str)
    def intitule(self, nom: str) -> str:
        """Intitulé affiché d'une fiche (son nom si elle n'en a pas)."""
        profil = charger_profils().get(nom)
        return "" if profil is None else profil.get("label") or nom

    @Slot(str)
    def lancer(self, nom: str) -> None:
        """Demande le lancement de la recherche de la fiche."""
        if nom in charger_profils():
            self.lancement_demande.emit(nom)

    @Slot(str)
    def modifier(self, nom: str) -> None:
        """Demande l'ouverture de la fiche en édition, sans lancer."""
        if nom in charger_profils():
            self.modification_demandee.emit(nom)

    @Slot(str, str, str, result=str)
    def dupliquer(self, nom: str, nouveau_nom: str, intitule: str) -> str:
        """Copie la fiche sous un nouveau nom et un nouvel intitulé (celui
        d'origine s'il est laissé vide).

        Returns:
            Message d'erreur à afficher, chaîne vide si la copie a réussi.
        """
        nouveau_nom = nouveau_nom.strip()
        profils = charger_profils()
        if not nouveau_nom:
            return "Donner un nom à la nouvelle fiche."
        if nouveau_nom in profils:
            return "Une fiche porte déjà ce nom."
        if nom not in profils:
            return "La fiche d'origine n'existe plus."
        dupliquer_profil(nom, nouveau_nom, intitule.strip() or None)
        self.rafraichir()
        return ""

    @Slot(str)
    def supprimer(self, nom: str) -> None:
        """Supprime la fiche."""
        if nom in charger_profils():
            supprimer_profil(nom)
        self.rafraichir()

    # --- Relevé quotidien ---

    def lancer_releve(self, orgas_cache: Organisations, aujourd_hui: date) -> None:
        """Compte en arrière-plan les nouvelles des fiches pas encore
        relevées aujourd'hui. Appelé par `main()`, jamais par le
        constructeur : les tests construisent l'interface sans réseau."""
        if self._thread_releve is not None:
            return
        thread = QThread()
        releve = ReleveFiches(orgas_cache, aujourd_hui)
        releve.moveToThread(thread)
        thread.started.connect(releve.executer)
        releve.fiche_relevee.connect(self._on_fiche_relevee)
        releve.termine.connect(thread.quit)
        self._thread_releve = thread
        self._releve = releve
        thread.start()

    def _on_fiche_relevee(self, _nom: str) -> None:
        self.rafraichir()

    def arreter(self) -> None:
        """Interrompt le relevé et attend la fin du thread : détruire un
        `QThread` encore actif fait planter le processus."""
        if self._releve is not None:
            self._releve.arreter()
        if self._thread_releve is not None and self._thread_releve.isRunning():
            self._thread_releve.quit()
            self._thread_releve.wait()
