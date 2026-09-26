"""Ligne de widgets qui repasse en colonne verticale si la largeur
disponible ne suffit pas à afficher tous les enfants à leur largeur
minimale — pas de wrap multi-colonnes (QFlowLayout complet), seulement
une bascule horizontal/vertical, suffisante pour 2-3 widgets."""

from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QBoxLayout, QHBoxLayout, QVBoxLayout, QWidget


class LigneResponsive(QWidget):
    """Conteneur qui aligne `enfants` en ligne tant que la largeur le
    permet, et bascule en colonne sinon (et inversement).

    Args:
        *enfants: Widgets à disposer, dans l'ordre d'affichage.
        espacement: Espace entre deux enfants, en pixels.
        parent: Widget parent Qt.
    """

    def __init__(
        self, *enfants: QWidget, espacement: int = 16, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._enfants = list(enfants)
        self._espacement = espacement
        self._horizontal = True
        # Typé QBoxLayout : bascule entre QHBoxLayout et QVBoxLayout.
        self._disposition: QBoxLayout = QHBoxLayout(self)
        self._disposition.setContentsMargins(0, 0, 0, 0)
        self._disposition.setSpacing(espacement)
        for enfant in self._enfants:
            self._disposition.addWidget(enfant)
        self._disposition.addStretch()

    def _largeur_min(self, enfant: QWidget) -> int:
        # max() avec minimumWidth() : minimumSizeHint() seul ignore un
        # setMinimumWidth() explicite posé sur l'enfant.
        return max(enfant.minimumSizeHint().width(), enfant.minimumWidth())

    def _largeur_horizontale_requise(self) -> int:
        return sum(self._largeur_min(e) for e in self._enfants) + self._espacement * (
            len(self._enfants) - 1
        )

    def minimumSizeHint(self) -> QSize:
        # Toujours le mini vertical (le plus petit), jamais celui du
        # layout horizontal courant — sinon le parent ne peut jamais nous
        # offrir une largeur assez étroite pour déclencher la bascule
        # (piège de l'œuf et la poule).
        largeur = max(self._largeur_min(e) for e in self._enfants)
        hauteur = sum(e.minimumSizeHint().height() for e in self._enfants)
        hauteur += self._espacement * (len(self._enfants) - 1)
        return QSize(largeur, hauteur)

    def sizeHint(self) -> QSize:
        if self._horizontal:
            hauteur = max(e.sizeHint().height() for e in self._enfants)
            return QSize(self._largeur_horizontale_requise(), hauteur)
        return self.minimumSizeHint()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        veut_horizontal = self.width() >= self._largeur_horizontale_requise()
        if veut_horizontal != self._horizontal:
            self._horizontal = veut_horizontal
            self._reconstruire()

    def _reconstruire(self) -> None:
        ancien = self.layout()
        if ancien is not None:
            for enfant in self._enfants:
                ancien.removeWidget(enfant)  # détache sans détruire
            QWidget().setLayout(ancien)  # jette l'ancien layout, désormais vide
        nouveau: QBoxLayout = QHBoxLayout() if self._horizontal else QVBoxLayout()
        nouveau.setContentsMargins(0, 0, 0, 0)
        nouveau.setSpacing(self._espacement)
        for enfant in self._enfants:
            nouveau.addWidget(enfant)
        if self._horizontal:
            # Sans ça, un QHBoxLayout sans concurrence étire les boutons
            # bien au-delà de leur sizeHint (vérifié) — en vertical, remplir
            # la colonne étroite est normal, pas besoin de stretch.
            nouveau.addStretch()
        self.setLayout(nouveau)
        self._disposition = nouveau
        self.updateGeometry()
