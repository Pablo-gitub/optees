"""Educational result view for univariate time-series forecasting."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from optees.application.codecs.forecasting_result_codec import ForecastingResultCodec
from optees.application.contracts.solution_validation import SolutionValidation
from optees.application.validation.forecasting_solution_validator import (
    ForecastingIndependentSolutionValidator,
)
from optees.core import charts
from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.forecasting import (
    ForecastPoint,
    ForecastSegment,
    ForecastingSolution,
)
from optees.domain.models.forecasting import ForecastingModel
from optees.presentation.views.lp_view.section import Section

_MAX_PLOT_POINTS = 500


class ForecastingChartWidget(QWidget):
    """Plot actual, fitted, evaluated and future values with bounded rendering."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[ForecastingModel] = None
        self._solution: Optional[ForecastingSolution] = None
        self.visualization_state = "empty"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status_label)
        self._figure = None
        self._canvas = None
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self._figure = Figure(figsize=(7.2, 4.0))
            self._canvas = FigureCanvasQTAgg(self._figure)
            self._canvas.setObjectName("forecastingChartCanvas")
            self._canvas.setMinimumHeight(320)
            self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            root.addWidget(self._canvas, 1)
        except Exception:
            pass

    def set_problem(self, model: ForecastingModel) -> None:
        self._model = model
        self._render()

    def set_solution(self, solution: ForecastingSolution) -> None:
        self._solution = solution
        self._render()

    def refresh_strings(self) -> None:
        self._render()

    def refresh_theme(self) -> None:
        self.status_label.setStyleSheet(f"color: {charts.current().text_muted};")
        self._render()

    def _render(self) -> None:
        if (
            self._model is None
            or self._solution is None
            or self._canvas is None
            or self._figure is None
        ):
            self.visualization_state = "unavailable"
            self.status_label.setText(S.t("forecasting.solution.chart.unavailable"))
            if self._canvas is not None:
                self._canvas.hide()
            return

        solution = self._solution
        actual = _sample(tuple(self._model.observations), _MAX_PLOT_POINTS)
        fitted = tuple(point for point in solution.points if point.segment is ForecastSegment.FITTED)
        future = tuple(point for point in solution.points if point.segment is ForecastSegment.FUTURE)
        holdout = tuple(point for fold in solution.evaluation_folds for point in fold.points)

        self._figure.clear()
        axis = self._figure.add_subplot(111)
        colors = charts.current()
        if actual:
            axis.plot(
                [item.timestamp for item in actual],
                [item.value for item in actual],
                color=charts.to_mpl(colors.text),
                linewidth=1.7,
                label=S.t("forecasting.solution.chart.actual"),
            )
        if fitted:
            axis.plot(
                [item.timestamp for item in fitted],
                [item.predicted for item in fitted],
                color=charts.to_mpl(colors.accent),
                linewidth=1.5,
                label=S.t("forecasting.solution.chart.fitted"),
            )
        if holdout:
            axis.scatter(
                [item.timestamp for item in holdout],
                [item.predicted for item in holdout],
                color=charts.to_mpl(colors.warning),
                s=34,
                marker="o",
                label=S.t("forecasting.solution.chart.holdout"),
                zorder=4,
            )
        if future:
            axis.plot(
                [item.timestamp for item in future],
                [item.predicted for item in future],
                color=charts.to_mpl(colors.success),
                linewidth=2.2,
                marker="o",
                label=S.t("forecasting.solution.chart.future"),
            )
            intervals = [point for point in future if point.interval is not None]
            if len(intervals) == len(future):
                coverage = intervals[0].interval.coverage  # type: ignore[union-attr]
                axis.fill_between(
                    [item.timestamp for item in intervals],
                    [item.interval.lower for item in intervals],  # type: ignore[union-attr]
                    [item.interval.upper for item in intervals],  # type: ignore[union-attr]
                    color=charts.to_mpl(colors.success),
                    alpha=0.18,
                    label=S.t(
                        "forecasting.solution.chart.interval",
                        coverage=f"{coverage:.0%}",
                    ),
                )
        axis.axvline(
            solution.origin,
            color=charts.to_mpl(colors.text_muted),
            linestyle="--",
            linewidth=1.0,
            label=S.t("forecasting.solution.chart.origin"),
        )
        axis.set_xlabel(S.t("forecasting.solution.chart.time"))
        axis.set_ylabel(self._model.target_name)
        axis.legend(loc="best")
        charts.style_axes(self._figure, axis)
        try:
            self._figure.autofmt_xdate()
            self._figure.tight_layout()
        except Exception:
            pass
        sampled = len(self._model.observations) > len(actual)
        self.status_label.setText(
            S.t(
                "forecasting.solution.chart.sampled"
                if sampled
                else "forecasting.solution.chart.hint",
                count=len(actual),
            )
        )
        self.visualization_state = "ready"
        self._canvas.show()
        self._canvas.draw()


