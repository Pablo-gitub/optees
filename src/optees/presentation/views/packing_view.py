from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from optees.core.design import tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.application.services.packing_complexity import (
    PackingComplexityLevel,
    estimate_packing_complexity,
)
from optees.domain.entities.packing.container import PackingContainer
from optees.domain.entities.packing.geometry import Dimensions3D, generate_orientations
from optees.domain.entities.packing.item import PackingItem
from optees.domain.entities.packing.resource import ResourceCapacity, ResourceConsumption
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.domain.value_objects.packing.rotation_policy import RotationPolicy
from optees.domain.value_objects.packing.selection_policy import PackingSelectionPolicy
from optees.domain.value_objects.packing.gravity_mode import PackingGravityMode
from optees.presentation.error_feedback import localized_error_detail
from optees.presentation.views.lp_view.section import Section
from optees.utility.packing_json_io import packing_model_from_file


_BASE_ITEM_COLUMNS = 10


class _WorkerSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class _SolveWorker(QRunnable):
    def __init__(self, usecase: object, model: SingleContainerPackingModel) -> None:
        super().__init__()
        self.usecase = usecase
        self.model = model
        self.signals = _WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self.usecase.execute(self.model)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            self.signals.failed.emit(str(exc))
            return
        self.signals.completed.emit(result)


