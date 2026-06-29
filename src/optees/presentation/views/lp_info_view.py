from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStyle,
    QFrame,
    QTextBrowser,
)

from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.core.assets import asset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_doc(doc_key: str) -> str:
    """Read the .md file for the current language, falling back to English."""
    lang = S.current_language()
    for code in (lang, "en"):
        try:
            p = Path(asset(f"docs/{code}/{doc_key}.md"))
            if p.exists():
                return p.read_text(encoding="utf-8")
        except Exception:
            pass
    return f"# {doc_key}\n\nDocument not found."


def _to_html(markdown_text: str) -> str:
    """Convert markdown to HTML.  Falls back to a <pre> block if unavailable."""
    try:
        import markdown  # type: ignore
        return markdown.markdown(
            markdown_text,
            extensions=["tables", "fenced_code"],
        )
    except ImportError:
        import html
        return f"<pre>{html.escape(markdown_text)}</pre>"


def _make_css(dark: bool) -> str:
    if dark:
        bg         = "#1b1b1b"
        fg         = "rgba(255,255,255,0.88)"
        h_color    = "rgba(255,255,255,0.95)"
        secondary  = "rgba(255,255,255,0.55)"
        code_bg    = "#272727"
        border_clr = "rgba(255,255,255,0.13)"
        link_clr   = "#7eb8f7"
        blockq_clr = "rgba(255,255,255,0.45)"
    else:
        bg         = "#ffffff"
        fg         = "rgba(0,0,0,0.84)"
        h_color    = "rgba(0,0,0,0.90)"
        secondary  = "rgba(0,0,0,0.52)"
        code_bg    = "#f2f2f2"
        border_clr = "rgba(0,0,0,0.12)"
        link_clr   = "#1a6bbf"
        blockq_clr = "rgba(0,0,0,0.42)"

    return f"""
        body {{
            background-color: {bg};
            color: {fg};
            font-family: -apple-system, Arial, 'Helvetica Neue', sans-serif;
            font-size: 14px;
            margin: 0;
            padding: 12px 0 24px 0;
            line-height: 1.65;
        }}
        h1 {{
            font-size: 21px;
            font-weight: 800;
            color: {h_color};
            margin-top: 0;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 2px solid {border_clr};
        }}
        h2 {{
            font-size: 15px;
            font-weight: 700;
            color: {h_color};
            margin-top: 22px;
            margin-bottom: 6px;
            padding-bottom: 4px;
            border-bottom: 1px solid {border_clr};
        }}
        h3 {{
            font-size: 14px;
            font-weight: 600;
            color: {h_color};
            margin-top: 14px;
            margin-bottom: 4px;
        }}
        p {{
            color: {fg};
            margin: 5px 0 9px 0;
        }}
        a {{
            color: {link_clr};
        }}
        ul, ol {{
            margin: 4px 0 8px 0;
            padding-left: 22px;
        }}
        li {{
            margin: 3px 0;
            color: {fg};
        }}
        code {{
            font-family: 'Fira Code', 'JetBrains Mono', 'Courier New', monospace;
            font-size: 12px;
            background-color: {code_bg};
            color: {fg};
            padding: 1px 5px;
        }}
        pre {{
            background-color: {code_bg};
            border: 1px solid {border_clr};
            padding: 12px 14px;
            margin: 8px 0 12px 0;
            white-space: pre;
        }}
        pre code {{
            background-color: transparent;
            padding: 0;
            font-size: 12px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0 14px 0;
            font-size: 13px;
        }}
        th, td {{
            border: 1px solid {border_clr};
            padding: 6px 10px;
            text-align: left;
            color: {fg};
        }}
        th {{
            font-weight: 600;
            background-color: {code_bg};
            color: {h_color};
        }}
        hr {{
            border: none;
            border-top: 1px solid {border_clr};
            margin: 18px 0;
        }}
        blockquote {{
            border-left: 3px solid {border_clr};
            margin: 8px 0;
            padding: 4px 12px;
            color: {blockq_clr};
        }}
        blockquote p {{
            color: {blockq_clr};
        }}
    """


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------

class LPInfoView(QWidget):
    back_requested = Signal()

    def __init__(self, doc_key: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._doc_key = doc_key

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── header bar ──────────────────────────────────────────────────────
        hdr_bar = QWidget()
        hdr_bar.setObjectName("InfoHdrBar")
        hdr_layout = QHBoxLayout(hdr_bar)
        hdr_layout.setContentsMargins(8, 6, 8, 6)

        self.btn_back = QPushButton()
        self.btn_back.setObjectName("btnBack")
        self.btn_back.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.btn_back.setFlat(True)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_requested.emit)
        hdr_layout.addWidget(self.btn_back)
        hdr_layout.addStretch(1)
        root.addWidget(hdr_bar)

        # ── markdown browser ─────────────────────────────────────────────────
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setFrameShape(QFrame.Shape.NoFrame)
        self.browser.setViewportMargins(32, 8, 32, 8)
        font = QFont("Arial", 14)
        self.browser.document().setDefaultFont(font)
        root.addWidget(self.browser)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()

    # ── public API expected by MainWindow ────────────────────────────────────

    def refresh_strings(self) -> None:
        self.btn_back.setText(S.t("lp.sol.back"))
        self._render()

    def refresh_theme(self) -> None:
        dark = theme.is_dark()
        bg = "#1b1b1b" if dark else "#ffffff"
        self.browser.setStyleSheet(
            f"QTextBrowser {{ background-color: {bg}; border: none; }}"
        )
        self._render()

    # ── internals ────────────────────────────────────────────────────────────

    def _render(self) -> None:
        md_text   = _load_doc(self._doc_key)
        html_body = _to_html(md_text)
        css       = _make_css(theme.is_dark())
        self.browser.document().setDefaultStyleSheet(css)
        self.browser.setHtml(html_body)


# ---------------------------------------------------------------------------
# Concrete pages
# ---------------------------------------------------------------------------

class LPExampleView(LPInfoView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("lp_example", parent=parent)


class LPProblemDescriptionView(LPInfoView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("lp_problem", parent=parent)


class MILPExampleView(LPInfoView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("milp_example", parent=parent)


class MILPProblemDescriptionView(LPInfoView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("milp_problem", parent=parent)


class KnapsackExampleView(LPInfoView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("knapsack_example", parent=parent)


class KnapsackProblemDescriptionView(LPInfoView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("knapsack_problem", parent=parent)
