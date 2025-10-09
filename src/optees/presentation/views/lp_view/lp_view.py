# src/optees/presentation/views/lp_view/lp_view.py
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy, QScrollArea, QPushButton
)

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.controllers.lp_controller import LPController, LPVariable
from optees.presentation.views.widgets.flow_layout import FlowLayout
from .var_row import VarRow
from .bound_row import BoundRow

# ---------------- Card/Section con bordo ----------------
class Section(QFrame):
    def __init__(self, title_text: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setObjectName("Section")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)  # non richiede altezza extra

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(14, 10, 14, 10)
        self._root.setSpacing(8)

        self._title = QLabel(title_text, self)
        self._title.setObjectName("SectionTitle")
        self._title.setTextFormat(Qt.RichText)
        self._root.addWidget(self._title)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(8)
        self._root.addLayout(self.body)

        self.refresh_theme()

    def set_title(self, text: str) -> None:
        self._title.setText(f"<span style='font-size:16px; font-weight:600'>{text}</span>")

    def refresh_theme(self) -> None:
        if theme.is_dark():
            self.setStyleSheet("""
                QFrame#Section { border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; }
                QLabel#SectionTitle { color: rgba(255,255,255,0.92); }
            """)
        else:
            self.setStyleSheet("""
                QFrame#Section { border: 1px solid rgba(0,0,0,0.10); border-radius: 10px; }
                QLabel#SectionTitle { color: rgba(0,0,0,0.85); }
            """)


