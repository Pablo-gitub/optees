"""Educational two-variable view of a convex quadratic programme.

The chart samples the *declared* objective and the *declared* half-spaces to
draw contours and the feasible set. Its grid and plot window are presentation
derivations: they never change the retained problem, the returned candidate, or
the reported mathematical status, all of which come from the application layer.
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from optees.core import charts
from optees.core.string_manager import strings as S
from optees.domain.entities.qp.solution import QPSolution
from optees.domain.models.qp.qp_model import QPModel
from optees.domain.value_objects.lp.relation import Relation

_GRID_SIZE = 121
_PAD_FRACTION = 0.2


class QPContourPlotWidget(QWidget):
    """Contours of ``f(x) = ½ xᵀ Q x + cᵀ x + α`` over the feasible region."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[QPModel] = None
        self._solution: Optional[QPSolution] = None
        self._visualization_state = "no_model"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.status_label = QLabel()
        self.status_label.setObjectName("qpContourStatus")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumHeight(52)
        root.addWidget(self.status_label)

        self._matplotlib_available = False
        self._figure = None
        self._canvas = None
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self._figure = Figure(figsize=(6.2, 4.0))
            self._canvas = FigureCanvasQTAgg(self._figure)
            self._canvas.setObjectName("qpContourCanvas")
            self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._canvas.setMinimumHeight(300)
            root.addWidget(self._canvas, 1)
            self._matplotlib_available = True
        except Exception:
            self._matplotlib_available = False

        self.refresh_strings()
        self.refresh_theme()
        self._render()

    @property
    def visualization_state(self) -> str:
        """Stable diagnostic describing why the chart is or is not drawn."""
        return self._visualization_state

    def set_problem(self, model: Optional[QPModel]) -> None:
        self._model = model
        self._render()

    def set_solution(self, solution: Optional[QPSolution]) -> None:
        self._solution = solution
        self._render()

    def refresh_strings(self) -> None:
        self._render()

    def refresh_theme(self) -> None:
        colors = charts.current()
        self.status_label.setStyleSheet(f"color: {colors.text_muted};")
        self._render()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render(self) -> None:
        model = self._model
        if model is None:
            self._set_unavailable("no_model", S.t("qp.solution.visualization.no_model"))
            return
        if len(model.variables) != 2:
            self._set_unavailable(
                "unsupported_dimension",
                S.t(
                    "qp.solution.visualization.unsupported_dimension",
                    count=len(model.variables),
                ),
            )
            return
        if not self._matplotlib_available or self._figure is None or self._canvas is None:
            self._set_unavailable(
                "matplotlib_unavailable",
                S.t("qp.solution.visualization.matplotlib_unavailable"),
            )
            return
        window = self._plot_window(model)
        if window is None:
            self._set_unavailable("no_window", S.t("qp.solution.visualization.no_window"))
            return

        self._visualization_state = "ready"
        self._canvas.show()
        self.status_label.setText(S.t("qp.solution.visualization.hint"))
        self._figure.clear()
        axis = self._figure.add_subplot(111)
        self._draw(axis, model, window)
        try:
            self._figure.tight_layout()
        except Exception:
            pass
        self._canvas.draw()

    def _set_unavailable(self, state: str, message: str) -> None:
        self._visualization_state = state
        self.status_label.setText(message)
        if self._canvas is not None:
            self._canvas.hide()

    def _draw(self, axis, model: QPModel, window) -> None:
        import numpy as np

        colors = charts.current()
        (x_min, x_max), (y_min, y_max) = window
        x_values = np.linspace(x_min, x_max, _GRID_SIZE)
        y_values = np.linspace(y_min, y_max, _GRID_SIZE)
        x_grid, y_grid = np.meshgrid(x_values, y_values)

        matrix = np.array([list(row) for row in model.objective.quadratic_matrix], dtype=float)
        linear = np.array(list(model.objective.linear_coefs), dtype=float)
        offset = float(model.objective.offset)
        objective = (
            0.5
            * (
                matrix[0][0] * x_grid**2
                + (matrix[0][1] + matrix[1][0]) * x_grid * y_grid
                + matrix[1][1] * y_grid**2
            )
            + linear[0] * x_grid
            + linear[1] * y_grid
            + offset
        )

        filled = axis.contourf(x_grid, y_grid, objective, levels=18, cmap="viridis", alpha=0.85)
        axis.contour(
            x_grid,
            y_grid,
            objective,
            levels=9,
            colors="white",
            alpha=0.25,
            linewidths=0.6,
        )
        self._style_colorbar(self._figure.colorbar(filled, ax=axis))

        feasible = np.ones_like(x_grid, dtype=bool)
        tolerance = 1e-9
        for constraint in model.constraints:
            coefficients = list(constraint.coefs)
            expression = coefficients[0] * x_grid + coefficients[1] * y_grid
            rhs = float(constraint.rhs)
            if constraint.relation is Relation.LE:
                feasible &= expression <= rhs + tolerance
            elif constraint.relation is Relation.GE:
                feasible &= expression >= rhs - tolerance
            else:
                feasible &= np.abs(expression - rhs) <= 1e-6 * max(1.0, abs(rhs))
            if abs(coefficients[1]) > 1e-12:
                axis.plot(
                    x_values,
                    (rhs - coefficients[0] * x_values) / coefficients[1],
                    linewidth=1.3,
                    color=charts.to_mpl(colors.cyan),
                )
            elif abs(coefficients[0]) > 1e-12:
                axis.axvline(rhs / coefficients[0], linewidth=1.3, color=charts.to_mpl(colors.cyan))

        for index, variable in enumerate(model.variables):
            lower, upper = variable.bounds.lb, variable.bounds.ub
            axis_grid = x_grid if index == 0 else y_grid
            if lower is not None:
                feasible &= axis_grid >= float(lower) - tolerance
                _draw_bound_line(axis, index, float(lower), colors)
            if upper is not None:
                feasible &= axis_grid <= float(upper) + tolerance
                _draw_bound_line(axis, index, float(upper), colors)

        if feasible.any():
            axis.contourf(
                x_grid,
                y_grid,
                feasible.astype(int),
                levels=[0.5, 1.5],
                colors=[charts.to_mpl(colors.accent)],
                alpha=0.20,
            )
            axis.contour(
                x_grid,
                y_grid,
                feasible.astype(int),
                levels=[0.5],
                colors=[charts.to_mpl(colors.accent)],
                linewidths=1.6,
            )

        candidate = self._candidate_point(model)
        if candidate is not None:
            axis.scatter(
                [candidate[0]],
                [candidate[1]],
                marker="o",
                s=70,
                color=charts.to_mpl(colors.success),
                edgecolors=charts.to_mpl(colors.on_accent),
                linewidths=1.2,
                zorder=6,
                label=S.t("qp.solution.visualization.candidate"),
            )
            self._style_legend(axis)

        variables = model.variables
        axis.set_xlabel(variables[0].label or variables[0].name)
        axis.set_ylabel(variables[1].label or variables[1].name)
        axis.set_title(S.t("qp.solution.visualization.title"))
        axis.set_xlim(x_min, x_max)
        axis.set_ylim(y_min, y_max)
        charts.style_axes(self._figure, axis)

    # ------------------------------------------------------------------
    # Window derivation
    # ------------------------------------------------------------------
    def _plot_window(self, model: QPModel):
        candidate = self._candidate_point(model)
        window = []
        for index, variable in enumerate(model.variables):
            anchors: list[float] = []
            lower, upper = variable.bounds.lb, variable.bounds.ub
            if lower is not None and math.isfinite(lower):
                anchors.append(float(lower))
            if upper is not None and math.isfinite(upper):
                anchors.append(float(upper))
            if candidate is not None:
                anchors.append(candidate[index])
            for constraint in model.constraints:
                coefficient = constraint.coefs[index]
                if abs(coefficient) > 1e-12:
                    intercept = float(constraint.rhs) / coefficient
                    if math.isfinite(intercept):
                        anchors.append(intercept)
            if not anchors:
                return None
            low, high = min(anchors), max(anchors)
            span = high - low
            pad = span * _PAD_FRACTION if span > 0 else max(1.0, abs(high) * 0.5)
            low, high = low - pad, high + pad
            if lower is not None and math.isfinite(lower):
                low = max(low, float(lower) - pad)
            if upper is not None and math.isfinite(upper):
                high = min(high, float(upper) + pad)
            if not math.isfinite(low) or not math.isfinite(high) or high <= low:
                return None
            window.append((low, high))
        return tuple(window)

    def _candidate_point(self, model: QPModel) -> Optional[tuple[float, float]]:
        if self._solution is None:
            return None
        values = self._solution.values
        point: list[float] = []
        for variable in model.variables:
            value = values.get(variable.name)
            if value is None or not math.isfinite(float(value)):
                return None
            point.append(float(value))
        return (point[0], point[1])

    def _style_colorbar(self, colorbar) -> None:
        colors = charts.current()
        try:
            colorbar.set_label(
                S.t("qp.solution.objective.recomputed"),
                color=charts.to_mpl(colors.text_muted),
            )
            colorbar.ax.tick_params(colors=charts.to_mpl(colors.text_muted))
        except Exception:
            pass

    def _style_legend(self, axis) -> None:
        handles, _labels = axis.get_legend_handles_labels()
        if not handles:
            return
        legend = axis.legend(loc="best")
        colors = charts.current()
        try:
            legend.get_frame().set_facecolor(charts.to_mpl(colors.surface_solid))
            legend.get_frame().set_edgecolor(charts.to_mpl(colors.border_strong))
            for text in legend.get_texts():
                text.set_color(charts.to_mpl(colors.text))
        except Exception:
            pass


def _draw_bound_line(axis, index: int, value: float, colors) -> None:
    style = {"linewidth": 1.0, "linestyle": "--", "color": charts.to_mpl(colors.text_faint)}
    if index == 0:
        axis.axvline(value, **style)
    else:
        axis.axhline(value, **style)
