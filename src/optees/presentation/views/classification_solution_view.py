"""Educational result view for local binary logistic regression."""

from __future__ import annotations

from typing import Mapping, Optional

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
from optees.domain.entities.classification.solution import ClassificationSolution
from optees.domain.models.classification.binary_classification_model import BinaryClassificationModel
from optees.domain.value_objects.classification.classification_status import ClassificationStatus
from optees.presentation.views.lp_view.section import Section


class ClassificationBoundaryPlot(QWidget):
    """Show a decision boundary only when exactly two numeric features exist."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[BinaryClassificationModel] = None
        self._solution: Optional[ClassificationSolution] = None
        self.visualization_state = "no_model"
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)
        self._figure = None
        self._canvas = None
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self._figure = Figure(figsize=(6.4, 4.0))
            self._canvas = FigureCanvasQTAgg(self._figure)
            self._canvas.setObjectName("classificationBoundaryPlotCanvas")
            self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._canvas.setMinimumHeight(300)
            root.addWidget(self._canvas, 1)
        except Exception:
            pass
        self.refresh_theme()
        self._render()

    def set_problem(self, model: Optional[BinaryClassificationModel]) -> None:
        self._model = model
        self._render()

    def set_solution(self, solution: Optional[ClassificationSolution]) -> None:
        self._solution = solution
        self._render()

    def refresh_strings(self) -> None:
        self._render()

    def refresh_theme(self) -> None:
        self.status.setStyleSheet(f"color: {charts.current().text_muted};")
        self._render()

    def _render(self) -> None:
        model, solution = self._model, self._solution
        if (
            model is None
            or solution is None
            or not solution.trained()
            or len(model.dataset.feature_names) != 2
            or solution.intercept is None
            or self._canvas is None
            or self._figure is None
        ):
            self._unavailable()
            return
        feature_x, feature_y = model.dataset.feature_names
        coefficient_x = solution.coefficients.get(feature_x)
        coefficient_y = solution.coefficients.get(feature_y)
        means = solution.extras.get("feature_means")
        scales = solution.extras.get("feature_scales")
        if (
            coefficient_x is None
            or coefficient_y is None
            or not isinstance(means, Mapping)
            or not isinstance(scales, Mapping)
        ):
            self._unavailable()
            return
        try:
            mean_x, mean_y = float(means[feature_x]), float(means[feature_y])
            scale_x, scale_y = float(scales[feature_x]), float(scales[feature_y])
            if scale_x <= 0 or scale_y <= 0:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            self._unavailable()
            return

        import numpy as np

        x_values = np.asarray([row[0] for row in model.dataset.feature_rows], dtype=float)
        y_values = np.asarray([row[1] for row in model.dataset.feature_rows], dtype=float)
        x_margin = max((x_values.max() - x_values.min()) * 0.1, 1.0)
        y_margin = max((y_values.max() - y_values.min()) * 0.1, 1.0)
        grid_x, grid_y = np.meshgrid(
            np.linspace(x_values.min() - x_margin, x_values.max() + x_margin, 140),
            np.linspace(y_values.min() - y_margin, y_values.max() + y_margin, 140),
        )
        logits = solution.intercept + coefficient_x * ((grid_x - mean_x) / scale_x) + coefficient_y * ((grid_y - mean_y) / scale_y)
        probabilities = 1.0 / (1.0 + np.exp(-np.clip(logits, -500, 500)))
        colors = charts.current()
        self._figure.clear()
        axis = self._figure.add_subplot(111)
        axis.contourf(grid_x, grid_y, probabilities, levels=[0, 0.5, 1], alpha=0.16, colors=[charts.to_mpl(colors.warning), charts.to_mpl(colors.accent)])
        axis.contour(grid_x, grid_y, probabilities, levels=[0.5], colors=[charts.to_mpl(colors.text)], linewidths=1.7)
        negative, positive = solution.negative_label, solution.positive_label
        labels = model.dataset.target_values
        for label, color in ((negative, colors.warning), (positive, colors.accent)):
            indices = [index for index, value in enumerate(labels) if value == label]
            axis.scatter(x_values[indices], y_values[indices], label=label, color=charts.to_mpl(color), s=46, edgecolors=charts.to_mpl(colors.surface), linewidths=0.8, zorder=3)
        axis.set_xlabel(feature_x)
        axis.set_ylabel(feature_y)
        axis.legend(title=S.t("classification.solution.boundary.legend"))
        charts.style_axes(self._figure, axis)
        try:
            self._figure.tight_layout()
        except Exception:
            pass
        self.visualization_state = "ready"
        self.status.setText(S.t("classification.solution.boundary.hint"))
        self._canvas.show()
        self._canvas.draw()

    def _unavailable(self) -> None:
        self.visualization_state = "unavailable"
        self.status.setText(S.t("classification.solution.boundary.unavailable"))
        if self._canvas is not None:
            self._canvas.hide()


class ClassificationSolutionView(QWidget):
    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[BinaryClassificationModel] = None
        self._solution: Optional[ClassificationSolution] = None
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
        self.btn_back.setObjectName("classificationSolutionBackButton")
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
        root.addWidget(summary)

        details = Section()
        self.details: dict[str, QLabel] = {}
        for key in ("method", "classes", "train_count", "test_count", "seed", "iterations", "message"):
            row = QHBoxLayout()
            label, value = QLabel(), QLabel("-")
            value.setWordWrap(True)
            row.addWidget(label)
            row.addWidget(value, 1)
            details.body.addLayout(row)
            self.details[f"{key}_label"] = label
            self.details[key] = value
        root.addWidget(details)

        equation = Section()
        self.coefficient_hint = QLabel()
        self.coefficient_hint.setWordWrap(True)
        equation.body.addWidget(self.coefficient_hint)
        self.coefficient_table = _table("classificationCoefficientTable")
        equation.body.addWidget(self.coefficient_table)
        root.addWidget(equation)

        metrics = Section()
        self.metrics_hint = QLabel()
        self.metrics_hint.setWordWrap(True)
        metrics.body.addWidget(self.metrics_hint)
        self.metrics_table = _table("classificationMetricsTable")
        metrics.body.addWidget(self.metrics_table)
        root.addWidget(metrics)

        confusion = Section()
        self.confusion_hint = QLabel()
        self.confusion_hint.setWordWrap(True)
        confusion.body.addWidget(self.confusion_hint)
        self.confusion_table = _table("classificationConfusionTable")
        confusion.body.addWidget(self.confusion_table)
        root.addWidget(confusion)

        predictions = Section()
        self.predictions_hint = QLabel()
        self.predictions_hint.setWordWrap(True)
        predictions.body.addWidget(self.predictions_hint)
        self.predictions_table = _table("classificationPredictionsTable")
        predictions.body.addWidget(self.predictions_table)
        root.addWidget(predictions)

        boundary = Section()
        self.boundary_plot = ClassificationBoundaryPlot()
        boundary.body.addWidget(self.boundary_plot)
        root.addWidget(boundary)
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()
        self._render()

    def set_problem(self, model: BinaryClassificationModel) -> None:
        self._model = model
        self.boundary_plot.set_problem(model)
        self._render()

    def set_solution(self, solution: ClassificationSolution) -> None:
        self._solution = solution
        self.boundary_plot.set_solution(solution)
        self._render()

    def refresh_strings(self) -> None:
        self.title.setText(f"<span style='font-size:22px; font-weight:700'>{S.t('classification.solution.title')}</span>")
        self.btn_back.setText(S.t("classification.solution.back"))
        for key in ("method", "classes", "train_count", "test_count", "seed", "iterations", "message"):
            self.details[f"{key}_label"].setText(S.t(f"classification.solution.details.{key}"))
        self.coefficient_hint.setText(S.t("classification.solution.coefficients.hint"))
        self.metrics_hint.setText(S.t("classification.solution.metrics.hint"))
        self.confusion_hint.setText(S.t("classification.solution.confusion.hint"))
        self.predictions_hint.setText(S.t("classification.solution.predictions.hint"))
        self.boundary_plot.refresh_strings()
        self._render()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.notice.setStyleSheet(f"color: {t.warning};")
        for value in self.details.values():
            value.setStyleSheet(f"color: {t.text_muted};")
        self.boundary_plot.refresh_theme()

    def _render(self) -> None:
        solution = self._solution
        if solution is None:
            self.status.setText(S.t("classification.solution.empty"))
            self.notice.setText("")
            self._clear_tables()
            return
        self.status.setText(S.t("classification.solution.status_line", status=S.t(f"classification.solution.status.{_status_key(solution.status)}")))
        self.notice.setText(S.t("classification.solution.notice"))
        extras = solution.extras
        self.details["method"].setText(str(extras.get("method", "-")))
        self.details["classes"].setText(f"{solution.negative_label} / {solution.positive_label}")
        self.details["train_count"].setText(str(extras.get("train_count", "-")))
        self.details["test_count"].setText(str(extras.get("test_count", "-")))
        self.details["seed"].setText(str(extras.get("random_seed", "-")))
        iterations = extras.get("iterations", "-")
        convergence = extras.get("converged")
        self.details["iterations"].setText(f"{iterations} ({S.t('classification.solution.details.converged') if convergence else S.t('classification.solution.details.iteration_limit')})")
        self.details["message"].setText(str(extras.get("message", "-")))
        self._render_coefficients(solution)
        self._render_metrics(solution)
        self._render_confusion(solution)
        self._render_predictions(solution)

    def _clear_tables(self) -> None:
        for table in (self.coefficient_table, self.metrics_table, self.confusion_table, self.predictions_table):
            table.clear()
            table.setRowCount(0)
            table.setColumnCount(0)

    def _render_coefficients(self, solution: ClassificationSolution) -> None:
        self.coefficient_table.setColumnCount(2)
        self.coefficient_table.setHorizontalHeaderLabels([S.t("classification.solution.coefficients.feature"), S.t("classification.solution.coefficients.coefficient")])
        self.coefficient_table.setRowCount(len(solution.coefficients) + 1)
        self._cell(self.coefficient_table, 0, 0, S.t("classification.solution.coefficients.intercept"))
        self._cell(self.coefficient_table, 0, 1, _number(solution.intercept), Qt.AlignCenter)
        for row, (name, coefficient) in enumerate(solution.coefficients.items(), start=1):
            self._cell(self.coefficient_table, row, 0, name)
            self._cell(self.coefficient_table, row, 1, _number(coefficient), Qt.AlignCenter)

    def _render_metrics(self, solution: ClassificationSolution) -> None:
        headers = [S.t("classification.solution.metrics.partition"), S.t("classification.solution.metrics.accuracy"), S.t("classification.solution.metrics.precision"), S.t("classification.solution.metrics.recall"), S.t("classification.solution.metrics.f1")]
        self.metrics_table.setColumnCount(len(headers))
        self.metrics_table.setHorizontalHeaderLabels(headers)
        self.metrics_table.setRowCount(2)
        for row, (partition, values) in enumerate((("train", solution.train_metrics), ("test", solution.test_metrics))):
            self._cell(self.metrics_table, row, 0, S.t(f"classification.solution.metrics.{partition}"))
            for column, value in enumerate((values.accuracy, values.precision, values.recall, values.f1), start=1):
                self._cell(self.metrics_table, row, column, _percent(value), Qt.AlignCenter)

    def _render_confusion(self, solution: ClassificationSolution) -> None:
        headers = [S.t("classification.solution.confusion.partition"), S.t("classification.solution.confusion.actual"), solution.negative_label, solution.positive_label]
        self.confusion_table.setColumnCount(len(headers))
        self.confusion_table.setHorizontalHeaderLabels(headers)
        self.confusion_table.setRowCount(4)
        for row, (partition, matrix) in enumerate((("train", solution.train_confusion), ("test", solution.test_confusion))):
            base = row * 2
            self._cell(self.confusion_table, base, 0, S.t(f"classification.solution.metrics.{partition}"))
            self._cell(self.confusion_table, base, 1, solution.negative_label)
            self._cell(self.confusion_table, base, 2, str(matrix.true_negative), Qt.AlignCenter)
            self._cell(self.confusion_table, base, 3, str(matrix.false_positive), Qt.AlignCenter)
            self._cell(self.confusion_table, base + 1, 0, S.t(f"classification.solution.metrics.{partition}"))
            self._cell(self.confusion_table, base + 1, 1, solution.positive_label)
            self._cell(self.confusion_table, base + 1, 2, str(matrix.false_negative), Qt.AlignCenter)
            self._cell(self.confusion_table, base + 1, 3, str(matrix.true_positive), Qt.AlignCenter)

    def _render_predictions(self, solution: ClassificationSolution) -> None:
        headers = [S.t("classification.solution.predictions.row"), S.t("classification.solution.predictions.partition"), S.t("classification.solution.predictions.actual"), S.t("classification.solution.predictions.predicted"), S.t("classification.solution.predictions.probability")]
        self.predictions_table.setColumnCount(len(headers))
        self.predictions_table.setHorizontalHeaderLabels(headers)
        self.predictions_table.setRowCount(len(solution.predictions))
        for row, prediction in enumerate(solution.predictions):
            self._cell(self.predictions_table, row, 0, str(prediction.row_index + 1), Qt.AlignCenter)
            self._cell(self.predictions_table, row, 1, S.t(f"classification.solution.metrics.{prediction.partition}"))
            self._cell(self.predictions_table, row, 2, prediction.actual)
            self._cell(self.predictions_table, row, 3, prediction.predicted)
            self._cell(self.predictions_table, row, 4, _percent(prediction.probability_positive), Qt.AlignCenter)

    @staticmethod
    def _cell(table: QTableWidget, row: int, column: int, text: str, alignment: Qt.AlignmentFlag = Qt.AlignLeft) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(int(alignment | Qt.AlignVCenter))
        table.setItem(row, column, item)


def _table(object_name: str) -> QTableWidget:
    table = QTableWidget()
    table.setObjectName(object_name)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.setMinimumHeight(130)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    return table


def _status_key(status: ClassificationStatus) -> str:
    return {
        ClassificationStatus.TRAINED: "trained",
        ClassificationStatus.FAILED: "failed",
        ClassificationStatus.NOT_TRAINED: "not_trained",
    }[status]


def _number(value: object) -> str:
    try:
        return f"{float(value):.6g}"
    except (TypeError, ValueError):
        return "-"


def _percent(value: object) -> str:
    try:
        return f"{100 * float(value):.1f}%"
    except (TypeError, ValueError):
        return "-"
