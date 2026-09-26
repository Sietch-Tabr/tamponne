"""Rendu du Suivi de candidature en modèle/vue : une ligne par candidature,
peinte par un délégué plutôt qu'un widget complet par ligne.

La logique d'affichage (titre, badges, résumé, historique) est isolée
dans `contenu_ligne`, fonction pure testable sans rendu. Le délégué ne
fait que la dessiner et convertir les clics en `action_demandee`.
"""

from dataclasses import dataclass
from datetime import date as date_cls

from PySide6.QtCore import (
    QAbstractItemModel,
    QAbstractListModel,
    QEvent,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QPoint,
    QRect,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QHelpEvent,
    QMouseEvent,
    QPainter,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolTip,
)

from src.candidatures import TYPES_EVENEMENT, relance_suggeree, statut_libelle
from src.gui.theme import palette_active
from src.types import Candidature

ACTIONS: list[tuple[str, str]] = [
    ("voir", "Voir l'offre"),
    ("detail", "Voir le détail"),
    ("evenement", "Ajouter un événement"),
    ("supprimer", "Supprimer"),
]
"""(clé d'action, libellé du bouton), dans l'ordre d'affichage."""

INFOBULLE_OFFRE_DEPUBLIEE = (
    "Cette offre n'est plus en ligne — le lien ne mènera plus à rien "
    "d'utile, l'historique reste ci-dessus."
)

ROLE_CONTENU = Qt.ItemDataRole.UserRole
"""`ContenuLigneCandidature` de la ligne."""
ROLE_REFERENCE = Qt.ItemDataRole.UserRole + 1
"""Référence (clé de `candidatures.json`) de la ligne."""

_MARGE_H = 14
_MARGE_V = 12
_ESPACE_COLONNES = 20
_ESPACE_LIGNES = 6
_ESPACE_BOUTONS = 6
_LARGEUR_HISTORIQUE_MIN = 280
_LARGEUR_HISTORIQUE_MAX = 380
_PADDING_BOUTON_H = 10
_PADDING_BOUTON_V = 3
_PADDING_BADGE_H = 9
_RAYON_BOUTON = 5

type _Index = QModelIndex | QPersistentModelIndex


def reformater_date_iso(date_iso: str) -> str:
    """Reformate une date ISO (`YYYY-MM-DD`, format de `EvenementCandidature.date`)
    en JJ/MM/AAAA. Retourne la chaîne d'origine si le format n'est pas
    reconnu (ne devrait pas arriver, écrit uniquement par `src.candidatures`)."""
    try:
        return date_cls.fromisoformat(date_iso).strftime("%d/%m/%Y")
    except ValueError:
        return date_iso


@dataclass(frozen=True)
class ContenuLigneCandidature:
    """Textes affichés pour une candidature suivie."""

    reference: str
    titre: str
    badges: tuple[tuple[str, str], ...]
    """(texte, variante) — variante « neutre » ou « attention »."""
    resume: str
    historique: tuple[str, ...]
    """Événements déjà formatés, dans l'ordre chronologique."""
    disponible: bool

    def textes(self) -> list[str]:
        """Tous les textes affichés, dans l'ordre de lecture."""
        return [
            self.titre,
            *(texte for texte, _ in self.badges),
            self.resume,
            "Historique",
            *self.historique,
        ]


def contenu_ligne(reference: str, candidature: Candidature) -> ContenuLigneCandidature:
    """Construit le contenu affiché pour `candidature`.

    Args:
        reference: Référence de l'offre suivie.
        candidature: Candidature telle que stockée par `src.candidatures`.

    Returns:
        Textes de la ligne : badges « Offre dépubliée » / « Relance
        suggérée » si pertinents, historique trié par date.
    """
    disponible = candidature.get("disponible", True)
    badges: list[tuple[str, str]] = []
    if not disponible:
        badges.append(("Offre dépubliée", "neutre"))
    if relance_suggeree(candidature):
        badges.append(("Relance suggérée", "attention"))

    resume = (
        f"{candidature['offre_employeur']} · suivi depuis le "
        f"{reformater_date_iso(candidature['date_candidature'])} · "
        f"{statut_libelle(candidature)}"
    )

    lignes_historique = []
    for evenement in sorted(
        candidature.get("historique") or [], key=lambda e: e["date"]
    ):
        libelle = TYPES_EVENEMENT.get(evenement["type"], evenement["type"])
        texte = f"{reformater_date_iso(evenement['date'])} — {libelle}"
        if evenement.get("note"):
            texte += f" ({evenement['note']})"
        lignes_historique.append(texte)

    return ContenuLigneCandidature(
        reference=reference,
        titre=candidature["offre_titre"],
        badges=tuple(badges),
        resume=resume,
        historique=tuple(lignes_historique),
        disponible=disponible,
    )


