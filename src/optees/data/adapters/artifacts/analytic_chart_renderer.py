from __future__ import annotations

from io import BytesIO
from math import cos, isfinite, pi, sin

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from optees.application.contracts.artifact import ArtifactFormat
from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    RenderedArtifact,
)
from optees.application.services.analytic_artifact_visuals import (
    AnalyticVisualDefinition,
)
from optees.utility.nlp_expression import SafeNLPExpression


_PALETTES = {
    "light": {
        "background": "#ffffff",
        "panel": "#f5f7fb",
        "text": "#172033",
        "muted": "#667085",
        "grid": "#d8dee9",
        "accent": "#2563eb",
        "secondary": "#0891b2",
        "positive": "#16a34a",
        "negative": "#dc2626",
        "inactive": "#a7b0c0",
    },
    "dark": {
        "background": "#08111f",
        "panel": "#111c2e",
        "text": "#e7edf8",
        "muted": "#9aa8c1",
        "grid": "#34445f",
        "accent": "#4f7cff",
        "secondary": "#4fd1e5",
        "positive": "#34d399",
        "negative": "#fb7185",
        "inactive": "#526078",
    },
}


class AnalyticChartRenderer:
    renderer_version = "analytic-chart-1"

    def __init__(self, definition: AnalyticVisualDefinition) -> None:
        self._definition = definition

    def render(self, context: ArtifactRenderContext) -> RenderedArtifact:
        palette = _PALETTES[context.options.theme]
        figure = Figure(
            figsize=(context.options.width / 100, context.options.height / 100),
            dpi=100,
            facecolor=palette["background"],
        )
        FigureCanvasAgg(figure)
        kind = self._definition.chart_kind
        if kind == "nlp_landscape" and _extra(context, "view", "contour") == "surface":
            axes = figure.add_subplot(111, projection="3d")
        else:
            axes = figure.add_subplot(111)
        axes.set_facecolor(palette["panel"])

        drawers = {
            "dijkstra_graph": _draw_dijkstra,
            "nlp_convergence": _draw_convergence,
            "nlp_landscape": _draw_landscape,
            "regression_fit": _draw_regression_fit,
            "classification_confusion": _draw_confusion,
            "classification_boundary": _draw_decision_boundary,
        }
        drawers[kind](axes, context, palette)
        _style(axes, palette)
        figure.tight_layout()
        return _encode(figure, context, palette)


def _draw_dijkstra(axes, context, palette) -> None:
    vertices = _objects(context.problem.get("vertices"))
    edges = _objects(context.problem.get("edges"))
    if not vertices:
        raise ValueError("highlighted graph requires at least one vertex")
    if len(vertices) > 200:
        raise ValueError("highlighted graph supports at most 200 vertices")
    identifiers = [str(vertex.get("id", "")) for vertex in vertices]
    labels = {
        str(vertex.get("id", "")): str(
            vertex.get("label") or vertex.get("id") or ""
        )
        for vertex in vertices
    }
    positions = {
        identifier: (
            cos(2 * pi * index / len(identifiers)),
            sin(2 * pi * index / len(identifiers)),
        )
        for index, identifier in enumerate(identifiers)
    }
    raw_path = context.envelope.result.get("path")
    path = [str(node) for node in raw_path] if isinstance(raw_path, list) else []
    path_edges = set(zip(path, path[1:]))
    if not bool(context.problem.get("directed")):
        path_edges |= {(target, source) for source, target in path_edges}

    for edge in edges:
        source = str(edge.get("from", ""))
        target = str(edge.get("to", ""))
        if source not in positions or target not in positions:
            continue
        start = positions[source]
        end = positions[target]
        highlighted = (source, target) in path_edges
        color = palette["accent"] if highlighted else palette["inactive"]
        axes.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops={
                "arrowstyle": "->" if context.problem.get("directed") else "-",
                "color": color,
                "linewidth": 2.8 if highlighted else 1.2,
                "shrinkA": 14,
                "shrinkB": 14,
            },
            zorder=1,
        )
        midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        axes.text(
            *midpoint,
            _display_number(edge.get("weight")),
            color=palette["muted"],
            fontsize=8,
            ha="center",
            va="center",
        )
    for identifier, (x_value, y_value) in positions.items():
        highlighted = identifier in path
        axes.scatter(
            [x_value],
            [y_value],
            s=420,
            color=palette["accent"] if highlighted else palette["panel"],
            edgecolors=palette["secondary"],
            linewidths=1.5,
            zorder=2,
        )
        axes.text(
            x_value,
            y_value,
            labels[identifier],
            color=palette["background"] if highlighted else palette["text"],
            ha="center",
            va="center",
            zorder=3,
        )
    axes.set_title(
        "Cammino minimo evidenziato"
        if context.options.locale == "it"
        else "Highlighted shortest path",
        color=palette["text"],
    )
    axes.set_aspect("equal")
    axes.set_xlim(-1.25, 1.25)
    axes.set_ylim(-1.25, 1.25)
    axes.axis("off")


