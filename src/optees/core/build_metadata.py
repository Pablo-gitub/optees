"""Metadata shared by desktop build definitions.

Keeping release metadata in Python makes the packaged application use the same
version as the update checker and the distribution tag.  Build specifications
must import this module instead of duplicating version strings.
"""

from __future__ import annotations

from typing import Any

from optees import __version__
from optees.core.release_version import (
    display_release_version,
    numeric_release_version,
    release_version_components,
)


def macos_info_plist() -> dict[str, Any]:
    """Return the macOS bundle metadata for the current Optees version."""
    native_version = numeric_release_version(__version__)
    return {
        "CFBundleName": "Optees",
        "CFBundleDisplayName": "Optees",
        "CFBundleVersion": native_version,
        "CFBundleShortVersionString": native_version,
        "CFBundleGetInfoString": f"Optees {display_release_version(__version__)}",
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "NSAppleScriptEnabled": False,
        "LSMinimumSystemVersion": "13.0",
    }


def windows_version_info_text() -> str:
    """Return a PyInstaller version resource using the application version."""
    major, minor, patch, _rc_number = release_version_components(__version__)
    parts = (major, minor, patch)
    numeric_version = ", ".join(str(part) for part in (*parts, 0))
    display_version = display_release_version(__version__)
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({numeric_version}),
    prodvers=({numeric_version}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Optees contributors'),
          StringStruct('FileDescription', 'Optees optimization workbench'),
          StringStruct('FileVersion', '{display_version}'),
          StringStruct('InternalName', 'optees'),
          StringStruct('OriginalFilename', 'optees.exe'),
          StringStruct('ProductName', 'Optees'),
          StringStruct('ProductVersion', '{display_version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
