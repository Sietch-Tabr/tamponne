"""Dialogues modaux de sélection multiple avec recherche.

Remplacent les listes longues (Domaines, Localisations, Organisations —
jusqu'à ~2400 sous-organisations) auparavant empilées directement dans
la barre de gauche de l'écran Recherche, illisible à cette échelle
(défilement imbriqué). Une modale donne à chaque liste tout l'espace
disponible, avec un champ de recherche pour la réduire.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.types import Organisations


def boutons_ok_annuler() -> QDialogButtonBox:
    """QDialogButtonBox OK/Annuler avec libellés français explicites —
    les standard buttons de Qt ne sont traduits que si les fichiers de
    traduction Qt sont chargés, ce qui n'est pas le cas ici ; sans ça,
    « Cancel » reste en anglais quelle que soit la langue du système."""
    boutons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    bouton_ok = boutons.button(QDialogButtonBox.StandardButton.Ok)
    if bouton_ok is not None:
        bouton_ok.setText("OK")
    bouton_annuler = boutons.button(QDialogButtonBox.StandardButton.Cancel)
    if bouton_annuler is not None:
        bouton_annuler.setText("Annuler")
    return boutons


def question_oui_non(parent: QWidget | None, titre: str, texte: str) -> bool:
    """Boîte de confirmation Oui/Non avec libellés français explicites —
    même motif que `boutons_ok_annuler` : `QMessageBox.question` avec
    ses boutons standard (`Yes`/`No`) reste affiché en anglais sans les
    fichiers de traduction Qt, non chargés ici. Retourne True si
    l'utilisateur a cliqué sur « Oui »."""
    boite = QMessageBox(parent)
    boite.setWindowTitle(titre)
    boite.setText(texte)
    bouton_oui = boite.addButton("Oui", QMessageBox.ButtonRole.YesRole)
    boite.addButton("Non", QMessageBox.ButtonRole.NoRole)
    boite.exec()
    return boite.clickedButton() is bouton_oui


def _liste_cochable(options: list[str], deja_selectionnes: list[str]) -> QListWidget:
    liste = QListWidget()
    for option in options:
        item = QListWidgetItem(option)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(
            Qt.CheckState.Checked
            if option in deja_selectionnes
            else Qt.CheckState.Unchecked
        )
        liste.addItem(item)
    return liste


