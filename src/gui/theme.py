"""Feuille de style QSS de Tamponné.

Dérivée des mêmes tokens de couleur que la maquette validée
(« Vigie Carrière », 2026-08-31) — voir REFONTE.md §5bis pour la
chronologie du passage TUI → GUI.

Les variantes de widgets (`QPushButton[variant="primaire"]`, etc.) se
sélectionnent via une propriété Qt dynamique, à poser avec
``widget.setProperty("variant", "primaire")`` **avant** l'affichage du
widget (ou en forçant un repolish avec
``widget.style().unpolish(widget); widget.style().polish(widget)``
si posée après coup).
"""

BG = "#0A0D14"
SURFACE = "#131826"
PANEL = "#1A2133"
BORDER = "#2A3348"
TEXTE = "#E7EAF2"
TEXTE_DIM = "#8891A6"
ACCENT = "#8B93F8"
ACCENT_CLAIR = "#A0A7FA"
ACCENT_SOFT = "#3A3F82"
SUCCES = "#5FCB8D"
ATTENTION = "#E8B15C"
DANGER = "#E1685C"

FEUILLE_STYLE = f"""
QWidget {{
    background-color: {BG};
    color: {TEXTE};
    font-size: 13px;
}}

QLabel {{
    background: transparent;
}}
QLabel[role="titre"] {{
    font-size: 18px;
    font-weight: bold;
}}
QLabel[role="sousTexte"] {{
    color: {TEXTE_DIM};
}}
QLabel[role="nom"] {{
    font-size: 14px;
    font-weight: bold;
}}
QLabel[role="statut"] {{
    color: {ACCENT_CLAIR};
    font-size: 14px;
    font-weight: bold;
}}
QLabel[role="badge"] {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT_CLAIR};
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: bold;
}}
QLabel[role="badgeAttention"] {{
    background-color: {ATTENTION};
    color: {BG};
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: bold;
}}
QLabel[role="badgeNeutre"] {{
    background-color: {PANEL};
    color: {TEXTE_DIM};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: bold;
}}

QPushButton {{
    background-color: {PANEL};
    color: {TEXTE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    border-color: {ACCENT};
}}
QPushButton[variant="primaire"] {{
    background-color: {ACCENT};
    color: {BG};
    font-weight: bold;
    border: none;
}}
QPushButton[variant="primaire"]:hover {{
    background-color: {ACCENT_CLAIR};
}}
QPushButton[variant="ligneAction"] {{
    padding: 3px 10px;
    font-size: 12px;
    border-radius: 5px;
    color: {TEXTE_DIM};
}}
QPushButton[variant="ligneAction"]:hover {{
    color: {TEXTE};
    border-color: {ACCENT};
}}
QPushButton[variant="ligneActionDanger"] {{
    padding: 3px 10px;
    font-size: 12px;
    border-radius: 5px;
    color: {DANGER};
    border-color: {DANGER};
}}
QPushButton[variant="ligneActionDanger"]:hover {{
    background-color: {DANGER};
    color: {BG};
}}
QPushButton[variant="entete"] {{
    background-color: transparent;
    border: none;
    border-radius: 0;
    text-align: left;
    padding: 6px 2px;
    color: {TEXTE_DIM};
    font-weight: bold;
}}
QPushButton[variant="entete"]:hover {{
    color: {TEXTE};
}}

#barreNavigation {{
    background-color: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}
QPushButton[variant="nav"] {{
    background-color: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: 10px 18px;
    color: {TEXTE_DIM};
    font-weight: bold;
}}
QPushButton[variant="nav"]:hover {{
    color: {TEXTE};
}}
QPushButton[variant="nav"]:checked {{
    color: {TEXTE};
    border-bottom: 2px solid {ACCENT};
}}

QLineEdit, QComboBox {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {ACCENT};
}}

QCheckBox {{
    background: transparent;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {BORDER};
    border-radius: 4px;
    background-color: {SURFACE};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border: 2px solid {ACCENT_CLAIR};
}}

QTableWidget, QTreeWidget, QListWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: {BORDER};
    outline: none;
}}
QListWidget::item {{
    border-bottom: 1px solid {BORDER};
    padding: 2px;
}}
QListWidget::item:last {{
    border-bottom: none;
}}
QListWidget::item:hover {{
    background-color: {PANEL};
}}
QListWidget::item:selected {{
    background-color: {ACCENT_SOFT};
}}
QHeaderView::section {{
    background-color: {PANEL};
    color: {TEXTE_DIM};
    border: none;
    padding: 6px;
    font-weight: bold;
}}

QSplitter::handle {{
    background-color: {BORDER};
}}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: {SURFACE};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {TEXTE_DIM};
    font-weight: bold;
}}

QScrollBar:vertical {{
    background: {BG};
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {PANEL};
    border-radius: 4px;
}}

QProgressBar {{
    background-color: {PANEL};
    border: none;
    border-radius: 3px;
    max-height: 6px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
"""
