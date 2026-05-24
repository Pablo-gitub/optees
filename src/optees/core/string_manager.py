# src/optees/core/string_manager.py
from __future__ import annotations
from pathlib import Path
import json
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Signal, QSettings

from optees.core.assets import asset


class StringManager(QObject):
    """Tiny i18n helper with JSON files and a Qt signal for live updates."""
    language_changed = Signal(str)  # <- emit when language changes

    def __init__(self, locales_dir: Path, default_lang: str = "en", parent: Optional[QObject] = None):
        super().__init__(parent)
        self._dir = Path(locales_dir)
        self._default = default_lang
        self._lang: str = default_lang
        self._strings: Dict[str, Any] = {}

        self._settings = QSettings("optees", "optees")
        saved = self._settings.value("language", type=str)
        self.set_language(saved or default_lang, emit=False)

    # --- public API ---
    def get_language(self) -> str:
        return self._lang

    # compatibility alias (your SettingsView calls this)
    def current_language(self) -> str:
        return self._lang

    def set_language(self, code: Optional[str], *, emit: bool = True) -> None:
        code = (code or self._default)
        code = code.split("-")[0].split("_")[0]  # normalize like 'en', 'it'

        data = self._load_locale(code)
        if not data:
            data = self._load_locale(self._default) or {}

        self._lang = code if data else self._default
        self._strings = data
        self._settings.setValue("language", self._lang)
        if emit:
            self.language_changed.emit(self._lang)

    def t(self, key: str, **fmt) -> str:
        """Translate key; supports dotted paths; fallback to default then key."""
        val = self._get(self._strings, key)
        if val is None and self._lang != self._default:
            val = self._get(self._load_locale(self._default) or {}, key)
        if val is None:
            val = key  # last resort: show the key
        if fmt:
            try:
                return val.format(**fmt)
            except Exception:
                return val
        return val

    # --- internals ---
    def _load_locale(self, code: str) -> Optional[Dict[str, Any]]:
        # try exact, then base (already normalized, but keep it defensive)
        candidates = [code, code.split("-")[0], code.split("_")[0]]
        for c in candidates:
            p = self._dir / f"{c}.json"
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    pass
        return None

    @staticmethod
    def _get(data: Dict[str, Any], dotted: str) -> Optional[str]:
        cur: Any = data
        for part in dotted.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur if isinstance(cur, str) else None


# Instantiate a shared singleton
_LOCALES_DIR = Path(asset("i18n"))
strings = StringManager(_LOCALES_DIR)