class DialogueSelectionListe(QDialog):
    """Modale de sélection multiple avec recherche, pour une liste plate
    (Domaines, Localisations)."""

    def __init__(
        self,
        titre: str,
        options: list[str],
        deja_selectionnes: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.resize(420, 520)
        disposition = QVBoxLayout(self)

        self._recherche = QLineEdit()
        self._recherche.setPlaceholderText("Rechercher...")
        self._recherche.textChanged.connect(self._filtrer)
        disposition.addWidget(self._recherche)

        self._liste = _liste_cochable(options, deja_selectionnes)
        disposition.addWidget(self._liste, 1)

        boutons = boutons_ok_annuler()
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        disposition.addWidget(boutons)

    def _filtrer(self, texte: str) -> None:
        texte = texte.strip().lower()
        for i in range(self._liste.count()):
            item = self._liste.item(i)
            if item is not None:
                item.setHidden(texte not in item.text().lower())

    def selection(self) -> list[str]:
        """Éléments cochés — à lire après `exec() == DialogCode.Accepted`."""
        resultat = []
        for i in range(self._liste.count()):
            item = self._liste.item(i)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                resultat.append(item.text())
        return resultat


class DialogueSelectionOrganisations(QDialog):
    """Modale de sélection multiple avec recherche, pour l'arbre
    ministère → sous-organisation (jusqu'à ~2400 sous-organisations)."""

    def __init__(
        self,
        orgas_cache: Organisations,
        deja_selectionnees: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Organisation(s)")
        self.resize(460, 560)
        disposition = QVBoxLayout(self)

        self._recherche = QLineEdit()
        self._recherche.setPlaceholderText("Rechercher...")
        self._recherche.textChanged.connect(self._filtrer)
        disposition.addWidget(self._recherche)

        self._arbre = QTreeWidget()
        self._arbre.setHeaderHidden(True)
        deja = set(deja_selectionnees)
        for ministere in sorted(orgas_cache):
            item_ministere = QTreeWidgetItem([ministere])
            for sous_org in sorted(orgas_cache[ministere]):
                valeur = f"{ministere} - {sous_org}"
                item_sous_org = QTreeWidgetItem([sous_org])
                item_sous_org.setFlags(
                    item_sous_org.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                item_sous_org.setCheckState(
                    0,
                    (
                        Qt.CheckState.Checked
                        if valeur in deja
                        else Qt.CheckState.Unchecked
                    ),
                )
                item_ministere.addChild(item_sous_org)
            self._arbre.addTopLevelItem(item_ministere)
        disposition.addWidget(self._arbre, 1)

        boutons = boutons_ok_annuler()
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        disposition.addWidget(boutons)

    def _filtrer(self, texte: str) -> None:
        """Cache les sous-organisations ne correspondant pas, masque un
        ministère si aucun de ses enfants n'est visible, déplie les
        ministères ayant une correspondance pour l'afficher directement."""
        texte = texte.strip().lower()
        for i in range(self._arbre.topLevelItemCount()):
            item_ministere = self._arbre.topLevelItem(i)
            if item_ministere is None:
                continue
            un_enfant_visible = False
            for j in range(item_ministere.childCount()):
                enfant = item_ministere.child(j)
                if enfant is None:
                    continue
                correspond = not texte or texte in enfant.text(0).lower()
                enfant.setHidden(not correspond)
                un_enfant_visible = un_enfant_visible or correspond
            item_ministere.setHidden(not un_enfant_visible)
            item_ministere.setExpanded(bool(texte) and un_enfant_visible)

    def selection(self) -> list[str]:
        """Sous-organisations cochées ("Ministère - Sous-org"), à lire
        après `exec() == DialogCode.Accepted`."""
        resultat = []
        for i in range(self._arbre.topLevelItemCount()):
            item_ministere = self._arbre.topLevelItem(i)
            if item_ministere is None:
                continue
            for j in range(item_ministere.childCount()):
                enfant = item_ministere.child(j)
                if enfant is not None and enfant.checkState(0) == Qt.CheckState.Checked:
                    resultat.append(f"{item_ministere.text(0)} - {enfant.text(0)}")
        return resultat


class DialogueSelectionGrades(QDialog):
    """Modale de sélection multiple avec recherche, pour l'arbre
    corps → grade (ex. Attaché → Attaché principal → Attaché hors
    classe) — même pattern que `DialogueSelectionOrganisations`, en plus
    compact (peu de corps/grades) donc déplié par défaut."""

    def __init__(
        self,
        corps_grades: dict[str, list[str]],
        deja_selectionnes: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Corps / Grade")
        self.resize(380, 420)
        disposition = QVBoxLayout(self)

        self._recherche = QLineEdit()
        self._recherche.setPlaceholderText("Rechercher...")
        self._recherche.textChanged.connect(self._filtrer)
        disposition.addWidget(self._recherche)

        self._arbre = QTreeWidget()
        self._arbre.setHeaderHidden(True)
        deja = set(deja_selectionnes)
        for corps, grades in corps_grades.items():
            item_corps = QTreeWidgetItem([corps])
            for grade in grades:
                item_grade = QTreeWidgetItem([grade])
                item_grade.setFlags(
                    item_grade.flags() | Qt.ItemFlag.ItemIsUserCheckable
                )
                item_grade.setCheckState(
                    0,
                    Qt.CheckState.Checked if grade in deja else Qt.CheckState.Unchecked,
                )
                item_corps.addChild(item_grade)
            self._arbre.addTopLevelItem(item_corps)
            # setExpanded() après addTopLevelItem() : sans effet sur un item
            # pas encore attaché à l'arbre (vérifié).
            item_corps.setExpanded(True)
        disposition.addWidget(self._arbre, 1)

        boutons = boutons_ok_annuler()
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        disposition.addWidget(boutons)

    def _filtrer(self, texte: str) -> None:
        """Même comportement que `DialogueSelectionOrganisations._filtrer` :
        cache les grades ne correspondant pas, cache un corps si aucun de
        ses grades n'est visible."""
        texte = texte.strip().lower()
        for i in range(self._arbre.topLevelItemCount()):
            item_corps = self._arbre.topLevelItem(i)
            if item_corps is None:
                continue
            un_enfant_visible = False
            for j in range(item_corps.childCount()):
                enfant = item_corps.child(j)
                if enfant is None:
                    continue
                correspond = not texte or texte in enfant.text(0).lower()
                enfant.setHidden(not correspond)
                un_enfant_visible = un_enfant_visible or correspond
            item_corps.setHidden(not un_enfant_visible)

    def selection(self) -> list[str]:
        """Grades cochés (libellés seuls, sans le nom du corps), à lire
        après `exec() == DialogCode.Accepted`."""
        resultat = []
        for i in range(self._arbre.topLevelItemCount()):
            item_corps = self._arbre.topLevelItem(i)
            if item_corps is None:
                continue
            for j in range(item_corps.childCount()):
                enfant = item_corps.child(j)
                if enfant is not None and enfant.checkState(0) == Qt.CheckState.Checked:
                    resultat.append(enfant.text(0))
        return resultat
