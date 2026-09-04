"""Section de panneau repliable — regroupe des filtres sous un en-tête
cliquable plutôt qu'une pile de `QGroupBox` toujours dépliées, pour garder
le panneau de filtres lisible à mesure que le nombre de filtres augmente."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class SectionRepliable(QWidget):
    """En-tête cliquable (flèche + titre) qui bascule la visibilité d'un
    corps où le code appelant ajoute ses propres widgets via `corps()`."""

    def __init__(
        self, titre: str, deplie: bool = True, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._titre = titre

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(0, 0, 0, 0)

        self._bouton_entete = QPushButton()
        self._bouton_entete.setCheckable(True)
        self._bouton_entete.setChecked(deplie)
        self._bouton_entete.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bouton_entete.setProperty("variant", "entete")
        self._bouton_entete.clicked.connect(self._basculer)
        disposition.addWidget(self._bouton_entete)

        self._widget_corps = QWidget()
        self._widget_corps.setVisible(deplie)
        self._corps = QVBoxLayout(self._widget_corps)
        disposition.addWidget(self._widget_corps)

        self._maj_libelle_entete()

    def corps(self) -> QVBoxLayout:
        """Layout où ajouter les widgets de la section."""
        return self._corps

    def _basculer(self) -> None:
        deplie = self._bouton_entete.isChecked()
        self._widget_corps.setVisible(deplie)
        self._maj_libelle_entete()

    def _maj_libelle_entete(self) -> None:
        fleche = "▾" if self._bouton_entete.isChecked() else "▸"
        self._bouton_entete.setText(f"{fleche} {self._titre}")
