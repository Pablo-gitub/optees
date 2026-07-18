from __future__ import annotations
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtCore import QLocale

from optees.core.version import get_app_version
from optees.core.string_manager import strings as S
from optees.presentation.error_feedback import localized_error_detail
from optees.application.services.local_server_process import (
    DEFAULT_LOCAL_SERVER_PORT,
    LocalServerSnapshot,
    LocalServerState,
)


class SettingsView(QWidget):
    service_start_requested = Signal(int)
    service_stop_requested = Signal()
    service_copy_url_requested = Signal()
    service_copy_authorization_requested = Signal()
    service_copy_configuration_requested = Signal()
    service_open_docs_requested = Signal()

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

        self.service_group = QGroupBox(self)
        service_layout = QVBoxLayout(self.service_group)
        self.service_description = QLabel(self.service_group)
        self.service_description.setWordWrap(True)
        service_layout.addWidget(self.service_description)

        service_form = QFormLayout()
        self.service_port_label = QLabel(self.service_group)
        self.service_port = QSpinBox(self.service_group)
        self.service_port.setObjectName("localServerPort")
        self.service_port.setRange(1024, 65535)
        self.service_port.setValue(DEFAULT_LOCAL_SERVER_PORT)
        self.service_status_label = QLabel(self.service_group)
        self.service_status_value = QLabel(self.service_group)
        self.service_status_value.setObjectName("localServerStatus")
        self.service_status_value.setWordWrap(True)
        self.service_url_label = QLabel(self.service_group)
        self.service_url_value = QLabel("-", self.service_group)
        self.service_url_value.setObjectName("localServerUrl")
        self.service_url_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        service_form.addRow(self.service_port_label, self.service_port)
        service_form.addRow(self.service_status_label, self.service_status_value)
        service_form.addRow(self.service_url_label, self.service_url_value)
        service_layout.addLayout(service_form)

        primary_actions = QHBoxLayout()
        secondary_actions = QHBoxLayout()
        self.service_start_button = QPushButton(self.service_group)
        self.service_start_button.setObjectName("localServerStartButton")
        self.service_stop_button = QPushButton(self.service_group)
        self.service_stop_button.setObjectName("localServerStopButton")
        self.service_copy_url_button = QPushButton(self.service_group)
        self.service_copy_url_button.setObjectName("localServerCopyUrlButton")
        self.service_copy_config_button = QPushButton(self.service_group)
        self.service_copy_config_button.setObjectName("localServerCopyConfigButton")
        self.service_copy_authorization_button = QPushButton(self.service_group)
        self.service_copy_authorization_button.setObjectName(
            "localServerCopyAuthorizationButton"
        )
        self.service_open_docs_button = QPushButton(self.service_group)
        self.service_open_docs_button.setObjectName("localServerOpenDocsButton")
        primary_actions.addWidget(self.service_start_button)
        primary_actions.addWidget(self.service_stop_button)
        primary_actions.addStretch(1)
        secondary_actions.addWidget(self.service_copy_url_button)
        secondary_actions.addWidget(self.service_copy_authorization_button)
        secondary_actions.addWidget(self.service_copy_config_button)
        secondary_actions.addWidget(self.service_open_docs_button)
        secondary_actions.addStretch(1)
        service_layout.addLayout(primary_actions)
        service_layout.addLayout(secondary_actions)

        self.service_security_note = QLabel(self.service_group)
        self.service_security_note.setWordWrap(True)
        service_layout.addWidget(self.service_security_note)
        root.addWidget(self.service_group)

        self.service_start_button.clicked.connect(
            lambda: self.service_start_requested.emit(self.service_port.value())
        )
        self.service_stop_button.clicked.connect(self.service_stop_requested)
        self.service_copy_url_button.clicked.connect(self.service_copy_url_requested)
        self.service_copy_authorization_button.clicked.connect(
            self.service_copy_authorization_requested
        )
        self.service_copy_config_button.clicked.connect(
            self.service_copy_configuration_requested
        )
        self.service_open_docs_button.clicked.connect(self.service_open_docs_requested)
        self._service_snapshot = LocalServerSnapshot(LocalServerState.STOPPED)
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
        self.service_group.setTitle(S.t("settings.local_service.title"))
        self.service_description.setText(S.t("settings.local_service.description"))
        self.service_port_label.setText(S.t("settings.local_service.port"))
        self.service_status_label.setText(S.t("settings.local_service.status"))
        self.service_url_label.setText(S.t("settings.local_service.url"))
        self.service_start_button.setText(S.t("settings.local_service.start"))
        self.service_stop_button.setText(S.t("settings.local_service.stop"))
        self.service_copy_url_button.setText(S.t("settings.local_service.copy_url"))
        self.service_copy_authorization_button.setText(
            S.t("settings.local_service.copy_authorization")
        )
        self.service_copy_config_button.setText(
            S.t("settings.local_service.copy_configuration")
        )
        self.service_open_docs_button.setText(S.t("settings.local_service.open_docs"))
        self.service_security_note.setText(S.t("settings.local_service.security_note"))
        # update combo labels according to current language
        labels = {
            "en": S.t("settings.lang.english"),
            "it": S.t("settings.lang.italian"),
        }
        for i, (code, _) in enumerate(self._langs):
            self.combo_lang.setItemText(i, labels.get(code, code))
        self._refresh_update_text()
        self.set_service_snapshot(self._service_snapshot)

    def set_service_snapshot(self, snapshot: LocalServerSnapshot) -> None:
        self._service_snapshot = snapshot
        state = snapshot.state
        if state is LocalServerState.ERROR:
            error_key = snapshot.error_code or "operation_failed"
            detail = S.t(
                f"settings.local_service.errors.{error_key}",
                detail=snapshot.message or "-",
            )
            status = S.t("settings.local_service.state.error", detail=detail)
        else:
            status = S.t(f"settings.local_service.state.{state.value}")
        if state is LocalServerState.RUNNING and snapshot.used_fallback_port:
            status = S.t(
                "settings.local_service.state.running_fallback",
                port=snapshot.actual_port,
            )
        self.service_status_value.setText(status)
        self.service_url_value.setText(snapshot.url or "-")
        running = state is LocalServerState.RUNNING
        busy = state in {LocalServerState.STARTING, LocalServerState.STOPPING}
        self.service_port.setEnabled(not running and not busy)
        self.service_start_button.setEnabled(not running and not busy)
        self.service_stop_button.setEnabled(running)
        self.service_copy_url_button.setEnabled(running)
        self.service_copy_authorization_button.setEnabled(running)
        self.service_copy_config_button.setEnabled(running)
        self.service_open_docs_button.setEnabled(running)

    def set_service_action_error(self, error_code: str) -> None:
        detail = S.t(f"settings.local_service.errors.{error_code}", detail="-")
        self.service_status_value.setText(
            S.t("settings.local_service.state.action_error", detail=detail)
        )

    def refresh_theme(self) -> None:
        # if needed, apply theme-related changes here
        pass

    def set_update_checking(self, current_version: str | None = None) -> None:
        if current_version:
            self._current_version = current_version
        self._update_state = "checking"
        self._update_message = ""
        self._refresh_update_text()

    def set_update_development_build(self, current_version: str | None = None) -> None:
        if current_version:
            self._current_version = current_version
        self._update_state = "development"
        self._update_message = ""
        self._refresh_update_text()

    def set_update_disabled(self, current_version: str | None = None) -> None:
        if current_version:
            self._current_version = current_version
        self._update_state = "disabled"
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
        elif self._update_state == "development":
            text = S.t("settings.update_development")
        elif self._update_state == "disabled":
            text = S.t("settings.update_disabled")
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
            text = S.t(
                "settings.update_error",
                detail=localized_error_detail("update", self._update_message),
            )
        else:
            text = S.t("settings.update_unknown")
        self.value_update.setText(text)
