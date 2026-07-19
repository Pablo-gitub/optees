from __future__ import annotations

from pathlib import Path

import pytest

from optees.application.services.update_staging import UpdateStagingService
from optees.domain.entities.update import (
    CpuArchitecture,
    ReleaseAsset,
    UpdateArtifactKind,
    UpdateHandoffMethod,
    UpdatePlan,
    UpdatePlatform,
)


def _plan(platform: UpdatePlatform) -> UpdatePlan:
    return UpdatePlan(
        platform=platform,
        architecture=CpuArchitecture.X86_64,
        artifact=ReleaseAsset("package.bin", "https://example.test/package.bin"),
        artifact_kind=UpdateArtifactKind.LINUX_APPIMAGE,
        handoff_method=UpdateHandoffMethod.OPEN_PORTABLE_PACKAGE,
        staging_subdirectory=f"0.2.0/{platform.value}-x86_64",
    )


@pytest.mark.parametrize(
    ("system_name", "platform_value", "environment", "expected"),
    [
        (
            "Darwin",
            UpdatePlatform.MACOS,
            {},
            "/home/user/Library/Caches/Optees/updates/0.2.0/macos-x86_64",
        ),
        (
            "Windows",
            UpdatePlatform.WINDOWS,
            {"LOCALAPPDATA": "/local"},
            "/local/Optees/updates/0.2.0/windows-x86_64",
        ),
        (
            "Linux",
            UpdatePlatform.LINUX,
            {"XDG_CACHE_HOME": "/cache"},
            "/cache/optees/updates/0.2.0/linux-x86_64",
        ),
    ],
)
def test_staging_uses_persistent_platform_location(
    system_name,
    platform_value,
    environment,
    expected,
):
    service = UpdateStagingService(
        system_name=system_name,
        environment=environment,
        home=Path("/home/user"),
    )

    assert service.directory_for(_plan(platform_value)) == Path(expected)


def test_staging_rejects_plan_for_another_platform():
    service = UpdateStagingService(system_name="Linux", environment={}, home=Path("/home"))

    with pytest.raises(RuntimeError, match="another platform"):
        service.directory_for(_plan(UpdatePlatform.MACOS))
