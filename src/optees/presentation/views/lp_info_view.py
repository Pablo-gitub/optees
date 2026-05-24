from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QStyle,
    QFrame,
)

from optees.core.string_manager import strings as S
from optees.core.theme import theme


class _InfoBlock(QFrame):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("InfoBlock")
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(14, 12, 14, 12)
        self._root.setSpacing(8)

        self._title = QLabel()
        self._title.setObjectName("InfoBlockTitle")
        self._title.setTextFormat(Qt.RichText)
        self._root.addWidget(self._title)

        self._body = QLabel()
        self._body.setObjectName("InfoBlockBody")
        self._body.setTextFormat(Qt.RichText)
        self._body.setWordWrap(True)
        self._body.setOpenExternalLinks(False)
        self._root.addWidget(self._body)

    def set_content(self, title: str, body: str) -> None:
        self._title.setText(f"<span style='font-size:16px; font-weight:700'>{title}</span>")
        self._body.setText(body)

    def refresh_theme(self) -> None:
        if theme.is_dark():
            self.setStyleSheet("""
                QFrame#InfoBlock { border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; }
                QLabel#InfoBlockTitle { color: rgba(255,255,255,0.95); }
                QLabel#InfoBlockBody { color: rgba(255,255,255,0.78); line-height: 150%; }
            """)
        else:
            self.setStyleSheet("""
                QFrame#InfoBlock { border: 1px solid rgba(0,0,0,0.10); border-radius: 10px; }
                QLabel#InfoBlockTitle { color: rgba(0,0,0,0.90); }
                QLabel#InfoBlockBody { color: rgba(0,0,0,0.72); line-height: 150%; }
            """)


class LPInfoView(QWidget):
    back_requested = Signal()

    def __init__(self, page_key: str, block_count: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._page_key = page_key
        self._blocks: list[_InfoBlock] = []

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

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("btnBack")
        self.btn_back.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.btn_back.setFlat(True)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_requested.emit)
        hdr.addWidget(self.btn_back)
        hdr.addStretch(1)
        root.addLayout(hdr)

        self._title = QLabel()
        self._title.setObjectName("InfoPageTitle")
        self._title.setTextFormat(Qt.RichText)
        self._title.setWordWrap(True)
        root.addWidget(self._title)

        self._intro = QLabel()
        self._intro.setObjectName("InfoPageIntro")
        self._intro.setTextFormat(Qt.RichText)
        self._intro.setWordWrap(True)
        root.addWidget(self._intro)

        for _ in range(block_count):
            block = _InfoBlock()
            self._blocks.append(block)
            root.addWidget(block)

        root.addStretch(1)

        S.language_changed.connect(self.refresh_strings)
        theme.theme_changed.connect(self.refresh_theme)
        self.refresh_strings()
        self.refresh_theme()

    def refresh_strings(self) -> None:
        base = f"lp.info.{self._page_key}"
        self.btn_back.setText(S.t("lp.sol.back"))
        self._title.setText(
            f"<span style='font-size:22px; font-weight:800'>{S.t(base + '.title')}</span>"
        )
        self._intro.setText(S.t(base + ".intro"))
        for i, block in enumerate(self._blocks, start=1):
            block.set_content(S.t(f"{base}.block{i}.title"), S.t(f"{base}.block{i}.body"))

    def refresh_theme(self) -> None:
        if theme.is_dark():
            self._title.setStyleSheet("color: rgba(255,255,255,0.95); margin-top: 8px;")
            self._intro.setStyleSheet("color: rgba(255,255,255,0.78); margin-bottom: 8px;")
        else:
            self._title.setStyleSheet("color: rgba(0,0,0,0.90); margin-top: 8px;")
            self._intro.setStyleSheet("color: rgba(0,0,0,0.72); margin-bottom: 8px;")
        for block in self._blocks:
            block.refresh_theme()


class LPExampleView(LPInfoView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("example", block_count=4, parent=parent)


class LPProblemDescriptionView(LPInfoView):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("problem", block_count=4, parent=parent)