# ---------------- LPView ----------------
class LPView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # --- contenitore scrollabile top-aligned ---
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        sc = QScrollArea(self)
        sc.setWidgetResizable(True)
        sc.setAlignment(Qt.AlignTop)             # allinea in alto
        outer.addWidget(sc)

        page = QWidget()
        sc.setWidget(page)

        root = QVBoxLayout(page)
        root.setContentsMargins(16, 12, 16, 16)  # margini compatti
        root.setSpacing(12)

        # ---------- Intestazione algoritmo ----------
        self.page_title = QLabel()
        self.page_title.setTextFormat(Qt.RichText)
        self.page_title.setWordWrap(True)
        self.page_title.setObjectName("PageTitle")
        root.addWidget(self.page_title)

        # Card descrizione + pulsanti
        self.sec_intro = Section()
        root.addWidget(self.sec_intro)

        self._intro_desc = QLabel()
        self._intro_desc.setWordWrap(True)
        self._intro_desc.setObjectName("IntroDesc")
        self._intro_desc.setStyleSheet(theme.secondary_text_css(self))
        self.sec_intro.body.addWidget(self._intro_desc)

        intro_btns = QHBoxLayout()
        intro_btns.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_problem = QPushButton()
        intro_btns.addWidget(self.btn_example)
        intro_btns.addWidget(self.btn_problem)
        self.sec_intro.body.addLayout(intro_btns)

        # ---------- Cards row (Variables + Bounds side-by-side) ----------
        row_cards = FlowLayout(hspacing=16, vspacing=16)
        root.addLayout(row_cards)

        # Variables card
        self.sec_vars = Section()
        self.sec_vars.setFixedWidth(520)                              # fixed width, dynamic height
        self.sec_vars.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        row_cards.addWidget(self.sec_vars)

        # Bounds card (placeholder for now)
        self.sec_bounds = Section()
        self.sec_bounds.setFixedWidth(520)
        self.sec_bounds.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        row_cards.addWidget(self.sec_bounds)

        self._bounds_rows: list[BoundRow] = []

        # header della tabella bounds (col names)
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(8)
        hdr.addWidget(QLabel(S.t("lp.bounds.columns.var")), 1)
        hdr.addWidget(QLabel(S.t("lp.bounds.columns.lb")), 0)
        hdr.addWidget(QLabel(S.t("lp.bounds.columns.ub")), 0)
        hdr.addWidget(QLabel(S.t("lp.bounds.columns.preset")), 0)
        self.sec_bounds.body.addLayout(hdr)

        # hint sotto l'header
        self._bounds_hint = QLabel(S.t("lp.bounds.hint"))
        self._bounds_hint.setStyleSheet(theme.secondary_text_css(self))
        self.sec_bounds.body.addWidget(self._bounds_hint)

        # container verticale per le righe bounds
        self._bounds_container = QVBoxLayout()
        self._bounds_container.setContentsMargins(0, 0, 0, 0)
        self._bounds_container.setSpacing(8)
        self.sec_bounds.body.addLayout(self._bounds_container)

        # hint iniziale
        self._vars_hint = QLabel()
        self._vars_hint.setWordWrap(True)
        self._vars_hint.setStyleSheet(theme.secondary_text_css(self))
        self.sec_vars.body.addWidget(self._vars_hint)

        # container righe
        self._vars_container = QVBoxLayout()
        self._vars_container.setContentsMargins(0, 0, 0, 0)
        self._vars_container.setSpacing(8)
        self.sec_vars.body.addLayout(self._vars_container)

        # footer della sezione variabili
        vars_footer = QHBoxLayout()
        vars_footer.addStretch(1)
        self.btn_add_var = QPushButton()
        vars_footer.addWidget(self.btn_add_var)
        self.sec_vars.body.addLayout(vars_footer)

        # --- stretch per ancorare tutto in alto ---
        root.addStretch(1)

        # --- Footer pagina (Ottimizza) ---
        footer = QHBoxLayout()
        footer.addStretch(1)
        self.btn_optimize = QPushButton()
        self.btn_optimize.setEnabled(False)  # si abiliterà più avanti
        footer.addWidget(self.btn_optimize)
        root.addLayout(footer)

        # wiring: lingua/tema (il tema viene anche propagato da MainWindow)
        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)

        self._ctrl: Optional[LPController] = None

        self.refresh_theme()
        self.refresh_strings()

        # handlers locali
        self.btn_add_var.clicked.connect(self._on_add_var_clicked)

    # -------- Controller wiring --------
    def set_controller(self, controller: LPController) -> None:
        self._ctrl = controller
        if not self._ctrl.variables():
            self._ctrl.add_variable()
            self._ctrl.add_variable()

        self._rebuild_var_rows(self._ctrl.variables())
        self._ctrl.variables_changed.connect(self._rebuild_var_rows)
        self._ctrl.variable_updated.connect(self._on_var_updated)

        self._rebuild_bounds_rows(self._ctrl.variables())
        self._ctrl.variables_changed.connect(self._rebuild_bounds_rows)
        self._ctrl.bound_updated.connect(lambda i, lb, ub: None)    # reserved for future granular UI tweaks
        self._ctrl.bounds_changed.connect(lambda _: None)           # reserved


    # -------- Var rows helpers --------

    def _rebuild_var_rows(self, vars_list: list[LPVariable]) -> None:
        self._clear_layout_items(self._vars_container)
        for i, v in enumerate(vars_list):
            row = VarRow(index=i, name=v.name, description=v.label)
            row.refresh_strings()
            row.remove_requested.connect(self._on_var_remove)
            row.desc_changed.connect(self._on_var_desc_changed)
            self._vars_container.addWidget(row)

    def _on_var_remove(self, index: int):
        if self._ctrl:
            self._ctrl.remove_variable(index)

    def _on_var_desc_changed(self, index: int, text: str):
        if self._ctrl:
            self._ctrl.set_description(index, text)

    def _on_var_updated(self, index: int, text: str):
        # la riga ha già aggiornato il testo localmente; manteniamo per futuri side-effects
        pass

    def _on_add_var_clicked(self):
        if self._ctrl:
            self._ctrl.add_variable()

    # -------- Refresh UI --------
    def refresh_strings(self) -> None:
        # Header
        self.page_title.setText(
            f"<span style='font-size:20px; font-weight:700'>{S.t('lp.header.title')}</span>"
        )
        self._intro_desc.setText(S.t("lp.header.description"))
        self.btn_example.setText(S.t("lp.header.buttons.example"))
        self.btn_problem.setText(S.t("lp.header.buttons.problem"))

        # Variables Section
        self.sec_vars.set_title(S.t("lp.vars.section"))
        self._vars_hint.setText(S.t("lp.vars.hint"))
        self.btn_add_var.setText(S.t("lp.vars.add"))

        # refresh rows
        for row in self.findChildren(VarRow):
           row.refresh_strings()

        # Bounds
        self.sec_bounds.set_title(S.t("lp.bounds.section"))
        # header labels
        try:
            # header layout is the first item in sec_bounds.body
            hdr_lay = self.sec_bounds.body.itemAt(0).layout()
            hdr_lay.itemAt(0).widget().setText(S.t("lp.bounds.columns.var"))
            hdr_lay.itemAt(1).widget().setText(S.t("lp.bounds.columns.lb"))
            hdr_lay.itemAt(2).widget().setText(S.t("lp.bounds.columns.ub"))
            hdr_lay.itemAt(3).widget().setText(S.t("lp.bounds.columns.preset"))
        except Exception:
            pass
        self._bounds_hint.setText(S.t("lp.bounds.hint"))
        for row in self._bounds_rows:
            row.refresh_strings()

        # Page Footer 
        self.btn_optimize.setText(S.t("lp.actions.optimize"))

    def refresh_theme(self) -> None:
        self.sec_intro.refresh_theme()
        self.sec_vars.refresh_theme()
        self.sec_bounds.refresh_theme()
        self._intro_desc.setStyleSheet(theme.secondary_text_css(self))
        self._vars_hint.setStyleSheet(theme.secondary_text_css(self))
        self._bounds_hint.setStyleSheet(theme.secondary_text_css(self))

        # titolo fuori dalla card
        if theme.is_dark():
            self.page_title.setStyleSheet("color: rgba(255,255,255,0.95); margin-top: 8px; margin-bottom: 8px;")
        else:
            self.page_title.setStyleSheet("color: rgba(0,0,0,0.90); margin-top: 8px; margin-bottom: 8px;")

    def _clear_layout_items(self, lay: QVBoxLayout) -> None:
        while lay.count():
            it = lay.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()

    def _rebuild_bounds_rows(self, vars_list: list[LPVariable]) -> None:
        self._clear_layout_items(self._bounds_container)
        self._bounds_rows = []
        for i, v in enumerate(vars_list):
            row = BoundRow(
                index=i,
                var_name=v.name,
                display_label=v.label,
                lb=v.lb,
                ub=v.ub
            )
            row.refresh_strings()
            row.lb_changed.connect(self._on_lb_changed)
            row.ub_changed.connect(self._on_ub_changed)
            row.preset_clicked.connect(self._on_preset_clicked)
            self._bounds_container.addWidget(row)
            self._bounds_rows.append(row)

    def _on_lb_changed(self, index: int, lb_val: Optional[float]) -> None:
        # read current UB from controller to validate order (if available)
        if not self._ctrl or not (0 <= index < len(self._ctrl.variables())):
            return
        cur = self._ctrl.variables()[index]
        ub_val = cur.ub
        # validate order after tentative update
        if (lb_val is not None) and (ub_val is not None) and (lb_val > ub_val):
            # show soft error on the row
            self._bounds_rows[index].show_error("lb", S.t("lp.bounds.errors.order"))
            return
        self._bounds_rows[index].clear_error()
        self._ctrl.set_bounds(index, lb_val, ub_val)

    def _on_ub_changed(self, index: int, ub_val: Optional[float]) -> None:
        if not self._ctrl or not (0 <= index < len(self._ctrl.variables())):
            return
        cur = self._ctrl.variables()[index]
        lb_val = cur.lb
        if (lb_val is not None) and (ub_val is not None) and (lb_val > ub_val):
            self._bounds_rows[index].show_error("ub", S.t("lp.bounds.errors.order"))
            return
        self._bounds_rows[index].clear_error()
        self._ctrl.set_bounds(index, lb_val, ub_val)

    def _on_preset_clicked(self, index: int, preset: str) -> None:
        if not self._ctrl:
            return
        self._ctrl.apply_preset(index, preset)
        # refresh the row UI from controller values
        v = self._ctrl.variables()[index]
        self._bounds_rows[index].edit_lb.setText(BoundRow._format_value(v.lb, is_lb=True))
        self._bounds_rows[index].edit_ub.setText(BoundRow._format_value(v.ub, is_lb=False))
        self._bounds_rows[index].clear_error()

