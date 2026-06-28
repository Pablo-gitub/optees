# src/optees/presentation/views/lp_view/objective_section.py
from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QLabel, QComboBox
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from .section import Section

def _parse_number(text: str) -> Optional[float]:
    s = (text or "").strip().lower().replace(",", ".")
    if s == "": return None
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

class ObjectiveSection(Section):
    """Objective card: only sense (min/max) and constant offset."""
    sense_changed = Signal(str)      # "min" | "max"
    offset_changed = Signal(object)  # float|None

    def __init__(self, parent: QWidget | None = None):
        super().__init__("", parent)

        # Row: sense selector (Min/Max)
        top = QHBoxLayout()
        top.setContentsMargins(0,0,0,0); top.setSpacing(8)
        self.lbl_sense = QLabel()
        self.combo_sense = QComboBox()
        self.combo_sense.addItems(["Min", "Max"])   # verrà localizzato in refresh_strings
        self.combo_sense.currentIndexChanged.connect(self._on_sense_changed)
        top.addWidget(self.lbl_sense)
        top.addWidget(self.combo_sense)
        top.addStretch(1)
        self.body.addLayout(top)

        # Row: offset field
        off = QHBoxLayout()
        off.setContentsMargins(0,0,0,0); off.setSpacing(8)
        self.lbl_offset = QLabel()
        self.edit_offset = QLineEdit()
        self.edit_offset.setFixedHeight(28)
        self.edit_offset.editingFinished.connect(self._on_offset_commit)
        off.addWidget(self.lbl_offset)
        off.addWidget(self.edit_offset, 1)
        self.body.addLayout(off)

        self.refresh_strings()

    # no vars binding needed, but keep a no-op for API symmetry if ever called
    def set_variables(self, *_args, **_kwargs) -> None:
        pass

    def refresh_strings(self) -> None:
        self.set_title(S.t("lp.obj.section"))
        # localize Min/Max and label
        txt_min = S.t("lp.obj.min"); txt_max = S.t("lp.obj.max")
        self.combo_sense.blockSignals(True)
        cur = max(self.combo_sense.currentIndex(), 0)
        self.combo_sense.clear()
        self.combo_sense.addItems([txt_min, txt_max])
        self.combo_sense.setCurrentIndex(cur)
        self.combo_sense.blockSignals(False)

        self.lbl_sense.setText(S.t("lp.obj.sense"))
        self.lbl_offset.setText(S.t("lp.obj.offset"))
        self.edit_offset.setPlaceholderText(S.t("lp.obj.offset_ph"))

    def refresh_theme(self) -> None:
        super().refresh_theme()
        # eventuali stili aggiuntivi con theme.* se servono

    def set_values(self, sense_str: str, offset: Optional[float]) -> None:
        """Populate sense and offset fields from code without emitting signals."""
        self.combo_sense.blockSignals(True)
        self.combo_sense.setCurrentIndex(0 if sense_str == "min" else 1)
        self.combo_sense.blockSignals(False)
        self.edit_offset.blockSignals(True)
        self.edit_offset.setText("" if offset is None else str(offset))
        self.edit_offset.blockSignals(False)

    # ---- handlers ----
    def _on_sense_changed(self, idx: int) -> None:
        self.sense_changed.emit("min" if idx == 0 else "max")

    def _on_offset_commit(self) -> None:
        val = _parse_number(self.edit_offset.text())
        self.offset_changed.emit(val)
