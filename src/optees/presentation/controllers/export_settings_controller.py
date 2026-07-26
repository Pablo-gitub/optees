from __future__ import annotations

from PySide6.QtCore import QObject

from optees.data.adapters.settings import LocalExportSettings


class ExportSettingsController(QObject):
    def __init__(self, view, settings: LocalExportSettings, parent=None) -> None:
        super().__init__(parent)
        self._view = view
        self._settings = settings
        view.export_directory_change_requested.connect(self.set_directory)
        view.set_export_directory(str(settings.get_directory()))

    def set_directory(self, directory: str) -> None:
        try:
            selected = self._settings.set_directory(directory)
        except (OSError, ValueError) as exc:
            self._view.set_export_directory_error(str(exc))
            return
        self._view.set_export_directory(str(selected))
