# src/optees/presentation/views/lp_solution_view/solution_table.py
from __future__ import annotations
from typing import Dict, Any, Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QLabel
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

from optees.core.string_manager import strings as S
from optees.core.theme import theme


class SolutionTable(QWidget):
    """
    Displays variable names and their corresponding values
    in a simple read-only table.

    Expected input dictionary:
      {
        "status": str,
        "objective": float | None,
        "values": { var_name: value, ... },
        "extras": { ... }
      }

    This widget:
      - Builds a title label ("Variables")
      - Creates a QTableView with 2 columns (Name, Value)
      - Automatically updates on `set_result(...)`
    """

    def __init__(self, parent: Optional[QWidget] = None, title: Optional[str] = None):
        super().__init__(parent)

        self._result: Optional[Dict[str, Any]] = None

        # ------------------------------------------------------------------
        # Layout structure
        # ------------------------------------------------------------------
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # === Section title ================================================
        self._title_lbl = QLabel(title or S.t("lp.sol.variables.section"))
        self._title_lbl.setStyleSheet("font-weight: 700;")
        root.addWidget(self._title_lbl)

        # === Table view ===================================================
        self._tv = QTableView(self)
        self._tv.verticalHeader().setVisible(False)
        self._tv.setAlternatingRowColors(True)
        self._tv.setSelectionBehavior(QTableView.SelectRows)
        self._tv.setEditTriggers(QTableView.NoEditTriggers)
        self._tv.setSortingEnabled(False)
        root.addWidget(self._tv, 1)

        # === Internal model ===============================================
        self._model = QStandardItemModel(self)
        self._tv.setModel(self._model)

        # === Initialize theme & language ==================================
        self.refresh_strings()
        self.refresh_theme()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_result(self, result: Dict[str, Any]) -> None:
        """
        Update the table with a new LP solution result dict.
        """
        self._result = result or {}
        self._rebuild()

    def refresh_strings(self) -> None:
        """Refresh UI text (titles, column headers)."""
        self._title_lbl.setText(S.t("lp.sol.variables.section"))
        self._rebuild()

    def refresh_theme(self) -> None:
        """Apply the current theme style."""
        fg = "rgba(255,255,255,0.95)" if theme.is_dark() else "rgba(0,0,0,0.90)"
        self._title_lbl.setStyleSheet(f"font-weight:700; color:{fg};")
        self._tv.setStyleSheet("")  # rely on Qt platform theme

    def model(self):
        return self._model

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _rebuild(self) -> None:
        """
        Rebuild the table contents based on the current result.
        """
        self._model.clear()

        # --- Column headers ---------------------------------------------
        self._model.setHorizontalHeaderLabels([
            S.t("lp.sol.columns.var"),
            S.t("lp.sol.columns.value"),
        ])

        # --- Retrieve variable values -----------------------------------
        # Compatible with both "values" (new) and "x" (legacy) keys
        vals = (self._result or {}).get("values") or (self._result or {}).get("x") or {}

        for var_name, value in vals.items():
            # Ensure numeric display
            try:
                display_val = f"{float(value):.6g}"
            except Exception:
                display_val = str(value)

            # Create non-editable items
            row_items = [
                QStandardItem(str(var_name)),
                QStandardItem(display_val),
            ]
            for it in row_items:
                it.setEditable(False)

            self._model.appendRow(row_items)

        # Adjust table layout
        self._tv.resizeColumnsToContents()
        self._tv.horizontalHeader().setStretchLastSection(True)
