"""Formulation view for the first local educational regression workflow."""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.error_feedback import localized_error_detail
from optees.domain.entities.regression.dataset import RegressionDataset
from optees.domain.models.regression.regression_model import RegressionModel, RegressionOptions
from optees.domain.value_objects.regression.regression_method import RegressionMethod
from optees.presentation.views.lp_view.section import Section
from optees.utility.regression_json_io import regression_model_from_file


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
        self.setMinimumSize(520, 360)
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


class RegressionView(QWidget):
    """Collect a numeric dataset and train a reproducible OLS or Ridge model."""

    solve_completed = Signal(object)
    example_requested = Signal()
    problem_description_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._solve_usecase = None

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

        intro = Section()
        intro_header = QHBoxLayout()
        self.intro_text = QLabel()
        self.intro_text.setWordWrap(True)
        intro_header.addWidget(self.intro_text, 1)
        self.btn_import_json = QPushButton()
        self.btn_import_json.setObjectName("regressionImportJsonButton")
        self.btn_import_json.clicked.connect(self._on_import_json)
        self.btn_json_info = _make_info_button("regressionJsonInfoButton")
        self.btn_json_info.clicked.connect(lambda: self._show_info("import"))
        intro_header.addWidget(self.btn_import_json)
        intro_header.addWidget(self.btn_json_info)
        intro.body.addLayout(intro_header)
        intro_actions = QHBoxLayout()
        intro_actions.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_example.setObjectName("regressionExampleButton")
        self.btn_example.clicked.connect(self.example_requested.emit)
        self.btn_problem = QPushButton()
        self.btn_problem.setObjectName("regressionProblemButton")
        self.btn_problem.clicked.connect(self.problem_description_requested.emit)
        intro_actions.addWidget(self.btn_example)
        intro_actions.addWidget(self.btn_problem)
        intro.body.addLayout(intro_actions)
        self.intro_section = intro
        root.addWidget(intro)

        dataset = Section()
        dataset_header = QHBoxLayout()
        self.dataset_hint = QLabel()
        self.dataset_hint.setWordWrap(True)
        dataset_header.addWidget(self.dataset_hint, 1)
        self.btn_dataset_info = _make_info_button("regressionDatasetInfoButton")
        self.btn_dataset_info.clicked.connect(lambda: self._show_info("dataset"))
        dataset_header.addWidget(self.btn_dataset_info)
        dataset.body.addLayout(dataset_header)

        schema = QHBoxLayout()
        self.lbl_features = QLabel()
        self.edit_features = QLineEdit("feature_1")
        self.edit_features.setObjectName("regressionFeatureNames")
        self.lbl_target = QLabel()
        self.edit_target = QLineEdit("target")
        self.edit_target.setObjectName("regressionTargetName")
        self.btn_apply_columns = QPushButton()
        self.btn_apply_columns.setObjectName("regressionApplyColumnsButton")
        self.btn_apply_columns.clicked.connect(self._on_apply_columns)
        schema.addWidget(self.lbl_features)
        schema.addWidget(self.edit_features, 1)
        schema.addWidget(self.lbl_target)
        schema.addWidget(self.edit_target, 1)
        schema.addWidget(self.btn_apply_columns)
        dataset.body.addLayout(schema)

        self.lbl_rows = QLabel()
        dataset.body.addWidget(self.lbl_rows)
        self.data_table = QTableWidget()
        self.data_table.setObjectName("regressionDatasetTable")
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setMinimumHeight(230)
        dataset.body.addWidget(self.data_table)
        data_actions = QHBoxLayout()
        data_actions.addStretch(1)
        self.btn_add_row = QPushButton()
        self.btn_add_row.setObjectName("regressionAddRowButton")
        self.btn_add_row.clicked.connect(self._add_row)
        self.btn_remove_rows = QPushButton()
        self.btn_remove_rows.setObjectName("regressionRemoveRowsButton")
        self.btn_remove_rows.clicked.connect(self._remove_selected_rows)
        data_actions.addWidget(self.btn_add_row)
        data_actions.addWidget(self.btn_remove_rows)
        dataset.body.addLayout(data_actions)
        self.dataset_section = dataset
        root.addWidget(dataset)

        training = Section()
        training_header = QHBoxLayout()
        self.training_hint = QLabel()
        self.training_hint.setWordWrap(True)
        training_header.addWidget(self.training_hint, 1)
        self.btn_training_info = _make_info_button("regressionTrainingInfoButton")
        self.btn_training_info.clicked.connect(lambda: self._show_info("training"))
        training_header.addWidget(self.btn_training_info)
        training.body.addLayout(training_header)
        options = QHBoxLayout()
        self.lbl_method = QLabel()
        self.combo_method = QComboBox()
        self.combo_method.setObjectName("regressionMethod")
        self.combo_method.addItem("", RegressionMethod.OLS.value)
        self.combo_method.addItem("", RegressionMethod.RIDGE.value)
        self.combo_method.currentIndexChanged.connect(self._update_method_controls)
        self.lbl_test_fraction = QLabel()
        self.edit_test_fraction = QLineEdit("0.2")
        self.edit_test_fraction.setObjectName("regressionTestFraction")
        self.edit_test_fraction.setFixedWidth(90)
        self.lbl_seed = QLabel()
        self.edit_seed = QLineEdit("42")
        self.edit_seed.setObjectName("regressionRandomSeed")
        self.edit_seed.setFixedWidth(90)
        self.lbl_ridge_alpha = QLabel()
        self.edit_ridge_alpha = QLineEdit("1.0")
        self.edit_ridge_alpha.setObjectName("regressionRidgeAlpha")
        self.edit_ridge_alpha.setFixedWidth(90)
        options.addWidget(self.lbl_method)
        options.addWidget(self.combo_method)
        options.addSpacing(12)
        options.addWidget(self.lbl_test_fraction)
        options.addWidget(self.edit_test_fraction)
        options.addSpacing(12)
        options.addWidget(self.lbl_seed)
        options.addWidget(self.edit_seed)
        options.addSpacing(12)
        options.addWidget(self.lbl_ridge_alpha)
        options.addWidget(self.edit_ridge_alpha)
        options.addStretch(1)
        training.body.addLayout(options)
        self.training_section = training
        root.addWidget(training)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_train = QPushButton()
        self.btn_train.setObjectName("regressionTrainButton")
        self.btn_train.clicked.connect(self._on_train)
        actions.addWidget(self.btn_train)
        root.addLayout(actions)
        root.addStretch(1)

        self._set_table_columns(("feature_1",), "target", row_count=6)
        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()

    def set_solve_usecase(self, usecase) -> None:
        self._solve_usecase = usecase

    def set_model(self, model: RegressionModel) -> None:
        self.edit_features.setText(", ".join(model.dataset.feature_names))
        self.edit_target.setText(model.dataset.target_name)
        self._set_table_columns(
            model.dataset.feature_names,
            model.dataset.target_name,
            row_count=model.dataset.row_count,
        )
        for row_index, (features, target) in enumerate(
            zip(model.dataset.feature_rows, model.dataset.target_values, strict=True)
        ):
            for column_index, value in enumerate((*features, target)):
                self._set_cell_text(row_index, column_index, _format_number(value))
        self.combo_method.setCurrentIndex(
            max(0, self.combo_method.findData(model.options.method.value))
        )
        self.edit_test_fraction.setText(_format_number(model.options.test_fraction))
        self.edit_seed.setText(str(model.options.random_seed))
        self.edit_ridge_alpha.setText(_format_number(model.options.ridge_alpha))
        self._update_method_controls()

    def current_model(self) -> RegressionModel:
        feature_names = self._feature_names_from_text()
        target_name = self.edit_target.text().strip()
        if not target_name:
            raise ValueError("target name is required")
        rows: list[tuple[tuple[float, ...], float]] = []
        for row_index in range(self.data_table.rowCount()):
            cells = [
                self._cell_text(row_index, column_index)
                for column_index in range(self.data_table.columnCount())
            ]
            if not any(cells):
                continue
            if not all(cells):
                raise ValueError(f"observation row {row_index + 1} is incomplete")
            values = tuple(
                _parse_number(cell, f"observation row {row_index + 1}")
                for cell in cells
            )
            rows.append((values[:-1], values[-1]))
        try:
            seed = int(self.edit_seed.text().strip())
        except ValueError as exc:
            raise ValueError("random seed must be a non-negative integer") from exc
        return RegressionModel(
            dataset=RegressionDataset.from_rows(
                feature_names=feature_names,
                target_name=target_name,
                rows=rows,
            ),
            options=RegressionOptions(
                method=RegressionMethod.from_str(self.combo_method.currentData()),
                test_fraction=_parse_number(self.edit_test_fraction.text(), "test fraction"),
                random_seed=seed,
                ridge_alpha=_parse_number(self.edit_ridge_alpha.text(), "Ridge alpha"),
            ),
        )

    def refresh_strings(self) -> None:
        self.title.setText(
            f"<span style='font-size:26px; font-weight:700'>{S.t('regression.header.title')}</span>"
        )
        self.intro_section.set_title(S.t("regression.header.section"))
        self.intro_text.setText(S.t("regression.header.description"))
        self.btn_import_json.setText(S.t("regression.import.button"))
        self.btn_json_info.setToolTip(S.t("regression.import.info_tooltip"))
        self.btn_example.setText(S.t("regression.header.buttons.example"))
        self.btn_problem.setText(S.t("regression.header.buttons.problem"))
        self.dataset_section.set_title(S.t("regression.dataset.section"))
        self.dataset_hint.setText(S.t("regression.dataset.hint"))
        self.btn_dataset_info.setToolTip(S.t("regression.dataset.info_tooltip"))
        self.lbl_features.setText(S.t("regression.dataset.features"))
        self.edit_features.setPlaceholderText(S.t("regression.dataset.features_placeholder"))
        self.lbl_target.setText(S.t("regression.dataset.target"))
        self.edit_target.setPlaceholderText(S.t("regression.dataset.target_placeholder"))
        self.btn_apply_columns.setText(S.t("regression.dataset.apply_columns"))
        self.lbl_rows.setText(S.t("regression.dataset.rows"))
        self.btn_add_row.setText(S.t("regression.dataset.add"))
        self.btn_remove_rows.setText(S.t("regression.dataset.remove"))
        self.training_section.set_title(S.t("regression.training.section"))
        self.training_hint.setText(S.t("regression.training.hint"))
        self.btn_training_info.setToolTip(S.t("regression.training.info_tooltip"))
        self.lbl_method.setText(S.t("regression.training.method"))
        self.combo_method.setItemText(0, S.t("regression.training.ols"))
        self.combo_method.setItemText(1, S.t("regression.training.ridge"))
        self.lbl_test_fraction.setText(S.t("regression.training.test_fraction"))
        self.lbl_seed.setText(S.t("regression.training.seed"))
        self.lbl_ridge_alpha.setText(S.t("regression.training.ridge_alpha"))
        self.btn_train.setText(S.t("regression.actions.train"))
        self._refresh_table_headers()

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {t.text};")
        self.intro_text.setStyleSheet(f"color: {t.text_muted};")
        self.dataset_hint.setStyleSheet(f"color: {t.text_muted};")
        self.training_hint.setStyleSheet(f"color: {t.text_muted};")

    def _on_apply_columns(self) -> None:
        try:
            self._set_table_columns(
                self._feature_names_from_text(),
                self._target_name_from_text(),
                row_count=max(6, self.data_table.rowCount()),
                preserve=True,
            )
        except ValueError as exc:
            self._show_validation_error(exc)

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            S.t("regression.import.dialog_title"),
            "",
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            self.set_model(regression_model_from_file(path))
        except ValueError as exc:
            QMessageBox.warning(
                self,
                S.t("regression.import.error_title"),
                S.t("regression.import.error_body", detail=localized_error_detail("regression_import", exc)),
            )

    def _on_train(self) -> None:
        if self._solve_usecase is None:
            return
        try:
            model = self.current_model()
        except ValueError as exc:
            self._show_validation_error(exc)
            return
        self.solve_completed.emit(self._solve_usecase.execute(model))

    def _show_validation_error(self, exc: Exception) -> None:
        QMessageBox.warning(
            self,
            S.t("regression.validation.title"),
            S.t("regression.validation.body", detail=localized_error_detail("regression_validation", exc)),
        )

    def _show_info(self, topic: str) -> None:
        _InfoDialog(
            S.t(f"regression.{topic}.info_title"),
            S.t(f"regression.{topic}.info_body"),
            S.t(f"regression.{topic}.info_html"),
            self,
        ).exec()

    def _feature_names_from_text(self) -> tuple[str, ...]:
        feature_names = tuple(
            name.strip() for name in self.edit_features.text().split(",") if name.strip()
        )
        if not feature_names:
            raise ValueError("at least one feature name is required")
        if len(feature_names) != len(set(feature_names)):
            raise ValueError("feature names must be unique")
        return feature_names

    def _target_name_from_text(self) -> str:
        target_name = self.edit_target.text().strip()
        if not target_name:
            raise ValueError("target name is required")
        return target_name

    def _set_table_columns(
        self,
        feature_names: tuple[str, ...],
        target_name: str,
        *,
        row_count: int,
        preserve: bool = False,
    ) -> None:
        previous: dict[str, list[str]] = {}
        if preserve:
            for column_index in range(self.data_table.columnCount()):
                header = self.data_table.horizontalHeaderItem(column_index)
                if header is not None:
                    previous[header.text()] = [
                        self._cell_text(row_index, column_index)
                        for row_index in range(self.data_table.rowCount())
                    ]
        headers = (*feature_names, target_name)
        self.data_table.clear()
        self.data_table.setColumnCount(len(headers))
        self.data_table.setRowCount(row_count)
        self.data_table.setHorizontalHeaderLabels(list(headers))
        self.data_table.horizontalHeader().setStretchLastSection(True)
        for column_index in range(len(headers) - 1):
            self.data_table.horizontalHeader().setSectionResizeMode(
                column_index,
                QHeaderView.Stretch,
            )
        for column_index, header in enumerate(headers):
            for row_index, value in enumerate(previous.get(header, ())[:row_count]):
                self._set_cell_text(row_index, column_index, value)
        self._refresh_table_headers()

    def _refresh_table_headers(self) -> None:
        for column_index in range(self.data_table.columnCount()):
            for row_index in range(self.data_table.rowCount()):
                item = self.data_table.item(row_index, column_index)
                if item is None:
                    item = QTableWidgetItem()
                    item.setTextAlignment(Qt.AlignCenter)
                    self.data_table.setItem(row_index, column_index, item)
                item.setToolTip(S.t("regression.dataset.value_placeholder"))

    def _add_row(self) -> None:
        self.data_table.insertRow(self.data_table.rowCount())
        self._refresh_table_headers()

    def _remove_selected_rows(self) -> None:
        row_indices = sorted({index.row() for index in self.data_table.selectedIndexes()}, reverse=True)
        for row_index in row_indices:
            self.data_table.removeRow(row_index)
        if self.data_table.rowCount() == 0:
            self._add_row()

    def _update_method_controls(self) -> None:
        ridge_enabled = self.combo_method.currentData() == RegressionMethod.RIDGE.value
        self.lbl_ridge_alpha.setEnabled(ridge_enabled)
        self.edit_ridge_alpha.setEnabled(ridge_enabled)

    def _cell_text(self, row_index: int, column_index: int) -> str:
        item = self.data_table.item(row_index, column_index)
        return item.text().strip() if item is not None else ""

    def _set_cell_text(self, row_index: int, column_index: int, text: str) -> None:
        item = self.data_table.item(row_index, column_index)
        if item is None:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignCenter)
            self.data_table.setItem(row_index, column_index, item)
        item.setText(text)


def _parse_number(text: str, label: str) -> float:
    normalized = text.strip().replace(",", ".")
    if not normalized:
        raise ValueError(f"{label} is required")
    try:
        value = float(normalized)
    except ValueError as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return value


def _format_number(value: float) -> str:
    return f"{float(value):.10g}"