class ForecastingSolutionView(QWidget):
    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[ForecastingModel] = None
        self._solution: Optional[ForecastingSolution] = None
        self._validation: Optional[SolutionValidation] = None

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
        self.btn_back.setObjectName("forecastingSolutionBackButton")
        self.btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(self.btn_back)
        root.addLayout(header)

        self.summary_section = Section()
        self.status = QLabel()
        self.status.setTextFormat(Qt.RichText)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        self.summary_section.body.addWidget(self.status)
        self.summary_section.body.addWidget(self.notice)
        root.addWidget(self.summary_section)

        self.details_section = Section()
        self.detail_labels: dict[str, QLabel] = {}
        for key in ("method", "horizon", "origin", "evaluation", "validation"):
            row = QHBoxLayout()
            name = QLabel()
            value = QLabel("-")
            value.setWordWrap(True)
            row.addWidget(name)
            row.addWidget(value, 1)
            self.details_section.body.addLayout(row)
            self.detail_labels[f"{key}_label"] = name
            self.detail_labels[key] = value
        root.addWidget(self.details_section)

        self.metrics_section, self.metrics_table = _table_section("forecastingMetricsTable")
        root.addWidget(self.metrics_section)
        self.parameters_section, self.parameters_table = _table_section(
            "forecastingParametersTable"
        )
        root.addWidget(self.parameters_section)
        self.points_section, self.points_table = _table_section("forecastingPointsTable")
        root.addWidget(self.points_section)
        self.diagnostics_section, self.diagnostics_table = _table_section(
            "forecastingDiagnosticsTable"
        )
        root.addWidget(self.diagnostics_section)

        self.chart_section = Section()
        self.chart = ForecastingChartWidget()
        self.chart_section.body.addWidget(self.chart)
        root.addWidget(self.chart_section)
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()
        self._render()

    def set_problem(self, model: ForecastingModel) -> None:
        self._model = model
        self.chart.set_problem(model)
        self._update_validation()
        self._render()

    def set_solution(self, solution: ForecastingSolution) -> None:
        self._solution = solution
        self.chart.set_solution(solution)
        self._update_validation()
        self._render()

    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:24px; font-weight:700'>"
            f"{S.t('forecasting.solution.title')}</span>"
        )
        self.btn_back.setText(S.t("forecasting.solution.back"))
        self.summary_section.set_title(S.t("forecasting.solution.summary.section"))
        self.notice.setText(S.t("forecasting.solution.notice"))
        self.details_section.set_title(S.t("forecasting.solution.details.section"))
        for key in ("method", "horizon", "origin", "evaluation", "validation"):
            self.detail_labels[f"{key}_label"].setText(
                S.t(f"forecasting.solution.details.{key}")
            )
        self.metrics_section.set_title(S.t("forecasting.solution.metrics.section"))
        self.parameters_section.set_title(S.t("forecasting.solution.parameters.section"))
        self.points_section.set_title(S.t("forecasting.solution.points.section"))
        self.diagnostics_section.set_title(S.t("forecasting.solution.diagnostics.section"))
        self.chart_section.set_title(S.t("forecasting.solution.chart.section"))
        self.chart.refresh_strings()
        self._render()

    def refresh_theme(self) -> None:
        current = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {current.text};")
        self.status.setStyleSheet(f"color: {current.text}; font-weight: 600;")
        self.notice.setStyleSheet(f"color: {current.warning};")
        for key, label in self.detail_labels.items():
            label.setStyleSheet(
                f"color: {current.text if key.endswith('_label') else current.text_muted};"
            )
        self.chart.refresh_theme()

    def _update_validation(self) -> None:
        if self._model is None or self._solution is None:
            self._validation = None
            return
        serialized = ForecastingResultCodec().serialize(self._solution)
        self._validation = ForecastingIndependentSolutionValidator()(
            self._model,
            serialized,
        )

    def _render(self) -> None:
        solution = self._solution
        model = self._model
        if solution is None:
            self.status.setText(S.t("forecasting.solution.empty"))
            for key in ("method", "horizon", "origin", "evaluation", "validation"):
                self.detail_labels[key].setText("-")
            self._set_metrics(None)
            self._set_parameters(())
            self._set_points(())
            self._set_diagnostics(())
            return

        self.status.setText(
            S.t(
                "forecasting.solution.status_line",
                status=S.t(f"forecasting.solution.status.{solution.status.value}"),
            )
        )
        self.detail_labels["method"].setText(
            S.t(f"forecasting.method.name.{solution.method.value}")
        )
        horizon = model.horizon if model is not None else sum(
            point.segment is ForecastSegment.FUTURE for point in solution.points
        )
        self.detail_labels["horizon"].setText(str(horizon))
        self.detail_labels["origin"].setText(solution.origin.isoformat(sep=" "))
        self.detail_labels["evaluation"].setText(
            S.t(f"forecasting.solution.evaluation.{solution.evaluation_status.value}")
        )
        self.detail_labels["validation"].setText(
            "-"
            if self._validation is None
            else S.t(f"forecasting.solution.validation.{self._validation.status.value}")
        )
        self._set_metrics(solution)
        self._set_parameters(solution.parameters)
        self._set_points(solution.points)
        self._set_diagnostics(solution.diagnostics)

    def _set_metrics(self, solution: Optional[ForecastingSolution]) -> None:
        self.metrics_table.setColumnCount(5)
        self.metrics_table.setHorizontalHeaderLabels(
            [
                S.t("forecasting.solution.metrics.scope"),
                "MAE",
                "RMSE",
                "MAPE",
                "MASE",
            ]
        )
        rows: list[tuple[str, object]] = []
        if solution is not None:
            rows.append((S.t("forecasting.solution.metrics.aggregate"), solution.metrics))
            rows.extend(
                (
                    S.t("forecasting.solution.metrics.fold", number=index + 1),
                    fold.metrics,
                )
                for index, fold in enumerate(solution.evaluation_folds)
            )
        self.metrics_table.setRowCount(len(rows))
        for row, (scope, metric_set) in enumerate(rows):
            values = (
                scope,
                _number(metric_set.mae),
                _number(metric_set.rmse),
                _number(metric_set.mape),
                _number(metric_set.mase),
            )
            _set_row(self.metrics_table, row, values)

    def _set_parameters(self, parameters: tuple[tuple[str, float], ...]) -> None:
        self.parameters_table.setColumnCount(2)
        self.parameters_table.setHorizontalHeaderLabels(
            [
                S.t("forecasting.solution.parameters.name"),
                S.t("forecasting.solution.parameters.value"),
            ]
        )
        self.parameters_table.setRowCount(len(parameters))
        for row, (name, value) in enumerate(parameters):
            _set_row(self.parameters_table, row, (name, _number(value)))

    def _set_points(self, points: tuple[ForecastPoint, ...]) -> None:
        self.points_table.setSortingEnabled(False)
        self.points_table.setColumnCount(7)
        self.points_table.setHorizontalHeaderLabels(
            [
                S.t("forecasting.solution.points.timestamp"),
                S.t("forecasting.solution.points.segment"),
                S.t("forecasting.solution.points.actual"),
                S.t("forecasting.solution.points.predicted"),
                S.t("forecasting.solution.points.residual"),
                S.t("forecasting.solution.points.lower"),
                S.t("forecasting.solution.points.upper"),
            ]
        )
        rows: list[ForecastPoint] = list(points)
        if self._solution is not None:
            rows.extend(
                point for fold in self._solution.evaluation_folds for point in fold.points
            )
        rows.sort(key=lambda item: (item.timestamp, item.segment.value))
        self.points_table.setRowCount(len(rows))
        for row, point in enumerate(rows):
            _set_row(
                self.points_table,
                row,
                (
                    point.timestamp.isoformat(sep=" "),
                    S.t(f"forecasting.solution.segment.{point.segment.value}"),
                    _number(point.actual),
                    _number(point.predicted),
                    _number(point.residual),
                    _number(point.interval.lower if point.interval else None),
                    _number(point.interval.upper if point.interval else None),
                ),
            )
        self.points_table.setSortingEnabled(True)

    def _set_diagnostics(self, diagnostics: tuple[object, ...]) -> None:
        self.diagnostics_table.setColumnCount(3)
        self.diagnostics_table.setHorizontalHeaderLabels(
            [
                S.t("forecasting.solution.diagnostics.severity"),
                S.t("forecasting.solution.diagnostics.code"),
                S.t("forecasting.solution.diagnostics.message"),
            ]
        )
        self.diagnostics_table.setRowCount(len(diagnostics))
        for row, diagnostic in enumerate(diagnostics):
            _set_row(
                self.diagnostics_table,
                row,
                (
                    S.t(f"forecasting.solution.severity.{diagnostic.severity}"),
                    diagnostic.code,
                    diagnostic.message,
                ),
            )


def _table_section(object_name: str) -> tuple[Section, QTableWidget]:
    section = Section()
    table = QTableWidget()
    table.setObjectName(object_name)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.setSortingEnabled(False)
    table.setMinimumHeight(180)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
    table.horizontalHeader().setStretchLastSection(True)
    section.body.addWidget(table)
    return section, table


def _set_row(table: QTableWidget, row: int, values: tuple[str, ...]) -> None:
    for column, value in enumerate(values):
        item = QTableWidgetItem(value)
        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, column, item)


def _number(value: object) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.10g}"
    except (TypeError, ValueError):
        return "-"


def _sample(values: tuple[object, ...], limit: int) -> tuple[object, ...]:
    if len(values) <= limit:
        return values
    step = max((len(values) - 1) / (limit - 1), 1)
    indices = sorted({round(index * step) for index in range(limit)})
    return tuple(values[min(index, len(values) - 1)] for index in indices)
