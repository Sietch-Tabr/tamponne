"""Point de statut — petit indicateur circulaire dessiné au `QPainter`,
même motif que la coche de `CaseACocher` (couleur seule non suffisante,
mais ici l'indicateur est déjà purement décoratif/attire-l'œil en plus
d'une carte textuelle explicite, pas le seul porteur d'information)."""

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from src.gui.theme import palette_active

_TAILLE = 8
_RETRAIT_DROITE = 3
_RETRAIT_HAUT = 5


class PointStatut(QWidget):
    """Point plein coloré, caché par défaut — affiché pour signaler un
    état à surveiller (ex. mise à jour disponible) sans texte."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(_TAILLE, _TAILLE)
        self.setVisible(False)

    def paintEvent(self, _event: QPaintEvent) -> None:
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        peintre.setPen(Qt.PenStyle.NoPen)
        peintre.setBrush(QColor(palette_active().succes))
        peintre.drawEllipse(QRectF(0, 0, _TAILLE, _TAILLE))

    def ancrer_sur(self, hote: QWidget) -> None:
        """Pose le point en badge dans le coin haut-droit de `hote` (ex. un
        bouton de navigation) et l'y maintient quand `hote` est redimensionné.

        Args:
            hote: Widget qui porte le point ; il en devient le parent.
        """
        self.setParent(hote)
        hote.installEventFilter(self)
        self._positionner()

    def _positionner(self) -> None:
        hote = self.parentWidget()
        if hote is not None:
            self.move(hote.width() - _RETRAIT_DROITE - _TAILLE, _RETRAIT_HAUT)
            self.raise_()

    def eventFilter(self, objet: QObject, evenement: QEvent) -> bool:
        if objet is self.parentWidget() and evenement.type() == QEvent.Type.Resize:
            self._positionner()
        return super().eventFilter(objet, evenement)
