"""Reusable tabular data-entry widget with clipboard paste and live validation.

Capabilities whose problems are lists of homogeneous rows (forecasting
observations, regression datasets, knapsack items, ...) all suffer from the same
friction: typing every cell by hand. This widget centralizes that entry model so
a view only declares its columns and reads back validated rows.

It intentionally knows nothing about any capability contract: validation is
per-column and structural (finite number, ISO timestamp, non-empty text). The
owning view remains responsible for building the final domain/JSON payload.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Literal

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from optees.core.design import tokens
from optees.core.theme import theme

ColumnKind = Literal["text", "number", "integer", "timestamp"]


@dataclass(frozen=True)
class ColumnSpec:
    """One column: a stable key, a validation kind, and whether it may be blank."""

    key: str
    kind: ColumnKind = "text"
    required: bool = True


def _parse_timestamp(text: str) -> datetime:
    normalized = text.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized)


def _parse_number(text: str) -> float:
    value = float(text.strip().replace(",", "."))
    if not math.isfinite(value):
        raise ValueError("not finite")
    return value


class DataEntryTable(QTableWidget):
    """A column-configured table that supports CSV paste and per-cell checks.

    The widget never raises for user typos: invalid cells are highlighted and
    reported through :meth:`invalid_cells`, so the view can block submission with
    a localized message instead.
    """

    data_changed = Signal()

    def __init__(self, columns: Sequence[ColumnSpec], parent=None) -> None:
        super().__init__(parent)
        self._columns: tuple[ColumnSpec, ...] = tuple(columns)
        self.setColumnCount(len(self._columns))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setMinimumHeight(240)
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        for index in range(len(self._columns) - 1):
            header.setSectionResizeMode(index, QHeaderView.Stretch)
        self.itemChanged.connect(self._on_item_changed)

    # -- configuration ----------------------------------------------------
    def set_header_titles(self, titles: Sequence[str]) -> None:
        self.setHorizontalHeaderLabels(list(titles))

    def ensure_row_count(self, count: int) -> None:
        if self.rowCount() < count:
            self.setRowCount(count)
            self._revalidate_all()

    # -- row operations ---------------------------------------------------
    def add_row(self) -> None:
        self.insertRow(self.rowCount())

    def remove_selected_rows(self) -> None:
        rows = sorted({index.row() for index in self.selectedIndexes()}, reverse=True)
        for row in rows:
            self.removeRow(row)
        if self.rowCount() == 0:
            self.add_row()
        self.data_changed.emit()

    def clear_cells(self) -> None:
        for row in range(self.rowCount()):
            for column in range(self.columnCount()):
                self._set_cell(row, column, "")

    def set_column_values(self, column: int, values: Sequence[str]) -> None:
        """Fill one column top-to-bottom, growing the table if needed."""
        self.ensure_row_count(len(values))
        for row, value in enumerate(values):
            self._set_cell(row, column, value)
        self.data_changed.emit()

    def set_data(self, rows: Iterable[Sequence[str]]) -> None:
        rows = [list(row) for row in rows]
        self.setRowCount(max(len(rows), 1))
        for row_index in range(self.rowCount()):
            for column in range(self.columnCount()):
                text = rows[row_index][column] if row_index < len(rows) and column < len(rows[row_index]) else ""
                self._set_cell(row_index, column, str(text))
        self._revalidate_all()
        self.data_changed.emit()

    # -- clipboard --------------------------------------------------------
    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.matches(QKeySequence.Paste):
            self.paste_from_clipboard()
            return
        super().keyPressEvent(event)

    def paste_from_clipboard(self) -> None:
        text = QApplication.clipboard().text()
        if not text.strip():
            return
        matrix = self._parse_clipboard(text)
        if not matrix:
            return
        start_row = self.currentRow() if self.currentRow() >= 0 else 0
        start_col = self.currentColumn() if self.currentColumn() >= 0 else 0
        needed = start_row + len(matrix)
        if self.rowCount() < needed:
            self.setRowCount(needed)
        for r, cells in enumerate(matrix):
            for c, cell in enumerate(cells):
                col = start_col + c
                if col < self.columnCount():
                    self._set_cell(start_row + r, col, cell)
        self._revalidate_all()
        self.data_changed.emit()

    @staticmethod
    def _parse_clipboard(text: str) -> list[list[str]]:
        rows: list[list[str]] = []
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            if line == "" and not rows:
                continue
            if "\t" in line:
                cells = line.split("\t")
            elif ";" in line:
                cells = line.split(";")
            else:
                cells = line.split(",")
            rows.append([cell.strip() for cell in cells])
        while rows and all(cell == "" for cell in rows[-1]):
            rows.pop()
        return rows

    # -- reading ----------------------------------------------------------
    def non_empty_rows(self) -> list[list[str]]:
        result: list[list[str]] = []
        for row in range(self.rowCount()):
            cells = [self._cell_text(row, column) for column in range(self.columnCount())]
            if any(cells):
                result.append(cells)
        return result

    def invalid_cells(self) -> list[tuple[int, int]]:
        """Return (row, column) of every cell that fails its column validation.

        Fully blank rows are ignored so trailing empty rows do not count as
        errors; a partially filled row reports its missing required cells.
        """
        invalid: list[tuple[int, int]] = []
        for row in range(self.rowCount()):
            cells = [self._cell_text(row, column) for column in range(self.columnCount())]
            if not any(cells):
                continue
            for column, spec in enumerate(self._columns):
                if not self._cell_is_valid(cells[column], spec):
                    invalid.append((row, column))
        return invalid

    # -- internals --------------------------------------------------------
    @staticmethod
    def _cell_is_valid(text: str, spec: ColumnSpec) -> bool:
        text = text.strip()
        if not text:
            return not spec.required
        try:
            if spec.kind == "number":
                _parse_number(text)
            elif spec.kind == "integer":
                int(text.replace(" ", ""))
            elif spec.kind == "timestamp":
                _parse_timestamp(text)
        except (ValueError, TypeError):
            return False
        return True

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        self._apply_validation_style(item)
        self.data_changed.emit()

    def _revalidate_all(self) -> None:
        for row in range(self.rowCount()):
            for column in range(self.columnCount()):
                item = self.item(row, column)
                if item is not None:
                    self._apply_validation_style(item)

    def _apply_validation_style(self, item: QTableWidgetItem) -> None:
        column = item.column()
        if column >= len(self._columns):
            return
        row_blank = not any(
            self._cell_text(item.row(), c) for c in range(self.columnCount())
        )
        valid = row_blank or self._cell_is_valid(item.text(), self._columns[column])
        t = tokens(theme.is_dark())
        if valid:
            item.setData(Qt.BackgroundRole, None)
        else:
            danger = QColor(t.danger)
            danger.setAlpha(60)
            item.setBackground(danger)

    def _cell_text(self, row: int, column: int) -> str:
        item = self.item(row, column)
        return item.text().strip() if item is not None else ""

    def _set_cell(self, row: int, column: int, text: str) -> None:
        item = self.item(row, column)
        if item is None:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignCenter)
            self.setItem(row, column, item)
        item.setText(text)
