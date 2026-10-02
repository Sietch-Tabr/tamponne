"""Modèle Qt des résultats de recherche (modèle/vue) : tri par colonne et
filtrage en direct sans reconstruire le tableau."""

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
)

from src.formatage import cle_tri_date, offre_vers_ligne
from src.types import Offre

ENTETES = ["Titre", "Employeur", "Localisation", "Publiée le", "Source"]
COLONNE_DATE = 3

ROLE_OFFRE = Qt.ItemDataRole.UserRole
"""Offre brute (`Offre`) portée par chaque cellule de la ligne."""
ROLE_TRI = Qt.ItemDataRole.UserRole + 1
"""Clé de tri : date ISO pour « Publiée le », texte en minuscules sinon."""

type _Index = QModelIndex | QPersistentModelIndex


class ModeleOffres(QAbstractTableModel):
    """Offres affichées dans le tableau de résultats, une ligne par offre.

    Les nouvelles offres (références dans `nouvelles`) sont préfixées
    d'une ★ dans la colonne Titre.
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._offres: list[Offre] = []
        self._lignes: list[tuple[str, str, str, str, str]] = []
        self._nouvelles: set[str] = set()

    def definir_offres(self, offres: list[Offre], nouvelles: set[str]) -> None:
        """Remplace entièrement le contenu du modèle.

        Args:
            offres: Offres à afficher, dans l'ordre d'origine.
            nouvelles: Références des offres à marquer d'une ★.
        """
        self.beginResetModel()
        self._offres = list(offres)
        self._lignes = [offre_vers_ligne(offre) for offre in self._offres]
        self._nouvelles = set(nouvelles)
        self.endResetModel()

    def offre(self, ligne: int) -> Offre:
        """Offre de la ligne `ligne` (index du modèle source, pas du proxy)."""
        return self._offres[ligne]

    def est_nouvelle(self, ligne: int) -> bool:
        """Vrai si l'offre de la ligne `ligne` est marquée nouvelle."""
        return self._offres[ligne].get("reference") in self._nouvelles

    def rowCount(self, parent: _Index = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._offres)

    def columnCount(self, parent: _Index = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(ENTETES)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object:
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
            and 0 <= section < len(ENTETES)
        ):
            return ENTETES[section]
        return None

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        ligne, colonne = index.row(), index.column()
        valeur = self._lignes[ligne][colonne]
        if role == Qt.ItemDataRole.DisplayRole:
            if colonne == 0 and self.est_nouvelle(ligne):
                return f"★ {valeur}"
            return valeur
        if role == Qt.ItemDataRole.ToolTipRole and colonne == 0:
            # Filet de sécurité si même 2 lignes ne suffisent pas au titre.
            return valeur
        if role == ROLE_OFFRE:
            return self._offres[ligne]
        if role == ROLE_TRI:
            if colonne == COLONNE_DATE:
                return cle_tri_date(valeur)
            return valeur.casefold()
        return None


class ProxyOffres(QSortFilterProxyModel):
    """Tri (`ROLE_TRI`) et filtrage des offres : texte libre insensible à
    la casse sur toutes les colonnes, et option « nouvelles seulement »."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._nouvelles_seulement = False
        self.setSortRole(ROLE_TRI)
        self.setFilterKeyColumn(-1)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def definir_nouvelles_seulement(self, actif: bool) -> None:
        """Restreint (ou non) l'affichage aux seules offres nouvelles."""
        self.beginFilterChange()
        self._nouvelles_seulement = actif
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: _Index) -> bool:
        modele = self.sourceModel()
        if (
            self._nouvelles_seulement
            and isinstance(modele, ModeleOffres)
            and not modele.est_nouvelle(source_row)
        ):
            return False
        return super().filterAcceptsRow(source_row, source_parent)

    def offres_visibles(self) -> list[Offre]:
        """Offres affichées, dans l'ordre courant (tri et filtres compris)."""
        return [
            self.index(ligne, 0).data(ROLE_OFFRE) for ligne in range(self.rowCount())
        ]
