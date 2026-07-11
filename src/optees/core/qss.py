# src/optees/core/qss.py
"""Qt palette and global style sheet built from the central design tokens.

Keeping every color in :mod:`optees.core.design` means the whole app is themed
from one place: widgets no longer need to hardcode colors, they just use the
right ``objectName`` / property and inherit the global stylesheet.
"""
from __future__ import annotations

from PySide6.QtGui import QPalette, QColor

from optees.core.design import Tokens


def _qcolor(value: str) -> QColor:
    """Parse a hex or ``rgba(r, g, b, a)`` token string into a QColor."""
    value = value.strip()
    if value.startswith("rgba"):
        inner = value[value.index("(") + 1 : value.index(")")]
        parts = [p.strip() for p in inner.split(",")]
        r, g, b = (int(float(parts[i])) for i in range(3))
        a = int(round(float(parts[3]) * 255)) if len(parts) > 3 else 255
        return QColor(r, g, b, a)
    return QColor(value)


def qcolor(value: str) -> QColor:
    """Public helper: parse a token color string into a QColor.

    Used by custom ``QPainter`` widgets (charts) that paint with tokens.
    """
    return _qcolor(value)


def build_palette(t: Tokens) -> QPalette:
    """Build a QPalette so native painting (and palette-based widgets) match."""
    pal = QPalette()
    window = _qcolor(t.window)
    base = _qcolor(t.base)
    text = _qcolor(t.text)
    accent = _qcolor(t.accent)
    on_accent = _qcolor(t.on_accent)
    faint = _qcolor(t.text_faint)

    pal.setColor(QPalette.Window, window)
    pal.setColor(QPalette.WindowText, text)
    pal.setColor(QPalette.Base, base)
    pal.setColor(QPalette.AlternateBase, window)
    pal.setColor(QPalette.Text, text)
    pal.setColor(QPalette.Button, _qcolor(t.surface_solid))
    pal.setColor(QPalette.ButtonText, text)
    pal.setColor(QPalette.ToolTipBase, base)
    pal.setColor(QPalette.ToolTipText, text)
    pal.setColor(QPalette.PlaceholderText, faint)
    pal.setColor(QPalette.Highlight, accent)
    pal.setColor(QPalette.HighlightedText, on_accent)
    pal.setColor(QPalette.Link, accent)
    pal.setColor(QPalette.LinkVisited, accent)

    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, faint)

    return pal


