from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.milp.variable import MILPVariable
from optees.domain.value_objects.milp.integrality import Integrality
from optees.presentation.controllers.milp_controller import MILPController
from optees.presentation.views.lp_view.bounds_section import BoundsSection
from optees.presentation.views.lp_view.objective_constraints_section import (
    ObjectiveConstraintsSection,
)
from optees.presentation.views.lp_view.objective_section import ObjectiveSection
from optees.presentation.views.lp_view.section import Section
from optees.presentation.views.widgets.flow_layout import FlowLayout

log = logging.getLogger(__name__)

_INFO_HTML_STYLE = """\
<style>
  body  { font-family: system-ui, sans-serif; font-size: 13px; margin: 0; }
  h3    { margin: 12px 0 4px; font-size: 13px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 10px; }
  th    { text-align: left; padding: 4px 8px; background: rgba(128,128,128,.15); }
  td    { padding: 3px 8px; vertical-align: top; }
  tr:nth-child(even) td { background: rgba(128,128,128,.07); }
  code  { font-family: "Courier New", monospace; font-size: 12px;
          background: rgba(128,128,128,.12); padding: 1px 4px; border-radius: 3px; }
  pre   { font-family: "Courier New", monospace; font-size: 12px;
          background: rgba(128,128,128,.12); padding: 10px; border-radius: 4px;
          margin: 6px 0; white-space: pre; }
</style>
"""

_MILP_JSON_SCHEMA_HTML = _INFO_HTML_STYLE + """\
<h3>Top-level object</h3>
<table>
  <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
  <tr><td><code>version</code></td><td><code>"1"</code></td><td>Yes</td><td>Schema version.</td></tr>
  <tr><td><code>variables</code></td><td>array</td><td>Yes</td><td>Decision variables with bounds and integrality.</td></tr>
  <tr><td><code>objective</code></td><td>object</td><td>Yes</td><td>Objective function.</td></tr>
  <tr><td><code>constraints</code></td><td>array</td><td>Yes</td><td>Linear constraints; may be empty.</td></tr>
  <tr><td><code>solver</code></td><td>object</td><td>No</td><td>Optional time limit and MIP gap.</td></tr>
</table>

<h3>Variable object</h3>
<table>
  <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
  <tr><td><code>name</code></td><td>string</td><td>No</td><td>Short identifier. Defaults to <code>X{n}</code>.</td></tr>
  <tr><td><code>label</code></td><td>string</td><td>No</td><td>Human-readable description.</td></tr>
  <tr><td><code>lb</code></td><td>number | null</td><td>Yes</td><td>Lower bound. Use <code>null</code> for unbounded.</td></tr>
  <tr><td><code>ub</code></td><td>number | null</td><td>Yes</td><td>Upper bound. Use <code>null</code> for unbounded.</td></tr>
  <tr><td><code>integrality</code></td><td><code>"C"</code> | <code>"I"</code> | <code>"B"</code></td><td>No</td><td>Continuous, integer, or binary/Boolean.</td></tr>
</table>

<h3>Solver object</h3>
<table>
  <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
  <tr><td><code>time_limit</code></td><td>number</td><td>No</td><td>Maximum solve time in seconds.</td></tr>
  <tr><td><code>mip_gap</code></td><td>number</td><td>No</td><td>Relative optimality gap, e.g. <code>0.01</code>.</td></tr>
</table>

<h3>Example</h3>
<pre>{
  "version": "1",
  "variables": [
    { "name": "y", "label": "open facility", "lb": 0, "ub": 1, "integrality": "B" },
    { "name": "x", "label": "units shipped", "lb": 0, "ub": null, "integrality": "C" }
  ],
  "objective": { "sense": "min", "coefficients": [800, 6], "offset": 0 },
  "constraints": [
    { "coefficients": [-120, 1], "relation": "&lt;=", "rhs": 0 }
  ],
  "solver": { "time_limit": 10, "mip_gap": 0.01 }
}</pre>
"""

