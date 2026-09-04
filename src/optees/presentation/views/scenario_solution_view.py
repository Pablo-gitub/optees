"""Result view for the linear scenario min-max / max-min capabilities.

Everything shown here is read from the ``ExecutionEnvelope`` published by the
application layer. Job status, mathematical status, termination reason and
independent-validation status are four separate facts and are rendered as such.
The view performs no mathematical recomputation: guarantee, scenario values and
binding scenarios are displayed exactly as returned.
"""

from __future__ import annotations

from html import escape
import math
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.views.lp_view.section import Section
from optees.presentation.views.scenario_comparison_widget import (
    BINDING_MARKER,
    ScenarioComparisonWidget,
)

_DIAGNOSTIC_ROWS = (
    "backend",
    "backend_id",
    "status_code",
    "iterations",
    "wall_time",
    "elapsed_seconds",
    "success",
    "message",
)


def _format_number(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            return "-"
        return f"{number:.10g}"
    return str(value)


def _make_table(object_name: str) -> QTableWidget:
    table = QTableWidget()
    table.setObjectName(object_name)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(False)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return table


def _fit_table_height(table: QTableWidget) -> None:
    header = table.horizontalHeader().height()
    rows = sum(table.rowHeight(row) for row in range(table.rowCount()))
    table.setFixedHeight(header + rows + 2 * table.frameWidth() + 2)


class ScenarioSolutionView(QWidget):
    """Renders one scenario execution envelope, or one structured rejection."""

    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._envelope: Any = None
        self._error: Any = None

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
        self.btn_back.setObjectName("scenarioSolutionBackButton")
        self.btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(self.btn_back)
        root.addLayout(header)

        root.addWidget(self._build_error_section())
        root.addWidget(self._build_status_section())
        root.addWidget(self._build_guarantee_section())
        root.addWidget(self._build_variables_section())
        root.addWidget(self._build_scenarios_section())
        root.addWidget(self._build_validation_section())
        root.addWidget(self._build_diagnostics_section())
        root.addWidget(self._build_comparison_section())
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()
        self._render()

    # -- construction ----------------------------------------------------
    def _build_error_section(self) -> Section:
        section = Section()
        self.error_code = QLabel()
        self.error_code.setObjectName("scenarioErrorCode")
        self.error_code.setWordWrap(True)
        self.error_message = QLabel()
        self.error_message.setObjectName("scenarioErrorMessage")
        self.error_message.setWordWrap(True)
        self.error_details = QLabel()
        self.error_details.setObjectName("scenarioErrorDetails")
        self.error_details.setWordWrap(True)
        self.error_details.setTextFormat(Qt.RichText)
        for widget in (self.error_code, self.error_message, self.error_details):
            section.body.addWidget(widget)
        self.error_section = section
        return section

    def _build_status_section(self) -> Section:
        section = Section()
        self.status_hint = QLabel()
        self.status_hint.setWordWrap(True)
        section.body.addWidget(self.status_hint)
        self.status_labels: dict[str, QLabel] = {}
        for key in ("job", "mathematical", "termination", "validation"):
            row = QHBoxLayout()
            caption = QLabel()
            caption.setObjectName(f"scenarioStatusCaption_{key}")
            value = QLabel()
            value.setObjectName(f"scenarioStatus_{key}")
            value.setWordWrap(True)
            row.addWidget(caption)
            row.addWidget(value, 1)
            section.body.addLayout(row)
            self.status_labels[f"{key}_caption"] = caption
            self.status_labels[key] = value
        self.warnings_label = QLabel()
        self.warnings_label.setObjectName("scenarioWarnings")
        self.warnings_label.setWordWrap(True)
        section.body.addWidget(self.warnings_label)
        self.status_section = section
        return section

    def _build_guarantee_section(self) -> Section:
        section = Section()
        self.orientation_label = QLabel()
        self.orientation_label.setObjectName("scenarioOrientationLabel")
        self.orientation_label.setWordWrap(True)
        section.body.addWidget(self.orientation_label)
        self.guarantee_value = QLabel()
        self.guarantee_value.setObjectName("scenarioGuaranteeValue")
        self.guarantee_value.setWordWrap(True)
        section.body.addWidget(self.guarantee_value)
        self.guarantee_hint = QLabel()
        self.guarantee_hint.setWordWrap(True)
        section.body.addWidget(self.guarantee_hint)
        self.guarantee_section = section
        return section

    def _build_variables_section(self) -> Section:
        section = Section()
        self.variables_hint = QLabel()
        self.variables_hint.setWordWrap(True)
        section.body.addWidget(self.variables_hint)
        self.variables_table = _make_table("scenarioSolutionVariablesTable")
        section.body.addWidget(self.variables_table)
        self.variables_empty = QLabel()
        self.variables_empty.setObjectName("scenarioSolutionVariablesEmpty")
        self.variables_empty.setWordWrap(True)
        section.body.addWidget(self.variables_empty)
        self.variables_section = section
        return section

    def _build_scenarios_section(self) -> Section:
        section = Section()
        self.scenarios_hint = QLabel()
        self.scenarios_hint.setWordWrap(True)
        section.body.addWidget(self.scenarios_hint)
        self.scenarios_table = _make_table("scenarioSolutionScenariosTable")
        section.body.addWidget(self.scenarios_table)
        self.binding_summary = QLabel()
        self.binding_summary.setObjectName("scenarioBindingSummary")
        self.binding_summary.setWordWrap(True)
        section.body.addWidget(self.binding_summary)
        self.scenarios_empty = QLabel()
        self.scenarios_empty.setObjectName("scenarioSolutionScenariosEmpty")
        self.scenarios_empty.setWordWrap(True)
        section.body.addWidget(self.scenarios_empty)
        self.scenarios_section = section
        return section

    def _build_validation_section(self) -> Section:
        section = Section()
        self.validation_hint = QLabel()
        self.validation_hint.setWordWrap(True)
        section.body.addWidget(self.validation_hint)
        self.validation_table = _make_table("scenarioValidationTable")
        section.body.addWidget(self.validation_table)
        self.validation_limitations = QLabel()
        self.validation_limitations.setObjectName("scenarioValidationLimitations")
        self.validation_limitations.setWordWrap(True)
        self.validation_limitations.setTextFormat(Qt.RichText)
        section.body.addWidget(self.validation_limitations)
        self.validation_section = section
        return section

    def _build_diagnostics_section(self) -> Section:
        section = Section()
        self.diagnostics_hint = QLabel()
        self.diagnostics_hint.setWordWrap(True)
        section.body.addWidget(self.diagnostics_hint)
        self.diagnostics_table = _make_table("scenarioDiagnosticsTable")
        section.body.addWidget(self.diagnostics_table)
        self.diagnostics_section = section
        return section

    def _build_comparison_section(self) -> Section:
        section = Section()
        self.comparison = ScenarioComparisonWidget()
        section.body.addWidget(self.comparison)
        self.comparison_section = section
        return section

    # -- inputs -----------------------------------------------------------
    def set_envelope(self, envelope: Any) -> None:
        """Display one successful execution envelope."""
        self._envelope = envelope
        self._error = None
        self._render()

    def set_error(self, error: Any) -> None:
        """Display one structured rejection without inventing a result."""
        self._error = error
        self._envelope = None
        self._render()

    def clear(self) -> None:
        self._envelope = None
        self._error = None
        self._render()

    @property
    def envelope(self) -> Any:
        return self._envelope

    # -- rendering ---------------------------------------------------------
    def _payload(self) -> dict[str, Any]:
        if self._envelope is None:
            return {}
        to_dict = getattr(self._envelope, "to_dict", None)
        if callable(to_dict):
            payload = to_dict()
            return payload if isinstance(payload, dict) else {}
        return self._envelope if isinstance(self._envelope, dict) else {}

    def _render(self) -> None:
        payload = self._payload()
        self._render_error()
        self._render_status(payload)
        self._render_guarantee(payload)
        self._render_variables(payload)
        self._render_scenarios(payload)
        self._render_validation(payload)
        self._render_diagnostics(payload)
        self.comparison.set_result(payload.get("result") if payload else None)

    def _render_error(self) -> None:
        if self._error is None:
            self.error_section.setVisible(False)
            return
        self.error_section.setVisible(True)
        to_dict = getattr(self._error, "to_dict", None)
        payload = to_dict() if callable(to_dict) else {}
        error = payload.get("error", {}) if isinstance(payload, dict) else {}
        code = str(error.get("code", ""))
        self.error_code.setText(
            S.t("scenario.solution.error.code", code=S.t(f"scenario.solution.error.codes.{code}"))
        )
        self.error_message.setText(str(error.get("message", "")))
        details = error.get("details") or []
        if details:
            rows = "".join(
                f"<li><code>{escape(str(detail.get('path', '')))}</code> — "
                f"{escape(str(detail.get('code', '')))}: "
                f"{escape(str(detail.get('message', '')))}</li>"
                for detail in details
                if isinstance(detail, dict)
            )
            self.error_details.setText(
                f"<b>{S.t('scenario.solution.error.details')}</b><ul>{rows}</ul>"
            )
        else:
            self.error_details.setText("")

    def _render_status(self, payload: dict[str, Any]) -> None:
        if not payload:
            for key in ("job", "mathematical", "termination", "validation"):
                self.status_labels[key].setText(S.t("scenario.solution.empty"))
            self.warnings_label.setText("")
            return
        validation = payload.get("validation") or {}
        mapping = {
            "job": ("job_status", payload.get("job_status")),
            "mathematical": ("mathematical_status", payload.get("mathematical_status")),
            "termination": ("termination_reason", payload.get("termination_reason")),
            "validation": ("validation_status", validation.get("status")),
        }
        for key, (group, raw) in mapping.items():
            if raw is None:
                self.status_labels[key].setText(S.t("scenario.solution.status.unreported"))
                continue
            self.status_labels[key].setText(S.t(f"scenario.solution.{group}.{raw}"))
        warnings = payload.get("warnings") or []
        if warnings:
            self.warnings_label.setText(
                f"{S.t('scenario.solution.warnings')}: " + " ".join(str(w) for w in warnings)
            )
        else:
            self.warnings_label.setText("")

    def _render_guarantee(self, payload: dict[str, Any]) -> None:
        result = payload.get("result") or {}
        orientation = str(result.get("orientation", ""))
        if not orientation:
            self.orientation_label.setText("")
            self.guarantee_value.setText(S.t("scenario.solution.empty"))
            self.guarantee_hint.setText("")
            return
        self.orientation_label.setText(
            S.t(
                "scenario.solution.orientation",
                orientation=S.t(f"scenario.orientation.{_orientation_key(orientation)}"),
            )
        )
        guaranteed = result.get("guaranteed_value")
        if guaranteed is None:
            self.guarantee_value.setText(S.t("scenario.solution.guarantee.unavailable"))
            self.guarantee_hint.setText("")
            return
        self.guarantee_value.setText(
            f"{S.t(f'scenario.solution.guarantee.{_orientation_key(orientation)}')}: "
            f"{_format_number(guaranteed)}"
        )
        self.guarantee_hint.setText(
            S.t(f"scenario.solution.guarantee.hint_{_orientation_key(orientation)}")
        )

    def _render_variables(self, payload: dict[str, Any]) -> None:
        headers = [
            S.t("scenario.solution.variables.columns.order"),
            S.t("scenario.solution.variables.columns.name"),
            S.t("scenario.solution.variables.columns.value"),
        ]
        table = self.variables_table
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        rows = [
            entry
            for entry in ((payload.get("result") or {}).get("variables") or [])
            if isinstance(entry, dict)
        ]
        table.setRowCount(len(rows))
        for index, entry in enumerate(rows):
            cells = (
                str(index),
                str(entry.get("name", "")),
                _format_number(entry.get("value")),
            )
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column != 1:
                    item.setTextAlignment(Qt.AlignCenter)
                table.setItem(index, column, item)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        _fit_table_height(table)
        table.setVisible(bool(rows))
        self.variables_empty.setVisible(not rows)

    def _render_scenarios(self, payload: dict[str, Any]) -> None:
        headers = [
            S.t("scenario.solution.scenarios.columns.order"),
            S.t("scenario.solution.scenarios.columns.id"),
            S.t("scenario.solution.scenarios.columns.value"),
            S.t("scenario.solution.scenarios.columns.binding"),
        ]
        table = self.scenarios_table
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        result = payload.get("result") or {}
        rows = [entry for entry in (result.get("scenario_values") or []) if isinstance(entry, dict)]
        table.setRowCount(len(rows))
        for index, entry in enumerate(rows):
            is_binding = bool(entry.get("is_binding"))
            binding_text = (
                f"{BINDING_MARKER} {S.t('scenario.solution.scenarios.binding_yes')}"
                if is_binding
                else S.t("scenario.solution.scenarios.binding_no")
            )
            cells = (
                str(index),
                str(entry.get("scenario_id", "")),
                _format_number(entry.get("value")),
                binding_text,
            )
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column != 1:
                    item.setTextAlignment(Qt.AlignCenter)
                if is_binding:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                table.setItem(index, column, item)
        header = table.horizontalHeader()
        for column in range(len(headers)):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        _fit_table_height(table)
        table.setVisible(bool(rows))
        self.scenarios_empty.setVisible(not rows)

        binding_ids = [str(value) for value in (result.get("binding_scenario_ids") or [])]
        if binding_ids:
            self.binding_summary.setText(
                S.t("scenario.solution.scenarios.binding_summary", ids=", ".join(binding_ids))
            )
        elif rows:
            self.binding_summary.setText(S.t("scenario.solution.scenarios.binding_none"))
        else:
            self.binding_summary.setText("")

    def _render_validation(self, payload: dict[str, Any]) -> None:
        headers = [
            S.t("scenario.solution.validation.columns.check"),
            S.t("scenario.solution.validation.columns.result"),
            S.t("scenario.solution.validation.columns.detail"),
        ]
        table = self.validation_table
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        validation = payload.get("validation") or {}
        checks = [check for check in (validation.get("checks") or []) if isinstance(check, dict)]
        violations: dict[str, list[str]] = {}
        for violation in validation.get("violations") or []:
            if isinstance(violation, dict):
                violations.setdefault(str(violation.get("check_code", "")), []).append(
                    str(violation.get("path", ""))
                )
        table.setRowCount(len(checks))
        for index, check in enumerate(checks):
            code = str(check.get("code", ""))
            leaf = code.removeprefix("scenario.")
            passed = str(check.get("status", "")) == "passed"
            detail = S.t(f"scenario.solution.validation.checks.{leaf}")
            paths = violations.get(code)
            if paths:
                detail = (
                    f"{detail} — {S.t('scenario.solution.validation.violations')}: "
                    f"{', '.join(paths)}"
                )
            cells = (
                S.t(f"scenario.solution.validation.names.{leaf}"),
                S.t(
                    "scenario.solution.validation.passed"
                    if passed
                    else "scenario.solution.validation.failed"
                ),
                detail,
            )
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column == 1:
                    item.setTextAlignment(Qt.AlignCenter)
                table.setItem(index, column, item)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        table.resizeRowsToContents()
        _fit_table_height(table)
        table.setVisible(bool(checks))

        limitations = [str(item) for item in (validation.get("limitations") or [])]
        if limitations:
            bullets = "".join(
                f"<li>{escape(_localized_limitation(index, text))}</li>"
                for index, text in enumerate(limitations)
            )
            self.validation_limitations.setText(
                f"<b>{S.t('scenario.solution.validation.limitations')}</b><ul>{bullets}</ul>"
            )
        else:
            self.validation_limitations.setText("")

    def _render_diagnostics(self, payload: dict[str, Any]) -> None:
        headers = [
            S.t("scenario.solution.diagnostics.columns.field"),
            S.t("scenario.solution.diagnostics.columns.value"),
        ]
        table = self.diagnostics_table
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        diagnostics = payload.get("diagnostics") or {}
        rows = [(key, diagnostics[key]) for key in _DIAGNOSTIC_ROWS if key in diagnostics]
        extra = sorted(key for key in diagnostics if key not in _DIAGNOSTIC_ROWS)
        rows.extend((key, diagnostics[key]) for key in extra)
        table.setRowCount(len(rows))
        for index, (key, value) in enumerate(rows):
            label = S.t(f"scenario.solution.diagnostics.fields.{key}")
            if label == f"scenario.solution.diagnostics.fields.{key}":
                label = key
            table.setItem(index, 0, QTableWidgetItem(label))
            table.setItem(index, 1, QTableWidgetItem(_format_number(value)))
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        _fit_table_height(table)
        table.setVisible(bool(rows))

    # -- localization and theme -------------------------------------------
    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:24px; font-weight:700'>{S.t('scenario.solution.title')}</span>"
        )
        self.btn_back.setText(S.t("scenario.solution.back"))
        self.error_section.set_title(S.t("scenario.solution.error.section"))
        self.status_section.set_title(S.t("scenario.solution.status.section"))
        self.status_hint.setText(S.t("scenario.solution.status.hint"))
        for key in ("job", "mathematical", "termination", "validation"):
            self.status_labels[f"{key}_caption"].setText(
                S.t(f"scenario.solution.status.captions.{key}")
            )
        self.guarantee_section.set_title(S.t("scenario.solution.guarantee.section"))
        self.variables_section.set_title(S.t("scenario.solution.variables.section"))
        self.variables_hint.setText(S.t("scenario.solution.variables.hint"))
        self.variables_empty.setText(S.t("scenario.solution.variables.empty"))
        self.scenarios_section.set_title(S.t("scenario.solution.scenarios.section"))
        self.scenarios_hint.setText(S.t("scenario.solution.scenarios.hint"))
        self.scenarios_empty.setText(S.t("scenario.solution.scenarios.empty"))
        self.validation_section.set_title(S.t("scenario.solution.validation.section"))
        self.validation_hint.setText(S.t("scenario.solution.validation.hint"))
        self.diagnostics_section.set_title(S.t("scenario.solution.diagnostics.section"))
        self.diagnostics_hint.setText(S.t("scenario.solution.diagnostics.hint"))
        self.comparison_section.set_title(S.t("scenario.solution.comparison.section"))
        self.comparison.refresh_strings()
        self._render()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.error_code.setStyleSheet(f"color: {t.danger}; font-weight: 700;")
        self.guarantee_value.setStyleSheet(f"color: {t.accent}; font-size: 16px; font-weight: 700;")
        self.orientation_label.setStyleSheet(f"color: {t.text}; font-weight: 600;")
        self.binding_summary.setStyleSheet(f"color: {t.text}; font-weight: 600;")
        self.warnings_label.setStyleSheet(f"color: {t.warning};")
        for key in ("job", "mathematical", "termination", "validation"):
            self.status_labels[f"{key}_caption"].setStyleSheet(f"color: {t.text_muted};")
            self.status_labels[key].setStyleSheet(f"color: {t.text}; font-weight: 600;")
        for label in (
            self.status_hint,
            self.error_message,
            self.error_details,
            self.guarantee_hint,
            self.variables_hint,
            self.variables_empty,
            self.scenarios_hint,
            self.scenarios_empty,
            self.validation_hint,
            self.validation_limitations,
            self.diagnostics_hint,
        ):
            label.setStyleSheet(f"color: {t.text_muted};")
        self.comparison.refresh_theme()


def _orientation_key(orientation: str) -> str:
    return "min_max_loss" if orientation == "minimize_maximum_loss" else "max_min_reward"


def _localized_limitation(index: int, original: str) -> str:
    """Prefer the translated caveat, but never drop one we cannot translate."""
    key = f"scenario.solution.validation.limitation.{index + 1}"
    translated = S.t(key)
    return original if translated == key else translated
