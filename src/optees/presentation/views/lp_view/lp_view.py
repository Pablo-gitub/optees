# src/optees/presentation/views/lp_view/lp_view.py
from __future__ import annotations
import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox,
)

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.core.design import tokens
from optees.presentation.controllers.lp_controller import LPController, LPVariable
from optees.presentation.views.widgets.flow_layout import FlowLayout
from .intro_section import IntroSection
from .variables_section import VariablesSection
from .bounds_section import BoundsSection
from .objective_section import ObjectiveSection
from .objective_constraints_section import ObjectiveConstraintsSection

log = logging.getLogger(__name__)

class LPView(QWidget):
    solve_completed = Signal(object)
    example_requested = Signal()
    problem_description_requested = Signal()

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
        self.obj_cons_sec.obj_coef_changed.connect(self._on_obj_coef_changed)
        self.obj_cons_sec.cons_coef_changed.connect(self._on_cons_coef_changed)
        self.obj_cons_sec.cons_rel_changed.connect(self._on_cons_rel_changed)
        self.obj_cons_sec.cons_rhs_changed.connect(self._on_cons_rhs_changed)
        self.obj_cons_sec.add_cons_clicked.connect(self._on_add_constraint_clicked)
        self.obj_cons_sec.remove_cons_clicked.connect(self._on_remove_constraint_clicked)

        # optimize button
        self._solve_uc = None
        self.btn_optimize.clicked.connect(self._on_optimize_clicked)
        self.intro.example_clicked.connect(self.example_requested.emit)
        self.intro.problem_clicked.connect(self.problem_description_requested.emit)
        self.intro.import_clicked.connect(self._on_import_json)


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

        # keep optimize button state in sync + repaint objective fields
        if hasattr(self._ctrl, "objective_changed"):
            self._ctrl.objective_changed.connect(lambda *_: self._update_optimize_enabled())
            self._ctrl.objective_changed.connect(self._on_objective_changed)

        self._update_optimize_enabled()

    # solver usecase binding
    def set_solve_usecase(self, usecase):
        self._solve_uc = usecase

    def _on_vars_changed(self, vars_list: list[LPVariable]) -> None:
        self.vars_sec.set_variables(vars_list)
        self.bounds_sec.set_variables(vars_list)
        self.obj_cons_sec.set_variables(vars_list)
        self._update_optimize_enabled()

    # -------- handlers --------
    def _update_optimize_enabled(self) -> None:
        has_vars = bool(self._ctrl and self._ctrl.variables())
        self.btn_optimize.setEnabled(has_vars)

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
        ub_val = cur.bounds.ub   # <-- PRIMA era cur.ub
        if (lb_val is not None) and (ub_val is not None) and (lb_val > ub_val):
            return
        self._ctrl.set_bounds(index, lb_val, ub_val)

    def _on_ub_changed(self, index: int, ub_val) -> None:
        if not self._ctrl: return
        cur = self._ctrl.variables()[index]
        lb_val = cur.bounds.lb   # <-- PRIMA era cur.lb
        if (lb_val is not None) and (ub_val is not None) and (lb_val > ub_val):
            return
        self._ctrl.set_bounds(index, lb_val, ub_val)

    def _on_preset_clicked(self, index: int, preset: str) -> None:
        if not self._ctrl: return
        self._ctrl.apply_preset(index, preset)

    # NEW: Objective handlers (no coefs)
    def _on_obj_coef_changed(self, index: int, value) -> None:
        if self._ctrl:
            self._ctrl.set_objective_coef(index, value)

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

    def _on_remove_constraint_clicked(self, row: int) -> None:
        if self._ctrl:
            self._ctrl.remove_constraint(row)

    def _on_objective_changed(self, objective) -> None:
        """Push objective sense, offset, and coefs into the UI after a model load."""
        sense = getattr(getattr(objective, "sense", None), "name", "max").lower()
        offset_raw = getattr(objective, "offset", None)
        offset = float(offset_raw) if offset_raw is not None else None
        coefs = list(getattr(objective, "coefs", None) or [])
        self.obj_sec.set_values(sense, offset)
        self.obj_cons_sec.set_objective_coefs(coefs)

    def _on_constraints_changed(self, cons_snapshot) -> None:
        """Sync row count AND fill values after a model load."""
        vars_now = self._ctrl.variables() if self._ctrl else []
        self.obj_cons_sec.set_constraints_count(len(cons_snapshot), vars_now)
        for r_idx, c in enumerate(cons_snapshot):
            coefs = list(getattr(c, "coefs", None) or [])
            rel_str = getattr(getattr(c, "relation", None), "symbol", lambda: "<=")()
            rhs = getattr(c, "rhs", None)
            self.obj_cons_sec.set_constraint_values(r_idx, coefs, rel_str, rhs)

    def _on_cons_coef_changed(self, row: int, index: int, value) -> None:
        if self._ctrl:
            self._ctrl.set_constraint_coef(row, index, value)

    def _on_cons_rel_changed(self, row: int, rel: str) -> None:
        if self._ctrl:
            self._ctrl.set_constraint_rel(row, rel)

    def _on_cons_rhs_changed(self, row: int, value) -> None:
        if self._ctrl:
            self._ctrl.set_constraint_rhs(row, value)

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            S.t("lp.import.dialog_title"),
            "",
            "JSON (*.json);;All files (*)",
        )
        if not path:
            return
        try:
            from optees.utility.lp_json_io import lp_model_from_file
            model = lp_model_from_file(path)
        except ValueError as exc:
            QMessageBox.warning(
                self,
                S.t("lp.import.error_title"),
                S.t("lp.import.error_body", detail=str(exc)),
            )
            return
        if self._ctrl:
            self._ctrl.load_model(model)

    def _on_optimize_clicked(self):
        if not self._ctrl or not self._solve_uc:
            return

        # flush coefs dalla UI
        for j, val in enumerate(self.obj_cons_sec.get_objective_coefs()):
            self._ctrl.set_objective_coef(j, val)

        model = self._ctrl.model()
        n = len(model.variables)

        if log.isEnabledFor(logging.DEBUG):
            def _as_list_coefs(coefs, n):
                if coefs is None: return [None]*n
                if isinstance(coefs, dict): return [coefs.get(i) for i in range(n)]
                try:
                    seq = list(coefs)
                    return (seq + [None]*max(0, n-len(seq)))[:n]
                except Exception:
                    return [None]*n

            c_list = _as_list_coefs(getattr(model.objective, "coefs", None), n)
            cons_list = [(_as_list_coefs(getattr(c, "coefs", None), n), c.relation.symbol(), c.rhs)
                        for c in model.constraints]

            log.debug("sense=%s offset=%s c=%s bounds=%s cons=%s",
                    getattr(model.objective.sense, "name", model.objective.sense),
                    getattr(model.objective, "offset", None),
                    c_list,
                    [(v.bounds.lb, v.bounds.ub) for v in model.variables],
                    cons_list)

        solution = self._solve_uc.execute(model, method="highs")
        self.solve_completed.emit(solution)


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
        self.page_title.setStyleSheet(
            f"color: {tokens(theme.is_dark()).text}; margin-top: 8px; margin-bottom: 8px;"
        )
        self.intro.refresh_theme()
        self.vars_sec.refresh_theme()
        self.bounds_sec.refresh_theme()
        self.obj_sec.refresh_theme()
        self.obj_cons_sec.refresh_theme()
