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

        # === Problem context ===============================================
        # Problem context: variable names, objective unit values (coefs), and offset
        self._context = {"names": [], "coefs": [], "offset": 0.0}

        # === Initialize theme & language ==================================
        self.refresh_strings()
        self.refresh_theme()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_context(self, ctx: Dict[str, Any]) -> None:
        """
        Provide problem context coming from the LP model:
        - names: List[str]        -> variable names
        - coefs: List[float|None] -> objective unit values (cᵢ)
        - offset: float            -> objective constant term
        """
        self._context = ctx or {"names": [], "coefs": [], "offset": 0.0}
        self._rebuild()

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
        # Headers: Variable | Quantity (xᵢ) | Unit value (cᵢ) | Sub-total (cᵢ·xᵢ)
        self._model.setHorizontalHeaderLabels([
            S.t("lp.sol.columns.var"),
            S.t("lp.sol.columns.qty"),
            S.t("lp.sol.columns.unit"),
            S.t("lp.sol.columns.subtotal"),
        ])

        # Optional: header tooltips (didactic)
        try:
            self._model.setHeaderData(1, Qt.Horizontal, S.t("lp.sol.tip.qty"), Qt.ToolTipRole)
            self._model.setHeaderData(2, Qt.Horizontal, S.t("lp.sol.tip.unit"), Qt.ToolTipRole)
            self._model.setHeaderData(3, Qt.Horizontal, S.t("lp.sol.tip.subtotal"), Qt.ToolTipRole)
        except Exception:
            pass

        # --- Retrieve variable values -----------------------------------
        # Gather data
        vals_map = (self._result or {}).get("values") or (self._result or {}).get("x") or {}
        names = self._context.get("names") or list(vals_map.keys())
        coefs = self._context.get("coefs") or []
        try:
            offset = float(self._context.get("offset") or 0.0)
        except Exception:
            offset = 0.0

        # Small formatter
        def fmt(x):
            if x is None:
                return "—"
            try:
                return f"{float(x):.6g}"
            except Exception:
                return str(x)

        # Build rows
        total = 0.0
        for i, name in enumerate(names):
            qty = vals_map.get(name, None)
            try:
                qty_f = float(qty) if qty is not None else None
            except Exception:
                qty_f = None

            unit = None
            if i < len(coefs):
                try:
                    unit = None if coefs[i] is None else float(coefs[i])
                except Exception:
                    unit = None

            subtotal = None
            if qty_f is not None and unit is not None:
                subtotal = qty_f * unit
                total += subtotal

            row_items = [
                QStandardItem(str(name)),
                QStandardItem(fmt(qty_f)),
                QStandardItem(fmt(unit)),
                QStandardItem(fmt(subtotal)),
            ]
            for col, it in enumerate(row_items):
                it.setEditable(False)
                if col in (1, 2, 3):
                    it.setData(Qt.AlignRight | Qt.AlignVCenter, Qt.TextAlignmentRole)
            # (soft accent for subtotal column: handled by stylesheet at view level if needed)
            self._model.appendRow(row_items)

        # Append a "Total" row if we have any variables
        if names:
            grand_total = total + offset
            total_label = QStandardItem(S.t("lp.sol.total"))
            total_qty   = QStandardItem("")  # empty cell
            total_unit  = QStandardItem(S.t("lp.sol.offset", value=fmt(offset)) if offset else "")
            total_sum   = QStandardItem(fmt(grand_total))

            for it in (total_label, total_qty, total_unit, total_sum):
                it.setEditable(False)
                it.setData(Qt.AlignRight | Qt.AlignVCenter, Qt.TextAlignmentRole)

            # Make the grand total bold
            font = total_sum.font(); font.setBold(True); total_sum.setFont(font)
            self._model.appendRow([total_label, total_qty, total_unit, total_sum])

        # Adjust table layout
        self._tv.resizeColumnsToContents()
        self._tv.horizontalHeader().setStretchLastSection(True)
