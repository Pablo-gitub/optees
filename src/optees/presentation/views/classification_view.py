"""Formulation view for transparent local binary classification."""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
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
from optees.domain.entities.classification.dataset import ClassificationDataset
from optees.domain.models.classification.binary_classification_model import (
    BinaryClassificationModel,
    ClassificationOptions,
)
from optees.presentation.error_feedback import localized_error_detail
from optees.presentation.views.lp_view.section import Section
from optees.utility.classification_json_io import classification_model_from_file


class _InfoDialog(QDialog):
    def __init__(self, title: str, intro: str, html: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(520, 360)
        root = QVBoxLayout(self)
        label = QLabel(intro)
        label.setWordWrap(True)
        root.addWidget(label)
        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setHtml(html)
        root.addWidget(browser, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)


class ClassificationView(QWidget):
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
        intro_head = QHBoxLayout()
        self.intro_text = QLabel()
        self.intro_text.setWordWrap(True)
        intro_head.addWidget(self.intro_text, 1)
        self.btn_import_json = QPushButton()
        self.btn_import_json.setObjectName("classificationImportJsonButton")
        self.btn_import_json.clicked.connect(self._on_import_json)
        self.btn_json_info = self._info_button("classificationJsonInfoButton")
        self.btn_json_info.clicked.connect(lambda: self._show_info("import"))
        intro_head.addWidget(self.btn_import_json)
        intro_head.addWidget(self.btn_json_info)
        intro.body.addLayout(intro_head)
        intro_actions = QHBoxLayout()
        intro_actions.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_example.setObjectName("classificationExampleButton")
        self.btn_example.clicked.connect(self.example_requested.emit)
        self.btn_problem = QPushButton()
        self.btn_problem.setObjectName("classificationProblemButton")
        self.btn_problem.clicked.connect(self.problem_description_requested.emit)
        intro_actions.addWidget(self.btn_example)
        intro_actions.addWidget(self.btn_problem)
        intro.body.addLayout(intro_actions)
        root.addWidget(intro)

        dataset = Section()
        dataset_head = QHBoxLayout()
        self.dataset_hint = QLabel()
        self.dataset_hint.setWordWrap(True)
        dataset_head.addWidget(self.dataset_hint, 1)
        self.btn_dataset_info = self._info_button("classificationDatasetInfoButton")
        self.btn_dataset_info.clicked.connect(lambda: self._show_info("dataset"))
        dataset_head.addWidget(self.btn_dataset_info)
        dataset.body.addLayout(dataset_head)
        fields = QHBoxLayout()
        self.lbl_features = QLabel()
        self.edit_features = QLineEdit("feature_1")
        self.edit_features.setObjectName("classificationFeatureNames")
        self.lbl_target = QLabel()
        self.edit_target = QLineEdit("class")
        self.edit_target.setObjectName("classificationTargetName")
        self.btn_apply_columns = QPushButton()
        self.btn_apply_columns.setObjectName("classificationApplyColumnsButton")
        self.btn_apply_columns.clicked.connect(self._on_apply_columns)
        fields.addWidget(self.lbl_features)
        fields.addWidget(self.edit_features, 1)
        fields.addWidget(self.lbl_target)
        fields.addWidget(self.edit_target, 1)
        fields.addWidget(self.btn_apply_columns)
        dataset.body.addLayout(fields)
        self.lbl_rows = QLabel()
        dataset.body.addWidget(self.lbl_rows)
        self.data_table = QTableWidget()
        self.data_table.setObjectName("classificationDatasetTable")
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setMinimumHeight(230)
        dataset.body.addWidget(self.data_table)
        row_actions = QHBoxLayout()
        row_actions.addStretch(1)
        self.btn_add_row = QPushButton()
        self.btn_add_row.setObjectName("classificationAddRowButton")
        self.btn_add_row.clicked.connect(self._add_row)
        self.btn_remove_rows = QPushButton()
        self.btn_remove_rows.setObjectName("classificationRemoveRowsButton")
        self.btn_remove_rows.clicked.connect(self._remove_rows)
        row_actions.addWidget(self.btn_add_row)
        row_actions.addWidget(self.btn_remove_rows)
        dataset.body.addLayout(row_actions)
        root.addWidget(dataset)

        options = Section()
        options_head = QHBoxLayout()
        self.options_hint = QLabel()
        self.options_hint.setWordWrap(True)
        options_head.addWidget(self.options_hint, 1)
        self.btn_options_info = self._info_button("classificationOptionsInfoButton")
        self.btn_options_info.clicked.connect(lambda: self._show_info("training"))
        options_head.addWidget(self.btn_options_info)
        options.body.addLayout(options_head)
        option_fields = QHBoxLayout()
        self.lbl_method = QLabel()
        self.value_method = QLabel()
        self.lbl_test_fraction = QLabel()
        self.edit_test_fraction = QLineEdit("0.25")
        self.edit_test_fraction.setObjectName("classificationTestFraction")
        self.edit_test_fraction.setFixedWidth(82)
        self.lbl_seed = QLabel()
        self.edit_seed = QLineEdit("42")
        self.edit_seed.setObjectName("classificationRandomSeed")
        self.edit_seed.setFixedWidth(82)
        self.lbl_learning_rate = QLabel()
        self.edit_learning_rate = QLineEdit("0.1")
        self.edit_learning_rate.setObjectName("classificationLearningRate")
        self.edit_learning_rate.setFixedWidth(82)
        self.lbl_iterations = QLabel()
        self.edit_iterations = QLineEdit("2000")
        self.edit_iterations.setObjectName("classificationMaxIterations")
        self.edit_iterations.setFixedWidth(82)
        self.lbl_l2_alpha = QLabel()
        self.edit_l2_alpha = QLineEdit("0")
        self.edit_l2_alpha.setObjectName("classificationL2Alpha")
        self.edit_l2_alpha.setFixedWidth(82)
        for widget in (
            self.lbl_method, self.value_method, self.lbl_test_fraction, self.edit_test_fraction,
            self.lbl_seed, self.edit_seed, self.lbl_learning_rate, self.edit_learning_rate,
            self.lbl_iterations, self.edit_iterations, self.lbl_l2_alpha, self.edit_l2_alpha,
        ):
            option_fields.addWidget(widget)
        option_fields.addStretch(1)
        options.body.addLayout(option_fields)
        root.addWidget(options)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_train = QPushButton()
        self.btn_train.setObjectName("classificationTrainButton")
        self.btn_train.clicked.connect(self._on_train)
        actions.addWidget(self.btn_train)
        root.addLayout(actions)
        root.addStretch(1)

        self._set_table_columns(("feature_1",), "class", row_count=6)
        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()

    def set_solve_usecase(self, usecase) -> None:
        self._solve_usecase = usecase

    def set_model(self, model: BinaryClassificationModel) -> None:
        self.edit_features.setText(", ".join(model.dataset.feature_names))
        self.edit_target.setText(model.dataset.target_name)
        self._set_table_columns(model.dataset.feature_names, model.dataset.target_name, model.dataset.row_count)
        for row_index, (features, target) in enumerate(
            zip(model.dataset.feature_rows, model.dataset.target_values, strict=True)
        ):
            for column_index, value in enumerate((*features, target)):
                self._set_cell(row_index, column_index, _format(value))
        self.edit_test_fraction.setText(_format(model.options.test_fraction))
        self.edit_seed.setText(str(model.options.random_seed))
        self.edit_learning_rate.setText(_format(model.options.learning_rate))
        self.edit_iterations.setText(str(model.options.max_iterations))
        self.edit_l2_alpha.setText(_format(model.options.l2_alpha))

    def current_model(self) -> BinaryClassificationModel:
        features = self._feature_names()
        target_name = self.edit_target.text().strip()
        if not target_name:
            raise ValueError("Classification target name is required")
        rows: list[tuple[tuple[float, ...], str]] = []
        for row_index in range(self.data_table.rowCount()):
            values = [self._cell_text(row_index, column) for column in range(self.data_table.columnCount())]
            if not any(values):
                continue
            if not all(values):
                raise ValueError(f"Classification row {row_index + 1} is incomplete")
            try:
                feature_values = tuple(_finite_number(value) for value in values[:-1])
            except ValueError as exc:
                raise ValueError(f"Classification row {row_index + 1} contains an invalid feature") from exc
            rows.append((feature_values, values[-1]))
        options = ClassificationOptions(
            test_fraction=_finite_number(self.edit_test_fraction.text()),
            random_seed=_non_negative_integer(self.edit_seed.text()),
            learning_rate=_finite_number(self.edit_learning_rate.text()),
            max_iterations=_positive_integer(self.edit_iterations.text()),
            l2_alpha=_finite_number(self.edit_l2_alpha.text()),
        )
        return BinaryClassificationModel(
            ClassificationDataset.from_rows(feature_names=features, target_name=target_name, rows=rows),
            options,
        )

    def refresh_strings(self) -> None:
        self.title.setText(f"<span style='font-size:22px; font-weight:700'>{S.t('classification.header.title')}</span>")
        self.intro_text.setText(S.t("classification.header.description"))
        self.btn_import_json.setText(S.t("classification.import.button"))
        self.btn_json_info.setText("i")
        self.btn_json_info.setToolTip(S.t("classification.import.info_tooltip"))
        self.btn_example.setText(S.t("classification.header.buttons.example"))
        self.btn_problem.setText(S.t("classification.header.buttons.problem"))
        self.dataset_hint.setText(S.t("classification.dataset.hint"))
        self.btn_dataset_info.setText("i")
        self.btn_dataset_info.setToolTip(S.t("classification.dataset.info_tooltip"))
        self.lbl_features.setText(S.t("classification.dataset.features"))
        self.edit_features.setPlaceholderText(S.t("classification.dataset.features_placeholder"))
        self.lbl_target.setText(S.t("classification.dataset.target"))
        self.edit_target.setPlaceholderText(S.t("classification.dataset.target_placeholder"))
        self.btn_apply_columns.setText(S.t("classification.dataset.apply_columns"))
        self.lbl_rows.setText(S.t("classification.dataset.rows"))
        self.btn_add_row.setText(S.t("classification.dataset.add"))
        self.btn_remove_rows.setText(S.t("classification.dataset.remove"))
        self.options_hint.setText(S.t("classification.training.hint"))
        self.btn_options_info.setText("i")
        self.btn_options_info.setToolTip(S.t("classification.training.info_tooltip"))
        self.lbl_method.setText(S.t("classification.training.method"))
        self.value_method.setText(S.t("classification.training.logistic"))
        self.lbl_test_fraction.setText(S.t("classification.training.test_fraction"))
        self.lbl_seed.setText(S.t("classification.training.seed"))
        self.lbl_learning_rate.setText(S.t("classification.training.learning_rate"))
        self.lbl_iterations.setText(S.t("classification.training.max_iterations"))
        self.lbl_l2_alpha.setText(S.t("classification.training.l2_alpha"))
        self.btn_train.setText(S.t("classification.actions.train"))
        self._set_headers(self._feature_names_or_default(), self._target_or_default())

    def refresh_theme(self) -> None:
        t = tokens(theme.is_dark())
        for label in (self.title, self.intro_text, self.dataset_hint, self.options_hint):
            label.setStyleSheet(f"color: {t.text if label is self.title else t.text_muted};")

    def _on_apply_columns(self) -> None:
        try:
            self._set_table_columns(self._feature_names(), self._target_name(), self.data_table.rowCount(), preserve=True)
        except ValueError as exc:
            self._show_validation_error(exc)

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, S.t("classification.import.dialog_title"), "", "JSON (*.json);;All files (*)")
        if not path:
            return
        try:
            self.set_model(classification_model_from_file(path))
        except ValueError as exc:
            QMessageBox.warning(
                self,
                S.t("classification.import.error_title"),
                S.t("classification.import.error_body", detail=localized_error_detail("classification_import", exc)),
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

    def _show_validation_error(self, error: Exception) -> None:
        QMessageBox.warning(
            self,
            S.t("classification.validation.title"),
            S.t("classification.validation.body", detail=localized_error_detail("classification_validation", error)),
        )

    def _show_info(self, topic: str) -> None:
        dialog = _InfoDialog(
            S.t(f"classification.{topic}.info_title"),
            S.t(f"classification.{topic}.info_body"),
            S.t(f"classification.{topic}.info_html"),
            self,
        )
        dialog.exec()

    def _set_table_columns(self, features: tuple[str, ...], target: str, row_count: int, preserve: bool = False) -> None:
        prior = self._table_values() if preserve else []
        self.data_table.setColumnCount(len(features) + 1)
        self.data_table.setRowCount(max(0, row_count))
        self._set_headers(features, target)
        for row_index, row in enumerate(prior[:row_count]):
            for column_index, value in enumerate(row[: self.data_table.columnCount()]):
                self._set_cell(row_index, column_index, value)

    def _set_headers(self, features: tuple[str, ...], target: str) -> None:
        if self.data_table.columnCount() != len(features) + 1:
            return
        self.data_table.setHorizontalHeaderLabels([*features, target])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _table_values(self) -> list[list[str]]:
        return [
            [self._cell_text(row, column) for column in range(self.data_table.columnCount())]
            for row in range(self.data_table.rowCount())
        ]

    def _add_row(self) -> None:
        self.data_table.insertRow(self.data_table.rowCount())

    def _remove_rows(self) -> None:
        rows = sorted({index.row() for index in self.data_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.data_table.removeRow(row)

    def _feature_names(self) -> tuple[str, ...]:
        names = tuple(part.strip() for part in self.edit_features.text().split(",") if part.strip())
        if not names or len(set(names)) != len(names):
            raise ValueError("Classification feature names must be non-empty and unique")
        return names

    def _feature_names_or_default(self) -> tuple[str, ...]:
        try:
            return self._feature_names()
        except ValueError:
            return ("feature_1",)

    def _target_name(self) -> str:
        target = self.edit_target.text().strip()
        if not target:
            raise ValueError("Classification target name is required")
        return target

    def _target_or_default(self) -> str:
        try:
            return self._target_name()
        except ValueError:
            return "class"

    def _cell_text(self, row: int, column: int) -> str:
        item = self.data_table.item(row, column)
        return item.text().strip() if item is not None else ""

    def _set_cell(self, row: int, column: int, value: str) -> None:
        item = self.data_table.item(row, column) or QTableWidgetItem()
        item.setText(value)
        self.data_table.setItem(row, column, item)

    @staticmethod
    def _info_button(object_name: str) -> QPushButton:
        button = QPushButton("i")
        button.setObjectName(object_name)
        button.setProperty("variant", "info")
        button.setFixedSize(24, 24)
        button.setCursor(Qt.PointingHandCursor)
        return button


def _finite_number(value: str) -> float:
    normalized = value.strip().replace(",", ".")
    if not normalized:
        raise ValueError("number is required")
    try:
        result = float(normalized)
    except ValueError as exc:
        raise ValueError("number must be finite") from exc
    if not math.isfinite(result):
        raise ValueError("number must be finite")
    return result


def _non_negative_integer(value: str) -> int:
    normalized = _finite_number(value)
    if not normalized.is_integer() or normalized < 0:
        raise ValueError("seed must be a non-negative integer")
    return int(normalized)


def _positive_integer(value: str) -> int:
    normalized = _finite_number(value)
    if not normalized.is_integer() or normalized < 1:
        raise ValueError("max iterations must be a positive integer")
    return int(normalized)


def _format(value: object) -> str:
    return f"{value:g}" if isinstance(value, float) else str(value)