def build_stylesheet(t: Tokens) -> str:
    """Return the global application style sheet for the given tokens."""
    return f"""
    QWidget {{
        color: {t.text};
        font-size: 14px;
    }}

    QToolTip {{
        color: {t.text};
        background-color: {t.base};
        border: 1px solid {t.border};
        padding: 6px 8px;
        border-radius: {t.radius_sm}px;
    }}

    /* Toolbar / navigation */
    QToolBar {{
        background: {t.window};
        border: none;
        border-bottom: 1px solid {t.border};
        padding: 6px 10px;
        spacing: 4px;
    }}
    QToolButton {{
        color: {t.text};
        background: transparent;
        border: 1px solid transparent;
        border-radius: {t.radius_sm}px;
        padding: 6px 12px;
        font-weight: 600;
    }}
    QToolButton:hover {{ background: {t.surface_hover}; }}
    QToolButton:pressed, QToolButton:checked {{ background: {t.accent_soft}; }}
    QToolButton::menu-indicator {{ width: 0; }}

    /* Buttons */
    QPushButton {{
        color: {t.text};
        background: {t.surface_solid};
        border: 1px solid {t.border};
        border-radius: {t.radius}px;
        padding: 8px 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {t.surface_hover}; border-color: {t.border_strong}; }}
    QPushButton:pressed {{ background: {t.surface}; }}
    QPushButton:disabled {{ color: {t.text_faint}; border-color: {t.border}; }}
    QPushButton[variant="primary"] {{
        color: {t.on_accent};
        background: {t.accent};
        border: 1px solid transparent;
    }}
    QPushButton[variant="primary"]:hover {{ background: {t.accent_hover}; }}
    QPushButton[variant="primary"]:pressed {{ background: {t.accent_press}; }}

    /* Inputs */
    QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        color: {t.text};
        background: {t.base};
        border: 1px solid {t.border};
        border-radius: {t.radius_sm}px;
        padding: 6px 10px;
        selection-background-color: {t.accent};
        selection-color: {t.on_accent};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QComboBox:on {{
        border-color: {t.accent};
    }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background: {t.base};
        border: 1px solid {t.border};
        border-radius: {t.radius_sm}px;
        selection-background-color: {t.accent};
        selection-color: {t.on_accent};
        outline: none;
    }}

    /* Menus */
    QMenu {{
        background: {t.base};
        border: 1px solid {t.border};
        border-radius: {t.radius_sm}px;
        padding: 6px;
    }}
    QMenu::item {{ padding: 7px 22px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {t.accent}; color: {t.on_accent}; }}
    QMenu::separator {{ height: 1px; background: {t.border}; margin: 6px 8px; }}

    /* Tables */
    QTableView, QTableWidget {{
        background: {t.base};
        alternate-background-color: {t.surface};
        gridline-color: {t.border};
        border: 1px solid {t.border};
        border-radius: {t.radius_sm}px;
        selection-background-color: {t.accent};
        selection-color: {t.on_accent};
        outline: none;
    }}
    QHeaderView::section {{
        background: {t.surface_solid};
        color: {t.text_muted};
        border: none;
        border-bottom: 1px solid {t.border};
        padding: 8px 10px;
        font-weight: 600;
    }}
    QTableCornerButton::section {{
        background: {t.surface_solid};
        border: none;
    }}

    /* Scrollbars */
    QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
    QScrollBar::handle:vertical {{
        background: {t.scroll};
        border-radius: 5px;
        min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {t.scroll_hover}; }}
    QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
    QScrollBar::handle:horizontal {{
        background: {t.scroll};
        border-radius: 5px;
        min-width: 32px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {t.scroll_hover}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    /* App components */
    QFrame#Card {{
        background: {t.surface};
        border: 1px solid {t.border};
        border-radius: {t.radius_lg}px;
    }}
    QFrame#Card:hover {{
        background: {t.surface_hover};
        border-color: {t.border_strong};
    }}
    QLabel#badge {{
        background: {t.accent};
        color: {t.on_accent};
        border-radius: 9px;
        padding: 3px 9px;
        font-size: 11px;
        font-weight: 700;
    }}
    QPushButton#updateBannerButton {{
        text-align: left;
        padding: 14px 18px;
        border-radius: {t.radius}px;
        border: 1px solid {t.accent};
        background: {t.accent_soft};
        color: {t.text};
        font-weight: 700;
    }}
    QPushButton#updateBannerButton:hover {{ background: {t.accent_soft_hover}; }}
    QPushButton#updateBannerButton:disabled {{
        color: {t.text_muted};
        border-color: {t.border};
        background: {t.surface};
    }}

    /* Small round "i" info buttons (fixed 24x24) */
    QPushButton[variant="info"], QPushButton#btnSchemaInfo, QPushButton#knapsackJsonInfoButton {{
        padding: 0;
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
        border-radius: 12px;
        background: {t.accent_soft};
        border: 1px solid {t.accent_soft_hover};
        color: {t.accent};
        font-size: 15px;
        font-weight: 800;
    }}
    QPushButton[variant="info"]:hover, QPushButton#btnSchemaInfo:hover, QPushButton#knapsackJsonInfoButton:hover {{
        color: {t.on_accent};
        background: {t.accent};
        border-color: transparent;
    }}

    /* Compact flat icon buttons (e.g. row remove) */
    QToolButton#rowRemoveButton {{
        padding: 0;
        border-radius: {t.radius_sm}px;
        background: transparent;
        border: 1px solid transparent;
        color: {t.text_muted};
    }}
    QToolButton#rowRemoveButton:hover {{
        color: {t.danger};
        background: {t.surface_hover};
    }}

    /* Section card (title + bordered body), used across all views */
    QFrame#Section {{
        border: 1px solid {t.border};
        border-radius: {t.radius}px;
        background: {t.surface};
    }}
    QLabel#SectionTitle {{ color: {t.text}; }}
    """
