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

class LPView(QWidget):
    """High-level LP page: orchestrates sections and wires to the controller."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # scrollable container
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

        # page title (outside any card)
        self.page_title = QLabel()
        self.page_title.setTextFormat(Qt.RichText)
        self.page_title.setWordWrap(True)
        root.addWidget(self.page_title)

        # intro (description + buttons)
        self.intro = IntroSection()
        root.addWidget(self.intro)

        # row with two cards side-by-side
        row = FlowLayout(hspacing=16, vspacing=16)
        root.addLayout(row)

        # variables + bounds cards
        self.vars_sec = VariablesSection(max_width=520)
        self.bounds_sec = BoundsSection(max_width=520)
        row.addWidget(self.vars_sec)
        row.addWidget(self.bounds_sec)

        # footer (optimize)
        root.addStretch(1)
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_optimize = QPushButton()
        self.btn_optimize.setEnabled(False)
        footer.addWidget(self.btn_optimize)
        root.addLayout(footer)

        # listen to i18n/theme
        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)

        self._ctrl: Optional[LPController] = None
        self.refresh_theme()
        self.refresh_strings()

        # delegate section-level signals outward (controller will be attached later)
        self.vars_sec.add_clicked.connect(self._on_add_var_clicked)
        self.vars_sec.remove_clicked.connect(self._on_var_remove)
        self.vars_sec.label_changed.connect(self._on_var_label_changed)

        self.bounds_sec.lb_changed.connect(self._on_lb_changed)
        self.bounds_sec.ub_changed.connect(self._on_ub_changed)
        self.bounds_sec.preset_clicked.connect(self._on_preset_clicked)

    # -------- controller binding --------
    def set_controller(self, controller: LPController) -> None:
        self._ctrl = controller
        if not self._ctrl.variables():
            self._ctrl.add_variable()
            self._ctrl.add_variable()

        # initial paint
        self._on_vars_changed(self._ctrl.variables())

        # controller -> sections
        self._ctrl.variables_changed.connect(self._on_vars_changed)
        self._ctrl.variable_updated.connect(self.vars_sec.update_label)
        self._ctrl.bounds_changed.connect(lambda _: self.bounds_sec.set_variables(self._ctrl.variables()))

    def _on_vars_changed(self, vars_list: list[LPVariable]) -> None:
        self.vars_sec.set_variables(vars_list)
        self.bounds_sec.set_variables(vars_list)

    # -------- section signal handlers -> controller --------
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
            # let the row show error; controller update is skipped
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
        # bounds_sec will refresh via bounds_changed -> set_variables

    # -------- refresh --------
    def refresh_strings(self) -> None:
        self.page_title.setText(f"<span style='font-size:20px; font-weight:700'>{S.t('lp.header.title')}</span>")
        self.intro.refresh_strings()
        self.vars_sec.refresh_strings()
        self.bounds_sec.refresh_strings()
        self.btn_optimize.setText(S.t("lp.actions.optimize"))

    def refresh_theme(self) -> None:
        # only top-level tweaks; sections handle their own theme
        if theme.is_dark():
            self.page_title.setStyleSheet("color: rgba(255,255,255,0.95); margin-top: 8px; margin-bottom: 8px;")
        else:
            self.page_title.setStyleSheet("color: rgba(0,0,0,0.90); margin-top: 8px; margin-bottom: 8px;")
        self.intro.refresh_theme()
        self.vars_sec.refresh_theme()
        self.bounds_sec.refresh_theme()
