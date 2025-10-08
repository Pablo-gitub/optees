from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QFormLayout

from PySide6.QtCore import QLocale

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
        # update combo labels according to current language
        labels = {
            "en": S.t("settings.lang.english"),
            "it": S.t("settings.lang.italian"),
        }
        for i, (code, _) in enumerate(self._langs):
            self.combo_lang.setItemText(i, labels.get(code, code))

    def refresh_theme(self) -> None:
        # if needed, apply theme-related changes here
        pass
