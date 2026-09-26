"""Feuille de style QSS de Tamponné, en variantes claire et sombre.

Dérivée des mêmes tokens de couleur que la maquette validée
(« Vigie Carrière », 2026-08-31) — voir REFONTE.md §5bis pour la
chronologie du passage TUI → GUI. La palette dépend du mode choisi dans
les Paramètres (`palette_pour_mode`) : imposée (sombre, clair) ou, en mode
automatique, dérivée du réglage système (`palette_systeme`) et réappliquée
à chaud quand il change (`appliquer_theme`).

Les variantes de widgets (`QPushButton[variant="primaire"]`, etc.) se
sélectionnent via une propriété Qt dynamique, à poser avec
``widget.setProperty("variant", "primaire")`` **avant** l'affichage du
widget (ou en forçant un repolish avec
``widget.style().unpolish(widget); widget.style().polish(widget)``
si posée après coup).
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from src.parametres_affichage import MODE_THEME_DEFAUT, ModeTheme


@dataclass(frozen=True)
class Palette:
    """Tokens de couleur d'un thème (valeurs hexadécimales `#RRGGBB`)."""

    bg: str
    surface: str
    panel: str
    bordure: str
    texte: str
    texte_dim: str
    accent: str
    accent_clair: str
    """Survol d'un fond accent et texte d'accent (statut, badge)."""
    accent_soft: str
    succes: str
    attention: str
    danger: str
    sur_accent: str
    """Texte ou tracé posé sur un fond accent, attention ou danger."""


PALETTE_SOMBRE = Palette(
    bg="#0A0D14",
    surface="#131826",
    panel="#1A2133",
    bordure="#2A3348",
    texte="#E7EAF2",
    texte_dim="#8891A6",
    accent="#8B93F8",
    accent_clair="#A0A7FA",
    # Assombri depuis #3A3F82 : texte des badges à 4,25:1, sous le seuil AA.
    accent_soft="#363B7B",
    succes="#5FCB8D",
    attention="#E8B15C",
    danger="#E1685C",
    sur_accent="#0A0D14",
)

PALETTE_CLAIRE = Palette(
    bg="#F5F6FA",
    surface="#FFFFFF",
    panel="#ECEEF4",
    bordure="#CDD2DE",
    texte="#161B29",
    texte_dim="#535C70",
    accent="#4A53D6",
    accent_clair="#3A42B8",
    accent_soft="#E1E3FC",
    succes="#1F8A4C",
    attention="#8F5400",
    danger="#B83227",
    sur_accent="#FFFFFF",
)

_palette_active = PALETTE_SOMBRE
_taille_base_pt = 13.0
_mode_theme: ModeTheme = MODE_THEME_DEFAUT


def palette_systeme() -> Palette:
    """Palette correspondant au réglage clair/sombre du système — sombre
    si le système ne l'indique pas (`ColorScheme.Unknown`), comme avant
    l'introduction du thème clair."""
    schema = QGuiApplication.styleHints().colorScheme()
    return PALETTE_CLAIRE if schema == Qt.ColorScheme.Light else PALETTE_SOMBRE


def palette_pour_mode(mode: ModeTheme) -> Palette:
    """Palette à appliquer pour `mode` : imposée (« sombre », « clair »)
    ou dérivée du réglage système (« auto », voir `palette_systeme`)."""
    if mode == "sombre":
        return PALETTE_SOMBRE
    if mode == "clair":
        return PALETTE_CLAIRE
    return palette_systeme()


def palette_active() -> Palette:
    """Palette appliquée en dernier par `appliquer_theme` — à lire au
    moment du dessin (`paintEvent`) par les widgets peints à la main."""
    return _palette_active


_SVG_FLECHE_BAS = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" '
    'viewBox="0 0 10 6"><path d="M1 1l4 4 4-4" fill="none" stroke="{couleur}" '
    'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


def chemin_fleche_bas(couleur: str) -> str:
    """Chemin d'une flèche SVG de liste déroulante dans la couleur donnée,
    générée au besoin dans le dossier temporaire (la QSS n'accepte que des
    fichiers ou ressources comme image, pas de SVG en ligne).

    Args:
        couleur: Couleur `#RRGGBB` du trait.

    Returns:
        Chemin absolu, avec des « / » comme l'exige la QSS sur tout système.
    """
    dossier = Path(tempfile.gettempdir()) / "tamponne"
    dossier.mkdir(exist_ok=True)
    chemin = dossier / f"fleche_bas_{couleur.lstrip('#').lower()}.svg"
    if not chemin.exists():
        chemin.write_text(_SVG_FLECHE_BAS.format(couleur=couleur), encoding="utf-8")
    return chemin.as_posix()