class ModeleCandidatures(QAbstractListModel):
    """Candidatures suivies, la plus récemment suivie en premier."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._contenus: list[ContenuLigneCandidature] = []

    def definir_candidatures(self, candidatures: dict[str, Candidature]) -> None:
        """Remplace le contenu du modèle par `candidatures` (référence → candidature)."""
        self.beginResetModel()
        self._contenus = [
            contenu_ligne(reference, candidature)
            for reference, candidature in sorted(
                candidatures.items(),
                key=lambda kv: kv[1]["date_candidature"],
                reverse=True,
            )
        ]
        self.endResetModel()

    def rowCount(self, parent: _Index = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._contenus)

    def data(self, index: _Index, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        contenu = self._contenus[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return contenu.titre
        if role == Qt.ItemDataRole.AccessibleTextRole:
            return " · ".join(contenu.textes())
        if role == ROLE_CONTENU:
            return contenu
        if role == ROLE_REFERENCE:
            return contenu.reference
        return None


@dataclass(frozen=True)
class _Polices:
    base: QFont
    titre: QFont
    badge: QFont
    action: QFont


def _polices(base: QFont) -> _Polices:
    """Mêmes ratios que la QSS (`theme.construire_feuille_style`)."""
    taille = base.pointSizeF()

    def _derivee(ratio: float, gras: bool) -> QFont:
        police = QFont(base)
        police.setPointSizeF(taille * ratio)
        police.setBold(gras)
        return police

    return _Polices(
        base=QFont(base),
        titre=_derivee(14 / 13, True),
        badge=_derivee(11 / 13, True),
        action=_derivee(12 / 13, False),
    )


class DelegueCandidature(QStyledItemDelegate):
    """Dessine une candidature : titre, badges, résumé et boutons d'action
    à gauche, historique à droite. Un clic sur un bouton émet
    `action_demandee(action, reference)`.

    La vue doit activer `setMouseTracking(True)` pour le survol des boutons.
    """

    action_demandee = Signal(str, str)
    """(clé d'action de `ACTIONS`, référence de la candidature)."""

    def __init__(self, vue: QAbstractItemView) -> None:
        super().__init__(vue)
        self._vue = vue
        self._survol: tuple[int, str] | None = None

    # --- Géométrie ---

    def _colonnes(self, rect: QRect) -> tuple[QRect, QRect]:
        """(colonne gauche, colonne historique) à l'intérieur des marges."""
        interieur = rect.adjusted(_MARGE_H, _MARGE_V, -_MARGE_H, -_MARGE_V)
        largeur_historique = min(
            _LARGEUR_HISTORIQUE_MAX,
            max(_LARGEUR_HISTORIQUE_MIN, int(interieur.width() * 0.35)),
        )
        largeur_gauche = max(
            0, interieur.width() - largeur_historique - _ESPACE_COLONNES
        )
        gauche = QRect(interieur.x(), interieur.y(), largeur_gauche, interieur.height())
        droite = QRect(
            gauche.right() + 1 + _ESPACE_COLONNES,
            interieur.y(),
            largeur_historique,
            interieur.height(),
        )
        return gauche, droite

    def _hauteur_bouton(self, polices: _Polices) -> int:
        return QFontMetrics(polices.action).height() + 2 * _PADDING_BOUTON_V

    def rectangles_boutons(self, rect: QRect, police: QFont) -> dict[str, QRect]:
        """Rectangles des boutons d'action d'une ligne occupant `rect`.

        Args:
            rect: Rectangle de la ligne dans la vue (`visualRect`).
            police: Police de base de la vue.

        Returns:
            Clé d'action → rectangle, en coordonnées du viewport.
        """
        polices = _polices(police)
        gauche, _ = self._colonnes(rect)
        y = (
            gauche.y()
            + QFontMetrics(polices.titre).height()
            + _ESPACE_LIGNES
            + QFontMetrics(polices.base).height()
            + _ESPACE_LIGNES
        )
        metriques = QFontMetrics(polices.action)
        hauteur = self._hauteur_bouton(polices)
        x = gauche.x()
        rectangles = {}
        for action, libelle in ACTIONS:
            largeur = metriques.horizontalAdvance(libelle) + 2 * _PADDING_BOUTON_H
            rectangles[action] = QRect(x, y, largeur, hauteur)
            x += largeur + _ESPACE_BOUTONS
        return rectangles

    def _action_sous(self, rect: QRect, police: QFont, position: QPoint) -> str | None:
        for action, rect_bouton in self.rectangles_boutons(rect, police).items():
            if rect_bouton.contains(position):
                return action
        return None

    def sizeHint(self, option: QStyleOptionViewItem, index: _Index) -> QSize:
        contenu: ContenuLigneCandidature = index.data(ROLE_CONTENU)
        polices = _polices(option.font)
        largeur = self._vue.viewport().width()
        _, droite = self._colonnes(QRect(0, 0, largeur, 10_000))

        hauteur_gauche = (
            QFontMetrics(polices.titre).height()
            + _ESPACE_LIGNES
            + QFontMetrics(polices.base).height()
            + _ESPACE_LIGNES
            + self._hauteur_bouton(polices)
        )
        metriques = QFontMetrics(polices.base)
        hauteur_droite = QFontMetrics(polices.titre).height()
        for ligne in contenu.historique:
            hauteur_droite += (
                3
                + metriques.boundingRect(
                    QRect(0, 0, droite.width(), 10_000),
                    Qt.TextFlag.TextWordWrap,
                    ligne,
                ).height()
            )
        return QSize(largeur, max(hauteur_gauche, hauteur_droite) + 2 * _MARGE_V)

    # --- Rendu ---

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: _Index
    ) -> None:
        contenu: ContenuLigneCandidature = index.data(ROLE_CONTENU)
        palette = palette_active()
        rect: QRect = option.rect
        etat = option.state
        polices = _polices(option.font)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if etat & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, QColor(palette.accent_soft))
        elif etat & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(rect, QColor(palette.panel))
        painter.setPen(QColor(palette.bordure))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        gauche, droite = self._colonnes(rect)
        self._peindre_entete(painter, contenu, gauche, polices)
        hauteur_titre = QFontMetrics(polices.titre).height()
        rect_resume = QRect(
            gauche.x(),
            gauche.y() + hauteur_titre + _ESPACE_LIGNES,
            gauche.width(),
            QFontMetrics(polices.base).height(),
        )
        painter.setFont(polices.base)
        painter.setPen(QColor(palette.texte_dim))
        painter.drawText(
            rect_resume,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            QFontMetrics(polices.base).elidedText(
                contenu.resume, Qt.TextElideMode.ElideRight, rect_resume.width()
            ),
        )
        self._peindre_boutons(painter, index.row(), rect, polices)
        self._peindre_historique(painter, contenu, droite, polices)
        painter.restore()

    def _peindre_entete(
        self,
        painter: QPainter,
        contenu: ContenuLigneCandidature,
        gauche: QRect,
        polices: _Polices,
    ) -> None:
        palette = palette_active()
        hauteur = QFontMetrics(polices.titre).height()
        metriques_badge = QFontMetrics(polices.badge)
        x_badge = gauche.right()
        rects_badges = []
        for texte, variante in reversed(contenu.badges):
            largeur = metriques_badge.horizontalAdvance(texte) + 2 * _PADDING_BADGE_H
            x_badge -= largeur
            rect_badge = QRect(
                x_badge,
                gauche.y() + (hauteur - metriques_badge.height() - 4) // 2,
                largeur,
                metriques_badge.height() + 4,
            )
            rects_badges.append((rect_badge, texte, variante))
            x_badge -= 12

        rect_titre = QRect(gauche.x(), gauche.y(), x_badge - gauche.x(), hauteur)
        painter.setFont(polices.titre)
        painter.setPen(QColor(palette.texte))
        painter.drawText(
            rect_titre,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            QFontMetrics(polices.titre).elidedText(
                contenu.titre, Qt.TextElideMode.ElideRight, rect_titre.width()
            ),
        )

        painter.setFont(polices.badge)
        for rect_badge, texte, variante in rects_badges:
            if variante == "attention":
                fond, bordure, couleur = (
                    palette.attention,
                    palette.attention,
                    palette.sur_accent,
                )
            else:
                fond, bordure, couleur = (
                    palette.panel,
                    palette.bordure,
                    palette.texte_dim,
                )
            rayon = rect_badge.height() / 2
            painter.setPen(QColor(bordure))
            painter.setBrush(QColor(fond))
            painter.drawRoundedRect(
                QRectF(rect_badge).adjusted(0.5, 0.5, -0.5, -0.5), rayon, rayon
            )
            painter.setPen(QColor(couleur))
            painter.drawText(rect_badge, Qt.AlignmentFlag.AlignCenter, texte)

    def _peindre_boutons(
        self, painter: QPainter, ligne: int, rect: QRect, polices: _Polices
    ) -> None:
        palette = palette_active()
        painter.setFont(polices.action)
        libelles = dict(ACTIONS)
        for action, rect_bouton in self.rectangles_boutons(rect, polices.base).items():
            survole = self._survol == (ligne, action)
            danger = action == "supprimer"
            if danger:
                fond = palette.danger if survole else palette.panel
                bordure = palette.danger
                couleur = palette.sur_accent if survole else palette.danger
            else:
                fond = palette.panel
                bordure = palette.accent if survole else palette.bordure
                couleur = palette.texte if survole else palette.texte_dim
            painter.setPen(QColor(bordure))
            painter.setBrush(QColor(fond))
            painter.drawRoundedRect(
                QRectF(rect_bouton).adjusted(0.5, 0.5, -0.5, -0.5),
                _RAYON_BOUTON,
                _RAYON_BOUTON,
            )
            painter.setPen(QColor(couleur))
            painter.drawText(
                rect_bouton, Qt.AlignmentFlag.AlignCenter, libelles[action]
            )

    def _peindre_historique(
        self,
        painter: QPainter,
        contenu: ContenuLigneCandidature,
        droite: QRect,
        polices: _Polices,
    ) -> None:
        palette = palette_active()
        painter.setFont(polices.titre)
        painter.setPen(QColor(palette.texte))
        hauteur_titre = QFontMetrics(polices.titre).height()
        painter.drawText(
            QRect(droite.x(), droite.y(), droite.width(), hauteur_titre),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Historique",
        )
        painter.setFont(polices.base)
        painter.setPen(QColor(palette.texte_dim))
        metriques = QFontMetrics(polices.base)
        y = droite.y() + hauteur_titre
        for ligne in contenu.historique:
            y += 3
            rect_ligne = metriques.boundingRect(
                QRect(droite.x(), y, droite.width(), 10_000),
                Qt.TextFlag.TextWordWrap,
                ligne,
            )
            painter.drawText(
                QRect(droite.x(), y, droite.width(), rect_ligne.height()),
                Qt.TextFlag.TextWordWrap,
                ligne,
            )
            y += rect_ligne.height()

    # --- Interaction ---

    def editorEvent(
        self,
        event: QEvent,
        model: QAbstractItemModel,
        option: QStyleOptionViewItem,
        index: _Index,
    ) -> bool:
        if not isinstance(event, QMouseEvent):
            return super().editorEvent(event, model, option, index)
        rect: QRect = option.rect
        police: QFont = option.font
        action = self._action_sous(rect, police, event.position().toPoint())

        if event.type() == QEvent.Type.MouseMove:
            survol = (index.row(), action) if action else None
            if survol != self._survol:
                self._survol = survol
                self._vue.viewport().update()
            return False
        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
            and action is not None
        ):
            self.action_demandee.emit(action, index.data(ROLE_REFERENCE))
            return True
        return super().editorEvent(event, model, option, index)

    def helpEvent(
        self,
        event: QHelpEvent,
        view: QAbstractItemView,
        option: QStyleOptionViewItem,
        index: _Index,
    ) -> bool:
        contenu: ContenuLigneCandidature | None = index.data(ROLE_CONTENU)
        if contenu is not None and not contenu.disponible:
            rect: QRect = option.rect
            police: QFont = option.font
            if self._action_sous(rect, police, event.pos()) == "voir":
                QToolTip.showText(event.globalPos(), INFOBULLE_OFFRE_DEPUBLIEE, view)
                return True
        QToolTip.hideText()
        return super().helpEvent(event, view, option, index)

    def reinitialiser_survol(self) -> None:
        """Oublie le bouton survolé (souris sortie de la vue)."""
        if self._survol is not None:
            self._survol = None
            self._vue.viewport().update()
