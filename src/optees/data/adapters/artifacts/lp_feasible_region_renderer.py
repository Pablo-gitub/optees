from __future__ import annotations

from io import BytesIO
from math import isfinite

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from optees.application.contracts.artifact import ArtifactFormat
from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    RenderedArtifact,
)


_PALETTES = {
    "light": {
        "background": "#ffffff",
        "panel": "#f5f7fb",
        "text": "#172033",
        "muted": "#667085",
        "grid": "#d8dee9",
        "accent": "#2563eb",
        "guide": "#0891b2",
        "point": "#dc2626",
    },
    "dark": {
        "background": "#08111f",
        "panel": "#111c2e",
        "text": "#e7edf8",
        "muted": "#9aa8c1",
        "grid": "#34445f",
        "accent": "#4f7cff",
        "guide": "#4fd1e5",
        "point": "#ffb347",
    },
}


class LPFeasibleRegionRenderer:
    """Render an LP feasible set without importing Qt or a GUI backend."""

    renderer_version = "lp-feasible-region-1"

    def render(self, context: ArtifactRenderContext) -> RenderedArtifact:
        variables = _object_list(context.problem.get("variables"))
        dimension = len(variables)
        if dimension not in (2, 3):
            raise ValueError("LP feasible-region artifacts require 2 or 3 variables")

        palette = _PALETTES[context.options.theme]
        figure = Figure(
            figsize=(
                context.options.width / 100,
                context.options.height / 100,
            ),
            dpi=100,
            facecolor=palette["background"],
        )
        FigureCanvasAgg(figure)
        if dimension == 2:
            axes = figure.add_subplot(111)
            _draw_2d(axes, context, variables, palette)
        else:
            axes = figure.add_subplot(111, projection="3d")
            _draw_3d(axes, context, variables, palette)
        figure.tight_layout()

        stream = BytesIO()
        if context.format is ArtifactFormat.SVG:
            figure.savefig(
                stream,
                format="svg",
                facecolor=palette["background"],
                metadata={"Creator": "Optees"},
            )
            return RenderedArtifact("image/svg+xml", stream.getvalue())
        if context.format is ArtifactFormat.PNG:
            figure.savefig(
                stream,
                format="png",
                facecolor=palette["background"],
                dpi=100,
                metadata={"Software": "Optees"},
            )
            return RenderedArtifact("image/png", stream.getvalue())
        raise ValueError("LP feasible-region renderer received an unsupported format")


def _draw_2d(axes, context, variables, palette) -> None:
    limits = _plot_limits(context, variables)
    x_values = np.linspace(*limits[0], 180)
    y_values = np.linspace(*limits[1], 180)
    x_grid, y_grid = np.meshgrid(x_values, y_values)
    mask = _feasible_mask(context, (x_grid, y_grid), limits)

    axes.set_facecolor(palette["panel"])
    if np.any(mask):
        axes.contourf(
            x_grid,
            y_grid,
            mask.astype(int),
            levels=[0.5, 1.5],
            colors=[palette["accent"]],
            alpha=0.25,
        )
    for constraint in _object_list(context.problem.get("constraints")):
        coefficients = _numbers(constraint.get("coefficients"), 2)
        rhs = _number(constraint.get("rhs"))
        if coefficients is None or rhs is None:
            continue
        a, b = coefficients
        if abs(b) > 1e-12:
            axes.plot(
                x_values,
                (rhs - a * x_values) / b,
                color=palette["guide"],
                linewidth=1.4,
            )
        elif abs(a) > 1e-12:
            axes.axvline(rhs / a, color=palette["guide"], linewidth=1.4)

    point = _solution_point(context, variables)
    axes.scatter(
        [point[0]],
        [point[1]],
        color=palette["point"],
        edgecolors=palette["background"],
        linewidths=1.2,
        s=55,
        zorder=5,
    )
    axes.annotate(
        f"({point[0]:.3g}, {point[1]:.3g})",
        point,
        xytext=(7, 7),
        textcoords="offset points",
        color=palette["text"],
    )
    axes.set_xlim(*limits[0])
    axes.set_ylim(*limits[1])
    _style_axes(axes, variables, context.options.locale, palette)


