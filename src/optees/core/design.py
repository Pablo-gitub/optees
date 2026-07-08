# src/optees/core/design.py
"""Centralized design tokens for the Optees desktop UI.

This module is the single source of truth for colors, radii and spacing used
across the app. It has no Qt dependency so it can be imported anywhere and unit
tested in isolation. Qt-specific helpers (QPalette / global stylesheet) live in
``optees.core.qss``.

The palette intentionally mirrors the public website (deep blue-tinted dark,
brand blue ``#4c7bff`` and a cyan accent) so the app and the landing page read
as one product.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tokens:
    """A resolved set of design tokens for one theme (dark or light).

    Color values are CSS-ready strings (hex or ``rgba(...)``) so they can be
    dropped straight into Qt style sheets. Translucent ``rgba`` surfaces are used
    for elevation; the ``*_solid`` variants exist for the QPalette, which needs
    opaque colors.
    """

    is_dark: bool

    # Base surfaces
    window: str          # app background
    base: str            # inputs, tables, menus (opaque)
    surface: str         # cards / elevated panels
    surface_hover: str
    surface_solid: str   # opaque surface, for QPalette.Button

    # Lines
    border: str
    border_strong: str

    # Text
    text: str
    text_muted: str
    text_faint: str

    # Accent
    accent: str
    accent_hover: str
    accent_press: str
    accent_soft: str
    accent_soft_hover: str
    on_accent: str

    # Semantic
    cyan: str
    success: str
    warning: str
    danger: str

    # Scrollbars
    scroll: str
    scroll_hover: str

    # Metrics (px)
    radius: int = 10
    radius_sm: int = 8
    radius_lg: int = 16


DARK = Tokens(
    is_dark=True,
    window="#0f1622",
    base="#0b111c",
    surface="rgba(255, 255, 255, 0.045)",
    surface_hover="rgba(255, 255, 255, 0.078)",
    surface_solid="#172032",
    border="rgba(255, 255, 255, 0.10)",
    border_strong="rgba(255, 255, 255, 0.18)",
    text="#e9edf8",
    text_muted="#98a3bd",
    text_faint="#667089",
    accent="#4c7bff",
    accent_hover="#5f8bff",
    accent_press="#3f6ae6",
    accent_soft="rgba(76, 123, 255, 0.18)",
    accent_soft_hover="rgba(76, 123, 255, 0.28)",
    on_accent="#ffffff",
    cyan="#57d3ff",
    success="#34d399",
    warning="#f7b955",
    danger="#f87171",
    scroll="rgba(255, 255, 255, 0.18)",
    scroll_hover="rgba(255, 255, 255, 0.30)",
)

LIGHT = Tokens(
    is_dark=False,
    window="#f3f6fb",
    base="#ffffff",
    surface="#ffffff",
    surface_hover="#eef3fa",
    surface_solid="#ffffff",
    border="rgba(15, 25, 50, 0.12)",
    border_strong="rgba(15, 25, 50, 0.22)",
    text="#101a30",
    text_muted="#55617a",
    text_faint="#8a93a8",
    accent="#2f57e6",
    accent_hover="#244ad0",
    accent_press="#1e40b8",
    accent_soft="rgba(47, 87, 230, 0.12)",
    accent_soft_hover="rgba(47, 87, 230, 0.20)",
    on_accent="#ffffff",
    cyan="#0e7490",
    success="#12805c",
    warning="#b7791f",
    danger="#dc2626",
    scroll="rgba(15, 25, 50, 0.22)",
    scroll_hover="rgba(15, 25, 50, 0.36)",
)


def tokens(is_dark: bool) -> Tokens:
    """Return the token set for the requested theme."""
    return DARK if is_dark else LIGHT


def _parse(color: str) -> tuple[int, int, int, float]:
    """Parse a hex / ``rgb`` / ``rgba`` string into an (r, g, b, alpha) tuple."""
    c = color.strip()
    if c.startswith("rgb"):
        inner = c[c.index("(") + 1 : c.index(")")]
        parts = [p.strip() for p in inner.split(",")]
        r, g, b = (int(float(parts[i])) for i in range(3))
        a = float(parts[3]) if len(parts) > 3 else 1.0
        return r, g, b, a
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 1.0


def rgba(color: str, alpha: float) -> str:
    """Return ``color`` as an ``rgba(...)`` string with the given alpha."""
    r, g, b, _ = _parse(color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def flatten(color: str, background: str) -> str:
    """Composite a (possibly translucent) color over ``background`` -> solid hex.

    Qt's rich-text engine (QTextBrowser) does not honor ``rgba(...)``, so token
    colors used there must be flattened to an opaque hex value first.
    """
    r, g, b, a = _parse(color)
    br, bg_, bb, _ = _parse(background)
    fr = round(r * a + br * (1 - a))
    fg = round(g * a + bg_ * (1 - a))
    fb = round(b * a + bb * (1 - a))
    return f"#{fr:02x}{fg:02x}{fb:02x}"
