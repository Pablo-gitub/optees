from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.data.adapters.settings.local_export_settings import LocalExportSettings


def test_settings_persist_an_absolute_directory_and_preserve_other_keys(
    tmp_path: Path,
):
    settings_path = tmp_path / "settings.json"
    settings_path.write_text('{"other": true}\n', encoding="utf-8")
    selected = tmp_path / "exports"

    settings = LocalExportSettings(settings_path)
    result = settings.set_directory(selected)

    assert result == selected
    assert settings.get_directory() == selected
    assert json.loads(settings_path.read_text(encoding="utf-8")) == {
        "export_directory": str(selected),
        "other": True,
    }


def test_settings_reject_a_relative_directory(tmp_path: Path):
    settings = LocalExportSettings(tmp_path / "settings.json")

    with pytest.raises(ValueError, match="absolute"):
        settings.set_directory("relative")
