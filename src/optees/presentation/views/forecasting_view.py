"""Formulation view for the first local univariate forecasting workflow.

The view only collects a versioned problem and delegates every mathematical
decision to the frozen application services (see docs/FORECASTING_ROADMAP.md,
Part B). It must never redefine statistical behaviour, and it must never
fabricate timestamps, values, or uncertainty.
"""
from __future__ import annotations

import calendar
import json
from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from optees.application.codecs.forecasting_problem_codec import (
    forecasting_model_from_public_dict,
)
from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.forecasting import ForecastObservation
from optees.domain.models.forecasting import (
    ForecastingEvaluationOptions,
    ForecastingMethodOptions,
    ForecastingModel,
)
from optees.domain.value_objects.forecasting import (
    EvaluationStrategy,
    ForecastingFrequency,
    ForecastingMethod,
)
from optees.presentation.error_feedback import localized_error_detail
from optees.presentation.views.lp_view.section import Section
from optees.presentation.views.widgets.data_entry_table import ColumnSpec, DataEntryTable

_METHODS = (
    ForecastingMethod.NAIVE,
    ForecastingMethod.SEASONAL_NAIVE,
    ForecastingMethod.HOLT_WINTERS_ADDITIVE,
)
_FREQUENCIES = (
    ForecastingFrequency.HOURLY,
    ForecastingFrequency.DAILY,
    ForecastingFrequency.WEEKLY,
    ForecastingFrequency.MONTHLY,
    ForecastingFrequency.QUARTERLY,
    ForecastingFrequency.YEARLY,
)
_STRATEGIES = (
    EvaluationStrategy.NONE,
    EvaluationStrategy.HOLDOUT,
    EvaluationStrategy.ROLLING_ORIGIN,
)
# Suggested season length per frequency, purely didactic (teaches the concept).
_SEASON_HINT = {
    ForecastingFrequency.HOURLY: "24",
    ForecastingFrequency.DAILY: "7",
    ForecastingFrequency.WEEKLY: "52",
    ForecastingFrequency.MONTHLY: "12",
    ForecastingFrequency.QUARTERLY: "4",
    ForecastingFrequency.YEARLY: "1",
}


def _make_info_button(object_name: str, parent: Optional[QWidget] = None) -> QPushButton:
    button = QPushButton("i", parent)
    button.setObjectName(object_name)
    button.setProperty("variant", "info")
    button.setFixedSize(24, 24)
    button.setCursor(Qt.PointingHandCursor)
    return button


class _InfoDialog(QDialog):
    def __init__(self, title: str, intro: str, html: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(560, 380)
        root = QVBoxLayout(self)
        intro_label = QLabel(intro)
        intro_label.setWordWrap(True)
        root.addWidget(intro_label)
        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setHtml(html)
        root.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)


