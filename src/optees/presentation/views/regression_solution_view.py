"""Educational result view for local OLS and Ridge regression."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from optees.core import charts
from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.regression.solution import RegressionSolution
from optees.domain.models.regression.regression_model import RegressionModel
from optees.domain.value_objects.regression.regression_status import RegressionStatus
from optees.presentation.views.lp_view.section import Section


class RegressionFitPlotWidget(QWidget):
    """Draw a truthful fitted line only for one-feature regression models."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[RegressionModel] = None
        self._solution: Optional[RegressionSolution] = None
        self.visualization_state = "no_model"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumHeight(42)
        root.addWidget(self.status_label)
        self._figure = None
        self._canvas = None
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self._figure = Figure(figsize=(6.4, 3.6))
            self._canvas = FigureCanvasQTAgg(self._figure)
            self._canvas.setObjectName("regressionFitPlotCanvas")
            self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._canvas.setMinimumHeight(280)
            root.addWidget(self._canvas, 1)
        except Exception:
            pass
        self.refresh_strings()
        self.refresh_theme()
        self._render()

    def set_problem(self, model: Optional[RegressionModel]) -> None:
        self._model = model
        self._render()

    def set_solution(self, solution: Optional[RegressionSolution]) -> None:
        self._solution = solution
        self._render()

    def refresh_strings(self) -> None:
        self._render()

    def refresh_theme(self) -> None:
        self.status_label.setStyleSheet(f"color: {charts.current().text_muted};")
        self._render()

    def _render(self) -> None:
        model = self._model
        solution = self._solution
        if (
            model is None
            or solution is None
            or not solution.trained()
            or len(model.dataset.feature_names) != 1
            or solution.intercept is None
            or self._canvas is None
            or self._figure is None
        ):
            self.visualization_state = "unavailable"
            self.status_label.setText(S.t("regression.solution.plot.unavailable"))
            if self._canvas is not None:
                self._canvas.hide()
            return
        feature_name = model.dataset.feature_names[0]
        coefficient = solution.coefficients.get(feature_name)
        if coefficient is None:
            self.visualization_state = "unavailable"
            self.status_label.setText(S.t("regression.solution.plot.unavailable"))
            self._canvas.hide()
            return

        predictions = {prediction.row_index: prediction for prediction in solution.predictions}
        if len(predictions) != model.dataset.row_count:
            self.visualization_state = "unavailable"
            self.status_label.setText(S.t("regression.solution.plot.unavailable"))
            self._canvas.hide()
            return
        import numpy as np

        x_values = np.asarray([row[0] for row in model.dataset.feature_rows], dtype=float)
        self._figure.clear()
        axis = self._figure.add_subplot(111)
        colors = charts.current()
        for partition, label, color in (
            ("train", S.t("regression.solution.plot.train"), colors.accent),
            ("test", S.t("regression.solution.plot.test"), colors.warning),
        ):
            indices = [index for index, prediction in predictions.items() if prediction.partition == partition]
            if indices:
                axis.scatter(
                    x_values[indices],
                    [predictions[index].actual for index in indices],
                    label=label,
                    color=charts.to_mpl(color),
                    s=42,
                    zorder=3,
                )
        line_x = np.linspace(float(x_values.min()), float(x_values.max()), 80)
        line_y = solution.intercept + coefficient * line_x
        axis.plot(
            line_x,
            line_y,
            label=S.t("regression.solution.plot.line"),
            color=charts.to_mpl(colors.text),
            linewidth=2.2,
            zorder=2,
        )
        axis.set_xlabel(feature_name)
        axis.set_ylabel(model.dataset.target_name)
        axis.legend()
        charts.style_axes(self._figure, axis)
        try:
            self._figure.tight_layout()
        except Exception:
            pass
        self.visualization_state = "ready"
        self.status_label.setText(S.t("regression.solution.plot.hint"))
        self._canvas.show()
        self._canvas.draw()


