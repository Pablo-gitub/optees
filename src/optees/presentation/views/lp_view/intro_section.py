# src/optees/presentation/views/lp_view/intro_section.py
from __future__ import annotations
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QPushButton,
    QDialog, QVBoxLayout, QTextBrowser, QDialogButtonBox,
)
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from .section import Section

_SCHEMA_HTML = """\
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

<h3>Top-level object</h3>
<table>
  <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
  <tr><td><code>version</code></td><td><code>"1"</code></td><td>Yes</td><td>Schema version — must be the string <code>"1"</code></td></tr>
  <tr><td><code>variables</code></td><td>array</td><td>Yes</td><td>At least one variable object (see below)</td></tr>
  <tr><td><code>objective</code></td><td>object</td><td>Yes</td><td>Objective function (see below)</td></tr>
  <tr><td><code>constraints</code></td><td>array</td><td>Yes</td><td>Constraint list, may be empty <code>[]</code></td></tr>
</table>

<h3>Variable object</h3>
<table>
  <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
  <tr><td><code>lb</code></td><td>number | null</td><td>Yes</td><td>Lower bound. Use <code>null</code> for −∞</td></tr>
  <tr><td><code>ub</code></td><td>number | null</td><td>Yes</td><td>Upper bound. Use <code>null</code> for +∞</td></tr>
  <tr><td><code>name</code></td><td>string</td><td>No</td><td>Short identifier, e.g. <code>"X1"</code>. Defaults to <code>X{n}</code></td></tr>
  <tr><td><code>label</code></td><td>string</td><td>No</td><td>Human-readable description, e.g. <code>"chairs/day"</code></td></tr>
</table>

<h3>Objective object</h3>
<table>
  <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
  <tr><td><code>sense</code></td><td><code>"min"</code> | <code>"max"</code></td><td>Yes</td><td>Optimization direction</td></tr>
  <tr><td><code>coefficients</code></td><td>number[]</td><td>Yes</td><td>One value per variable — the <em>c</em> vector in <em>c·x</em></td></tr>
  <tr><td><code>offset</code></td><td>number</td><td>No</td><td>Constant added to objective. Defaults to <code>0</code></td></tr>
</table>

<h3>Constraint object</h3>
<table>
  <tr><th>Field</th><th>Type</th><th>Required</th><th>Description</th></tr>
  <tr><td><code>coefficients</code></td><td>number[]</td><td>Yes</td><td>One value per variable — must match variable count</td></tr>
  <tr><td><code>relation</code></td><td><code>"&lt;="</code> | <code>"="</code> | <code>"&gt;="</code></td><td>Yes</td><td>Constraint sense</td></tr>
  <tr><td><code>rhs</code></td><td>number</td><td>Yes</td><td>Right-hand side value</td></tr>
</table>

<h3>Example</h3>
<pre>{
  "version": "1",
  "variables": [
    { "name": "X1", "label": "chairs/day", "lb": 0,    "ub": null },
    { "name": "X2", "label": "tables/day", "lb": 0,    "ub": null }
  ],
  "objective": {
    "sense": "max",
    "coefficients": [30, 50],
    "offset": 100
  },
  "constraints": [
    { "coefficients": [2, 4], "relation": "<=", "rhs": 80 },
    { "coefficients": [1, 1], "relation": "<=", "rhs": 30 }
  ]
}</pre>
"""


class _SchemaDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(520, 420)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        self._intro = QLabel()
        self._intro.setWordWrap(True)
        layout.addWidget(self._intro)

        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(False)
        browser.setHtml(_SCHEMA_HTML)
        layout.addWidget(browser)

        self._buttons = QDialogButtonBox(QDialogButtonBox.Close)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self.refresh_strings()

    def refresh_strings(self) -> None:
        self.setWindowTitle(S.t("lp.import.schema_title"))
        self._intro.setText(S.t("lp.import.schema_intro"))
        close_btn = self._buttons.button(QDialogButtonBox.Close)
        if close_btn:
            close_btn.setText(S.t("lp.import.schema_close"))


class IntroSection(Section):
    """Static intro: description + info buttons. Import JSON button in header."""
    example_clicked = Signal()
    problem_clicked = Signal()
    import_clicked  = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("", parent)

        # "Import JSON" + "i" buttons — placed in the header row (right side)
        self.btn_import = QPushButton()
        self.btn_import.setObjectName("btnImportJson")
        self.btn_import.setCursor(Qt.PointingHandCursor)
        self.btn_import.clicked.connect(self.import_clicked.emit)
        self.set_header_action(self.btn_import)

        self.btn_schema = QPushButton("i")
        self.btn_schema.setObjectName("btnSchemaInfo")
        self.btn_schema.setCursor(Qt.PointingHandCursor)
        self.btn_schema.setFixedSize(24, 24)
        self.btn_schema.setToolTip("JSON format")
        self.btn_schema.clicked.connect(self._show_schema)
        self.set_header_action(self.btn_schema)

        # description
        self._desc = QLabel()
        self._desc.setWordWrap(True)
        self._desc.setObjectName("IntroDesc")
        self._desc.setStyleSheet(theme.secondary_text_css(self))
        self.body.addWidget(self._desc)

        # info buttons (right-aligned)
        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_example = QPushButton()
        self.btn_problem = QPushButton()
        btns.addWidget(self.btn_example)
        btns.addWidget(self.btn_problem)
        self.body.addLayout(btns)

        self.btn_example.clicked.connect(self.example_clicked.emit)
        self.btn_problem.clicked.connect(self.problem_clicked.emit)

        self.refresh_strings()

    def _show_schema(self) -> None:
        dlg = _SchemaDialog(self)
        dlg.exec()

    def refresh_strings(self) -> None:
        self._desc.setText(S.t("lp.header.description"))
        self.btn_example.setText(S.t("lp.header.buttons.example"))
        self.btn_problem.setText(S.t("lp.header.buttons.problem"))
        self.btn_import.setText(S.t("lp.import.button"))

    def refresh_theme(self) -> None:
        super().refresh_theme()
        self._desc.setStyleSheet(theme.secondary_text_css(self))
