from __future__ import annotations

import pytest

from optees.core.release_version import (
    display_release_version,
    main,
    numeric_release_version,
    release_version_key,
    versions_equivalent,
)


def test_python_and_public_rc_versions_are_equivalent():
    assert versions_equivalent("0.9.0rc1", "v0.9.0-rc.1") is True
    assert display_release_version("0.9.0rc1") == "0.9.0-rc.1"
    assert numeric_release_version("0.9.0rc1") == "0.9.0"


def test_stable_release_sorts_after_its_candidates():
    assert release_version_key("0.9.0rc1") < release_version_key("0.9.0-rc.2")
    assert release_version_key("0.9.0-rc.2") < release_version_key("0.9.0")


@pytest.mark.parametrize("value", ["0.9", "release-0.9.0", "0.9.0-beta.1"])
def test_release_version_rejects_unsupported_notation(value):
    with pytest.raises(ValueError, match="Unsupported release version"):
        release_version_key(value)


def test_release_tag_cli_accepts_current_candidate(capsys):
    assert main(["v0.9.0-rc.1"]) == 0
    assert "matches Optees 0.9.0rc1" in capsys.readouterr().out


def test_release_tag_cli_rejects_mismatch(capsys):
    assert main(["v0.9.0-rc.2"]) == 1
    assert "does not match" in capsys.readouterr().err