def _draw_3d(axes, context, variables, palette) -> None:
    limits = _plot_limits(context, variables)
    samples = tuple(np.linspace(*axis_limits, 20) for axis_limits in limits)
    grids = np.meshgrid(*samples, indexing="ij")
    mask = _feasible_mask(context, grids, limits)
    coordinates = [grid[mask] for grid in grids]

    axes.set_facecolor(palette["panel"])
    if coordinates[0].size:
        axes.scatter(
            coordinates[0],
            coordinates[1],
            coordinates[2],
            color=palette["accent"],
            alpha=0.16,
            s=7,
            depthshade=False,
        )
    point = _solution_point(context, variables)
    axes.scatter(
        [point[0]],
        [point[1]],
        [point[2]],
        color=palette["point"],
        edgecolors=palette["background"],
        linewidths=1.0,
        s=65,
        depthshade=False,
    )
    axes.text(
        point[0],
        point[1],
        point[2],
        f"({point[0]:.3g}, {point[1]:.3g}, {point[2]:.3g})",
        color=palette["text"],
    )
    axes.set_xlim(*limits[0])
    axes.set_ylim(*limits[1])
    axes.set_zlim(*limits[2])
    _style_axes(axes, variables, context.options.locale, palette)


def _style_axes(axes, variables, locale: str, palette) -> None:
    labels = [
        str(variable.get("label") or variable.get("name") or f"x{index + 1}")
        for index, variable in enumerate(variables)
    ]
    axes.set_xlabel(labels[0], color=palette["text"])
    axes.set_ylabel(labels[1], color=palette["text"])
    if len(labels) == 3:
        axes.set_zlabel(labels[2], color=palette["text"])
    title = "Regione ammissibile e soluzione ottima" if locale == "it" else (
        "Feasible region and optimal solution"
    )
    axes.set_title(title, color=palette["text"])
    axes.tick_params(colors=palette["muted"])
    axes.grid(True, color=palette["grid"], alpha=0.55)
    for spine in getattr(axes, "spines", {}).values():
        spine.set_color(palette["grid"])


def _plot_limits(context, variables) -> tuple[tuple[float, float], ...]:
    point = _solution_point(context, variables)
    rhs_scale = max(
        [
            abs(rhs)
            for constraint in _object_list(context.problem.get("constraints"))
            if (rhs := _number(constraint.get("rhs"))) is not None
        ]
        + [1.0]
    )
    limits: list[tuple[float, float]] = []
    for index, variable in enumerate(variables):
        lower = _number(variable.get("lb"))
        upper = _number(variable.get("ub"))
        center = point[index]
        lower_value = lower if lower is not None else min(0.0, center - rhs_scale)
        upper_value = upper if upper is not None else max(
            lower_value + 1.0,
            center + rhs_scale * 0.25,
            rhs_scale * 1.25,
        )
        if upper_value <= lower_value:
            upper_value = lower_value + max(1.0, abs(lower_value) * 0.1)
        padding = (upper_value - lower_value) * 0.04
        limits.append((lower_value - padding, upper_value + padding))
    return tuple(limits)


def _feasible_mask(context, grids, limits) -> np.ndarray:
    mask = np.ones_like(grids[0], dtype=bool)
    steps = [
        (upper - lower) / max(1, grid.shape[index] - 1)
        for index, ((lower, upper), grid) in enumerate(zip(limits, grids))
    ]
    equality_tolerance = max(steps) * 0.7
    for index, variable in enumerate(
        _object_list(context.problem.get("variables"))
    ):
        lower = _number(variable.get("lb"))
        upper = _number(variable.get("ub"))
        if lower is not None:
            mask &= grids[index] >= lower - 1e-9
        if upper is not None:
            mask &= grids[index] <= upper + 1e-9
    for constraint in _object_list(context.problem.get("constraints")):
        coefficients = _numbers(constraint.get("coefficients"), len(grids))
        rhs = _number(constraint.get("rhs"))
        relation = constraint.get("relation")
        if coefficients is None or rhs is None:
            continue
        expression = sum(
            coefficient * grid
            for coefficient, grid in zip(coefficients, grids)
        )
        if relation == "<=":
            mask &= expression <= rhs + 1e-9
        elif relation == ">=":
            mask &= expression >= rhs - 1e-9
        elif relation == "=":
            mask &= np.abs(expression - rhs) <= equality_tolerance
    return mask


def _solution_point(context, variables) -> tuple[float, ...]:
    result_rows = _object_list(context.envelope.result.get("variables"))
    values = {
        str(row.get("name")): _number(row.get("value"))
        for row in result_rows
    }
    point: list[float] = []
    for variable in variables:
        name = str(variable.get("name", ""))
        value = values.get(name)
        if value is None:
            raise ValueError("LP result does not contain every plotted variable")
        point.append(value)
    return tuple(point)


def _object_list(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _numbers(value, expected: int) -> tuple[float, ...] | None:
    if not isinstance(value, list) or len(value) != expected:
        return None
    numbers = tuple(_number(item) for item in value)
    if any(item is None for item in numbers):
        return None
    return tuple(item for item in numbers if item is not None)


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if isfinite(number) else None