def _draw_convergence(axes, context, palette) -> None:
    raw_history = context.envelope.diagnostics.get("convergence_history")
    history = _finite_values(raw_history)
    if not history:
        raise ValueError("convergence chart requires a non-empty convergence history")
    max_points = int(_extra(context, "max_points", 500))
    history = _sample_series(history, max_points)
    steps = list(range(len(history)))
    axes.plot(steps, history, color=palette["accent"], linewidth=2)
    axes.scatter(steps, history, color=palette["secondary"], s=20)
    axes.set_xlabel(
        "Iterazione" if context.options.locale == "it" else "Iteration",
        color=palette["text"],
    )
    axes.set_ylabel(
        "Obiettivo" if context.options.locale == "it" else "Objective",
        color=palette["text"],
    )
    axes.set_title(
        "Storia di convergenza"
        if context.options.locale == "it"
        else "Convergence history",
        color=palette["text"],
    )


def _draw_landscape(axes, context, palette) -> None:
    variables = _objects(context.problem.get("variables"))
    if len(variables) != 2:
        raise ValueError("objective landscape requires exactly two variables")
    names = tuple(str(variable.get("name", "")) for variable in variables)
    raw_objective = context.problem.get("objective")
    objective = raw_objective if isinstance(raw_objective, dict) else {}
    expression = SafeNLPExpression.compile(objective.get("expression"), names)
    candidate = _variable_values(context)
    if any(name not in candidate for name in names):
        raise ValueError("objective landscape requires a complete candidate vector")
    limits = tuple(
        _variable_limits(variable, candidate.get(name, 0.0))
        for variable, name in zip(variables, names, strict=True)
    )
    resolution = int(_extra(context, "resolution", 80))
    x_values = np.linspace(*limits[0], resolution)
    y_values = np.linspace(*limits[1], resolution)
    x_grid, y_grid = np.meshgrid(x_values, y_values)
    z_grid = np.empty_like(x_grid)
    for row_index in range(resolution):
        for column_index in range(resolution):
            try:
                z_grid[row_index, column_index] = expression.evaluate(
                    {
                        names[0]: x_grid[row_index, column_index],
                        names[1]: y_grid[row_index, column_index],
                    }
                )
            except ValueError:
                z_grid[row_index, column_index] = np.nan
    if not np.isfinite(z_grid).any():
        raise ValueError("objective expression is not finite in the plotted bounds")
    view = _extra(context, "view", "contour")
    if view == "surface":
        axes.plot_surface(
            x_grid,
            y_grid,
            z_grid,
            cmap="viridis",
            alpha=0.82,
            linewidth=0,
        )
        point_z = context.envelope.result.get("objective")
        if _number(point_z) is not None:
            axes.scatter(
                [candidate[names[0]]],
                [candidate[names[1]]],
                [float(point_z)],
                color=palette["negative"],
                s=55,
            )
        axes.set_zlabel(
            "Obiettivo" if context.options.locale == "it" else "Objective",
            color=palette["text"],
        )
    else:
        axes.contourf(x_grid, y_grid, z_grid, levels=24, cmap="viridis")
        axes.contour(
            x_grid,
            y_grid,
            z_grid,
            levels=12,
            colors=palette["grid"],
            linewidths=0.5,
        )
        axes.scatter(
            [candidate[names[0]]],
            [candidate[names[1]]],
            color=palette["negative"],
            edgecolors=palette["background"],
            s=60,
        )
    axes.set_xlabel(_variable_label(variables[0]), color=palette["text"])
    axes.set_ylabel(_variable_label(variables[1]), color=palette["text"])
    axes.set_title(
        "Paesaggio dell'obiettivo"
        if context.options.locale == "it"
        else "Objective landscape",
        color=palette["text"],
    )