class ForecastingView(QWidget):
    """Collect an ordered univariate series and request a validated forecast."""

    solve_completed = Signal(object)
    example_requested = Signal()
    problem_description_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._solve_usecase = None
        self._season_memory = ""

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

        self.title = QLabel()
        self.title.setTextFormat(Qt.RichText)
        root.addWidget(self.title)

        root.addWidget(self._build_intro())
        root.addWidget(self._build_series_section())
        root.addWidget(self._build_config_section())

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_forecast = QPushButton()
        self.btn_forecast.setObjectName("forecastingSolveButton")
        self.btn_forecast.clicked.connect(self._on_forecast)
        actions.addWidget(self.btn_forecast)
        root.addLayout(actions)
        root.addStretch(1)

        self.table.ensure_row_count(8)
        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self._update_method_controls()
        self._update_strategy_controls()
        self.refresh_strings()
        self.refresh_theme()

    # -- construction helpers --------------------------------------------
    def _build_intro(self) -> Section:
        intro = Section()
        header = QHBoxLayout()
        self.intro_text = QLabel()
        self.intro_text.setWordWrap(True)
        header.addWidget(self.intro_text, 1)
        self.btn_import_json = QPushButton()
        self.btn_import_json.setObjectName("forecastingImportJsonButton")
        self.btn_import_json.clicked.connect(self._on_import_json)
        self.btn_json_info = _make_info_button("forecastingJsonInfoButton")
        self.btn_json_info.clicked.connect(lambda: self._show_info("import"))
        header.addWidget(self.btn_import_json)
        header.addWidget(self.btn_json_info)
        intro.body.addLayout(header)
        row = QHBoxLayout()
        row.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_example.setObjectName("forecastingExampleButton")
        self.btn_example.clicked.connect(self.example_requested.emit)
        self.btn_problem = QPushButton()
        self.btn_problem.setObjectName("forecastingProblemButton")
        self.btn_problem.clicked.connect(self.problem_description_requested.emit)
        row.addWidget(self.btn_example)
        row.addWidget(self.btn_problem)
        intro.body.addLayout(row)
        self.intro_section = intro
        return intro

    def _build_series_section(self) -> Section:
        section = Section()
        header = QHBoxLayout()
        self.series_hint = QLabel()
        self.series_hint.setWordWrap(True)
        header.addWidget(self.series_hint, 1)
        self.btn_series_info = _make_info_button("forecastingSeriesInfoButton")
        self.btn_series_info.clicked.connect(lambda: self._show_info("series"))
        header.addWidget(self.btn_series_info)
        section.body.addLayout(header)

        target_row = QHBoxLayout()
        self.lbl_target = QLabel()
        self.edit_target = QLineEdit("value")
        self.edit_target.setObjectName("forecastingTargetName")
        target_row.addWidget(self.lbl_target)
        target_row.addWidget(self.edit_target, 1)
        section.body.addLayout(target_row)

        # Assisted entry: auto timestamps + paste help a tedious time-series table.
        assist = QHBoxLayout()
        self.lbl_start = QLabel()
        self.edit_start = QLineEdit("2024-01-01")
        self.edit_start.setObjectName("forecastingStartTimestamp")
        self.edit_start.setFixedWidth(150)
        self.btn_autofill = QPushButton()
        self.btn_autofill.setObjectName("forecastingAutofillButton")
        self.btn_autofill.clicked.connect(self._on_autofill_timestamps)
        self.btn_paste = QPushButton()
        self.btn_paste.setObjectName("forecastingPasteButton")
        self.btn_paste.clicked.connect(self._on_paste)
        assist.addWidget(self.lbl_start)
        assist.addWidget(self.edit_start)
        assist.addWidget(self.btn_autofill)
        assist.addWidget(self.btn_paste)
        assist.addStretch(1)
        section.body.addLayout(assist)

        self.table = DataEntryTable(
            (ColumnSpec("timestamp", "timestamp"), ColumnSpec("value", "number"))
        )
        self.table.setObjectName("forecastingObservationsTable")
        section.body.addWidget(self.table)

        table_actions = QHBoxLayout()
        table_actions.addStretch(1)
        self.btn_add_row = QPushButton()
        self.btn_add_row.setObjectName("forecastingAddRowButton")
        self.btn_add_row.clicked.connect(self.table.add_row)
        self.btn_remove_rows = QPushButton()
        self.btn_remove_rows.setObjectName("forecastingRemoveRowsButton")
        self.btn_remove_rows.clicked.connect(self.table.remove_selected_rows)
        table_actions.addWidget(self.btn_add_row)
        table_actions.addWidget(self.btn_remove_rows)
        section.body.addLayout(table_actions)
        self.series_section = section
        return section

    def _build_config_section(self) -> Section:
        section = Section()
        header = QHBoxLayout()
        self.config_hint = QLabel()
        self.config_hint.setWordWrap(True)
        header.addWidget(self.config_hint, 1)
        self.btn_config_info = _make_info_button("forecastingConfigInfoButton")
        self.btn_config_info.clicked.connect(lambda: self._show_info("config"))
        header.addWidget(self.btn_config_info)
        section.body.addLayout(header)

        method_row = QHBoxLayout()
        self.lbl_method = QLabel()
        self.combo_method = QComboBox()
        self.combo_method.setObjectName("forecastingMethod")
        for method in _METHODS:
            self.combo_method.addItem("", method.value)
        self.combo_method.currentIndexChanged.connect(self._update_method_controls)
        self.lbl_horizon = QLabel()
        self.edit_horizon = QLineEdit("3")
        self.edit_horizon.setObjectName("forecastingHorizon")
        self.edit_horizon.setFixedWidth(80)
        self.lbl_frequency = QLabel()
        self.combo_frequency = QComboBox()
        self.combo_frequency.setObjectName("forecastingFrequency")
        for frequency in _FREQUENCIES:
            self.combo_frequency.addItem("", frequency.value)
        self.combo_frequency.setCurrentIndex(3)  # monthly default
        self.combo_frequency.currentIndexChanged.connect(self._update_season_hint)
        method_row.addWidget(self.lbl_method)
        method_row.addWidget(self.combo_method)
        method_row.addSpacing(12)
        method_row.addWidget(self.lbl_horizon)
        method_row.addWidget(self.edit_horizon)
        method_row.addSpacing(12)
        method_row.addWidget(self.lbl_frequency)
        method_row.addWidget(self.combo_frequency)
        method_row.addStretch(1)
        section.body.addLayout(method_row)

        # Teaching one-liner: why you would pick this method.
        self.method_rationale = QLabel()
        self.method_rationale.setWordWrap(True)
        self.method_rationale.setObjectName("forecastingMethodRationale")
        section.body.addWidget(self.method_rationale)

        self.season_row = QWidget()
        season_layout = QHBoxLayout(self.season_row)
        season_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_season = QLabel()
        self.edit_season = QLineEdit()
        self.edit_season.setObjectName("forecastingSeasonLength")
        self.edit_season.setFixedWidth(80)
        self.lbl_season_hint = QLabel()
        season_layout.addWidget(self.lbl_season)
        season_layout.addWidget(self.edit_season)
        season_layout.addWidget(self.lbl_season_hint)
        season_layout.addStretch(1)
        section.body.addWidget(self.season_row)

        self.advanced_row = QWidget()
        advanced_layout = QHBoxLayout(self.advanced_row)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_max_iter = QLabel()
        self.edit_max_iter = QLineEdit("1000")
        self.edit_max_iter.setObjectName("forecastingMaxIterations")
        self.edit_max_iter.setFixedWidth(90)
        self.lbl_tolerance = QLabel()
        self.edit_tolerance = QLineEdit("1e-8")
        self.edit_tolerance.setObjectName("forecastingTolerance")
        self.edit_tolerance.setFixedWidth(90)
        advanced_layout.addWidget(self.lbl_max_iter)
        advanced_layout.addWidget(self.edit_max_iter)
        advanced_layout.addSpacing(12)
        advanced_layout.addWidget(self.lbl_tolerance)
        advanced_layout.addWidget(self.edit_tolerance)
        advanced_layout.addStretch(1)
        section.body.addWidget(self.advanced_row)

        eval_row = QHBoxLayout()
        self.lbl_strategy = QLabel()
        self.combo_strategy = QComboBox()
        self.combo_strategy.setObjectName("forecastingEvaluationStrategy")
        for strategy in _STRATEGIES:
            self.combo_strategy.addItem("", strategy.value)
        self.combo_strategy.setCurrentIndex(1)  # holdout default
        self.combo_strategy.currentIndexChanged.connect(self._update_strategy_controls)
        eval_row.addWidget(self.lbl_strategy)
        eval_row.addWidget(self.combo_strategy)
        eval_row.addStretch(1)
        section.body.addLayout(eval_row)

        self.holdout_row = QWidget()
        holdout_layout = QHBoxLayout(self.holdout_row)
        holdout_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_holdout = QLabel()
        self.edit_holdout = QLineEdit("1")
        self.edit_holdout.setObjectName("forecastingHoldoutSize")
        self.edit_holdout.setFixedWidth(80)
        holdout_layout.addWidget(self.lbl_holdout)
        holdout_layout.addWidget(self.edit_holdout)
        holdout_layout.addStretch(1)
        section.body.addWidget(self.holdout_row)

        self.rolling_row = QWidget()
        rolling_layout = QHBoxLayout(self.rolling_row)
        rolling_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_origins = QLabel()
        self.edit_origins = QLineEdit("3")
        self.edit_origins.setObjectName("forecastingOriginCount")
        self.edit_origins.setFixedWidth(70)
        self.lbl_step = QLabel()
        self.edit_step = QLineEdit("1")
        self.edit_step.setObjectName("forecastingStep")
        self.edit_step.setFixedWidth(70)
        self.lbl_eval_horizon = QLabel()
        self.edit_eval_horizon = QLineEdit("1")
        self.edit_eval_horizon.setObjectName("forecastingEvalHorizon")
        self.edit_eval_horizon.setFixedWidth(70)
        self.lbl_min_training = QLabel()
        self.edit_min_training = QLineEdit("2")
        self.edit_min_training.setObjectName("forecastingMinTraining")
        self.edit_min_training.setFixedWidth(70)
        for widget in (
            self.lbl_origins, self.edit_origins, self.lbl_step, self.edit_step,
            self.lbl_eval_horizon, self.edit_eval_horizon,
            self.lbl_min_training, self.edit_min_training,
        ):
            rolling_layout.addWidget(widget)
        rolling_layout.addStretch(1)
        section.body.addWidget(self.rolling_row)

        self.config_section = section
        return section

    # -- public API -------------------------------------------------------
    def set_solve_usecase(self, usecase) -> None:
        self._solve_usecase = usecase

    def set_model(self, model: ForecastingModel) -> None:
        self.edit_target.setText(model.target_name)
        self.table.set_data(
            [
                (_format_timestamp(obs.timestamp), _format_number(obs.value))
                for obs in model.observations
            ]
        )
        self.combo_method.setCurrentIndex(max(0, self.combo_method.findData(model.method.value)))
        self.edit_horizon.setText(str(model.horizon))
        self.combo_frequency.setCurrentIndex(
            max(0, self.combo_frequency.findData(model.frequency.value))
        )
        if model.season_length is not None:
            self.edit_season.setText(str(model.season_length))
            self._season_memory = str(model.season_length)
        self.combo_strategy.setCurrentIndex(
            max(0, self.combo_strategy.findData(model.evaluation.strategy.value))
        )
        self.edit_holdout.setText(str(model.evaluation.holdout_size))
        self.edit_origins.setText(str(model.evaluation.origin_count))
        self.edit_step.setText(str(model.evaluation.step))
        self.edit_eval_horizon.setText(str(model.evaluation.evaluation_horizon))
        self.edit_min_training.setText(str(model.evaluation.minimum_training_size))
        self.edit_max_iter.setText(str(model.method_options.max_iterations))
        self.edit_tolerance.setText(_format_number(model.method_options.tolerance))
        self._update_method_controls()
        self._update_strategy_controls()

    def current_model(self) -> ForecastingModel:
        invalid = self.table.invalid_cells()
        if invalid:
            row = invalid[0][0] + 1
            raise ValueError(f"observation row {row} has an invalid timestamp or value")
        rows = self.table.non_empty_rows()
        if not rows:
            raise ValueError("at least one observation is required")
        observations = tuple(
            ForecastObservation(
                timestamp=_parse_timestamp(cells[0]),
                value=float(cells[1].replace(",", ".")),
            )
            for cells in rows
        )
        method = ForecastingMethod.from_value(self.combo_method.currentData())
        season_length = None
        if method.requires_season_length:
            season_length = _parse_int(self.edit_season.text(), "season length")
        evaluation = self._evaluation_options()
        options = ForecastingMethodOptions(
            max_iterations=_parse_int(self.edit_max_iter.text(), "max iterations"),
            tolerance=float(self.edit_tolerance.text().strip().replace(",", ".")),
        )
        return ForecastingModel(
            target_name=self.edit_target.text().strip() or "value",
            observations=observations,
            method=method,
            horizon=_parse_int(self.edit_horizon.text(), "horizon"),
            frequency=ForecastingFrequency.from_value(self.combo_frequency.currentData()),
            season_length=season_length,
            evaluation=evaluation,
            method_options=options,
        )

    def _evaluation_options(self) -> ForecastingEvaluationOptions:
        strategy = EvaluationStrategy.from_value(self.combo_strategy.currentData())
        return ForecastingEvaluationOptions(
            strategy=strategy,
            holdout_size=_parse_int(self.edit_holdout.text(), "holdout size"),
            origin_count=_parse_int(self.edit_origins.text(), "origin count"),
            step=_parse_int(self.edit_step.text(), "step"),
            evaluation_horizon=_parse_int(self.edit_eval_horizon.text(), "evaluation horizon"),
            minimum_training_size=_parse_int(self.edit_min_training.text(), "minimum training size"),
        )

    # -- events -----------------------------------------------------------
    def _on_forecast(self) -> None:
        if self._solve_usecase is None:
            return
        try:
            model = self.current_model()
        except ValueError as exc:
            self._show_validation_error(exc)
            return
        self.solve_completed.emit(self._solve_usecase.execute(model))

    def _on_autofill_timestamps(self) -> None:
        try:
            start = _parse_timestamp(self.edit_start.text())
        except ValueError:
            self._show_validation_error(ValueError("start timestamp is not a valid date"))
            return
        frequency = ForecastingFrequency.from_value(self.combo_frequency.currentData())
        count = max(self.table.rowCount(), 1)
        stamps = [
            _format_timestamp(_advance(start, frequency, index), frequency)
            for index in range(count)
        ]
        self.table.set_column_values(0, stamps)

    def _on_paste(self) -> None:
        self.table.paste_from_clipboard()

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, S.t("forecasting.import.dialog_title"), "", "JSON (*.json);;All files (*)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
            self.set_model(forecasting_model_from_public_dict(payload))
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            QMessageBox.warning(
                self,
                S.t("forecasting.import.error_title"),
                S.t(
                    "forecasting.import.error_body",
                    detail=localized_error_detail("forecasting_import", exc),
                ),
            )

    def _show_validation_error(self, exc: Exception) -> None:
        QMessageBox.warning(
            self,
            S.t("forecasting.validation.title"),
            S.t(
                "forecasting.validation.body",
                detail=localized_error_detail("forecasting_validation", exc),
            ),
        )

    def _show_info(self, topic: str) -> None:
        _InfoDialog(
            S.t(f"forecasting.{topic}.info_title"),
            S.t(f"forecasting.{topic}.info_body"),
            S.t(f"forecasting.{topic}.info_html"),
            self,
        ).exec()

    # -- dynamic behaviour ------------------------------------------------
    def _update_method_controls(self) -> None:
        method = ForecastingMethod.from_value(self.combo_method.currentData())
        needs_season = method.requires_season_length
        if not needs_season and self.edit_season.text().strip():
            self._season_memory = self.edit_season.text().strip()
        self.season_row.setVisible(needs_season)
        if needs_season and not self.edit_season.text().strip() and self._season_memory:
            self.edit_season.setText(self._season_memory)
        self.advanced_row.setVisible(method == ForecastingMethod.HOLT_WINTERS_ADDITIVE)
        self.method_rationale.setText(S.t(f"forecasting.method.rationale.{method.value}"))
        self._update_season_hint()

    def _update_season_hint(self) -> None:
        frequency = ForecastingFrequency.from_value(self.combo_frequency.currentData())
        self.edit_season.setPlaceholderText(_SEASON_HINT.get(frequency, ""))
        self.lbl_season_hint.setText(
            S.t("forecasting.config.season_hint", suggestion=_SEASON_HINT.get(frequency, "?"))
        )

    def _update_strategy_controls(self) -> None:
        strategy = EvaluationStrategy.from_value(self.combo_strategy.currentData())
        self.holdout_row.setVisible(strategy == EvaluationStrategy.HOLDOUT)
        self.rolling_row.setVisible(strategy == EvaluationStrategy.ROLLING_ORIGIN)

    # -- i18n / theme -----------------------------------------------------
    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:26px; font-weight:700'>{S.t('forecasting.header.title')}</span>"
        )
        self.intro_section.set_title(S.t("forecasting.header.section"))
        self.intro_text.setText(S.t("forecasting.header.description"))
        self.btn_import_json.setText(S.t("forecasting.import.button"))
        self.btn_json_info.setToolTip(S.t("forecasting.import.info_tooltip"))
        self.btn_example.setText(S.t("forecasting.header.buttons.example"))
        self.btn_problem.setText(S.t("forecasting.header.buttons.problem"))
        self.series_section.set_title(S.t("forecasting.series.section"))
        self.series_hint.setText(S.t("forecasting.series.hint"))
        self.btn_series_info.setToolTip(S.t("forecasting.series.info_tooltip"))
        self.lbl_target.setText(S.t("forecasting.series.target"))
        self.lbl_start.setText(S.t("forecasting.series.start"))
        self.btn_autofill.setText(S.t("forecasting.series.autofill"))
        self.btn_autofill.setToolTip(S.t("forecasting.series.autofill_tooltip"))
        self.btn_paste.setText(S.t("forecasting.series.paste"))
        self.btn_paste.setToolTip(S.t("forecasting.series.paste_tooltip"))
        self.btn_add_row.setText(S.t("forecasting.series.add"))
        self.btn_remove_rows.setText(S.t("forecasting.series.remove"))
        self.table.set_header_titles(
            (S.t("forecasting.series.timestamp"), S.t("forecasting.series.value"))
        )
        self.config_section.set_title(S.t("forecasting.config.section"))
        self.config_hint.setText(S.t("forecasting.config.hint"))
        self.btn_config_info.setToolTip(S.t("forecasting.config.info_tooltip"))
        self.lbl_method.setText(S.t("forecasting.config.method"))
        for index, method in enumerate(_METHODS):
            self.combo_method.setItemText(index, S.t(f"forecasting.method.name.{method.value}"))
        self.lbl_horizon.setText(S.t("forecasting.config.horizon"))
        self.lbl_frequency.setText(S.t("forecasting.config.frequency"))
        for index, frequency in enumerate(_FREQUENCIES):
            self.combo_frequency.setItemText(
                index, S.t(f"forecasting.frequency.{frequency.value}")
            )
        self.lbl_season.setText(S.t("forecasting.config.season"))
        self.lbl_max_iter.setText(S.t("forecasting.config.max_iterations"))
        self.lbl_tolerance.setText(S.t("forecasting.config.tolerance"))
        self.lbl_strategy.setText(S.t("forecasting.config.evaluation"))
        for index, strategy in enumerate(_STRATEGIES):
            self.combo_strategy.setItemText(
                index, S.t(f"forecasting.strategy.{strategy.value}")
            )
        self.lbl_holdout.setText(S.t("forecasting.config.holdout_size"))
        self.lbl_origins.setText(S.t("forecasting.config.origin_count"))
        self.lbl_step.setText(S.t("forecasting.config.step"))
        self.lbl_eval_horizon.setText(S.t("forecasting.config.eval_horizon"))
        self.lbl_min_training.setText(S.t("forecasting.config.min_training"))
        self.btn_forecast.setText(S.t("forecasting.actions.forecast"))
        self._update_method_controls()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        for label in (self.intro_text, self.series_hint, self.config_hint, self.lbl_season_hint):
            label.setStyleSheet(f"color: {t.text_muted};")
        self.method_rationale.setStyleSheet(f"color: {t.text_muted}; font-style: italic;")


