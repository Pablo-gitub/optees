from __future__ import annotations

from optees import __version__


def get_app_version() -> str:
    """Return the application version used for release/update checks."""
    return __version__