def _draw_regression_fit(axes, context, palette) -> None:
    dataset = _dataset(context)
    feature_names = dataset.get("feature_names")
    if not isinstance(feature_names, list) or len(feature_names) != 1:
        raise ValueError("regression fit chart requires exactly one feature")
    rows = _objects(dataset.get("rows"))
    max_points = int(_extra(context, "max_points", 500))
    points = [
        (features[0], _number(row.get("target")))
        for row in rows[:max_points]
        if (features := _numbers(row.get("features"))) is not None
        and len(features) == 1
        and _number(row.get("target")) is not None
    ]
    if not points:
        raise ValueError("regression fit chart contains no numeric rows")
    x_values = np.array([point[0] for point in points])
    y_values = np.array([point[1] for point in points])
    intercept = _number(context.envelope.result.get("intercept"))
    coefficients = _objects(context.envelope.result.get("coefficients"))
    coefficient = next(
        (
            _number(item.get("value"))
            for item in coefficients
            if item.get("feature") == feature_names[0]
        ),
        None,
    )
    if intercept is None or coefficient is None:
        raise ValueError("regression fit chart requires a trained coefficient")
    line_x = np.linspace(float(x_values.min()), float(x_values.max()), 100)
    axes.scatter(x_values, y_values, color=palette["accent"], alpha=0.75)
    axes.plot(
        line_x,
        intercept + coefficient * line_x,
        color=palette["negative"],
        linewidth=2.2,
    )
    axes.set_xlabel(str(feature_names[0]), color=palette["text"])
    axes.set_ylabel(str(dataset.get("target_name", "target")), color=palette["text"])
    axes.set_title(
        "Retta di regressione"
        if context.options.locale == "it"
        else "Regression fit",
        color=palette["text"],
    )


def _draw_confusion(axes, context, palette) -> None:
    partition = "test"
    raw = context.envelope.result.get("test_confusion")
    if not isinstance(raw, dict) or not raw:
        partition = "train"
        raw = context.envelope.result.get("train_confusion")
    if not isinstance(raw, dict) or not raw:
        raise ValueError("confusion matrix requires confusion counts")
    confusion = raw
    values = np.array(
        [
            [
                _number(confusion.get("true_negative")) or 0,
                _number(confusion.get("false_positive")) or 0,
            ],
            [
                _number(confusion.get("false_negative")) or 0,
                _number(confusion.get("true_positive")) or 0,
            ],
        ]
    )
    axes.imshow(values, cmap="Blues")
    negative = str(context.envelope.result.get("negative_label", "negative"))
    positive = str(context.envelope.result.get("positive_label", "positive"))
    axes.set_xticks((0, 1), (negative, positive))
    axes.set_yticks((0, 1), (negative, positive))
    for row_index in range(2):
        for column_index in range(2):
            axes.text(
                column_index,
                row_index,
                _display_number(values[row_index, column_index]),
                ha="center",
                va="center",
                color=palette["text"],
                fontsize=14,
            )
    axes.set_xlabel(
        "Predetto" if context.options.locale == "it" else "Predicted",
        color=palette["text"],
    )
    axes.set_ylabel(
        "Reale" if context.options.locale == "it" else "Actual",
        color=palette["text"],
    )
    axes.set_title(
        (
            f"Matrice di confusione ({partition})"
            if context.options.locale == "it"
            else f"Confusion matrix ({partition})"
        ),
        color=palette["text"],
    )


