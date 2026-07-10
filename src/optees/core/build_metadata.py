"""Metadata shared by desktop build definitions.

Keeping release metadata in Python makes the packaged application use the same
version as the update checker and the distribution tag.  Build specifications
must import this module instead of duplicating version strings.
"""

from __future__ import annotations

from typing import Any

from optees import __version__


def macos_info_plist() -> dict[str, Any]:
    """Return the macOS bundle metadata for the current Optees version."""
    return {
        "CFBundleName": "Optees",
        "CFBundleDisplayName": "Optees",
        "CFBundleVersion": __version__,
        "CFBundleShortVersionString": __version__,
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "NSAppleScriptEnabled": False,
        "LSMinimumSystemVersion": "13.0",
    }
