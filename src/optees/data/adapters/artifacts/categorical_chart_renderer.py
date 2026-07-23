from __future__ import annotations

from io import BytesIO
from math import isfinite

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from optees.application.contracts.artifact import ArtifactFormat
from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    RenderedArtifact,
)
from optees.application.services.categorical_artifact_visuals import (
    CategoricalVisualDefinition,
)


_PALETTES = {
    "light": {
        "background": "#ffffff",
        "panel": "#f5f7fb",
        "text": "#172033",
        "muted": "#667085",
        "grid": "#d8dee9",
        "accent": "#2563eb",
        "secondary": "#06b6d4",
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
        "inactive": "#526078",
    },
}


class CategoricalChartRenderer:
    renderer_version = "categorical-chart-1"

    def __init__(self, definition: CategoricalVisualDefinition) -> None:
        self._definition = definition

    def render(self, context: ArtifactRenderContext) -> RenderedArtifact:
        labels, first, second, selected, total = _chart_data(
            context,
            self._definition.chart_kind,
        )
        max_items = _max_items(context)
        if self._definition.bounded_categories:
            labels = labels[:max_items]
            first = first[:max_items]
            second = second[:max_items] if second is not None else None
            selected = selected[:max_items]
        if not labels:
            raise ValueError("categorical artifact contains no chartable rows")

        palette = _PALETTES[context.options.theme]
        figure = Figure(
            figsize=(context.options.width / 100, context.options.height / 100),
            dpi=100,
            facecolor=palette["background"],
        )
        FigureCanvasAgg(figure)
        axes = figure.add_subplot(111)
        axes.set_facecolor(palette["panel"])
        positions = list(range(len(labels)))
        if second is None:
            colors = [
                palette["accent"] if is_selected else palette["inactive"]
                for is_selected in selected
            ]
            axes.bar(positions, first, color=colors, width=0.68)
        else:
            left = [position - 0.2 for position in positions]
            right = [position + 0.2 for position in positions]
            axes.bar(left, first, color=palette["accent"], width=0.38, label=_value(context))
            axes.bar(
                right,
                second,
                color=palette["secondary"],
                width=0.38,
                label=_weight_or_capacity(context, self._definition.chart_kind),
            )
            axes.legend(frameon=False, labelcolor=palette["text"])

        axes.set_xticks(positions, labels, rotation=35, ha="right")
        axes.set_title(_title(context, self._definition.chart_kind), color=palette["text"])
        axes.tick_params(colors=palette["muted"])
        axes.grid(axis="y", color=palette["grid"], alpha=0.55)
        for spine in axes.spines.values():
            spine.set_color(palette["grid"])
        displayed = len(labels)
        if displayed < total:
            note = (
                f"Mostrate {displayed} categorie su {total}"
                if context.options.locale == "it"
                else f"Showing {displayed} of {total} categories"
            )
            figure.text(0.99, 0.01, note, ha="right", color=palette["muted"], fontsize=8)
        figure.tight_layout(rect=(0, 0.035, 1, 1))

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
        raise ValueError("categorical renderer received an unsupported format")


def _chart_data(context, kind):
    if kind == "variables":
        rows = _objects(context.envelope.result.get("variables"))
        return (
            [str(row.get("name", "")) for row in rows],
            [_required_number(row.get("value")) for row in rows],
            None,
            [True] * len(rows),
            len(rows),
        )
    if kind == "items":
        rows = _objects(context.problem.get("items"))
        selected_indices = {
            int(value)
            for value in _list(context.envelope.result.get("selected_indices"))
            if isinstance(value, int) and not isinstance(value, bool)
        }
        weights = [
            _number(row.get("weight"))
            for row in rows
        ]
        return (
            [str(row.get("name", "")) for row in rows],
            [_required_number(row.get("value")) for row in rows],
            (
                [_required_number(value) for value in weights]
                if all(value is not None for value in weights)
                else None
            ),
            [index in selected_indices for index in range(len(rows))],
            len(rows),
        )
    if kind == "capacity":
        capacity = _required_number(context.problem.get("capacity"))
        used = _required_number(context.envelope.result.get("total_weight"))
        return (
            ["Used", "Remaining"],
            [used, max(0.0, capacity - used)],
            None,
            [True, False],
            2,
        )
    if kind == "resources":
        rows = _objects(context.envelope.result.get("resources"))
        return (
            [str(row.get("name", "")) for row in rows],
            [_required_number(row.get("used")) for row in rows],
            [_required_number(row.get("capacity")) for row in rows],
            [True] * len(rows),
            len(rows),
        )
    raise ValueError("unsupported categorical chart kind")


def _max_items(context) -> int:
    extra = context.options.extra or {}
    value = extra.get("max_items", 40)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("max_items must be an integer")
    return value


def _title(context, kind: str) -> str:
    titles = {
        "variables": ("Valori delle variabili", "Variable values"),
        "items": ("Valore e peso degli oggetti", "Item value and weight"),
        "capacity": ("Utilizzo della capacita'", "Capacity utilization"),
        "resources": ("Utilizzo delle risorse", "Resource utilization"),
    }
    return titles[kind][0 if context.options.locale == "it" else 1]


def _value(context) -> str:
    return "Valore" if context.options.locale == "it" else "Value"


def _weight_or_capacity(context, kind: str) -> str:
    if kind == "resources":
        return "Capacita'" if context.options.locale == "it" else "Capacity"
    return "Peso" if context.options.locale == "it" else "Weight"


def _objects(value) -> list[dict]:
    return [item for item in _list(value) if isinstance(item, dict)]


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _required_number(value) -> float:
    number = _number(value)
    if number is None:
        raise ValueError("chart data must contain finite numeric values")
    return number


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if isfinite(number) else None
