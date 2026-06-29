from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QFormLayout

from PySide6.QtCore import QLocale

from optees.core.version import get_app_version
from optees.core.string_manager import strings as S


class SettingsView(QWidget):
    """
    Settings page: currently only language selection.
    Future settings can be added here.
    Note: changing language requires app restart to fully apply.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.combo_lang = QComboBox(self)
        self._current_version = get_app_version()
        self._latest_version: str | None = None
        self._update_state = "checking"
        self._update_message = ""

        # code map -> label user-friendly
        self._langs = [("en", "English"), ("it", "Italiano")]
        for code, label in self._langs:
            self.combo_lang.addItem(label, code)

        # set current language in combo
        cur = S.get_language() or self._detect_system_lang() or "en"
        idx = max(0, next((i for i, (_, c) in enumerate([(l, l) for l, _ in self._langs]) if c == cur), -1))
        # (more easy:)
        idx = next((i for i, (code, _) in enumerate(self._langs) if code == cur), 0)
        self.combo_lang.setCurrentIndex(idx)

        self.combo_lang.currentIndexChanged.connect(self._on_lang_changed)

        # layout
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        self.title = QLabel("<h2>Settings</h2>")
        self.title.setTextFormat(Qt.RichText)
        root.addWidget(self.title)

        form = QFormLayout()
        self.lbl_choose = QLabel("Choose language")
        form.addRow(self.lbl_choose, self.combo_lang)
        self.lbl_version = QLabel()
        self.lbl_update = QLabel()
        self.value_version = QLabel()
        self.value_update = QLabel()
        self.value_update.setWordWrap(True)
        form.addRow(self.lbl_version, self.value_version)
        form.addRow(self.lbl_update, self.value_update)
        root.addLayout(form)
        root.addStretch(1)

        # listen to changes in language/theme globally
        S.language_changed.connect(self.refresh_strings)
        self.refresh_strings()

    # ----- utils -----
    def _detect_system_lang(self) -> str | None:
        # use QLocale (Qt) for cross-platform detection
        lang = QLocale.system().name()  # es. 'it_IT', 'en_US'
        if lang.startswith("it"):
            return "it"
        if lang.startswith("en"):
            return "en"
        return None

    def _on_lang_changed(self, idx: int) -> None:
        code = self.combo_lang.itemData(idx)
        if code and code != S.get_language():
            S.set_language(code)  # emit language_changed

    # ----- hooks -----
    def refresh_strings(self) -> None:
        self.title.setText(f"<h2>{S.t('settings.title')}</h2>")
        self.lbl_choose.setText(S.t("settings.choose_language"))
        self.lbl_version.setText(S.t("settings.version_label"))
        self.lbl_update.setText(S.t("settings.update_label"))
        # update combo labels according to current language
        labels = {
            "en": S.t("settings.lang.english"),
            "it": S.t("settings.lang.italian"),
        }
        for i, (code, _) in enumerate(self._langs):
            self.combo_lang.setItemText(i, labels.get(code, code))
        self._refresh_update_text()

    def refresh_theme(self) -> None:
        # if needed, apply theme-related changes here
        pass

    def set_update_checking(self, current_version: str | None = None) -> None:
        if current_version:
            self._current_version = current_version
        self._update_state = "checking"
        self._update_message = ""
        self._refresh_update_text()

    def set_update_status(self, result) -> None:
        self._current_version = getattr(result, "current_version", self._current_version)
        self._latest_version = getattr(result, "latest_version", None)
        self._update_message = getattr(result, "message", "") or ""
        if getattr(result, "update_available", False):
            self._update_state = "available"
        elif self._latest_version:
            self._update_state = "latest" if not self._update_message else "unsupported"
        else:
            self._update_state = "unknown"
        self._refresh_update_text()

    def set_update_error(self, message: str) -> None:
        self._update_state = "error"
        self._update_message = message
        self._refresh_update_text()

    def set_update_downloading(self, version: str | None = None) -> None:
        if version:
            self._latest_version = version
        self._update_state = "downloading"
        self._refresh_update_text()

    def set_update_launching(self, path: str) -> None:
        self._update_state = "launching"
        self._update_message = path
        self._refresh_update_text()

    def _refresh_update_text(self) -> None:
        current = self._current_version or "-"
        latest = self._latest_version or "-"
        self.value_version.setText(S.t("settings.version_value", version=current))

        if self._update_state == "checking":
            text = S.t("settings.update_checking")
        elif self._update_state == "available":
            text = S.t("settings.update_available", version=latest)
        elif self._update_state == "latest":
            text = S.t("settings.update_latest")
        elif self._update_state == "unsupported":
            text = S.t("settings.update_unsupported", version=latest)
        elif self._update_state == "downloading":
            text = S.t("settings.update_downloading", version=latest)
        elif self._update_state == "launching":
            text = S.t("settings.update_launching")
        elif self._update_state == "error":
            text = S.t("settings.update_error", detail=self._update_message or "-")
        else:
            text = S.t("settings.update_unknown")
        self.value_update.setText(text)
