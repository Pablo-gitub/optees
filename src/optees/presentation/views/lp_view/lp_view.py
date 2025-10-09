# src/optees/presentation/views/lp_view/lp_view.py
from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout, QPushButton
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.controllers.lp_controller import LPController, LPVariable
from optees.presentation.views.widgets.flow_layout import FlowLayout
from .intro_section import IntroSection
from .variables_section import VariablesSection
from .bounds_section import BoundsSection
from .objective_section import ObjectiveSection
from .objective_constraints_section import ObjectiveConstraintsSection

class LPView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        sc = QScrollArea(self)
        sc.setWidgetResizable(True)
        sc.setAlignment(Qt.AlignTop)
        outer.addWidget(sc)

        page = QWidget(); sc.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(12)

        # title
        self.page_title = QLabel()
        self.page_title.setTextFormat(Qt.RichText)
        self.page_title.setWordWrap(True)
        root.addWidget(self.page_title)

        # intro
        self.intro = IntroSection()
        root.addWidget(self.intro)

        # row: variables + bounds (SIDE-BY-SIDE)
        row = FlowLayout(hspacing=16, vspacing=16)
        root.addLayout(row)

        self.vars_sec = VariablesSection(max_width=520)
        self.bounds_sec = BoundsSection(max_width=520)
        row.addWidget(self.vars_sec)
        row.addWidget(self.bounds_sec)

        # objective (sense + offset)
        self.obj_sec = ObjectiveSection()
        root.addWidget(self.obj_sec)

        # constraints/objective-function card
        self.obj_cons_sec = ObjectiveConstraintsSection(max_width=None)
        root.addWidget(self.obj_cons_sec)

        # footer
        root.addStretch(1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_optimize = QPushButton()
        self.btn_optimize.setEnabled(False)
        footer.addWidget(self.btn_optimize)
        root.addLayout(footer)

        # i18n / theme
        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)

        self._ctrl: Optional[LPController] = None
        self.refresh_theme()
        self.refresh_strings()

        # delegate: Variables
        self.vars_sec.add_clicked.connect(self._on_add_var_clicked)
        self.vars_sec.remove_clicked.connect(self._on_var_remove)
        self.vars_sec.label_changed.connect(self._on_var_label_changed)

        # delegate: Bounds
        self.bounds_sec.lb_changed.connect(self._on_lb_changed)
        self.bounds_sec.ub_changed.connect(self._on_ub_changed)
        self.bounds_sec.preset_clicked.connect(self._on_preset_clicked)

        # delegate: Objective (ONLY sense + offset)
        self.obj_sec.sense_changed.connect(self._on_obj_sense_changed)
        self.obj_sec.offset_changed.connect(self._on_obj_offset_changed)

        # delegate: Constraints (NEW, placeholder)
        self.obj_cons_sec.cons_coef_changed.connect(self._on_cons_coef_changed)
        self.obj_cons_sec.cons_rel_changed.connect(self._on_cons_rel_changed)
        self.obj_cons_sec.cons_rhs_changed.connect(self._on_cons_rhs_changed)
        self.obj_cons_sec.add_cons_clicked.connect(self._on_add_constraint_clicked)

    # -------- controller binding --------
    def set_controller(self, controller: LPController) -> None:
        self._ctrl = controller
        if not self._ctrl.variables():
            self._ctrl.add_variable()
            self._ctrl.add_variable()

        if not self._ctrl.constraints():
            self._ctrl.add_constraint()

        # initial paint
        vars_now = self._ctrl.variables()
        self._on_vars_changed(vars_now)

        # controller -> sections
        self._ctrl.variables_changed.connect(self._on_vars_changed)
        self._ctrl.variable_updated.connect(self.vars_sec.update_label)
        self._ctrl.bounds_changed.connect(lambda _: self.bounds_sec.set_variables(self._ctrl.variables()))
        self._ctrl.constraints_changed.connect(self._on_constraints_changed)

    def _on_vars_changed(self, vars_list: list[LPVariable]) -> None:
        self.vars_sec.set_variables(vars_list)
        self.bounds_sec.set_variables(vars_list)
        self.obj_cons_sec.set_variables(vars_list)

    # -------- handlers --------
    def _on_add_var_clicked(self) -> None:
        if self._ctrl:
            self._ctrl.add_variable()

    def _on_var_remove(self, index: int) -> None:
        if self._ctrl:
            self._ctrl.remove_variable(index)

    def _on_var_label_changed(self, index: int, text: str) -> None:
        if self._ctrl:
            self._ctrl.set_description(index, text)

    def _on_lb_changed(self, index: int, lb_val) -> None:
        if not self._ctrl: return
        cur = self._ctrl.variables()[index]
        ub_val = cur.ub
        if (lb_val is not None) and (ub_val is not None) and (lb_val > ub_val):
            return
        self._ctrl.set_bounds(index, lb_val, ub_val)

    def _on_ub_changed(self, index: int, ub_val) -> None:
        if not self._ctrl: return
        cur = self._ctrl.variables()[index]
        lb_val = cur.lb
        if (lb_val is not None) and (ub_val is not None) and (lb_val > ub_val):
            return
        self._ctrl.set_bounds(index, lb_val, ub_val)

    def _on_preset_clicked(self, index: int, preset: str) -> None:
        if not self._ctrl: return
        self._ctrl.apply_preset(index, preset)

    # NEW: Objective handlers (no coefs)
    def _on_obj_sense_changed(self, sense: str) -> None:
        if self._ctrl:
            self._ctrl.set_objective_sense(sense)

    def _on_obj_offset_changed(self, value) -> None:
        if self._ctrl:
            self._ctrl.set_objective_offset(value)

    # ---- Constraints handlers ----
    def _on_add_constraint_clicked(self) -> None:
        if self._ctrl:
            self._ctrl.add_constraint()

    def _on_constraints_changed(self, cons_snapshot) -> None:
        # cons_snapshot is List[LPConstraint]; we only need the count to sync rows
        self.obj_cons_sec.set_constraints_count(len(cons_snapshot), self._ctrl.variables())

    def _on_cons_coef_changed(self, row: int, index: int, value) -> None:
        if self._ctrl:
            self._ctrl.set_constraint_coef(row, index, value)

    def _on_cons_rel_changed(self, row: int, rel: str) -> None:
        if self._ctrl:
            self._ctrl.set_constraint_rel(row, rel)

    def _on_cons_rhs_changed(self, row: int, value) -> None:
        if self._ctrl:
            self._ctrl.set_constraint_rhs(row, value)

    # -------- refresh --------
    def refresh_strings(self) -> None:
        self.page_title.setText(f"<span style='font-size:20px; font-weight:700'>{S.t('lp.header.title')}</span>")
        self.intro.refresh_strings()
        self.vars_sec.refresh_strings()
        self.bounds_sec.refresh_strings()
        self.obj_sec.refresh_strings()  
        self.obj_cons_sec.refresh_strings()
        self.btn_optimize.setText(S.t("lp.actions.optimize"))

    def refresh_theme(self) -> None:
        if theme.is_dark():
            self.page_title.setStyleSheet("color: rgba(255,255,255,0.95); margin-top: 8px; margin-bottom: 8px;")
        else:
            self.page_title.setStyleSheet("color: rgba(0,0,0,0.90); margin-top: 8px; margin-bottom: 8px;")
        self.intro.refresh_theme()
        self.vars_sec.refresh_theme()
        self.bounds_sec.refresh_theme()
        self.obj_sec.refresh_theme()
        self.obj_cons_sec.refresh_theme()
