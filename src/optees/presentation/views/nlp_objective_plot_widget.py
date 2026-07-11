"""Educational objective-landscape charts for small continuous NLP models."""

from __future__ import annotations

import math
from typing import Mapping, Optional

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from optees.core import charts
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.nlp.solution import NLPSolution
from optees.domain.models.nlp.nlp_model import NLPModel


_GRID_SIZE = 61


class NLPObjectivePlotWidget(QWidget):
    """Plot finite, low-dimensional objective landscapes without overclaiming.

    Two decision variables can be displayed as a contour map or as the 3D
    surface ``f(x1, x2)``. With three decision variables the objective lives in
    four dimensions, therefore the widget renders an honest 2D slice through
    the local candidate (or the initial point if no candidate is available).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[NLPModel] = None
        self._solution: Optional[NLPSolution] = None
        self._visualization_state = "no_model"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        self.mode_label = QLabel()
        self.mode_combo = QComboBox()
        self.mode_combo.setObjectName("nlpObjectivePlotMode")
        self.mode_combo.currentIndexChanged.connect(self._render)
        self.slice_label = QLabel()
        self.slice_combo = QComboBox()
        self.slice_combo.setObjectName("nlpObjectivePlotSliceVariable")
        self.slice_combo.currentIndexChanged.connect(self._render)
        controls.addWidget(self.mode_label)
        controls.addWidget(self.mode_combo)
        controls.addWidget(self.slice_label)
        controls.addWidget(self.slice_combo)
        controls.addStretch(1)
        root.addLayout(controls)

        self.status_label = QLabel()
        self.status_label.setObjectName("nlpObjectivePlotStatus")
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

            self._figure = Figure(figsize=(6.2, 3.6))
            self._canvas = FigureCanvasQTAgg(self._figure)
            self._canvas.setObjectName("nlpObjectivePlotCanvas")
            self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._canvas.setMinimumHeight(280)
            root.addWidget(self._canvas, 1)
            self._matplotlib_available = True
        except Exception:
            self._matplotlib_available = False

        self.refresh_strings()
        self.refresh_theme()
        self._render()

    @property
    def visualization_state(self) -> str:
        """Small stable diagnostic for presentation tests and callers."""
        return self._visualization_state

    def set_problem(self, model: Optional[NLPModel]) -> None:
        self._model = model
        self._populate_slice_variables()
        self._render()

    def set_solution(self, solution: Optional[NLPSolution]) -> None:
        self._solution = solution
        self._render()

    def refresh_strings(self) -> None:
        current_mode = self.mode_combo.currentData()
        blocker = QSignalBlocker(self.mode_combo)
        self.mode_combo.clear()
        self.mode_combo.addItem(S.t("nlp.solution.visualization.contour"), "contour")
        self.mode_combo.addItem(S.t("nlp.solution.visualization.surface"), "surface")
        index = self.mode_combo.findData(current_mode)
        self.mode_combo.setCurrentIndex(index if index >= 0 else 0)
        del blocker
        self.mode_label.setText(S.t("nlp.solution.visualization.mode_label"))
        self.slice_label.setText(S.t("nlp.solution.visualization.slice_label"))
        self._populate_slice_variables()
        self._render()

    def refresh_theme(self) -> None:
        colors = charts.current()
        self.mode_label.setStyleSheet(f"color: {colors.text_muted};")
        self.slice_label.setStyleSheet(f"color: {colors.text_muted};")
        self.status_label.setStyleSheet(f"color: {colors.text_muted};")
        self._render()

    def _populate_slice_variables(self) -> None:
        current_data = self.slice_combo.currentData()
        blocker = QSignalBlocker(self.slice_combo)
        self.slice_combo.clear()
        if self._model is not None:
            for index, variable in enumerate(self._model.variables):
                self.slice_combo.addItem(_variable_label(variable.name, variable.label), index)
        index = self.slice_combo.findData(current_data)
        self.slice_combo.setCurrentIndex(index if index >= 0 else 0)
        del blocker

    def _render(self) -> None:
        model = self._model
        if model is None:
            self._set_unavailable("no_model", S.t("nlp.solution.visualization.no_model"))
            return

        dimension = len(model.variables)
        if dimension not in (2, 3):
            self._set_unavailable(
                "unsupported_dimension",
                S.t("nlp.solution.visualization.unsupported_dimension"),
            )
            return
        if not _has_finite_plot_bounds(model):
            self._set_unavailable(
                "bounds_required",
                S.t("nlp.solution.visualization.bounds_required"),
            )
            return
        if not self._matplotlib_available or self._figure is None or self._canvas is None:
            self._set_unavailable(
                "matplotlib_unavailable",
                S.t("nlp.solution.visualization.matplotlib_unavailable"),
            )
            return

        self._visualization_state = "ready"
        self._canvas.show()
        self.mode_label.setVisible(dimension == 2)
        self.mode_combo.setVisible(dimension == 2)
        self.slice_label.setVisible(dimension == 3)
        self.slice_combo.setVisible(dimension == 3)
        self.status_label.setText(S.t("nlp.solution.visualization.hint"))

        self._figure.clear()
        if dimension == 2:
            if self.mode_combo.currentData() == "surface":
                axis = self._figure.add_subplot(111, projection="3d")
                self._draw_surface(axis)
            else:
                axis = self._figure.add_subplot(111)
                self._draw_contour(axis, (0, 1), {})
        else:
            fixed_index = self._selected_slice_index()
            fixed_value = self._slice_value(fixed_index)
            varying_indices = tuple(index for index in range(3) if index != fixed_index)
            axis = self._figure.add_subplot(111)
            self._draw_contour(axis, varying_indices, {fixed_index: fixed_value})
            variable = model.variables[fixed_index]
            axis.set_title(
                S.t(
                    "nlp.solution.visualization.slice_title",
                    variable=_variable_label(variable.name, variable.label),
                    value=_format_number(fixed_value),
                )
            )

        try:
            self._figure.tight_layout()
        except Exception:
            pass
        self._canvas.draw()

    def _set_unavailable(self, state: str, message: str) -> None:
        self._visualization_state = state
        self.mode_label.hide()
        self.mode_combo.hide()
        self.slice_label.hide()
        self.slice_combo.hide()
        self.status_label.setText(message)
        if self._canvas is not None:
            self._canvas.hide()

    def _draw_contour(
        self,
        axis: object,
        varying_indices: tuple[int, int],
        fixed_values: Mapping[int, float],
    ) -> None:
        import numpy as np

        assert self._model is not None
        x_values, y_values, x_grid, y_grid, objective = self._sample_grid(
            varying_indices,
            fixed_values,
        )
        masked_objective = np.ma.masked_invalid(objective)
        if masked_objective.count() == 0:
            self._draw_no_finite_samples(axis)
            return

        filled = axis.contourf(x_grid, y_grid, masked_objective, levels=18, cmap="viridis")
        axis.contour(x_grid, y_grid, masked_objective, levels=9, colors="white", alpha=0.22, linewidths=0.6)
        self._style_colorbar(self._figure.colorbar(filled, ax=axis))
        self._style_2d_axis(axis, varying_indices)
        if not fixed_values:
            axis.set_title(S.t("nlp.solution.visualization.contour_title"))
        self._add_markers(axis, varying_indices, fixed_values)

    def _draw_surface(self, axis: object) -> None:
        import numpy as np

        assert self._model is not None
        _x_values, _y_values, x_grid, y_grid, objective = self._sample_grid((0, 1), {})
        if np.isfinite(objective).sum() == 0:
            self._draw_no_finite_samples(axis)
            return

        surface = axis.plot_surface(
            x_grid,
            y_grid,
            objective,
            cmap="viridis",
            edgecolor="none",
            antialiased=True,
            alpha=0.92,
        )
        self._style_colorbar(self._figure.colorbar(surface, ax=axis, shrink=0.72))
        variables = self._model.variables
        axis.set_xlabel(_variable_label(variables[0].name, variables[0].label))
        axis.set_ylabel(_variable_label(variables[1].name, variables[1].label))
        axis.set_zlabel(S.t("nlp.solution.visualization.objective_axis"))
        axis.set_title(S.t("nlp.solution.visualization.surface_title"))
        charts.style_axes(self._figure, axis)
        self._add_markers(axis, (0, 1), {}, is_surface=True)

    def _sample_grid(
        self,
        varying_indices: tuple[int, int],
        fixed_values: Mapping[int, float],
    ) -> tuple[object, object, object, object, object]:
        import numpy as np

        assert self._model is not None
        x_variable = self._model.variables[varying_indices[0]]
        y_variable = self._model.variables[varying_indices[1]]
        assert x_variable.lower_bound is not None and x_variable.upper_bound is not None
        assert y_variable.lower_bound is not None and y_variable.upper_bound is not None
        x_values = np.linspace(x_variable.lower_bound, x_variable.upper_bound, _GRID_SIZE)
        y_values = np.linspace(y_variable.lower_bound, y_variable.upper_bound, _GRID_SIZE)
        x_grid, y_grid = np.meshgrid(x_values, y_values)
        objective = np.full(x_grid.shape, np.nan, dtype=float)
        base_values = {
            variable.name: variable.initial_value for variable in self._model.variables
        }
        base_values.update(
            {
                self._model.variables[index].name: value
                for index, value in fixed_values.items()
            }
        )

        for row, y_value in enumerate(y_values):
            for column, x_value in enumerate(x_values):
                values = dict(base_values)
                values[x_variable.name] = float(x_value)
                values[y_variable.name] = float(y_value)
                try:
                    objective[row, column] = self._model.evaluate_objective(values)
                except (ArithmeticError, OverflowError, ValueError):
                    continue
        return x_values, y_values, x_grid, y_grid, objective

    def _style_2d_axis(self, axis: object, varying_indices: tuple[int, int]) -> None:
        assert self._model is not None
        x_variable = self._model.variables[varying_indices[0]]
        y_variable = self._model.variables[varying_indices[1]]
        axis.set_xlabel(_variable_label(x_variable.name, x_variable.label))
        axis.set_ylabel(_variable_label(y_variable.name, y_variable.label))
        charts.style_axes(self._figure, axis)

    def _style_colorbar(self, colorbar: object) -> None:
        colors = charts.current()
        try:
            colorbar.set_label(S.t("nlp.solution.visualization.objective_axis"), color=charts.to_mpl(colors.text_muted))
            colorbar.ax.tick_params(colors=charts.to_mpl(colors.text_muted))
        except Exception:
            pass

    def _add_markers(
        self,
        axis: object,
        varying_indices: tuple[int, int],
        fixed_values: Mapping[int, float],
        *,
        is_surface: bool = False,
    ) -> None:
        initial = self._initial_point()
        candidate = self._candidate_point()
        marker_data = (
            (initial, "x", charts.to_mpl(charts.current().warning), S.t("nlp.solution.visualization.initial_point")),
            (candidate, "o", charts.to_mpl(charts.current().success), S.t("nlp.solution.visualization.local_candidate")),
        )
        for point, marker, color, label in marker_data:
            if point is None or not _lies_on_slice(point, fixed_values):
                continue
            x_value = point[varying_indices[0]]
            y_value = point[varying_indices[1]]
            if is_surface:
                z_value = self._evaluate_point(point)
                if z_value is None:
                    continue
                axis.scatter([x_value], [y_value], [z_value], marker=marker, color=color, s=48, label=label)
            else:
                axis.scatter([x_value], [y_value], marker=marker, color=color, s=54, label=label, zorder=5)
        self._style_legend(axis)

    def _draw_no_finite_samples(self, axis: object) -> None:
        axis.text(
            0.5,
            0.5,
            S.t("nlp.solution.visualization.no_finite_samples"),
            ha="center",
            va="center",
            wrap=True,
            transform=axis.transAxes,
            color=charts.to_mpl(charts.current().text_muted),
        )
        charts.style_axes(self._figure, axis, grid=False)

    def _style_legend(self, axis: object) -> None:
        handles, labels = axis.get_legend_handles_labels()
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

    def _selected_slice_index(self) -> int:
        selected = self.slice_combo.currentData()
        try:
            return int(selected)
        except (TypeError, ValueError):
            return 0

    def _slice_value(self, index: int) -> float:
        candidate = self._candidate_point()
        if candidate is not None:
            return candidate[index]
        return self._initial_point()[index]  # type: ignore[index]

    def _initial_point(self) -> tuple[float, ...]:
        assert self._model is not None
        return self._model.initial_point()

    def _candidate_point(self) -> Optional[tuple[float, ...]]:
        if self._model is None or self._solution is None:
            return None
        values = self._solution.values
        candidate: list[float] = []
        for variable in self._model.variables:
            value = values.get(variable.name)
            if value is None or not math.isfinite(float(value)):
                return None
            candidate.append(float(value))
        return tuple(candidate)

    def _evaluate_point(self, point: tuple[float, ...]) -> Optional[float]:
        assert self._model is not None
        try:
            return self._model.evaluate_objective(
                {variable.name: point[index] for index, variable in enumerate(self._model.variables)}
            )
        except (ArithmeticError, OverflowError, ValueError):
            return None


def _has_finite_plot_bounds(model: NLPModel) -> bool:
    for variable in model.variables:
        lower = variable.lower_bound
        upper = variable.upper_bound
        if lower is None or upper is None:
            return False
        if not math.isfinite(lower) or not math.isfinite(upper) or lower >= upper:
            return False
    return True


def _lies_on_slice(point: tuple[float, ...], fixed_values: Mapping[int, float]) -> bool:
    return all(math.isclose(point[index], value, rel_tol=1e-9, abs_tol=1e-9) for index, value in fixed_values.items())


def _variable_label(name: str, label: str) -> str:
    return label or name


def _format_number(value: float) -> str:
    return f"{value:.6g}"
