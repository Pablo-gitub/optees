"""Accessible comparison of per-scenario values against the guaranteed bound.

The widget renders the returned result verbatim. It never recomputes a scenario
value, the guarantee, or which scenarios are binding: those facts arrive already
decided by the application layer and are only drawn here.

Binding scenarios are distinguished by a hatch pattern, a heavier bar outline
and a textual marker in the axis label, so the distinction survives greyscale
printing and colour-vision deficiency.
"""

from __future__ import annotations

import math
from typing import Any, Optional, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from optees.core import charts
from optees.core.string_manager import strings as S

#: Textual marker prefixed to binding scenario labels.
BINDING_MARKER = "◆"  # ◆
BINDING_HATCH = "///"

_MAX_PLOTTED_SCENARIOS = 40


class ScenarioComparisonWidget(QWidget):
    """Horizontal bar comparison of scenario values and the guaranteed bound."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._orientation: str = ""
        self._guaranteed_value: Optional[float] = None
        self._scenario_values: tuple[dict[str, Any], ...] = ()
        self._state = "empty"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.status_label = QLabel()
        self.status_label.setObjectName("scenarioComparisonStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumHeight(48)
        root.addWidget(self.status_label)

        self._matplotlib_available = False
        self._figure = None
        self._canvas = None
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self._figure = Figure(figsize=(6.4, 3.6))
            self._canvas = FigureCanvasQTAgg(self._figure)
            self._canvas.setObjectName("scenarioComparisonCanvas")
            self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._canvas.setMinimumHeight(240)
            root.addWidget(self._canvas, 1)
            self._matplotlib_available = True
        except Exception:
            self._matplotlib_available = False

        self.refresh_strings()
        self._render()

    # -- public API -----------------------------------------------------
    @property
    def visualization_state(self) -> str:
        """Stable diagnostic naming why the chart is or is not drawn."""
        return self._state

    @property
    def plotted_scenario_ids(self) -> tuple[str, ...]:
        """Scenario identifiers currently drawn, in declared order."""
        return tuple(str(entry.get("scenario_id", "")) for entry in self._scenario_values)

    def set_result(self, result: Optional[dict[str, Any]]) -> None:
        """Accept the inner result DTO exactly as the envelope published it."""
        if not result:
            self._orientation = ""
            self._guaranteed_value = None
            self._scenario_values = ()
        else:
            self._orientation = str(result.get("orientation", ""))
            guaranteed = result.get("guaranteed_value")
            self._guaranteed_value = _safe_float(guaranteed)
            raw = result.get("scenario_values") or ()
            self._scenario_values = tuple(entry for entry in raw if isinstance(entry, dict))
        self._render()

    def clear(self) -> None:
        self.set_result(None)

    def refresh_strings(self) -> None:
        self._render()

    def refresh_theme(self) -> None:
        colors = charts.current()
        self.status_label.setStyleSheet(f"color: {colors.text_muted};")
        self._render()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        if self._state == "ready" and self._figure is not None:
            try:
                self._figure.tight_layout()
            except Exception:
                pass
            if self._canvas is not None:
                self._canvas.draw_idle()

    # -- rendering ------------------------------------------------------
    def _render(self) -> None:
        if not self._scenario_values or self._guaranteed_value is None:
            self._set_unavailable("no_candidate", S.t("scenario.solution.comparison.no_candidate"))
            return
        if not self._matplotlib_available or self._figure is None or self._canvas is None:
            self._set_unavailable(
                "matplotlib_unavailable",
                S.t("scenario.solution.comparison.matplotlib_unavailable"),
            )
            return

        self._state = "ready"
        self._canvas.show()
        self.status_label.setText(self._legend_text())
        self._figure.clear()
        axis = self._figure.add_subplot(111)
        self._draw(axis)
        try:
            self._figure.tight_layout()
        except Exception:
            pass
        self._canvas.draw()
        self._apply_accessible_description()

    def _set_unavailable(self, state: str, message: str) -> None:
        self._state = state
        self.status_label.setText(message)
        if self._canvas is not None:
            self._canvas.hide()
        self.setAccessibleDescription(message)

    def _legend_text(self) -> str:
        return S.t(
            "scenario.solution.comparison.legend",
            marker=BINDING_MARKER,
            guarantee=_format_number(self._guaranteed_value),
        )

    def _draw(self, axis) -> None:
        colors = charts.current()
        entries = list(self._scenario_values[:_MAX_PLOTTED_SCENARIOS])
        # Declared order reads top-to-bottom, so the first scenario sits highest.
        positions = list(range(len(entries)))[::-1]
        values = [_safe_float(entry.get("value")) for entry in entries]
        binding_flags = [entry.get("is_binding") for entry in entries]
        if any(value is None for value in values) or any(
            not isinstance(flag, bool) for flag in binding_flags
        ):
            self._set_unavailable(
                "invalid_result",
                S.t("scenario.solution.comparison.invalid_result"),
            )
            return

        for position, value, is_binding in zip(positions, values, binding_flags):
            axis.barh(
                position,
                value,
                height=0.62,
                color=charts.to_mpl(colors.accent if is_binding else colors.text_faint),
                alpha=1.0 if is_binding else 0.55,
                edgecolor=charts.to_mpl(colors.text if is_binding else colors.border_strong),
                linewidth=2.0 if is_binding else 1.0,
                hatch=BINDING_HATCH if is_binding else None,
                zorder=3,
            )

        guarantee = float(self._guaranteed_value or 0.0)
        axis.axvline(
            guarantee,
            color=charts.to_mpl(colors.danger),
            linewidth=1.8,
            linestyle="--",
            zorder=4,
        )
        axis.annotate(
            S.t("scenario.solution.comparison.guarantee_line"),
            xy=(guarantee, 1.0),
            xycoords=("data", "axes fraction"),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color=charts.to_mpl(colors.danger),
        )
        # A zero reference keeps negative values readable against the bound.
        if min(values + [guarantee]) < 0.0 < max(values + [guarantee]):
            axis.axvline(
                0.0,
                color=charts.to_mpl(colors.text_faint),
                linewidth=1.0,
                zorder=2,
            )

        labels = [
            f"{BINDING_MARKER} {entry.get('scenario_id', '')}"
            if is_binding
            else str(entry.get("scenario_id", ""))
            for entry, is_binding in zip(entries, binding_flags)
        ]
        axis.set_yticks(positions)
        axis.set_yticklabels(labels)
        for tick_label, is_binding in zip(axis.get_yticklabels(), binding_flags):
            tick_label.set_fontweight("bold" if is_binding else "normal")

        for position, value in zip(positions, values):
            axis.annotate(
                _format_number(value),
                xy=(value, position),
                xytext=(6 if value >= 0 else -6, 0),
                textcoords="offset points",
                va="center",
                ha="left" if value >= 0 else "right",
                color=charts.to_mpl(colors.text),
                fontsize=9,
            )

        axis.set_xlabel(S.t(f"scenario.solution.comparison.axis.{_axis_key(self._orientation)}"))
        # Extra padding keeps the title clear of the guarantee-line label,
        # which is anchored just above the axes at the bound.
        axis.set_title(S.t("scenario.solution.comparison.title"), pad=22)
        axis.margins(x=0.18)
        charts.style_axes(self._figure, axis)

    def _apply_accessible_description(self) -> None:
        binding = [
            str(entry.get("scenario_id", ""))
            for entry in self._scenario_values
            if entry.get("is_binding")
        ]
        self.setAccessibleDescription(
            S.t(
                "scenario.solution.comparison.accessible_description",
                count=len(self._scenario_values),
                guarantee=_format_number(self._guaranteed_value),
                binding=", ".join(binding) if binding else "-",
            )
        )


def _axis_key(orientation: str) -> str:
    return "loss" if orientation == "minimize_maximum_loss" else "reward"


def _safe_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if math.isfinite(number):
            return number
    return None


def _format_number(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{float(value):.6g}"


def binding_ids(scenario_values: Sequence[dict[str, Any]]) -> tuple[str, ...]:
    """Binding identifiers as published, preserving declared order."""
    return tuple(
        str(entry.get("scenario_id", "")) for entry in scenario_values if entry.get("is_binding")
    )
