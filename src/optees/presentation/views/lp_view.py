from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout,
    QLineEdit, QPushButton, QFormLayout, QFrame, QMessageBox
)
from PySide6.QtCore import Qt

class LPView(QWidget):
    """
    Minimal LP view (placeholder):
      - Sense selector (min/max)
      - Objective coefficients (comma-separated)
      - Solve button (currently just validates/parses)
    Later: add constraints grid, bounds editor, and integration with solve_lp().
    """

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Linear Programming (LP)")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        root.addWidget(title)

        card = QFrame(self)
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("QFrame { border:1px solid #ddd; border-radius:10px; }")
        root.addWidget(card)

        form = QFormLayout(card)
        form.setLabelAlignment(Qt.AlignRight)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)

        self.sense = QComboBox()
        self.sense.addItems(["min", "max"])
        form.addRow("Sense:", self.sense)

        self.obj_line = QLineEdit()
        self.obj_line.setPlaceholderText("e.g. 3, 2, 1")
        form.addRow("Objective c:", self.obj_line)

        # Action row
        actions = QHBoxLayout()
        run = QPushButton("Solve (WIP)")
        run.clicked.connect(self._on_solve)
        actions.addStretch(1)
        actions.addWidget(run)
        root.addLayout(actions)
        root.addStretch(1)

    def _on_solve(self) -> None:
        c_text = self.obj_line.text().strip()
        try:
            c = [float(t.strip()) for t in c_text.split(",") if t.strip()]
            if not c:
                raise ValueError("Empty objective.")
        except Exception as e:
            QMessageBox.warning(self, "Input error", f"Invalid objective vector:\n{e}")
            return

        # Here we would build the canonical problem dict and call solve_lp(...)
        QMessageBox.information(
            self, "Parsed",
            f"Sense: {self.sense.currentText()}\n"
            f"c: {c}\n\n"
            "Constraints/bounds editor coming soon."
        )