def _draw_decision_boundary(axes, context, palette) -> None:
    dataset = _dataset(context)
    feature_names = dataset.get("feature_names")
    if not isinstance(feature_names, list) or len(feature_names) != 2:
        raise ValueError("decision boundary requires exactly two features")
    rows = _objects(dataset.get("rows"))
    max_points = int(_extra(context, "max_points", 500))
    points = [
        (features, str(row.get("target")))
        for row in rows[:max_points]
        if (features := _numbers(row.get("features"))) is not None
        and len(features) == 2
    ]
    if not points:
        raise ValueError("decision boundary contains no numeric rows")
    coefficients = _objects(context.envelope.result.get("coefficients"))
    coefficient_map = {
        str(item.get("feature")): _number(item.get("value"))
        for item in coefficients
    }
    intercept = _number(context.envelope.result.get("intercept"))
    if intercept is None or any(coefficient_map.get(str(name)) is None for name in feature_names):
        raise ValueError("decision boundary requires trained coefficients")
    scaling = {
        str(item.get("feature")): (
            _number(item.get("mean")) or 0.0,
            _nonzero_number(item.get("scale"), 1.0),
        )
        for item in _objects(context.envelope.result.get("feature_scaling"))
    }
    x_values = np.array([point[0][0] for point in points])
    y_values = np.array([point[0][1] for point in points])
    x_axis = np.linspace(*_padded_limits(x_values), 120)
    y_axis = np.linspace(*_padded_limits(y_values), 120)
    x_grid, y_grid = np.meshgrid(x_axis, y_axis)
    x_mean, x_scale = scaling.get(str(feature_names[0]), (0.0, 1.0))
    y_mean, y_scale = scaling.get(str(feature_names[1]), (0.0, 1.0))
    logits = (
        intercept
        + float(coefficient_map[str(feature_names[0])])
        * ((x_grid - x_mean) / x_scale)
        + float(coefficient_map[str(feature_names[1])])
        * ((y_grid - y_mean) / y_scale)
    )
    probabilities = 1.0 / (1.0 + np.exp(-np.clip(logits, -700, 700)))
    threshold = _number(context.envelope.result.get("decision_threshold")) or 0.5
    axes.contourf(
        x_grid,
        y_grid,
        probabilities,
        levels=[0.0, threshold, 1.0],
        colors=[palette["negative"], palette["positive"]],
        alpha=0.18,
    )
    axes.contour(
        x_grid,
        y_grid,
        probabilities,
        levels=[threshold],
        colors=[palette["text"]],
        linewidths=1.8,
    )
    positive_label = str(context.envelope.result.get("positive_label"))
    for label, color in (
        (positive_label, palette["positive"]),
        ("__negative__", palette["negative"]),
    ):
        selected = [
            point for point in points
            if (point[1] == positive_label) == (label == positive_label)
        ]
        if selected:
            axes.scatter(
                [point[0][0] for point in selected],
                [point[0][1] for point in selected],
                color=color,
                edgecolors=palette["background"],
                alpha=0.85,
            )
    axes.set_xlabel(str(feature_names[0]), color=palette["text"])
    axes.set_ylabel(str(feature_names[1]), color=palette["text"])
    axes.set_title(
        "Frontiera decisionale"
        if context.options.locale == "it"
        else "Decision boundary",
        color=palette["text"],
    )


def _style(axes, palette) -> None:
    axes.tick_params(colors=palette["muted"])
    axes.grid(True, color=palette["grid"], alpha=0.35)
    for spine in getattr(axes, "spines", {}).values():
        spine.set_color(palette["grid"])


def _encode(figure, context, palette) -> RenderedArtifact:
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
    raise ValueError("analytic renderer received an unsupported format")


def _objects(value) -> list[dict]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _numbers(value) -> list[float] | None:
    if not isinstance(value, list):
        return None
    normalized = [_number(item) for item in value]
    if any(item is None for item in normalized):
        return None
    return [float(item) for item in normalized if item is not None]


def _number(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        normalized = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return normalized if isfinite(normalized) else None


def _nonzero_number(value, default: float) -> float:
    normalized = _number(value)
    return normalized if normalized not in (None, 0.0) else default


def _finite_values(value) -> list[float]:
    if not isinstance(value, list):
        return []
    return [number for item in value if (number := _number(item)) is not None]


def _sample_series(values: list[float], maximum: int) -> list[float]:
    if len(values) <= maximum:
        return values
    indices = np.linspace(0, len(values) - 1, maximum, dtype=int)
    return [values[int(index)] for index in indices]


def _dataset(context) -> dict:
    raw = context.problem.get("dataset")
    return raw if isinstance(raw, dict) else {}


def _variable_values(context) -> dict[str, float]:
    values = {}
    for variable in _objects(context.envelope.result.get("variables")):
        value = _number(variable.get("value"))
        if value is not None:
            values[str(variable.get("name"))] = value
    return values


def _variable_limits(variable: dict, candidate: float) -> tuple[float, float]:
    lower = _number(variable.get("lb"))
    upper = _number(variable.get("ub"))
    scale = max(1.0, abs(candidate) * 0.5)
    low = lower if lower is not None else candidate - scale
    high = upper if upper is not None else candidate + scale
    if high <= low:
        high = low + 1.0
    return low, high


def _variable_label(variable: dict) -> str:
    return str(variable.get("label") or variable.get("name") or "variable")


def _padded_limits(values: np.ndarray) -> tuple[float, float]:
    low = float(values.min())
    high = float(values.max())
    span = high - low
    padding = span * 0.08 if span else max(1.0, abs(low) * 0.08)
    return low - padding, high + padding


def _extra(context, key: str, default):
    return (context.options.extra or {}).get(key, default)


def _display_number(value) -> str:
    normalized = _number(value)
    return f"{normalized:.4g}" if normalized is not None else "?"
