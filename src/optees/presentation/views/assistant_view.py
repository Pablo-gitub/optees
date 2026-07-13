from __future__ import annotations

import json
from typing import Any, Mapping

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.assistant import AssistantAnalysis


class AssistantView(QWidget):
    back_requested = Signal()
    load_lp_requested = Signal(object)
    load_milp_requested = Signal(object)
    load_knapsack_requested = Signal(object)
    load_regression_requested = Signal(object)
    load_classification_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._usecase = None
        self._analysis: AssistantAnalysis | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignTop)
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
        self.btn_back.clicked.connect(self.back_requested.emit)
        header.addWidget(self.btn_back)
        root.addLayout(header)

        self.intro = QLabel()
        self.intro.setWordWrap(True)
        root.addWidget(self.intro)

        prompt_section = self._make_section()
        prompt_layout = QVBoxLayout(prompt_section)
        prompt_layout.setContentsMargins(18, 18, 18, 18)
        prompt_layout.setSpacing(10)
        self.prompt_label = QLabel()
        prompt_layout.addWidget(self.prompt_label)
        self.prompt = QTextEdit()
        self.prompt.setObjectName("assistantPrompt")
        self.prompt.setMinimumHeight(150)
        self.prompt.setPlaceholderText("")
        prompt_layout.addWidget(self.prompt)
        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_analyze = QPushButton()
        self.btn_analyze.setObjectName("assistantAnalyzeButton")
        self.btn_analyze.clicked.connect(self._on_analyze)
        actions.addWidget(self.btn_analyze)
        prompt_layout.addLayout(actions)
        root.addWidget(prompt_section)

        self.result_section = self._make_section()
        result_layout = QVBoxLayout(self.result_section)
        result_layout.setContentsMargins(18, 18, 18, 18)
        result_layout.setSpacing(12)

        self.result_title = QLabel()
        self.result_title.setTextFormat(Qt.RichText)
        result_layout.addWidget(self.result_title)

        summary_grid = QGridLayout()
        summary_grid.setColumnStretch(1, 1)
        summary_grid.setHorizontalSpacing(18)
        summary_grid.setVerticalSpacing(8)
        self.lbl_family_key = QLabel()
        self.lbl_variant_key = QLabel()
        self.lbl_confidence_key = QLabel()
        self.lbl_status_key = QLabel()
        self.lbl_family_value = QLabel()
        self.lbl_variant_value = QLabel()
        self.lbl_confidence_value = QLabel()
        self.lbl_status_value = QLabel()
        for row, (key, value) in enumerate(
            (
                (self.lbl_family_key, self.lbl_family_value),
                (self.lbl_variant_key, self.lbl_variant_value),
                (self.lbl_confidence_key, self.lbl_confidence_value),
                (self.lbl_status_key, self.lbl_status_value),
            )
        ):
            summary_grid.addWidget(key, row, 0)
            summary_grid.addWidget(value, row, 1)
        result_layout.addLayout(summary_grid)

        self.reasons_label = QLabel()
        self.reasons_label.setTextFormat(Qt.RichText)
        self.reasons_label.setWordWrap(True)
        result_layout.addWidget(self.reasons_label)

        self.missing_label = QLabel()
        self.missing_label.setTextFormat(Qt.RichText)
        self.missing_label.setWordWrap(True)
        result_layout.addWidget(self.missing_label)

        self.json_label = QLabel()
        result_layout.addWidget(self.json_label)
        self.json_preview = QPlainTextEdit()
        self.json_preview.setReadOnly(True)
        self.json_preview.setMinimumHeight(190)
        self.json_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        result_layout.addWidget(self.json_preview)

        load_actions = QHBoxLayout()
        load_actions.addStretch(1)
        self.btn_load = QPushButton()
        self.btn_load.setObjectName("assistantLoadButton")
        self.btn_load.clicked.connect(self._on_load)
        load_actions.addWidget(self.btn_load)
        result_layout.addLayout(load_actions)

        root.addWidget(self.result_section)
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()
        self._render_empty_result()

    def set_usecase(self, usecase) -> None:
        self._usecase = usecase

    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:22px; font-weight:700'>{S.t('assistant.title')}</span>"
        )
        self.btn_back.setText(S.t("assistant.actions.back"))
        self.intro.setText(S.t("assistant.intro"))
        self.prompt_label.setText(S.t("assistant.prompt.label"))
        self.prompt.setPlaceholderText(S.t("assistant.prompt.placeholder"))
        self.btn_analyze.setText(S.t("assistant.actions.analyze"))
        self.result_title.setText(
            f"<span style='font-size:17px; font-weight:700'>{S.t('assistant.result.title')}</span>"
        )
        self.lbl_family_key.setText(S.t("assistant.result.family"))
        self.lbl_variant_key.setText(S.t("assistant.result.variant"))
        self.lbl_confidence_key.setText(S.t("assistant.result.confidence"))
        self.lbl_status_key.setText(S.t("assistant.result.status"))
        self.json_label.setText(S.t("assistant.result.json_preview"))
        self._render_analysis(self._analysis)

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.intro.setStyleSheet(f"color: {t.text_muted};")
        for section in (self.result_section,):
            section.setStyleSheet(
                f"QFrame {{ border: 1px solid {t.border}; border-radius: 8px; background: {t.surface}; }}"
            )
        for label in (
            self.prompt_label,
            self.result_title,
            self.lbl_family_key,
            self.lbl_variant_key,
            self.lbl_confidence_key,
            self.lbl_status_key,
            self.json_label,
        ):
            label.setStyleSheet(f"color: {t.text};")
        for label in (
            self.lbl_family_value,
            self.lbl_variant_value,
            self.lbl_confidence_value,
            self.lbl_status_value,
            self.reasons_label,
            self.missing_label,
        ):
            label.setStyleSheet(f"color: {t.text_muted};")

    def _make_section(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("assistantSection")
        t = tokens(theme.is_dark())
        frame.setStyleSheet(
            f"QFrame {{ border: 1px solid {t.border}; border-radius: 8px; background: {t.surface}; }}"
        )
        return frame

    def _on_analyze(self) -> None:
        if self._usecase is None:
            return
        self._analysis = self._usecase.execute(
            self.prompt.toPlainText(),
            language=S.current_language(),
        )
        self._render_analysis(self._analysis)

    def _on_load(self) -> None:
        analysis = self._analysis
        if analysis is None or not analysis.is_loadable or analysis.model_json is None:
            return

        confirm = QMessageBox(self)
        confirm.setWindowTitle(S.t("assistant.confirm.title"))
        confirm.setText(S.t("assistant.confirm.body"))
        confirm.setIcon(QMessageBox.Icon.NoIcon)
        confirm.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        confirm.setDefaultButton(QMessageBox.StandardButton.No)
        answer = confirm.exec()
        if answer != QMessageBox.StandardButton.Yes:
            return

        payload = dict(analysis.model_json)
        if analysis.load_target == "lp":
            self.load_lp_requested.emit(payload)
        elif analysis.load_target == "milp":
            self.load_milp_requested.emit(payload)
        elif analysis.load_target == "knapsack":
            self.load_knapsack_requested.emit(payload)
        elif analysis.load_target == "regression":
            self.load_regression_requested.emit(payload)
        elif analysis.load_target == "classification":
            self.load_classification_requested.emit(payload)

    def _render_empty_result(self) -> None:
        self.lbl_family_value.setText("-")
        self.lbl_variant_value.setText("-")
        self.lbl_confidence_value.setText("-")
        self.lbl_status_value.setText(S.t("assistant.status.waiting"))
        self.reasons_label.setText("")
        self.missing_label.setText("")
        self.json_preview.setPlainText("")
        self.json_preview.setVisible(False)
        self.json_label.setVisible(False)
        self.btn_load.setVisible(False)

    def _render_analysis(self, analysis: AssistantAnalysis | None) -> None:
        if analysis is None:
            self._render_empty_result()
            return
        self.lbl_family_value.setText(S.t(f"assistant.family.{analysis.family}"))
        self.lbl_variant_value.setText(_humanize_token(analysis.variant))
        self.lbl_confidence_value.setText(f"{analysis.confidence:.0%}")
        self.lbl_status_value.setText(
            S.t("assistant.status.unknown")
            if analysis.family == "unknown"
            else S.t("assistant.status.loadable")
            if analysis.is_loadable
            else S.t("assistant.status.guidance")
            if analysis.implemented
            else S.t("assistant.status.planned")
        )
        self.reasons_label.setText(
            _html_list(S.t("assistant.result.reasons"), analysis.reasons)
        )
        details = tuple(analysis.missing_information) + tuple(analysis.validation_errors)
        self.missing_label.setText(
            _html_list(S.t("assistant.result.missing"), details) if details else ""
        )

        if analysis.model_json is not None:
            self.json_preview.setPlainText(
                json.dumps(analysis.model_json, indent=2, ensure_ascii=False)
            )
            self.json_preview.setVisible(True)
            self.json_label.setVisible(True)
        else:
            self.json_preview.setPlainText("")
            self.json_preview.setVisible(False)
            self.json_label.setVisible(False)

        self.btn_load.setText(
            S.t(
                "assistant.actions.load",
                target=S.t(f"assistant.family.{analysis.load_target or analysis.family}"),
            )
        )
        self.btn_load.setVisible(analysis.is_loadable)


def _humanize_token(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").title()


def _html_list(title: str, values: tuple[str, ...]) -> str:
    if not values:
        return ""
    items = "".join(f"<li>{_escape_html(item)}</li>" for item in values)
    return f"<b>{_escape_html(title)}</b><ul>{items}</ul>"


def _escape_html(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
