from __future__ import annotations

import sys

from optees import __version__


def get_app_version() -> str:
    """Return the application version used for release/update checks."""
    return __version__


def is_packaged_app() -> bool:
    """Return True when Optees is running from a packaged PyInstaller build."""
    return bool(getattr(sys, "frozen", False))
