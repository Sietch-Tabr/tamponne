"""Case à cocher accessible : ajoute une coche dessinée à l'indicateur
coché — la couleur seule (QSS) n'est pas un indice suffisant."""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton, QWidget

from src.gui.theme import palette_active


class CaseACocher(QCheckBox):
    """`QCheckBox` standard (rendu QSS inchangé) + coche dessinée
    par-dessus l'indicateur quand cochée."""

    def __init__(self, texte: str = "", parent: QWidget | None = None) -> None:
        super().__init__(texte, parent)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if not self.isChecked():
            return

        option = QStyleOptionButton()
        self.initStyleOption(option)
        rect = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, option, self
        )

        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        stylo = QPen(QColor(palette_active().sur_accent))
        stylo.setWidthF(rect.width() * 0.14)
        stylo.setCapStyle(Qt.PenCapStyle.RoundCap)
        stylo.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        peintre.setPen(stylo)

        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        peintre.drawPolyline(
            [
                QPointF(x + w * 0.22, y + h * 0.52),
                QPointF(x + w * 0.42, y + h * 0.74),
                QPointF(x + w * 0.80, y + h * 0.28),
            ]
        )