class PackingView(QWidget):
    solve_completed = Signal(object)
    example_requested = Signal()
    problem_description_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._solve_usecase = None
        self._worker: Optional[_SolveWorker] = None
        self._solve_generation = 0

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

        self.intro_section = Section()
        intro = QHBoxLayout()
        self.intro_text = QLabel()
        self.intro_text.setWordWrap(True)
        intro.addWidget(self.intro_text, 1)
        self.btn_import = QPushButton()
        self.btn_import.setObjectName("packingImportJsonButton")
        self.btn_import.clicked.connect(self._on_import)
        self.btn_import_info = _info_button("packingImportInfoButton")
        self.btn_import_info.clicked.connect(lambda: self._show_info("import"))
        intro.addWidget(self.btn_import)
        intro.addWidget(self.btn_import_info)
        self.intro_section.body.addLayout(intro)
        intro_actions = QHBoxLayout()
        intro_actions.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_example.clicked.connect(self.example_requested.emit)
        self.btn_problem = QPushButton()
        self.btn_problem.clicked.connect(self.problem_description_requested.emit)
        intro_actions.addWidget(self.btn_example)
        intro_actions.addWidget(self.btn_problem)
        self.intro_section.body.addLayout(intro_actions)
        root.addWidget(self.intro_section)

        self.container_section = Section()
        container_header = QHBoxLayout()
        self.container_hint = QLabel()
        self.container_hint.setWordWrap(True)
        container_header.addWidget(self.container_hint, 1)
        self.btn_container_info = _info_button("packingContainerInfoButton")
        self.btn_container_info.clicked.connect(lambda: self._show_info("container"))
        container_header.addWidget(self.btn_container_info)
        self.container_section.body.addLayout(container_header)
        container_row = QHBoxLayout()
        self.container_name = _line("packingContainerName")
        self.container_length = _line("packingContainerLength")
        self.container_width = _line("packingContainerWidth")
        self.container_height = _line("packingContainerHeight")
        self._container_labels = [QLabel() for _ in range(4)]
        for label, field in zip(
            self._container_labels,
            (self.container_name, self.container_length, self.container_width, self.container_height),
        ):
            container_row.addWidget(label)
            container_row.addWidget(field)
        self.container_section.body.addLayout(container_row)
        root.addWidget(self.container_section)

        self.resources_section = Section()
        resource_header = QHBoxLayout()
        self.resources_hint = QLabel()
        self.resources_hint.setWordWrap(True)
        resource_header.addWidget(self.resources_hint, 1)
        self.btn_resources_info = _info_button("packingResourcesInfoButton")
        self.btn_resources_info.clicked.connect(lambda: self._show_info("resources"))
        resource_header.addWidget(self.btn_resources_info)
        self.resources_section.body.addLayout(resource_header)
        self.resources_table = _table("packingResourcesTable", 3)
        self.resources_table.cellChanged.connect(self._on_resource_changed)
        self.resources_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.resources_table.setColumnWidth(0, 116)
        self.resources_section.body.addWidget(self.resources_table)
        resource_actions = QHBoxLayout()
        resource_actions.addStretch(1)
        self.btn_add_resource = QPushButton()
        self.btn_add_resource.clicked.connect(self._add_resource)
        self.btn_remove_resource = QPushButton()
        self.btn_remove_resource.clicked.connect(self._remove_resources)
        resource_actions.addWidget(self.btn_add_resource)
        resource_actions.addWidget(self.btn_remove_resource)
        self.resources_section.body.addLayout(resource_actions)
        root.addWidget(self.resources_section)

        self.items_section = Section()
        item_header = QHBoxLayout()
        self.items_hint = QLabel()
        self.items_hint.setWordWrap(True)
        item_header.addWidget(self.items_hint, 1)
        self.btn_items_info = _info_button("packingItemsInfoButton")
        self.btn_items_info.clicked.connect(lambda: self._show_info("items"))
        item_header.addWidget(self.btn_items_info)
        self.items_section.body.addLayout(item_header)
        self.items_table = _table("packingItemsTable", _BASE_ITEM_COLUMNS)
        header = self.items_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(90)
        for column in range(_BASE_ITEM_COLUMNS):
            header.setSectionResizeMode(column, QHeaderView.Interactive)
        for column, width in enumerate((116, 150, 240, 130, 130, 130, 130, 130, 250, 220)):
            self.items_table.setColumnWidth(column, width)
        self.items_section.body.addWidget(self.items_table)
        item_actions = QHBoxLayout()
        item_actions.addStretch(1)
        self.btn_add_item = QPushButton()
        self.btn_add_item.clicked.connect(self._add_item)
        self.btn_remove_item = QPushButton()
        self.btn_remove_item.clicked.connect(self._remove_items)
        item_actions.addWidget(self.btn_add_item)
        item_actions.addWidget(self.btn_remove_item)
        self.items_section.body.addLayout(item_actions)
        root.addWidget(self.items_section)

        self.options_section = Section()
        options_header = QHBoxLayout()
        self.options_hint = QLabel()
        self.options_hint.setWordWrap(True)
        options_header.addWidget(self.options_hint, 1)
        self.btn_options_info = _info_button("packingOptionsInfoButton")
        self.btn_options_info.clicked.connect(lambda: self._show_info("options"))
        options_header.addWidget(self.btn_options_info)
        self.options_section.body.addLayout(options_header)
        options = QHBoxLayout()
        self.lbl_selection = QLabel()
        self.selection_policy = QComboBox()
        self.selection_policy.setObjectName("packingSelectionPolicy")
        self.lbl_gravity = QLabel()
        self.gravity_mode = QComboBox()
        self.gravity_mode.setObjectName("packingGravityMode")
        self.lbl_time = QLabel()
        self.time_limit = _line("packingTimeLimit")
        self.lbl_gap = QLabel()
        self.mip_gap = _line("packingMipGap")
        for label, field in (
            (self.lbl_selection, self.selection_policy),
            (self.lbl_gravity, self.gravity_mode),
            (self.lbl_time, self.time_limit),
            (self.lbl_gap, self.mip_gap),
        ):
            options.addWidget(label)
            options.addWidget(field)
        options.addStretch(1)
        self.options_section.body.addLayout(options)
        self.solve_notice = QLabel()
        self.solve_notice.setObjectName("packingSolveNotice")
        self.solve_notice.setWordWrap(True)
        self.options_section.body.addWidget(self.solve_notice)
        root.addWidget(self.options_section)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.btn_solve = QPushButton()
        self.btn_solve.setObjectName("packingSolveButton")
        self.btn_solve.setProperty("variant", "primary")
        self.btn_solve.clicked.connect(self._on_solve)
        actions.addWidget(self.btn_solve)
        self.btn_cancel = QPushButton()
        self.btn_cancel.setObjectName("packingCancelButton")
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.setVisible(False)
        actions.addWidget(self.btn_cancel)
        root.addLayout(actions)
        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self._load_defaults()
        self.refresh_strings()
        self.refresh_theme()

    def set_solve_usecase(self, usecase: object) -> None:
        self._solve_usecase = usecase

    def current_model(self) -> SingleContainerPackingModel:
        return self._build_model()

    def load_model(self, model: SingleContainerPackingModel) -> None:
        self.container_name.setText(model.container.name)
        dims = model.container.dimensions
        self.container_length.setText(_number(dims.length))
        self.container_width.setText(_number(dims.width))
        self.container_height.setText(_number(dims.height))
        self.resources_table.blockSignals(True)
        self.resources_table.setRowCount(0)
        self.items_table.setColumnCount(_BASE_ITEM_COLUMNS)
        for capacity in model.container.capacities:
            self._append_resource(capacity.name, _number(capacity.limit))
        self.resources_table.blockSignals(False)
        self.items_table.setRowCount(0)
        for item in model.items:
            self._append_item(item)
        self._select_combo(self.selection_policy, model.selection_policy.value)
        self._select_combo(self.gravity_mode, model.gravity_mode.value)
        self.time_limit.setText(_number(model.time_limit) if model.time_limit is not None else "")
        self.mip_gap.setText(_number(model.mip_gap) if model.mip_gap is not None else "")
        self.refresh_strings()

    def refresh_strings(self) -> None:
        self.title.setText(f"<span style='font-size:24px; font-weight:700'>{S.t('packing.header.title')}</span>")
        self.intro_section.set_title(S.t("packing.header.section"))
        self.intro_text.setText(S.t("packing.header.description"))
        self.btn_import.setText(S.t("packing.import.button"))
        self.btn_import_info.setToolTip(S.t("packing.import.info_tooltip"))
        self.btn_example.setText(S.t("packing.header.example"))
        self.btn_problem.setText(S.t("packing.header.problem"))
        self.container_section.set_title(S.t("packing.container.section"))
        self.container_hint.setText(S.t("packing.container.hint"))
        self.btn_container_info.setToolTip(S.t("packing.container.info_tooltip"))
        for label, key in zip(self._container_labels, ("name", "length", "width", "height")):
            label.setText(S.t(f"packing.container.{key}"))
        self.resources_section.set_title(S.t("packing.resources.section"))
        self.resources_hint.setText(S.t("packing.resources.hint"))
        self.resources_table.setHorizontalHeaderLabels([
            S.t("packing.common.select"), S.t("packing.resources.name"), S.t("packing.resources.limit")
        ])
        self.btn_add_resource.setText(S.t("packing.resources.add"))
        self.btn_remove_resource.setText(S.t("packing.common.remove_selected"))
        self.btn_resources_info.setToolTip(S.t("packing.resources.info_tooltip"))
        self.items_section.set_title(S.t("packing.items.section"))
        self.items_hint.setText(S.t("packing.items.hint"))
        self.btn_add_item.setText(S.t("packing.items.add"))
        self.btn_remove_item.setText(S.t("packing.common.remove_selected"))
        self.btn_items_info.setToolTip(S.t("packing.items.info_tooltip"))
        self.options_section.set_title(S.t("packing.options.section"))
        self.options_hint.setText(S.t("packing.options.hint"))
        self.lbl_selection.setText(S.t("packing.options.selection"))
        self.lbl_gravity.setText(S.t("packing.options.gravity"))
        self.lbl_time.setText(S.t("packing.options.time_limit"))
        self.lbl_gap.setText(S.t("packing.options.mip_gap"))
        self.btn_options_info.setToolTip(S.t("packing.options.info_tooltip"))
        self.btn_solve.setText(S.t("packing.solve.button"))
        self.btn_cancel.setText(S.t("packing.solve.cancel"))
        selected = self.selection_policy.currentData()
        self.selection_policy.clear()
        for policy in PackingSelectionPolicy:
            self.selection_policy.addItem(S.t(f"packing.options.selection_{policy.value}"), policy.value)
        self._select_combo(self.selection_policy, selected or PackingSelectionPolicy.OPTIONAL.value)
        gravity = self.gravity_mode.currentData()
        self.gravity_mode.clear()
        for mode in PackingGravityMode:
            self.gravity_mode.addItem(S.t(f"packing.options.gravity_{mode.value}"), mode.value)
        self._select_combo(self.gravity_mode, gravity or PackingGravityMode.SIMPLE.value)
        self._refresh_item_headers_and_combos()

    def refresh_theme(self) -> None:
        palette = tokens(theme.is_dark())
        self.title.setStyleSheet(f"color: {palette.text};")
        for hint in (self.intro_text, self.container_hint, self.resources_hint, self.items_hint, self.options_hint):
            hint.setStyleSheet(f"color: {palette.text_muted};")

    def _load_defaults(self) -> None:
        self.container_name.setText("Container 1")
        self.container_length.setPlaceholderText("120")
        self.container_width.setPlaceholderText("80")
        self.container_height.setPlaceholderText("100")
        self.time_limit.setPlaceholderText("60")
        self.mip_gap.setPlaceholderText("0.01")
        self._append_item()
        self._append_item()

    def _append_resource(self, name: str = "", limit: str = "") -> None:
        row = self.resources_table.rowCount()
        self.resources_table.insertRow(row)
        self.resources_table.setCellWidget(row, 0, _centered_checkbox())
        self.resources_table.setCellWidget(row, 1, _line(f"packingResourceName{row}"))
        self.resources_table.setCellWidget(row, 2, _line(f"packingResourceLimit{row}"))
        name_field = self._field(self.resources_table, row, 1)
        name_field.setText(name)
        name_field.textChanged.connect(lambda _text: self._refresh_item_headers_and_combos())
        self._field(self.resources_table, row, 2).setText(limit)
        self.items_table.insertColumn(_BASE_ITEM_COLUMNS + row)
        for item_row in range(self.items_table.rowCount()):
            self.items_table.setCellWidget(item_row, _BASE_ITEM_COLUMNS + row, _line())

    def _add_resource(self) -> None:
        self._append_resource()
        self.refresh_strings()

    def _remove_resources(self) -> None:
        rows = [row for row in range(self.resources_table.rowCount()) if _checked(self.resources_table, row)]
        for row in reversed(rows):
            self.resources_table.removeRow(row)
            self.items_table.removeColumn(_BASE_ITEM_COLUMNS + row)
        self.refresh_strings()

    def _append_item(self, item: Optional[PackingItem] = None) -> None:
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        self.items_table.setCellWidget(row, 0, _centered_checkbox())
        defaults = (
            item.item_id if item else f"item-{row + 1}",
            item.name if item else "",
            _number(item.dimensions.length) if item else "",
            _number(item.dimensions.width) if item else "",
            _number(item.dimensions.height) if item else "",
            str(item.quantity) if item else "1",
            _number(item.value) if item else "1",
        )
        for column, value in enumerate(defaults, start=1):
            field = _line()
            field.setText(value)
            self.items_table.setCellWidget(row, column, field)
        combo = QComboBox()
        combo.currentIndexChanged.connect(lambda _index, r=row: self._update_custom_enabled(r))
        self.items_table.setCellWidget(row, 8, combo)
        custom = _CustomOrientationsButton()
        custom.setObjectName(f"packingCustomOrientations{row}")
        custom.set_codes(item.custom_orientation_codes if item else ())
        custom.clicked.connect(lambda _checked=False, r=row: self._choose_custom_orientations(r))
        self.items_table.setCellWidget(row, 9, custom)
        for resource_row in range(self.resources_table.rowCount()):
            field = _line()
            if item is not None:
                name = self._field(self.resources_table, resource_row, 1).text().strip()
                field.setText(_number(item.consumption(name)))
            self.items_table.setCellWidget(row, _BASE_ITEM_COLUMNS + resource_row, field)
        self._populate_rotation_combo(combo, item.rotation_policy.value if item else RotationPolicy.ANY_ORTHOGONAL.value)
        self._update_custom_enabled(row)

    def _add_item(self) -> None:
        self._append_item()
        self.refresh_strings()

    def _remove_items(self) -> None:
        for row in reversed(range(self.items_table.rowCount())):
            if _checked(self.items_table, row):
                self.items_table.removeRow(row)

    def _refresh_item_headers_and_combos(self) -> None:
        headers = [
            "select", "id", "name", "length", "width", "height", "quantity", "value",
            "rotation", "custom_orientations",
        ]
        resource_names = [
            self._field(self.resources_table, row, 1).text().strip() or S.t("packing.resources.unnamed")
            for row in range(self.resources_table.rowCount())
        ]
        self.items_table.setHorizontalHeaderLabels(
            [S.t(f"packing.items.{name}") for name in headers] + resource_names
        )
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 8)
            if isinstance(combo, QComboBox):
                self._populate_rotation_combo(combo, combo.currentData() or RotationPolicy.ANY_ORTHOGONAL.value)
            custom = self.items_table.cellWidget(row, 9)
            if isinstance(custom, _CustomOrientationsButton):
                custom.refresh_text()
        for column in range(_BASE_ITEM_COLUMNS, self.items_table.columnCount()):
            self.items_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.Interactive)
            self.items_table.setColumnWidth(column, 160)

    def _populate_rotation_combo(self, combo: QComboBox, selected: str) -> None:
        combo.blockSignals(True)
        combo.clear()
        for policy in RotationPolicy:
            combo.addItem(S.t(f"packing.rotation.{policy.value}"), policy.value)
        self._select_combo(combo, selected)
        combo.blockSignals(False)

    def _update_custom_enabled(self, row: int) -> None:
        combo = self.items_table.cellWidget(row, 8)
        custom = self.items_table.cellWidget(row, 9)
        if isinstance(combo, QComboBox) and isinstance(custom, _CustomOrientationsButton):
            custom.setEnabled(combo.currentData() == RotationPolicy.CUSTOM.value)

    def _choose_custom_orientations(self, row: int) -> None:
        button = self.items_table.cellWidget(row, 9)
        if not isinstance(button, _CustomOrientationsButton):
            return
        try:
            dimensions = Dimensions3D(
                _float(self._field(self.items_table, row, 3).text(), "item length"),
                _float(self._field(self.items_table, row, 4).text(), "item width"),
                _float(self._field(self.items_table, row, 5).text(), "item height"),
            )
        except ValueError as exc:
            self._error(localized_error_detail("packing_validation", exc))
            return
        dialog = _OrientationDialog(dimensions, button.codes(), self)
        if dialog.exec() == QDialog.Accepted:
            button.set_codes(dialog.selected_codes())

    def _on_resource_changed(self, _row: int, _column: int) -> None:
        self._refresh_item_headers_and_combos()

    def _build_model(self) -> SingleContainerPackingModel:
        capacities = []
        for row in range(self.resources_table.rowCount()):
            capacities.append(ResourceCapacity(
                self._field(self.resources_table, row, 1).text(),
                _float(self._field(self.resources_table, row, 2).text(), "resource limit"),
            ))
        container = PackingContainer.from_parts(
            "container-1",
            self.container_name.text(),
            Dimensions3D(
                _float(self.container_length.text(), "container length"),
                _float(self.container_width.text(), "container width"),
                _float(self.container_height.text(), "container height"),
            ),
            capacities,
        )
        items = []
        for row in range(self.items_table.rowCount()):
            combo = self.items_table.cellWidget(row, 8)
            assert isinstance(combo, QComboBox)
            custom = self.items_table.cellWidget(row, 9)
            if not isinstance(custom, _CustomOrientationsButton):
                raise ValueError("custom orientation selector is missing")
            codes = custom.codes()
            consumptions = []
            for resource_row, capacity in enumerate(capacities):
                raw = self._field(self.items_table, row, _BASE_ITEM_COLUMNS + resource_row).text().strip()
                consumptions.append(ResourceConsumption(capacity.name, _float(raw or "0", "resource usage")))
            items.append(PackingItem.from_parts(
                self._field(self.items_table, row, 1).text(),
                self._field(self.items_table, row, 2).text(),
                Dimensions3D(
                    _float(self._field(self.items_table, row, 3).text(), "item length"),
                    _float(self._field(self.items_table, row, 4).text(), "item width"),
                    _float(self._field(self.items_table, row, 5).text(), "item height"),
                ),
                quantity=_integer(self._field(self.items_table, row, 6).text(), "quantity"),
                value=_float(self._field(self.items_table, row, 7).text(), "value"),
                rotation_policy=RotationPolicy.from_str(combo.currentData()),
                custom_orientation_codes=codes,
                consumptions=consumptions,
            ))
        return SingleContainerPackingModel.from_parts(
            container,
            items,
            selection_policy=PackingSelectionPolicy.from_str(self.selection_policy.currentData()),
            gravity_mode=PackingGravityMode.from_str(self.gravity_mode.currentData()),
            time_limit=_optional_float(self.time_limit.text()),
            mip_gap=_optional_float(self.mip_gap.text()),
        )

    def _on_solve(self) -> None:
        if self._solve_usecase is None or self._worker is not None:
            return
        try:
            model = self._build_model()
        except (TypeError, ValueError) as exc:
            self._error(localized_error_detail("packing_validation", exc))
            return
        estimate = estimate_packing_complexity(model)
        if estimate.level is not PackingComplexityLevel.LOW:
            answer = QMessageBox.question(
                self,
                S.t("packing.complexity.title"),
                S.t(
                    f"packing.complexity.{estimate.level.value}",
                    units=estimate.unit_count,
                    pairs=estimate.pair_count,
                    binaries=estimate.separation_binary_count,
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self.btn_solve.setEnabled(False)
        self.btn_solve.setText(S.t("packing.solve.running"))
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setVisible(True)
        self.solve_notice.setText(
            S.t(
                "packing.solve.model_size",
                units=estimate.unit_count,
                pairs=estimate.pair_count,
                variables=estimate.approximate_variable_count,
            )
        )
        self._solve_generation += 1
        generation = self._solve_generation
        QTimer.singleShot(60_000, lambda: self._show_runtime_notice(generation, 60))
        QTimer.singleShot(120_000, lambda: self._show_runtime_notice(generation, 120))
        worker = _SolveWorker(self._solve_usecase, model)
        self._worker = worker
        worker.signals.completed.connect(self._on_solved)
        worker.signals.failed.connect(self._on_solve_failed)
        QThreadPool.globalInstance().start(worker)

    def _on_solved(self, result: object) -> None:
        self._worker = None
        self._finish_solve_ui()
        self.solve_completed.emit(result)

    def _on_solve_failed(self, detail: str) -> None:
        self._worker = None
        self._finish_solve_ui()
        self._error(detail)

    def _finish_solve_ui(self) -> None:
        self._solve_generation += 1
        self.btn_solve.setEnabled(True)
        self.btn_solve.setText(S.t("packing.solve.button"))
        self.btn_cancel.setVisible(False)
        self.btn_cancel.setEnabled(True)
        self.solve_notice.clear()

    def _on_cancel(self) -> None:
        if self._worker is None or self._solve_usecase is None:
            return
        cancel = getattr(self._solve_usecase, "cancel", None)
        accepted = bool(cancel()) if callable(cancel) else False
        self.btn_cancel.setEnabled(False)
        self.solve_notice.setText(
            S.t("packing.solve.cancel_requested" if accepted else "packing.solve.cancel_pending")
        )

    def _show_runtime_notice(self, generation: int, seconds: int) -> None:
        if generation != self._solve_generation or self._worker is None:
            return
        key = "packing.solve.long_running" if seconds == 60 else "packing.solve.very_long_running"
        self.solve_notice.setText(S.t(key))

    def _on_import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, S.t("packing.import.dialog"), "", "JSON (*.json)")
        if not path:
            return
        try:
            self.load_model(packing_model_from_file(Path(path)))
        except (OSError, ValueError, TypeError) as exc:
            self._error(localized_error_detail("packing_import", exc))

    def _show_info(self, topic: str) -> None:
        dialog = _InfoDialog(
            S.t(f"packing.info.{topic}.title"),
            S.t(f"packing.info.{topic}.body"),
            S.t(f"packing.info.{topic}.html"),
            self,
        )
        dialog.exec()

    def _error(self, detail: str) -> None:
        QMessageBox.warning(self, S.t("packing.error.title"), detail)

    @staticmethod
    def _field(table: QTableWidget, row: int, column: int) -> QLineEdit:
        field = table.cellWidget(row, column)
        if not isinstance(field, QLineEdit):
            raise ValueError("packing table field is missing")
        return field

    @staticmethod
    def _select_combo(combo: QComboBox, value: object) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(max(0, index))


def _table(name: str, columns: int) -> QTableWidget:
    table = QTableWidget(0, columns)
    table.setObjectName(name)
    table.setAlternatingRowColors(True)
    table.setSelectionMode(QAbstractItemView.NoSelection)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.setMinimumHeight(150)
    return table


def _line(name: str = "") -> QLineEdit:
    field = QLineEdit()
    if name:
        field.setObjectName(name)
    return field


def _info_button(name: str) -> QPushButton:
    button = QPushButton("i")
    button.setObjectName(name)
    button.setProperty("variant", "info")
    button.setFixedSize(24, 24)
    button.setCursor(Qt.PointingHandCursor)
    return button


class _InfoDialog(QDialog):
    def __init__(self, title: str, intro: str, html: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setMinimumSize(520, 380)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        intro_label = QLabel(intro)
        intro_label.setWordWrap(True)
        layout.addWidget(intro_label)
        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(False)
        browser.setHtml(html)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.setText(S.t("packing.info.close"))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class _CustomOrientationsButton(QPushButton):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._codes: tuple[str, ...] = ()

    def set_codes(self, codes: Iterable[str]) -> None:
        self._codes = tuple(str(code).strip().upper() for code in codes)
        self.refresh_text()

    def codes(self) -> tuple[str, ...]:
        return self._codes

    def refresh_text(self) -> None:
        if self._codes:
            self.setText(S.t("packing.items.orientations_selected", count=len(self._codes)))
            self.setToolTip(", ".join(self._codes))
        else:
            self.setText(S.t("packing.items.choose_orientations"))
            self.setToolTip(S.t("packing.items.choose_orientations_tooltip"))


class _OrientationDialog(QDialog):
    def __init__(
        self,
        dimensions: Dimensions3D,
        selected_codes: tuple[str, ...],
        parent: Optional[QWidget],
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(S.t("packing.orientation_dialog.title"))
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        hint = QLabel(S.t("packing.orientation_dialog.hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self._boxes: list[tuple[str, QCheckBox]] = []
        selected = {code.upper() for code in selected_codes}
        for orientation in generate_orientations(dimensions, RotationPolicy.ANY_ORTHOGONAL):
            length, width, height = orientation.dimensions.as_tuple()
            box = QCheckBox(
                S.t(
                    "packing.orientation_dialog.option",
                    code=orientation.code,
                    length=_number(length),
                    width=_number(width),
                    height=_number(height),
                )
            )
            box.setChecked(orientation.code in selected)
            self._boxes.append((orientation.code, box))
            layout.addWidget(box)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._ok_button = buttons.button(QDialogButtonBox.Ok)
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        if self._ok_button is not None:
            self._ok_button.setText(S.t("packing.orientation_dialog.confirm"))
        if cancel_button is not None:
            cancel_button.setText(S.t("packing.orientation_dialog.cancel"))
        for _code, box in self._boxes:
            box.toggled.connect(lambda _checked: self._refresh_accept_enabled())
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_accept_enabled()

    def selected_codes(self) -> tuple[str, ...]:
        return tuple(code for code, box in self._boxes if box.isChecked())

    def _refresh_accept_enabled(self) -> None:
        if self._ok_button is not None:
            self._ok_button.setEnabled(any(box.isChecked() for _code, box in self._boxes))


def _centered_checkbox() -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    box = QCheckBox()
    layout.addWidget(box, 0, Qt.AlignCenter)
    container.setProperty("checkbox", box)
    return container


def _checked(table: QTableWidget, row: int) -> bool:
    widget = table.cellWidget(row, 0)
    box = widget.property("checkbox") if widget is not None else None
    return isinstance(box, QCheckBox) and box.isChecked()


def _float(value: object, label: str) -> float:
    try:
        return float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"{label} must be a number") from exc


def _optional_float(value: object) -> float | None:
    token = str(value).strip()
    return None if not token else _float(token, "solver option")


def _integer(value: object, label: str) -> int:
    parsed = _float(value, label)
    if not parsed.is_integer():
        raise ValueError(f"{label} must be an integer")
    return int(parsed)


def _number(value: object) -> str:
    return f"{float(value):.8g}"
