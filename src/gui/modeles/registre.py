"""Modèle du « Registre des offres » de l'écran Recherche QML : six
colonnes de la maquette (N°, Intitulé, Employeur, Lieu, Publiée, Source),
triable et filtrable par `ProxyOffres`."""

from typing import Any

from PySide6.QtCore import QByteArray, QModelIndex, QPersistentModelIndex, Qt

from src.formatage import SOURCE_PAR_DEFAUT, cle_tri_date, reformater_date
from src.gui.modeles.offres import ROLE_OFFRE, ROLE_TRI, ModeleOffres
from src.gui.presentation import date_courte

ENTETES_REGISTRE = ["N°", "Intitulé", "Employeur", "Lieu", "Publiée", "Source"]
COLONNE_NUMERO = 0
COLONNE_INTITULE = 1
COLONNE_EMPLOYEUR = 2
COLONNE_LIEU = 3
COLONNE_PUBLIEE = 4

ROLE_NOUVELLE = Qt.ItemDataRole.UserRole + 2
"""Vrai si l'offre de la ligne est nouvelle (tampon « Nouveau »)."""

type _Index = QModelIndex | QPersistentModelIndex


class ModeleRegistre(ModeleOffres):
    """Offres de la dernière recherche, numérotées dans l'ordre des sources."""

    def columnCount(self, parent: _Index = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(ENTETES_REGISTRE)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(ENTETES_REGISTRE)
        ):
            return ENTETES_REGISTRE[section]
        return None

    def roleNames(self) -> dict[int, QByteArray]:
        roles = super().roleNames()
        roles[ROLE_NOUVELLE] = QByteArray(b"nouvelle")
        return roles

    def numero(self, ligne: int) -> str:
        """N° d'ordre de la ligne, complété de zéros à la largeur du dernier
        (2 chiffres au moins) : « 01 » à « 28 » pour 28 offres."""
        largeur = max(2, len(str(self.rowCount())))
        return f"{ligne + 1:0{largeur}d}"

    def _valeur(self, ligne: int, colonne: int) -> str:
        offre = self.offre(ligne)
        if colonne == COLONNE_NUMERO:
            return self.numero(ligne)
        if colonne == COLONNE_INTITULE:
            return offre["titre"]
        if colonne == COLONNE_EMPLOYEUR:
            return offre["employeur"] or "—"
        if colonne == COLONNE_LIEU:
            return offre["localisation"] or "—"
        if colonne == COLONNE_PUBLIEE:
            return reformater_date(offre["date"]) if offre["date"] else "—"
        return offre.get("source") or SOURCE_PAR_DEFAUT

    def data(  # noqa: PLR0911 - une valeur par rôle Qt
        self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if not index.isValid():
            return None
        ligne, colonne = index.row(), index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            valeur = self._valeur(ligne, colonne)
            return date_courte(valeur) if colonne == COLONNE_PUBLIEE else valeur
        if role == ROLE_NOUVELLE:
            return colonne == COLONNE_INTITULE and self.est_nouvelle(ligne)
        if role == ROLE_OFFRE:
            return self.offre(ligne)
        if role == ROLE_TRI:
            if colonne == COLONNE_NUMERO:
                return f"{ligne:06d}"
            valeur = self._valeur(ligne, colonne)
            return (
                cle_tri_date(valeur)
                if colonne == COLONNE_PUBLIEE
                else valeur.casefold()
            )
        return None
