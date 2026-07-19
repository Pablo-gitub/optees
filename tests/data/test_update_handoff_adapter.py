from __future__ import annotations

from pathlib import Path

import pytest

from optees.data.adapters.system.update_handoff_adapter import (
    DesktopUpdateHandoffAdapter,
)
from optees.domain.entities.update import (
    CpuArchitecture,
    ReleaseAsset,
    UpdateArtifactKind,
    UpdateHandoffMethod,
    UpdatePlan,
    UpdatePlatform,
)


def _plan(platform: UpdatePlatform, filename: str) -> UpdatePlan:
    return UpdatePlan(
        platform=platform,
        architecture=CpuArchitecture.X86_64,
        artifact=ReleaseAsset(filename, f"https://example.test/{filename}"),
        artifact_kind=UpdateArtifactKind.LINUX_APPIMAGE,
        handoff_method=UpdateHandoffMethod.OPEN_PORTABLE_PACKAGE,
        staging_subdirectory="0.2.0/test",
    )


@pytest.mark.parametrize(
    ("system_name", "platform_value", "command"),
    [
        ("Darwin", UpdatePlatform.MACOS, "open"),
        ("Linux", UpdatePlatform.LINUX, "xdg-open"),
    ],
)
def test_desktop_handoff_starts_native_open_command(
    monkeypatch,
    tmp_path,
    system_name,
    platform_value,
    command,
):
    path = tmp_path / "package.bin"
    path.write_bytes(b"release")
    calls = []
    monkeypatch.setattr(
        "optees.data.adapters.system.update_handoff_adapter.subprocess.Popen",
        lambda args, **kwargs: calls.append((args, kwargs)),
    )

    started = DesktopUpdateHandoffAdapter(system_name=system_name).start(
        _plan(platform_value, path.name), path
    )

    assert started is True
    assert calls[0][0] == [command, str(path.resolve())]
    assert calls[0][1]["close_fds"] is True


def test_desktop_handoff_uses_windows_shell(monkeypatch, tmp_path):
    path = tmp_path / "setup.exe"
    path.write_bytes(b"release")
    calls = []
    monkeypatch.setattr(
        "optees.data.adapters.system.update_handoff_adapter.os.startfile",
        lambda value: calls.append(value),
        raising=False,
    )

    started = DesktopUpdateHandoffAdapter(system_name="Windows").start(
        _plan(UpdatePlatform.WINDOWS, path.name), path
    )

    assert started is True
    assert calls == [str(path.resolve())]


def test_desktop_handoff_rejects_plan_for_another_platform(tmp_path):
    path = Path(tmp_path) / "package.bin"
    path.write_bytes(b"release")

    with pytest.raises(RuntimeError, match="not the current platform"):
        DesktopUpdateHandoffAdapter(system_name="Linux").start(
            _plan(UpdatePlatform.MACOS, path.name), path
        )