class RegressionSolutionView(QWidget):
    """Show learned coefficients and split-aware regression diagnostics."""

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[RegressionModel] = None
        self._solution: Optional[RegressionSolution] = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        page = QWidget()
        scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        self.title = QLabel()
        self.title.setTextFormat(Qt.RichText)
        header.addWidget(self.title, 1)
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("regressionSolutionBackButton")
        self.btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(self.btn_back)
        root.addLayout(header)

        summary = Section()
        self.status = QLabel()
        self.status.setTextFormat(Qt.RichText)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        summary.body.addWidget(self.status)
        summary.body.addWidget(self.notice)
        self.summary_section = summary
        root.addWidget(summary)

        details = Section()
        self.detail_labels: dict[str, QLabel] = {}
        for key in ("method", "train_count", "test_count", "seed", "intercept", "message"):
            row = QHBoxLayout()
            name = QLabel()
            value = QLabel("-")
            value.setWordWrap(True)
            row.addWidget(name)
            row.addWidget(value, 1)
            details.body.addLayout(row)
            self.detail_labels[f"{key}_label"] = name
            self.detail_labels[key] = value
        self.details_section = details
        root.addWidget(details)

        coefficients = Section()
        self.coefficient_hint = QLabel()
        self.coefficient_hint.setWordWrap(True)
        coefficients.body.addWidget(self.coefficient_hint)
        self.coefficient_table = _make_table("regressionCoefficientTable")
        coefficients.body.addWidget(self.coefficient_table)
        self.coefficients_section = coefficients
        root.addWidget(coefficients)

        metrics = Section()
        self.metrics_hint = QLabel()
        self.metrics_hint.setWordWrap(True)
        metrics.body.addWidget(self.metrics_hint)
        self.metrics_table = _make_table("regressionMetricsTable")
        metrics.body.addWidget(self.metrics_table)
        self.metrics_section = metrics
        root.addWidget(metrics)

        predictions = Section()
        self.predictions_hint = QLabel()
        self.predictions_hint.setWordWrap(True)
        predictions.body.addWidget(self.predictions_hint)
        self.predictions_table = _make_table("regressionPredictionsTable")
        predictions.body.addWidget(self.predictions_table)
        self.predictions_section = predictions
        root.addWidget(predictions)

        plot = Section()
        self.fit_plot = RegressionFitPlotWidget()
        plot.body.addWidget(self.fit_plot)
        self.plot_section = plot
        root.addWidget(plot)
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()
        self._render_solution()

    def set_problem(self, model: RegressionModel) -> None:
        self._model = model
        self.fit_plot.set_problem(model)
        self._render_solution()

    def set_solution(self, solution: RegressionSolution) -> None:
        self._solution = solution
        self.fit_plot.set_solution(solution)
        self._render_solution()

    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:24px; font-weight:700'>{S.t('regression.solution.title')}</span>"
        )
        self.btn_back.setText(S.t("regression.solution.back"))
        self.summary_section.set_title(S.t("regression.solution.summary.section"))
        self.notice.setText(S.t("regression.solution.notice"))
        self.details_section.set_title(S.t("regression.solution.details.section"))
        for key in ("method", "train_count", "test_count", "seed", "intercept", "message"):
            self.detail_labels[f"{key}_label"].setText(S.t(f"regression.solution.details.{key}"))
        self.coefficients_section.set_title(S.t("regression.solution.coefficients.section"))
        self.coefficient_hint.setText(S.t("regression.solution.coefficients.hint"))
        self.metrics_section.set_title(S.t("regression.solution.metrics.section"))
        self.metrics_hint.setText(S.t("regression.solution.metrics.hint"))
        self.predictions_section.set_title(S.t("regression.solution.predictions.section"))
        self.predictions_hint.setText(S.t("regression.solution.predictions.hint"))
        self.plot_section.set_title(S.t("regression.solution.plot.section"))
        self.fit_plot.refresh_strings()
        self._render_solution()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.status.setStyleSheet(f"color: {t.text}; font-weight: 600;")
        self.notice.setStyleSheet(f"color: {t.warning};")
        for key, label in self.detail_labels.items():
            label.setStyleSheet(f"color: {t.text if key.endswith('_label') else t.text_muted};")
        for label in (self.coefficient_hint, self.metrics_hint, self.predictions_hint):
            label.setStyleSheet(f"color: {t.text_muted};")
        self.fit_plot.refresh_theme()

    def _render_solution(self) -> None:
        solution = self._solution
        if solution is None:
            self.status.setText(S.t("regression.solution.empty"))
            for key in ("method", "train_count", "test_count", "seed", "intercept", "message"):
                self.detail_labels[key].setText("-")
            self._set_coefficients({})
            self._set_metrics(None)
            self._set_predictions(())
            return

        self.status.setText(
            S.t("regression.solution.status_line", status=S.t(_status_key(solution.status)))
        )
        extras = solution.extras
        self.detail_labels["method"].setText(str(extras.get("method") or "-"))
        self.detail_labels["train_count"].setText(_format_number(extras.get("train_count")))
        self.detail_labels["test_count"].setText(_format_number(extras.get("test_count")))
        self.detail_labels["seed"].setText(_format_number(extras.get("random_seed")))
        self.detail_labels["intercept"].setText(_format_number(solution.intercept))
        self.detail_labels["message"].setText(str(extras.get("message") or "-"))
        self._set_coefficients(solution.coefficients)
        self._set_metrics(solution)
        self._set_predictions(solution.predictions)

    def _set_coefficients(self, coefficients: dict[str, float]) -> None:
        self.coefficient_table.setColumnCount(2)
        self.coefficient_table.setHorizontalHeaderLabels(
            [
                S.t("regression.solution.coefficients.feature"),
                S.t("regression.solution.coefficients.coefficient"),
            ]
        )
        self.coefficient_table.setRowCount(len(coefficients))
        for row, (feature, coefficient) in enumerate(coefficients.items()):
            self.coefficient_table.setItem(row, 0, QTableWidgetItem(feature))
            item = QTableWidgetItem(_format_number(coefficient))
            item.setTextAlignment(Qt.AlignCenter)
            self.coefficient_table.setItem(row, 1, item)

    def _set_metrics(self, solution: Optional[RegressionSolution]) -> None:
        self.metrics_table.setColumnCount(5)
        self.metrics_table.setHorizontalHeaderLabels(
            [
                S.t("regression.solution.metrics.partition"),
                S.t("regression.solution.metrics.mae"),
                S.t("regression.solution.metrics.mse"),
                S.t("regression.solution.metrics.rmse"),
                S.t("regression.solution.metrics.r_squared"),
            ]
        )
        rows = () if solution is None else (
            (S.t("regression.solution.metrics.train"), solution.train_metrics),
            (S.t("regression.solution.metrics.test"), solution.test_metrics),
        )
        self.metrics_table.setRowCount(len(rows))
        for row, (partition, metrics) in enumerate(rows):
            self.metrics_table.setItem(row, 0, QTableWidgetItem(partition))
            for column, value in enumerate(
                (metrics.mae, metrics.mse, metrics.rmse, metrics.r_squared),
                start=1,
            ):
                item = QTableWidgetItem(_format_number(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.metrics_table.setItem(row, column, item)

    def _set_predictions(self, predictions: tuple[object, ...]) -> None:
        self.predictions_table.setColumnCount(5)
        self.predictions_table.setHorizontalHeaderLabels(
            [
                S.t("regression.solution.predictions.row"),
                S.t("regression.solution.predictions.partition"),
                S.t("regression.solution.predictions.actual"),
                S.t("regression.solution.predictions.predicted"),
                S.t("regression.solution.predictions.residual"),
            ]
        )
        self.predictions_table.setRowCount(len(predictions))
        for row, prediction in enumerate(predictions):
            values = (
                str(prediction.row_index + 1),
                S.t(f"regression.solution.metrics.{prediction.partition}"),
                _format_number(prediction.actual),
                _format_number(prediction.predicted),
                _format_number(prediction.residual),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                self.predictions_table.setItem(row, column, item)


def _make_table(object_name: str) -> QTableWidget:
    table = QTableWidget()
    table.setObjectName(object_name)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
    table.horizontalHeader().setStretchLastSection(True)
    return table


def _status_key(status: RegressionStatus) -> str:
    return {
        RegressionStatus.TRAINED: "regression.solution.status.trained",
        RegressionStatus.FAILED: "regression.solution.status.failed",
        RegressionStatus.NOT_TRAINED: "regression.solution.status.not_trained",
    }[status]


def _format_number(value: object) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.10g}"
    except (TypeError, ValueError):
        return "-"
