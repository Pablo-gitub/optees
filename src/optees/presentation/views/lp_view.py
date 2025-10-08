from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy, QScrollArea, QPushButton
)
from PySide6.QtGui import QRegularExpressionValidator, QIcon
from PySide6.QtCore import QRegularExpression
from PySide6.QtWidgets import QLineEdit, QToolButton

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.presentation.controllers.lp_controller import LPController, LPVariable
from optees.presentation.views.widgets.flow_layout import FlowLayout


# ---------------- Row "Xk [name]  🗑︎" ----------------
class VarRow(QWidget):
    remove_requested = Signal(int)      # variable index
    desc_changed = Signal(int, str)     # (index, text)

    def __init__(self, index: int, name: str, description: str,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._index = index

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # left label "Xk"
        self.lbl = QLabel(name)
        self.lbl.setMinimumWidth(40)

        # single-line input for short variable name
        self.txt = QLineEdit(description)
        self.txt.setPlaceholderText(S.t("lp.vars.name_placeholder"))
        self.txt.setClearButtonEnabled(True)
        self.txt.setFixedHeight(28)                   # single-line height
        self.txt.setMinimumWidth(160)
        self.txt.setMaximumWidth(400)
        self.txt.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.setStretchFactor(self.txt, 1)

        # light validation: letters/numbers/space/-/_ up to 24 chars
        rx = QRegularExpression(r"^[\w\s\-]{0,100}$")
        self.txt.setValidator(QRegularExpressionValidator(rx, self))

        # emit only on user edits (prevents programmatic setText loops)
        self.txt.textEdited.connect(self._on_text_edited)

        # delete button: toolbutton, icon-only, compact
        self.btn_remove = QToolButton()
        icon = QIcon.fromTheme("edit-delete")
        if not icon.isNull():
            self.btn_remove.setIcon(icon)
        else:
            self.btn_remove.setText("🗑︎")
        self.btn_remove.setToolTip(S.t("lp.vars.remove"))
        self.btn_remove.setAutoRaise(True)      # flat look
        self.btn_remove.setFixedSize(28, 28)    # compact square
        self.btn_remove.clicked.connect(self._on_remove)

        layout.addWidget(self.lbl)
        layout.addWidget(self.txt)                 # no stretch; stays compact
        layout.addWidget(self.btn_remove)

    def set_index_and_name(self, index: int, name: str) -> None:
        self._index = index
        self.lbl.setText(name)

    def _on_remove(self) -> None:
        self.remove_requested.emit(self._index)

    def _on_text_edited(self, text: str) -> None:
        # emit trimmed value to controller
        self.desc_changed.emit(self._index, text.strip())

    def refresh_strings(self) -> None:
        """Refresh i18n-dependent strings (placeholder, tooltips)."""
        self.txt.setPlaceholderText(S.t("lp.vars.name_placeholder"))
        self.btn_remove.setToolTip(S.t("lp.vars.remove"))


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

        # simple placeholder so you see the second card
        bounds_lbl = QLabel("Bounds (coming soon)")
        bounds_lbl.setStyleSheet(theme.secondary_text_css(self))
        self.sec_bounds.body.addWidget(bounds_lbl)
        self.sec_bounds.set_title("Bounds")

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

    # -------- Var rows helpers --------
    def _clear_layout(self, lay: QVBoxLayout) -> None:
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _rebuild_var_rows(self, vars_list: list[LPVariable]) -> None:
        self._clear_layout(self._vars_container)
        for i, v in enumerate(vars_list):
            row = VarRow(index=i, name=v.name, description=v.description)
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

        # Page Footer 
        self.btn_optimize.setText(S.t("lp.actions.optimize"))

    def refresh_theme(self) -> None:
        self.sec_intro.refresh_theme()
        self.sec_vars.refresh_theme()
        self._intro_desc.setStyleSheet(theme.secondary_text_css(self))
        self._vars_hint.setStyleSheet(theme.secondary_text_css(self))

        # titolo fuori dalla card
        if theme.is_dark():
            self.page_title.setStyleSheet("color: rgba(255,255,255,0.95); margin-top: 8px; margin-bottom: 8px;")
        else:
            self.page_title.setStyleSheet("color: rgba(0,0,0,0.90); margin-top: 8px; margin-bottom: 8px;")