_SOLVER_OPTIONS_HTML = _INFO_HTML_STYLE + """\
<h3>Options</h3>
<table>
  <tr><th>Option</th><th>Meaning</th></tr>
  <tr><td><code>time_limit</code></td><td>Stops the search after the given number of seconds.</td></tr>
  <tr><td><code>mip_gap</code></td><td>Relative distance between incumbent and best bound.</td></tr>
</table>

<h3>Status</h3>
<table>
  <tr><th>Status</th><th>Meaning</th></tr>
  <tr><td><code>Optimal</code></td><td>The incumbent is proven optimal.</td></tr>
  <tr><td><code>Feasible</code></td><td>The incumbent satisfies all constraints, but optimality is not proven.</td></tr>
  <tr><td><code>Infeasible</code></td><td>No feasible solution exists.</td></tr>
  <tr><td><code>NotSolved</code></td><td>The solver did not return a usable solution.</td></tr>
</table>
"""


def _parse_optional_float(text: str) -> Optional[float]:
    s = (text or "").strip().lower().replace(",", ".")
    if s == "":
        return None
    if "/" in s:
        try:
            a, b = s.split("/", 1)
            return float(a) / float(b)
        except Exception:
            return None
    try:
        return float(s)
    except Exception:
        return None


def _format_optional_float(value: Optional[float]) -> str:
    if value is None:
        return ""
    return str(int(value)) if isinstance(value, float) and value == int(value) else str(value)


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()


def _make_info_button(tooltip: str, parent: Optional[QWidget] = None) -> QPushButton:
    button = QPushButton("i", parent)
    button.setObjectName("btnSchemaInfo")
    button.setText("i")
    button.setCursor(Qt.PointingHandCursor)
    button.setFixedSize(24, 24)
    button.setToolTip(tooltip)
    return button


