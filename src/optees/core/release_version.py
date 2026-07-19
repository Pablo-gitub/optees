"""Strict release-version parsing shared by packaging and update checks."""

from __future__ import annotations

import re
import sys


_VERSION_PATTERN = re.compile(
    r"^[vV]?(\d+)\.(\d+)\.(\d+)(?:-?rc(?:[.-]?)(\d+))?$",
    re.IGNORECASE,
)


def release_version_components(value: str) -> tuple[int, int, int, int | None]:
    """Parse stable or RC versions in Python or public-tag notation."""
    match = _VERSION_PATTERN.fullmatch((value or "").strip())
    if match is None:
        raise ValueError(
            f"Unsupported release version {value!r}; expected X.Y.Z or X.Y.Z-rc.N."
        )
    major, minor, patch, rc_number = match.groups()
    return int(major), int(minor), int(patch), (
        int(rc_number) if rc_number is not None else None
    )


def release_version_key(value: str) -> tuple[int, int, int, int, int]:
    """Return an ordering key where a stable release follows all of its RCs."""
    major, minor, patch, rc_number = release_version_components(value)
    return major, minor, patch, 1 if rc_number is None else 0, rc_number or 0


def versions_equivalent(left: str, right: str) -> bool:
    """Compare Python and public tag spellings of the same release."""
    return release_version_components(left) == release_version_components(right)


def numeric_release_version(value: str) -> str:
    """Return the three-component numeric version required by native metadata."""
    major, minor, patch, _rc_number = release_version_components(value)
    return f"{major}.{minor}.{patch}"


def display_release_version(value: str) -> str:
    """Return stable SemVer-like text suitable for installers and release notes."""
    major, minor, patch, rc_number = release_version_components(value)
    base = f"{major}.{minor}.{patch}"
    return base if rc_number is None else f"{base}-rc.{rc_number}"


def main(argv: list[str] | None = None) -> int:
    """Validate one public tag against the application's internal version."""
    from optees import __version__

    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print("usage: python -m optees.core.release_version TAG", file=sys.stderr)
        return 2
    tag = arguments[0]
    try:
        matches = versions_equivalent(tag, __version__)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not matches:
        print(
            f"Release tag {tag} does not match Optees {__version__}.",
            file=sys.stderr,
        )
        return 1
    print(f"Release tag {tag} matches Optees {__version__}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