# -- module helpers -------------------------------------------------------
def _advance(start: datetime, frequency: ForecastingFrequency, periods: int) -> datetime:
    if frequency == ForecastingFrequency.HOURLY:
        return start + timedelta(hours=periods)
    if frequency == ForecastingFrequency.DAILY:
        return start + timedelta(days=periods)
    if frequency == ForecastingFrequency.WEEKLY:
        return start + timedelta(weeks=periods)
    months = {
        ForecastingFrequency.MONTHLY: 1,
        ForecastingFrequency.QUARTERLY: 3,
        ForecastingFrequency.YEARLY: 12,
    }[frequency] * periods
    return _add_months(start, months)


def _add_months(start: datetime, months: int) -> datetime:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def _format_timestamp(value: datetime, frequency: ForecastingFrequency | None = None) -> str:
    if frequency == ForecastingFrequency.HOURLY or value.time() != value.min.time():
        return value.isoformat()
    return value.date().isoformat()


def _parse_timestamp(text: str) -> datetime:
    normalized = text.strip()
    if not normalized:
        raise ValueError("timestamp is required")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def _parse_int(text: str, label: str) -> int:
    normalized = text.strip()
    if not normalized:
        raise ValueError(f"{label} is required")
    try:
        return int(normalized)
    except ValueError as exc:
        raise ValueError(f"{label} must be an integer") from exc


def _format_number(value: float) -> str:
    return f"{float(value):.10g}"