class _InfoDialog(QDialog):
    def __init__(self, title: str, intro: str, html: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(520, 420)
        self.setWindowTitle(title)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._intro = QLabel(intro)
        self._intro.setWordWrap(True)
        layout.addWidget(self._intro)

        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(False)
        browser.setHtml(html)
        layout.addWidget(browser)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_btn = buttons.button(QDialogButtonBox.Close)
        if close_btn:
            close_btn.setText(S.t("lp.import.schema_close"))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class _MILPVarRow(QWidget):
    remove_requested = Signal(int)
    desc_changed = Signal(int, str)
    integrality_changed = Signal(int, str)

    def __init__(
        self,
        *,
        index: int,
        variable: MILPVariable,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._index = index

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.lbl = QLabel(variable.name)
        self.lbl.setMinimumWidth(40)

        self.txt = QLineEdit(variable.label)
        self.txt.setObjectName("milpVariableLabel")
        self.txt.setClearButtonEnabled(True)
        self.txt.setFixedHeight(28)
        self.txt.setMinimumWidth(150)
        self.txt.setMaximumWidth(360)
        self.txt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rx = QRegularExpression(r"^[\w\s\-]{0,100}$")
        self.txt.setValidator(QRegularExpressionValidator(rx, self))
        self.txt.textEdited.connect(self._on_text_edited)

        self.combo_type = QComboBox()
        self.combo_type.setObjectName("milpIntegralityCombo")
        self.combo_type.setFixedHeight(28)
        self.combo_type.setMinimumWidth(180)
        self._fill_integrality_combo(variable.integrality.value)
        self.combo_type.currentIndexChanged.connect(self._on_integrality_changed)

        self.btn_remove = QToolButton()
        icon = QIcon.fromTheme("edit-delete")
        if not icon.isNull():
            self.btn_remove.setIcon(icon)
        else:
            self.btn_remove.setText("x")
        self.btn_remove.setAutoRaise(True)
        self.btn_remove.setFixedSize(28, 28)
        self.btn_remove.clicked.connect(self._on_remove)

        row.addWidget(self.lbl)
        row.addWidget(self.txt, 1)
        row.addWidget(self.combo_type)
        row.addWidget(self.btn_remove)

        self.refresh_strings()

    def set_index_and_name(self, index: int, name: str) -> None:
        self._index = index
        self.lbl.setText(name)

    def set_integrality(self, value: str) -> None:
        self._fill_integrality_combo(value)

    def refresh_strings(self) -> None:
        self.txt.setPlaceholderText(S.t("milp.vars.name_placeholder"))
        self.btn_remove.setToolTip(S.t("milp.vars.remove"))
        current = self.combo_type.currentData() or "C"
        self._fill_integrality_combo(str(current))

    def _fill_integrality_combo(self, selected: str) -> None:
        self.combo_type.blockSignals(True)
        self.combo_type.clear()
        self.combo_type.addItem(S.t("milp.vars.type.continuous"), "C")
        self.combo_type.addItem(S.t("milp.vars.type.integer"), "I")
        self.combo_type.addItem(S.t("milp.vars.type.binary"), "B")
        idx = {"C": 0, "I": 1, "B": 2}.get(str(selected).upper(), 0)
        self.combo_type.setCurrentIndex(idx)
        self.combo_type.blockSignals(False)

    def _on_remove(self) -> None:
        self.remove_requested.emit(self._index)

    def _on_text_edited(self, text: str) -> None:
        self.desc_changed.emit(self._index, text.strip())

    def _on_integrality_changed(self, _index: int) -> None:
        token = self.combo_type.currentData() or "C"
        self.integrality_changed.emit(self._index, str(token))


class _MILPVariablesSection(Section):
    add_clicked = Signal()
    remove_clicked = Signal(int)
    label_changed = Signal(int, str)
    integrality_changed = Signal(int, str)

    def __init__(self, max_width: int | None = None, parent: Optional[QWidget] = None) -> None:
        super().__init__("", parent)
        if max_width:
            self.setFixedWidth(max_width)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(theme.secondary_text_css(self))
        self.body.addWidget(self._hint)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self.col_var = QLabel()
        self.col_label = QLabel()
        self.col_type = QLabel()
        header.addWidget(self.col_var)
        header.addWidget(self.col_label, 1)
        header.addWidget(self.col_type)
        header.addSpacing(28)
        self.body.addLayout(header)

        self._rows_lay = QVBoxLayout()
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(8)
        self.body.addLayout(self._rows_lay)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self.add_clicked.emit)
        footer.addWidget(self.btn_add)
        self.body.addLayout(footer)

        self.refresh_strings()

    def refresh_strings(self) -> None:
        self.set_title(S.t("milp.vars.section"))
        self._hint.setText(S.t("milp.vars.hint"))
        self.col_var.setText(S.t("milp.vars.columns.var"))
        self.col_label.setText(S.t("milp.vars.columns.label"))
        self.col_type.setText(S.t("milp.vars.columns.type"))
        self.btn_add.setText(S.t("milp.vars.add"))
        for row in self.findChildren(_MILPVarRow):
            row.refresh_strings()

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._hint.setStyleSheet(theme.secondary_text_css(self))

    def set_variables(self, variables: list[MILPVariable]) -> None:
        _clear_layout(self._rows_lay)
        for i, variable in enumerate(variables):
            row = _MILPVarRow(index=i, variable=variable)
            row.remove_requested.connect(self.remove_clicked.emit)
            row.desc_changed.connect(self.label_changed.emit)
            row.integrality_changed.connect(self.integrality_changed.emit)
            self._rows_lay.addWidget(row)

    def update_label(self, index: int, text: str) -> None:
        rows = self.findChildren(_MILPVarRow)
        if 0 <= index < len(rows):
            rows[index].txt.setText(text or "")

    def update_integrality(self, index: int, value: str) -> None:
        rows = self.findChildren(_MILPVarRow)
        if 0 <= index < len(rows):
            rows[index].set_integrality(value)


class _MILPSolverSection(Section):
    info_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("", parent)

        self.btn_info = _make_info_button(S.t("milp.solver.info_tooltip"), self)
        self.btn_info.clicked.connect(self.info_requested.emit)
        self.set_header_action(self.btn_info)

        hint = QLabel()
        hint.setWordWrap(True)
        hint.setStyleSheet(theme.secondary_text_css(self))
        self._hint = hint
        self.body.addWidget(hint)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        self.lbl_time = QLabel()
        self.edit_time = QLineEdit()
        self.edit_time.setObjectName("milpTimeLimit")
        self.edit_time.setFixedHeight(28)
        self.edit_time.setMaximumWidth(140)

        self.lbl_gap = QLabel()
        self.edit_gap = QLineEdit()
        self.edit_gap.setObjectName("milpMipGap")
        self.edit_gap.setFixedHeight(28)
        self.edit_gap.setMaximumWidth(140)

        row.addWidget(self.lbl_time)
        row.addWidget(self.edit_time)
        row.addSpacing(12)
        row.addWidget(self.lbl_gap)
        row.addWidget(self.edit_gap)
        row.addStretch(1)
        self.body.addLayout(row)

        self.refresh_strings()

    def values(self) -> tuple[Optional[float], Optional[float]]:
        time_limit = _parse_optional_float(self.edit_time.text())
        mip_gap = _parse_optional_float(self.edit_gap.text())
        if time_limit is not None and time_limit <= 0:
            time_limit = None
        if mip_gap is not None and mip_gap < 0:
            mip_gap = None
        return time_limit, mip_gap

    def set_values(self, time_limit: Optional[float], mip_gap: Optional[float]) -> None:
        self.edit_time.setText(_format_optional_float(time_limit))
        self.edit_gap.setText(_format_optional_float(mip_gap))

    def refresh_strings(self) -> None:
        self.set_title(S.t("milp.solver.section"))
        self._hint.setText(S.t("milp.solver.hint"))
        self.btn_info.setToolTip(S.t("milp.solver.info_tooltip"))
        self.lbl_time.setText(S.t("milp.solver.time_limit"))
        self.lbl_gap.setText(S.t("milp.solver.mip_gap"))
        self.edit_time.setPlaceholderText(S.t("milp.solver.time_limit_ph"))
        self.edit_gap.setPlaceholderText(S.t("milp.solver.mip_gap_ph"))

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._hint.setStyleSheet(theme.secondary_text_css(self))


class MILPView(QWidget):
    """Editable MILP formulation page."""

    solve_completed = Signal(object)
    example_requested = Signal()
    problem_description_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignTop)
        outer.addWidget(scroll)

        page = QWidget()
        scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(12)

        self.page_title = QLabel()
        self.page_title.setTextFormat(Qt.RichText)
        self.page_title.setWordWrap(True)
        root.addWidget(self.page_title)

        self.intro = Section()
        self.btn_import = QPushButton()
        self.btn_import.setObjectName("milpImportJsonButton")
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.clicked.connect(self._on_import_json)
        self.intro.set_header_action(self.btn_import)

        self.btn_import_info = _make_info_button(S.t("milp.import.info_tooltip"), self)
        self.btn_import_info.clicked.connect(self._show_import_schema)
        self.intro.set_header_action(self.btn_import_info)

        self.intro_text = QLabel()
        self.intro_text.setWordWrap(True)
        self.intro_text.setStyleSheet(theme.secondary_text_css(self))
        self.intro.body.addWidget(self.intro_text)

        info_actions = QHBoxLayout()
        info_actions.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_problem = QPushButton()
        self.btn_example.clicked.connect(self.example_requested.emit)
        self.btn_problem.clicked.connect(self.problem_description_requested.emit)
        info_actions.addWidget(self.btn_example)
        info_actions.addWidget(self.btn_problem)
        self.intro.body.addLayout(info_actions)
        root.addWidget(self.intro)

        row = FlowLayout(hspacing=16, vspacing=16)
        root.addLayout(row)

        self.vars_sec = _MILPVariablesSection(max_width=560)
        self.bounds_sec = BoundsSection(max_width=520)
        row.addWidget(self.vars_sec)
        row.addWidget(self.bounds_sec)

        self.obj_sec = ObjectiveSection()
        root.addWidget(self.obj_sec)

        self.obj_cons_sec = ObjectiveConstraintsSection(max_width=None)
        root.addWidget(self.obj_cons_sec)

        self.solver_sec = _MILPSolverSection()
        self.solver_sec.info_requested.connect(self._show_solver_info)
        root.addWidget(self.solver_sec)

        root.addStretch(1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_optimize = QPushButton()
        self.btn_optimize.setObjectName("milpOptimizeButton")
        self.btn_optimize.setEnabled(False)
        self.btn_optimize.clicked.connect(self._on_optimize_clicked)
        footer.addWidget(self.btn_optimize)
        root.addLayout(footer)

        self._ctrl: Optional[MILPController] = None
        self._solve_uc = None

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)

        self.vars_sec.add_clicked.connect(self._on_add_var_clicked)
        self.vars_sec.remove_clicked.connect(self._on_var_remove)
        self.vars_sec.label_changed.connect(self._on_var_label_changed)
        self.vars_sec.integrality_changed.connect(self._on_var_integrality_changed)

        self.bounds_sec.lb_changed.connect(self._on_lb_changed)
        self.bounds_sec.ub_changed.connect(self._on_ub_changed)
        self.bounds_sec.preset_clicked.connect(self._on_preset_clicked)

        self.obj_sec.sense_changed.connect(self._on_obj_sense_changed)
        self.obj_sec.offset_changed.connect(self._on_obj_offset_changed)

        self.obj_cons_sec.obj_coef_changed.connect(self._on_obj_coef_changed)
        self.obj_cons_sec.cons_coef_changed.connect(self._on_cons_coef_changed)
        self.obj_cons_sec.cons_rel_changed.connect(self._on_cons_rel_changed)
        self.obj_cons_sec.cons_rhs_changed.connect(self._on_cons_rhs_changed)
        self.obj_cons_sec.add_cons_clicked.connect(self._on_add_constraint_clicked)
        self.obj_cons_sec.remove_cons_clicked.connect(self._on_remove_constraint_clicked)

        self.refresh_theme()
        self.refresh_strings()

    def set_controller(self, controller: MILPController) -> None:
        self._ctrl = controller
        if not self._ctrl.variables():
            self._ctrl.add_variable()
            self._ctrl.add_variable()
        if not self._ctrl.constraints():
            self._ctrl.add_constraint()

        self._ctrl.variables_changed.connect(self._on_vars_changed)
        self._ctrl.variable_updated.connect(self.vars_sec.update_label)
        self._ctrl.integrality_updated.connect(self.vars_sec.update_integrality)
        self._ctrl.bounds_changed.connect(lambda _: self.bounds_sec.set_variables(self._ctrl.variables()))
        self._ctrl.objective_changed.connect(self._on_objective_changed)
        self._ctrl.objective_changed.connect(lambda *_: self._update_optimize_enabled())
        self._ctrl.constraints_changed.connect(self._on_constraints_changed)
        self._ctrl.solver_options_changed.connect(self.solver_sec.set_values)

        self._on_vars_changed(self._ctrl.variables())
        self._on_objective_changed(self._ctrl.objective())
        self._on_constraints_changed(self._ctrl.constraints())
        self.solver_sec.set_values(self._ctrl.time_limit(), self._ctrl.mip_gap())
        self._update_optimize_enabled()

    def set_solve_usecase(self, usecase) -> None:
        self._solve_uc = usecase

    def _on_vars_changed(self, variables: list[MILPVariable]) -> None:
        self.vars_sec.set_variables(variables)
        self.bounds_sec.set_variables(variables)
        self.obj_cons_sec.set_variables(variables)
        if self._ctrl:
            self._on_objective_changed(self._ctrl.objective())
            self._on_constraints_changed(self._ctrl.constraints())
        self._update_optimize_enabled()

    def _update_optimize_enabled(self) -> None:
        self.btn_optimize.setEnabled(bool(self._ctrl and self._ctrl.variables()))

    def _on_add_var_clicked(self) -> None:
        if self._ctrl:
            self._ctrl.add_variable()

    def _on_var_remove(self, index: int) -> None:
        if self._ctrl:
            self._ctrl.remove_variable(index)

    def _on_var_label_changed(self, index: int, text: str) -> None:
        if self._ctrl:
            self._ctrl.set_description(index, text)

    def _on_var_integrality_changed(self, index: int, value: str) -> None:
        if self._ctrl:
            self._ctrl.set_integrality(index, value)

    def _on_lb_changed(self, index: int, lb_val) -> None:
        if not self._ctrl:
            return
        var = self._ctrl.variables()[index]
        if var.integrality is Integrality.BINARY:
            self._ctrl.set_integrality(index, Integrality.BINARY)
            return
        ub_val = var.bounds.ub
        if (lb_val is not None) and (ub_val is not None) and (lb_val > ub_val):
            return
        self._ctrl.set_bounds(index, lb_val, ub_val)

    def _on_ub_changed(self, index: int, ub_val) -> None:
        if not self._ctrl:
            return
        var = self._ctrl.variables()[index]
        if var.integrality is Integrality.BINARY:
            self._ctrl.set_integrality(index, Integrality.BINARY)
            return
        lb_val = var.bounds.lb
        if (lb_val is not None) and (ub_val is not None) and (lb_val > ub_val):
            return
        self._ctrl.set_bounds(index, lb_val, ub_val)

    def _on_preset_clicked(self, index: int, preset: str) -> None:
        if self._ctrl:
            self._ctrl.apply_preset(index, preset)

    def _on_obj_coef_changed(self, index: int, value) -> None:
        if self._ctrl:
            self._ctrl.set_objective_coef(index, value)

    def _on_obj_sense_changed(self, sense: str) -> None:
        if self._ctrl:
            self._ctrl.set_objective_sense(sense)

    def _on_obj_offset_changed(self, value) -> None:
        if self._ctrl:
            self._ctrl.set_objective_offset(value)

    def _on_add_constraint_clicked(self) -> None:
        if self._ctrl:
            self._ctrl.add_constraint()

    def _on_remove_constraint_clicked(self, row: int) -> None:
        if self._ctrl:
            self._ctrl.remove_constraint(row)

    def _on_cons_coef_changed(self, row: int, index: int, value) -> None:
        if self._ctrl:
            self._ctrl.set_constraint_coef(row, index, value)

    def _on_cons_rel_changed(self, row: int, rel: str) -> None:
        if self._ctrl:
            self._ctrl.set_constraint_rel(row, rel)

    def _on_cons_rhs_changed(self, row: int, value) -> None:
        if self._ctrl:
            self._ctrl.set_constraint_rhs(row, value)

    def _on_objective_changed(self, objective) -> None:
        sense = getattr(getattr(objective, "sense", None), "name", "max").lower()
        offset_raw = getattr(objective, "offset", None)
        offset = float(offset_raw) if offset_raw is not None else None
        coefs = list(getattr(objective, "coefs", None) or [])
        self.obj_sec.set_values(sense, offset)
        self.obj_cons_sec.set_objective_coefs(coefs)

    def _on_constraints_changed(self, constraints) -> None:
        variables = self._ctrl.variables() if self._ctrl else []
        self.obj_cons_sec.set_constraints_count(len(constraints), variables)
        for row_index, constraint in enumerate(constraints):
            coefs = list(getattr(constraint, "coefs", None) or [])
            rel = getattr(getattr(constraint, "relation", None), "symbol", lambda: "<=")()
            rhs = getattr(constraint, "rhs", None)
            self.obj_cons_sec.set_constraint_values(row_index, coefs, rel, rhs)

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            S.t("milp.import.dialog_title"),
            "",
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            from optees.utility.milp_json_io import milp_model_from_file

            model = milp_model_from_file(path)
        except ValueError as exc:
            QMessageBox.warning(
                self,
                S.t("milp.import.error_title"),
                S.t("milp.import.error_body", detail=str(exc)),
            )
            return
        if self._ctrl:
            self._ctrl.load_model(model)

    def _show_import_schema(self) -> None:
        dlg = _InfoDialog(
            S.t("milp.import.info_title"),
            S.t("milp.import.info_body"),
            _MILP_JSON_SCHEMA_HTML,
            self,
        )
        dlg.exec()

    def _show_solver_info(self) -> None:
        dlg = _InfoDialog(
            S.t("milp.solver.info_title"),
            S.t("milp.solver.info_body"),
            _SOLVER_OPTIONS_HTML,
            self,
        )
        dlg.exec()

    def _on_optimize_clicked(self) -> None:
        if not self._ctrl or not self._solve_uc:
            return

        for index, value in enumerate(self.obj_cons_sec.get_objective_coefs()):
            self._ctrl.set_objective_coef(index, value)

        time_limit, mip_gap = self.solver_sec.values()
        self._ctrl.set_solver_options(time_limit=time_limit, mip_gap=mip_gap)
        model = self._ctrl.model()

        if log.isEnabledFor(logging.DEBUG):
            log.debug(
                "milp solve: vars=%s integrality=%s time_limit=%s mip_gap=%s",
                [v.name for v in model.variables],
                [v.integrality.value for v in model.variables],
                model.time_limit,
                model.mip_gap,
            )

        solution = self._solve_uc.execute(model)
        self.solve_completed.emit(solution)

    def refresh_strings(self) -> None:
        self.page_title.setText(
            f"<span style='font-size:20px; font-weight:700'>{S.t('milp.header.title')}</span>"
        )
        self.intro.set_title(S.t("milp.header.section"))
        self.intro_text.setText(S.t("milp.header.description"))
        self.btn_import.setText(S.t("milp.import.button"))
        self.btn_import_info.setToolTip(S.t("milp.import.info_tooltip"))
        self.btn_example.setText(S.t("milp.header.buttons.example"))
        self.btn_problem.setText(S.t("milp.header.buttons.problem"))
        self.vars_sec.refresh_strings()
        self.bounds_sec.refresh_strings()
        self.obj_sec.refresh_strings()
        self.obj_cons_sec.refresh_strings()
        self.solver_sec.refresh_strings()
        self.btn_optimize.setText(S.t("milp.actions.optimize"))

    def refresh_theme(self) -> None:
        if theme.is_dark():
            self.page_title.setStyleSheet(
                "color: rgba(255,255,255,0.95); margin-top: 8px; margin-bottom: 8px;"
            )
        else:
            self.page_title.setStyleSheet(
                "color: rgba(0,0,0,0.90); margin-top: 8px; margin-bottom: 8px;"
            )
        self.intro.refresh_theme()
        self.intro_text.setStyleSheet(theme.secondary_text_css(self))
        self.vars_sec.refresh_theme()
        self.bounds_sec.refresh_theme()
        self.obj_sec.refresh_theme()
        self.obj_cons_sec.refresh_theme()
        self.solver_sec.refresh_theme()