def construire_qpalette(palette: Palette) -> QPalette:
    """`QPalette` Qt équivalente, pour ce que la QSS ne couvre pas avec le
    style Fusion (infobulles, menus, calendrier de `QDateEdit`…)."""
    roles = QPalette.ColorRole
    qpalette = QPalette()
    for role, couleur in [
        (roles.Window, palette.bg),
        (roles.WindowText, palette.texte),
        (roles.Base, palette.surface),
        (roles.AlternateBase, palette.panel),
        (roles.Text, palette.texte),
        (roles.PlaceholderText, palette.texte_dim),
        (roles.Button, palette.panel),
        (roles.ButtonText, palette.texte),
        (roles.Highlight, palette.accent),
        (roles.HighlightedText, palette.sur_accent),
        (roles.ToolTipBase, palette.panel),
        (roles.ToolTipText, palette.texte),
        (roles.Link, palette.accent_clair),
        (roles.Light, palette.surface),
        (roles.Midlight, palette.panel),
        (roles.Mid, palette.bordure),
        (roles.Dark, palette.bordure),
        (roles.Shadow, palette.bordure),
    ]:
        qpalette.setColor(role, QColor(couleur))
    return qpalette


def appliquer_theme(
    app: QApplication,
    taille_base_pt: float | None = None,
    mode: ModeTheme | None = None,
) -> None:
    """Applique à `app` la palette et la feuille de style du mode de thème.

    Args:
        app: Application Qt.
        taille_base_pt: Taille de police de base, voir
            `construire_feuille_style` ; ``None`` reprend celle du dernier
            appel.
        mode: Mode de thème (« auto », « sombre », « clair ») ; ``None``
            reprend celui du dernier appel — cas de la réapplication à
            chaud quand le réglage clair/sombre du système change.
    """
    global _palette_active, _taille_base_pt, _mode_theme
    if taille_base_pt is not None:
        _taille_base_pt = taille_base_pt
    if mode is not None:
        _mode_theme = mode
    _palette_active = palette_pour_mode(_mode_theme)
    app.setPalette(construire_qpalette(_palette_active))
    app.setStyleSheet(construire_feuille_style(_taille_base_pt, _palette_active))


