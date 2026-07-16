from __future__ import annotations

import hashlib
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from optees.core.design import flatten, tokens
from optees.core.string_manager import strings as S
from optees.core.theme import theme
from optees.domain.entities.packing.solution import PackingSolution
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)


class Packing3DPlotWidget(QWidget):
    """Render an axis-aligned packing incumbent inside its container."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[SingleContainerPackingModel] = None
        self._solution: Optional[PackingSolution] = None
        self._visualization_state = "no_solution"
        self._hidden_item_ids: set[str] = set()
        self._highlighted_instance_id: Optional[str] = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        controls = QHBoxLayout()
        self.btn_reset_view = QPushButton()
        self.btn_reset_view.setObjectName("packingResetViewButton")
        self.btn_reset_view.clicked.connect(self.reset_view)
        self.show_container = QCheckBox()
        self.show_container.setObjectName("packingShowContainerCheck")
        self.show_container.setChecked(True)
        self.show_container.toggled.connect(self._render)
        self.show_labels = QCheckBox()
        self.show_labels.setObjectName("packingShowLabelsCheck")
        self.show_labels.setChecked(True)
        self.show_labels.toggled.connect(self._render)
        controls.addWidget(self.btn_reset_view)
        controls.addWidget(self.show_container)
        controls.addWidget(self.show_labels)
        controls.addStretch(1)
        root.addLayout(controls)

        self.legend = QListWidget()
        self.legend.setObjectName("packingLegend")
        self.legend.setFlow(QListWidget.LeftToRight)
        self.legend.setWrapping(True)
        self.legend.setMaximumHeight(82)
        self.legend.itemChanged.connect(self._on_legend_changed)
        self.legend.itemClicked.connect(self._on_legend_clicked)
        root.addWidget(self.legend)

        self.status = QLabel()
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(42)
        root.addWidget(self.status)

        self._figure = None
        self._canvas = None
        try:
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self._figure = Figure(figsize=(7.2, 4.8))
            self._canvas = FigureCanvasQTAgg(self._figure)
            self._canvas.setObjectName("packing3DCanvas")
            self._canvas.setMinimumHeight(380)
            self._canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            root.addWidget(self._canvas, 1)
        except Exception:
            self._visualization_state = "matplotlib_unavailable"

        self.refresh_theme()
        self._render()

    @property
    def visualization_state(self) -> str:
        return self._visualization_state

    def set_problem(self, model: SingleContainerPackingModel) -> None:
        self._model = model
        self._render()

    def set_solution(self, solution: Optional[PackingSolution]) -> None:
        self._solution = solution
        self._hidden_item_ids.clear()
        self._highlighted_instance_id = None
        self._rebuild_legend()
        self._render()

    def refresh_strings(self) -> None:
        self.btn_reset_view.setText(S.t("packing.solution.visualization.reset"))
        self.show_container.setText(S.t("packing.solution.visualization.show_container"))
        self.show_labels.setText(S.t("packing.solution.visualization.show_labels"))
        self._render()

    def refresh_theme(self) -> None:
        self.status.setStyleSheet(f"color: {tokens(theme.is_dark()).text_muted};")
        self._render()

    @property
    def visible_item_ids(self) -> set[str]:
        if self._solution is None:
            return set()
        return {p.item_id for p in self._solution.placements} - self._hidden_item_ids

    @property
    def highlighted_instance_id(self) -> Optional[str]:
        return self._highlighted_instance_id

    def select_instance(self, instance_id: Optional[str]) -> None:
        self._highlighted_instance_id = instance_id
        self._render()

    def reset_view(self) -> None:
        self._highlighted_instance_id = None
        self._render()

    def _rebuild_legend(self) -> None:
        self.legend.blockSignals(True)
        self.legend.clear()
        if self._solution is not None:
            labels: dict[str, str] = {}
            for placement in self._solution.placements:
                labels.setdefault(placement.item_id, placement.item_name)
            for item_id, label in labels.items():
                item = QListWidgetItem(_color_icon(_stable_color(item_id)), label)
                item.setData(Qt.UserRole, item_id)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.legend.addItem(item)
        self.legend.blockSignals(False)

    def _on_legend_changed(self, item: QListWidgetItem) -> None:
        item_id = str(item.data(Qt.UserRole))
        if item.checkState() == Qt.Checked:
            self._hidden_item_ids.discard(item_id)
        else:
            self._hidden_item_ids.add(item_id)
        self._render()

    def _on_legend_clicked(self, item: QListWidgetItem) -> None:
        item_id = str(item.data(Qt.UserRole))
        if self._solution is None:
            return
        placement = next(
            (value for value in self._solution.placements if value.item_id == item_id),
            None,
        )
        self._highlighted_instance_id = placement.instance_id if placement else None
        self._render()

    def _render(self) -> None:
        if self._canvas is None or self._figure is None:
            self._visualization_state = "matplotlib_unavailable"
            self.status.setText(S.t("packing.solution.visualization.unavailable"))
            return
        if self._model is None or self._solution is None or not self._solution.has_incumbent():
            self._visualization_state = "no_solution"
            self.status.setText(S.t("packing.solution.visualization.empty"))
            self._figure.clear()
            self._canvas.draw()
            return

        self._visualization_state = "ready"
        self.status.setText(S.t("packing.solution.visualization.hint"))
        self._figure.clear()
        axis = self._figure.add_subplot(111, projection="3d")
        dimensions = self._model.container.dimensions
        palette = tokens(theme.is_dark())
        colors = {
            placement.instance_id: _stable_color(placement.item_id)
            for placement in self._solution.placements
        }
        for placement in self._solution.placements:
            if placement.item_id in self._hidden_item_ids:
                continue
            selected = placement.instance_id == self._highlighted_instance_id
            axis.bar3d(
                placement.x,
                placement.y,
                placement.z,
                placement.length,
                placement.width,
                placement.height,
                color=colors[placement.instance_id],
                edgecolor=flatten(palette.border_strong, palette.base),
                linewidth=2.2 if selected else 0.7,
                alpha=1.0 if selected else 0.78,
                shade=True,
            )
            if self.show_labels.isChecked():
                axis.text(
                    placement.x + placement.length / 2,
                    placement.y + placement.width / 2,
                    placement.z + placement.height / 2,
                    placement.item_name,
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=palette.text,
                )

        if self.show_container.isChecked():
            _draw_container(axis, dimensions.length, dimensions.width, dimensions.height)
        axis.set_xlim(0, dimensions.length)
        axis.set_ylim(0, dimensions.width)
        axis.set_zlim(0, dimensions.height)
        axis.set_xlabel(S.t("packing.axes.length"))
        axis.set_ylabel(S.t("packing.axes.width"))
        axis.set_zlabel(S.t("packing.axes.height"))
        axis.set_box_aspect((dimensions.length, dimensions.width, dimensions.height))
        axis.view_init(elev=24, azim=-56)
        self._figure.patch.set_facecolor(palette.base)
        axis.set_facecolor(palette.base)
        axis.tick_params(colors=palette.text_muted)
        axis.xaxis.label.set_color(palette.text)
        axis.yaxis.label.set_color(palette.text)
        axis.zaxis.label.set_color(palette.text)
        try:
            self._figure.tight_layout()
        except Exception:
            pass
        self._canvas.draw()


def _stable_color(item_id: str) -> tuple[float, float, float, float]:
    from matplotlib import colormaps

    digest = hashlib.sha256(item_id.encode("utf-8")).digest()
    index = int.from_bytes(digest[:2], "big") % 20
    return colormaps["tab20"](index)


def _color_icon(color: tuple[float, float, float, float]) -> QIcon:
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor.fromRgbF(*color))
    return QIcon(pixmap)


def _draw_container(axis, length: float, width: float, height: float) -> None:
    corners = [
        (0, 0, 0),
        (length, 0, 0),
        (length, width, 0),
        (0, width, 0),
        (0, 0, height),
        (length, 0, height),
        (length, width, height),
        (0, width, height),
    ]
    edges = (
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    )
    for start, end in edges:
        a, b = corners[start], corners[end]
        axis.plot(
            (a[0], b[0]),
            (a[1], b[1]),
            (a[2], b[2]),
            color="#64748b",
            linewidth=1.4,
        )
