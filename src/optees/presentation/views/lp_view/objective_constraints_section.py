# src/optees/presentation/views/lp_view/objective_constraints_section.py
from __future__ import annotations
from typing import List, Optional
from dataclasses import dataclass

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton
)

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.controllers.lp_controller import LPVariable
from .section import Section

def _parse_number(text: str) -> Optional[float]:
    s = (text or "").strip().lower().replace(",", ".")
    if s in ("", "+inf", "inf", "infty", "infinite"):  # no inf allowed here, but accept empty
        return None if s == "" else None
    if "/" in s:
        try:
            a, b = s.split("/", 1)
            return float(a)/float(b)
        except Exception:
            return None
    try:
        return float(s)
    except Exception:
        return None

@dataclass
class _ConstraintRowWidgets:
    coef_edits: List[QLineEdit]
    rel_combo: QComboBox
    rhs_edit: QLineEdit
    layout: QHBoxLayout
    remove_btn: QPushButton

class ObjectiveConstraintsSection(Section):
    """
    One card with:
      - Objective function coefficients: "z = [edit] x1 + [edit] x2 + ..."
      - Constraints list: each row "[edit] x1 + [edit] x2  [rel_combo]  [rhs_edit]"
      - 'Add constraint' button.
    Emits granular signals upward. The View wires them to the controller.
    """
    # Objective coefs
    obj_coef_changed = Signal(int, object)          # (var_index, float|None)

    # Constraint edits
    cons_coef_changed = Signal(int, int, object)    # (row, var_index, float|None)
    cons_rel_changed = Signal(int, str)             # (row, rel)
    cons_rhs_changed = Signal(int, object)          # (row, float|None)
    add_cons_clicked = Signal()                     # request to add new constraint
    remove_cons_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None, max_width: int | None = None):
        super().__init__("", parent)
        if max_width is not None:
            # Optional: constrain width like other sections do
            self.setMaximumWidth(max_width)

        # INIT rows storage early to avoid AttributeError
        self._rows: List[_ConstraintRowWidgets] = []   # <-- ADD THIS LINE

        # ---- Objective function row ----
        self._obj_row = QHBoxLayout()
        self._obj_row.setContentsMargins(0, 0, 0, 0)
        self._obj_row.setSpacing(6)

        # Title "z ="
        self._lbl_z = QLabel("z =")
        self._obj_row.addWidget(self._lbl_z)

        self._obj_coef_edits: List[QLineEdit] = []
        self.body.addLayout(self._obj_row)

        # ---- Constraints header ----
        hdr = QLabel()
        hdr.setObjectName("ConsHeader")
        self.body.addWidget(hdr)
        self._lbl_cons_header = hdr

        # ---- Constraints container (vertical) ----
        self._cons_container = QVBoxLayout()
        self._cons_container.setContentsMargins(0, 0, 0, 0)
        self._cons_container.setSpacing(8)
        self.body.addLayout(self._cons_container)

        # ---- Add constraint button ----
        add_row = QHBoxLayout()
        add_row.addStretch(1)
        self.btn_add = QPushButton()
        self.btn_add.clicked.connect(self.add_cons_clicked.emit)
        add_row.addWidget(self.btn_add)
        self.body.addLayout(add_row)

        self.refresh_strings()

    # -------- Public API --------
    def set_variables(self, vars_list: List[LPVariable]) -> None:
        """Rebuild the objective row and reflow all constraints' coefficient editors."""
        # Rebuild objective row
        self._rebuild_objective_row(vars_list)
        # SAFE GUARD: ensure _rows exists
        # (not strictly needed after init, but cheap and defensive)
        if not hasattr(self, "_rows"):
            self._rows = []
        for r_idx, row in enumerate(self._rows):
            self._reflow_constraint_row(r_idx, row, vars_list)

    def set_constraints_count(self, n: int, vars_list: List[LPVariable]) -> None:
        """Ensure there are exactly n visible constraint rows."""
        # _rows is guaranteed by __init__, but be defensive:
        if not hasattr(self, "_rows"):
            self._rows = []
        cur = len(self._rows)
        if cur < n:
            for _ in range(n - cur):
                self._append_constraint_row(vars_list)
        elif cur > n:
            for _ in range(cur - n):
                row = self._rows.pop()
                self._delete_row(row)

    # (optional) paint helpers if you later want to set values programmatically:
    # set_objective_coefs(list[Optional[float]]), set_constraint_row(...)

    def refresh_strings(self) -> None:
        # card title split into two logical parts; we keep Section title generic 'Constraints' or custom
        self.set_title(S.t("lp.cons.section"))  # overall card title
        self._lbl_cons_header.setText(S.t("lp.cons.header"))
        self.btn_add.setText(S.t("lp.cons.add"))
        # placeholders update
        for i, e in enumerate(self._obj_coef_edits):
            e.setPlaceholderText(S.t("lp.obj.coef_ph", idx=i+1))
        for r in getattr(self, "_rows", []):
            for i, e in enumerate(r.coef_edits):
                e.setPlaceholderText(S.t("lp.cons.coef_ph", idx=i+1))
            r.rhs_edit.setPlaceholderText(S.t("lp.cons.rhs_ph"))
            r.remove_btn.setText(S.t("lp.cons.remove"))

    def refresh_theme(self) -> None:
        super().refresh_theme()
        # Secondary hint style to header
        self._lbl_cons_header.setStyleSheet(theme.secondary_text_css(self))

    # -------- Internal build helpers --------
    def _rebuild_objective_row(self, vars_list: List[LPVariable]) -> None:
        """Recreate 'z = ...' editors for current variables."""
        # remove old edits and labels (except the initial 'z =')
        while self._obj_row.count() > 1:
            it = self._obj_row.takeAt(1)
            w = it.widget()
            if w:
                w.deleteLater()
        self._obj_coef_edits.clear()

        for i, v in enumerate(vars_list):
            # coefficient edit
            edit = QLineEdit()
            edit.setFixedHeight(28)
            edit.setPlaceholderText(S.t("lp.obj.coef_ph", idx=i+1))
            edit.editingFinished.connect(lambda i=i, e=edit: self._emit_obj_coef(i, e))
            self._obj_row.addWidget(edit)
            # label x_i
            self._obj_row.addWidget(QLabel(v.name))
            # plus separator except last
            if i < len(vars_list) - 1:
                plus = QLabel("+")
                plus.setStyleSheet(theme.secondary_text_css(self))
                self._obj_row.addWidget(plus)
            self._obj_coef_edits.append(edit)

        self._obj_row.addStretch(1)

    def _append_constraint_row(self, vars_list: List[LPVariable]) -> None:
        """Add a brand-new empty constraint row at the bottom."""
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        coef_edits: List[QLineEdit] = []
        r_index = len(getattr(self, "_rows", []))  # index of the new row

        for i, v in enumerate(vars_list):
            e = QLineEdit()
            e.setFixedHeight(28)
            e.setPlaceholderText(S.t("lp.cons.coef_ph", idx=i+1))
            e.editingFinished.connect(lambda r=r_index, i=i, e=e: self._emit_cons_coef(r, i, e))
            row_layout.addWidget(e)
            row_layout.addWidget(QLabel(v.name))
            if i < len(vars_list) - 1:
                plus = QLabel("+")
                plus.setStyleSheet(theme.secondary_text_css(self))
                row_layout.addWidget(plus)
            coef_edits.append(e)

        # relation combo
        rel_combo = QComboBox()
        rel_combo.addItems(["≤", "=", "≥"])
        rel_combo.currentIndexChanged.connect(lambda _idx, r=r_index, cb=rel_combo: self._emit_cons_rel(r, cb))
        row_layout.addWidget(rel_combo)

        # RHS
        rhs = QLineEdit()
        rhs.setFixedHeight(28)
        rhs.setPlaceholderText(S.t("lp.cons.rhs_ph"))
        rhs.editingFinished.connect(lambda r=r_index, e=rhs: self._emit_cons_rhs(r, e))
        row_layout.addWidget(rhs, 1)

        btn = QPushButton(S.t("lp.cons.remove"))
        btn.setFixedHeight(28)
        # cattura l'indice di riga corrente al momento della creazione
        btn.clicked.connect(lambda _=False, r=r_index: self.remove_cons_clicked.emit(r))
        row_layout.addWidget(btn)
        
        self._rows.append(
            _ConstraintRowWidgets(
                coef_edits = coef_edits, 
                rel_combo = rel_combo, 
                rhs_edit = rhs,
                layout = row_layout, 
                remove_btn = btn
            )
        )

        # push into container
        self._cons_container.addLayout(row_layout)

    def _reflow_constraint_row(self, r_index: int, row: _ConstraintRowWidgets, vars_list: List[LPVariable]) -> None:
        """Adjust one constraint row to the current number of variables."""
        # remove all current coef widgets from layout
        # (leave rel_combo and rhs at the end; we will rebuild coef area)
        # strategy: clear layout and fully rebuild like _append but keeping rel/rhs instances
        parent_layout = row.layout

        # First, detach widgets from layout to delete
        while parent_layout.count():
            it = parent_layout.takeAt(0)
            w = it.widget()
            if w and w not in (row.rel_combo, row.rhs_edit, row.remove_btn):
                w.deleteLater()

        row.coef_edits.clear()

        # Re-add coef edits + labels
        for i, v in enumerate(vars_list):
            e = QLineEdit()
            e.setFixedHeight(28)
            e.setPlaceholderText(S.t("lp.cons.coef_ph", idx=i+1))
            e.editingFinished.connect(lambda r=r_index, i=i, e=e: self._emit_cons_coef(r, i, e))
            parent_layout.addWidget(e)
            parent_layout.addWidget(QLabel(v.name))
            if i < len(vars_list) - 1:
                plus = QLabel("+")
                plus.setStyleSheet(theme.secondary_text_css(self))
                parent_layout.addWidget(plus)
            row.coef_edits.append(e)

        # Re-append relation and rhs at the end
        parent_layout.addWidget(row.rel_combo)
        parent_layout.addWidget(row.rhs_edit, 1)

        # rebind remove button with current index
        try:
            row.remove_btn.clicked.disconnect()
        except Exception:
            pass
        row.remove_btn.clicked.connect(lambda _=False, r=r_index: self.remove_cons_clicked.emit(r))
        parent_layout.addWidget(row.remove_btn)

    def _delete_row(self, row: _ConstraintRowWidgets) -> None:
        """Remove a constraint row widgets from UI."""
        # find index in layout and remove it
        for i in range(self._cons_container.count()):
            if self._cons_container.itemAt(i).layout() is row.layout:
                self._cons_container.takeAt(i) 
                break
        # delete widgets and layout
        while row.layout.count():
            it = row.layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    # -------- Emitters --------
    def _emit_obj_coef(self, i: int, edit: QLineEdit) -> None:
        self.obj_coef_changed.emit(i, _parse_number(edit.text()))

    def _emit_cons_coef(self, r: int, i: int, edit: QLineEdit) -> None:
        self.cons_coef_changed.emit(r, i, _parse_number(edit.text()))

    def _emit_cons_rel(self, r: int, combo: QComboBox) -> None:
        idx = combo.currentIndex()
        rel = "<=" if idx == 0 else ("=" if idx == 1 else ">=")
        self.cons_rel_changed.emit(r, rel)

    def _emit_cons_rhs(self, r: int, edit: QLineEdit) -> None:
        self.cons_rhs_changed.emit(r, _parse_number(edit.text()))
