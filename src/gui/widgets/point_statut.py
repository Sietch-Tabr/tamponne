"""Point de statut — petit indicateur circulaire dessiné au `QPainter`,
même motif que la coche de `CaseACocher` (couleur seule non suffisante,
mais ici l'indicateur est déjà purement décoratif/attire-l'œil en plus
d'une carte textuelle explicite, pas le seul porteur d'information)."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from src.gui.theme import palette_active

_TAILLE = 8


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
