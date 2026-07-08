# src/optees/core/charts.py
"""Matplotlib theming helpers driven by the central design tokens.

Charts used to render with matplotlib's default white background, which clashed
badly with the dark app. These helpers restyle any Figure/Axes to match the
active theme so plots feel native in both light and dark.
"""
from __future__ import annotations

from optees.core.design import tokens as _tokens, Tokens
from optees.core.theme import theme


def to_mpl(css: str):
    """Convert a token color string to a matplotlib-friendly color.

    Hex strings pass through; ``rgba(...)`` / ``rgb(...)`` become 0..1 tuples.
    """
    css = css.strip()
    if css.startswith("rgb"):
        inner = css[css.index("(") + 1 : css.index(")")]
        parts = [p.strip() for p in inner.split(",")]
        r, g, b = (int(float(parts[i])) / 255.0 for i in range(3))
        a = float(parts[3]) if len(parts) > 3 else 1.0
        return (r, g, b, a)
    return css


def current() -> Tokens:
    """Tokens for the active theme."""
    return _tokens(theme.is_dark())


def style_axes(fig, ax, *, grid: bool = True) -> Tokens:
    """Restyle a Figure + Axes (2D or 3D) to match the current theme."""
    t = current()
    window = to_mpl(t.window)
    surface = to_mpl(t.surface_solid)
    muted = to_mpl(t.text_muted)
    text = to_mpl(t.text)
    border = to_mpl(t.border_strong)

    try:
        fig.patch.set_facecolor(window)
    except Exception:
        pass
    try:
        ax.set_facecolor(surface)
    except Exception:
        pass

    # Spines (2D only; 3D axes have no spines dict)
    for spine in getattr(ax, "spines", {}).values():
        try:
            spine.set_color(border)
        except Exception:
            pass

    try:
        ax.tick_params(colors=muted)
    except Exception:
        pass
    for axis_name in ("xaxis", "yaxis", "zaxis"):
        axis = getattr(ax, axis_name, None)
        if axis is None:
            continue
        try:
            axis.label.set_color(muted)
        except Exception:
            pass
        # 3D pane background
        try:
            axis.set_pane_color((*to_mpl(t.window)[:3], 1.0))
        except Exception:
            pass
    try:
        ax.title.set_color(text)
    except Exception:
        pass

    if grid:
        try:
            ax.grid(True, color=border, linewidth=0.6, alpha=0.4)
        except Exception:
            pass
    return t