def construire_feuille_style(
    taille_base_pt: float, palette: Palette = PALETTE_SOMBRE
) -> str:
    """QSS de `palette`, tailles de police dérivées de `taille_base_pt`
    (capturée depuis ``QApplication.font().pointSizeF()`` avant
    application) plutôt que codées en dur — respecte la police par défaut du système (donc,
    sur Linux/KDE notamment, les préférences d'accessibilité de taille de
    texte de l'utilisateur) au lieu de l'écraser. Ratios calqués sur les
    tailles historiques (13px/18px/14px/11px/12px, base 13px).

    Args:
        taille_base_pt: Taille de police de base, en points.
        palette: Tokens de couleur à utiliser (sombre par défaut).
    """
    p = palette
    fleche_bas = chemin_fleche_bas(p.texte_dim)
    pt_base = taille_base_pt
    pt_titre = taille_base_pt * (18 / 13)
    pt_nom = taille_base_pt * (14 / 13)
    pt_badge = taille_base_pt * (11 / 13)
    pt_ligne_action = taille_base_pt * (12 / 13)

    return f"""
QWidget {{
    background-color: {p.bg};
    color: {p.texte};
    font-size: {pt_base:.1f}pt;
}}

QLabel {{
    background: transparent;
}}
QLabel[role="titre"] {{
    font-size: {pt_titre:.1f}pt;
    font-weight: bold;
}}
QLabel[role="sousTexte"] {{
    color: {p.texte_dim};
}}
QLabel[role="nom"] {{
    font-size: {pt_nom:.1f}pt;
    font-weight: bold;
}}
QLabel[role="statut"] {{
    color: {p.accent_clair};
    font-size: {pt_nom:.1f}pt;
    font-weight: bold;
}}
QLabel[role="badge"] {{
    background-color: {p.accent_soft};
    color: {p.accent_clair};
    border-radius: 9px;
    padding: 2px 9px;
    font-size: {pt_badge:.1f}pt;
    font-weight: bold;
}}
QLabel[role="badgeAttention"] {{
    background-color: {p.attention};
    color: {p.sur_accent};
    border-radius: 9px;
    padding: 2px 9px;
    font-size: {pt_badge:.1f}pt;
    font-weight: bold;
}}
QLabel[role="badgeNeutre"] {{
    background-color: {p.panel};
    color: {p.texte_dim};
    border: 1px solid {p.bordure};
    border-radius: 9px;
    padding: 2px 9px;
    font-size: {pt_badge:.1f}pt;
    font-weight: bold;
}}

QPushButton {{
    background-color: {p.panel};
    color: {p.texte};
    border: 1px solid {p.bordure};
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    border-color: {p.accent};
}}
QPushButton[variant="primaire"] {{
    background-color: {p.accent};
    color: {p.sur_accent};
    font-weight: bold;
    border: none;
}}
QPushButton[variant="primaire"]:hover {{
    background-color: {p.accent_clair};
}}
QPushButton[variant="ligneAction"] {{
    padding: 3px 10px;
    font-size: {pt_ligne_action:.1f}pt;
    border-radius: 5px;
    color: {p.texte_dim};
}}
QPushButton[variant="ligneAction"]:hover {{
    color: {p.texte};
    border-color: {p.accent};
}}
QPushButton[variant="ligneActionDanger"] {{
    padding: 3px 10px;
    font-size: {pt_ligne_action:.1f}pt;
    border-radius: 5px;
    color: {p.danger};
    border-color: {p.danger};
}}
QPushButton[variant="ligneActionDanger"]:hover {{
    background-color: {p.danger};
    color: {p.sur_accent};
}}
QPushButton[variant="entete"] {{
    background-color: transparent;
    border: none;
    border-radius: 0;
    text-align: left;
    padding: 6px 2px;
    color: {p.texte_dim};
    font-weight: bold;
}}
QPushButton[variant="entete"]:hover {{
    color: {p.texte};
}}

#barreNavigation {{
    background-color: {p.surface};
    border-bottom: 1px solid {p.bordure};
}}
QPushButton[variant="nav"] {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: 6px 14px;
    color: {p.texte_dim};
    font-weight: bold;
}}
QPushButton[variant="nav"]:hover {{
    color: {p.texte};
}}
QPushButton[variant="nav"]:checked {{
    color: {p.texte};
    border-bottom: 2px solid {p.accent};
}}

QLineEdit, QComboBox {{
    background-color: {p.surface};
    border: 1px solid {p.bordure};
    border-radius: 6px;
    padding: 5px 8px;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {p.accent};
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
/* Styler ::drop-down fait disparaître la flèche native : image fournie. */
QComboBox::down-arrow {{
    image: url({fleche_bas});
    width: 10px;
    height: 6px;
}}

QCheckBox {{
    background: transparent;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {p.bordure};
    border-radius: 4px;
    background-color: {p.surface};
}}
QCheckBox::indicator:hover {{
    border-color: {p.accent};
}}
QCheckBox::indicator:checked {{
    background-color: {p.accent};
    border: 2px solid {p.accent_clair};
}}

QTableView, QTreeView, QListView {{
    background-color: {p.surface};
    border: 1px solid {p.bordure};
    border-radius: 8px;
    gridline-color: {p.bordure};
    outline: none;
    selection-background-color: {p.accent_soft};
    selection-color: {p.texte};
}}
QListWidget::item {{
    border-bottom: 1px solid {p.bordure};
    padding: 2px;
}}
QListWidget::item:last {{
    border-bottom: none;
}}
QListWidget::item:hover {{
    background-color: {p.panel};
}}
QListWidget::item:selected {{
    background-color: {p.accent_soft};
}}
QHeaderView::section {{
    background-color: {p.panel};
    color: {p.texte_dim};
    border: none;
    padding: 6px;
    font-weight: bold;
}}

QSplitter::handle {{
    background-color: {p.bordure};
}}

QGroupBox {{
    border: 1px solid {p.bordure};
    border-radius: 8px;
    /* Marge en em : le titre loge entièrement au-dessus du cadre, quelle
       que soit la taille de police (un décalage négatif le rognait). */
    margin-top: 1.6em;
    padding-top: 10px;
    background-color: {p.surface};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 4px;
    padding: 0 6px;
    color: {p.texte_dim};
    font-weight: bold;
}}

QScrollBar:vertical {{
    background: {p.bg};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {p.bordure};
    border-radius: 4px;
}}

QProgressBar {{
    background-color: {p.panel};
    border: none;
    border-radius: 3px;
    max-height: 6px;
}}
QProgressBar::chunk {{
    background-color: {p.accent};
    border-radius: 3px;
}}
"""
