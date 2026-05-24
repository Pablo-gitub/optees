# optees.spec
# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Optees.
# Run from the project root:
#   pyinstaller optees.spec --noconfirm
#
# Produces:
#   dist/optees/          (Windows & Linux — onedir)
#   dist/optees.app/      (macOS — .app bundle, additionally)

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Platform icon
# ---------------------------------------------------------------------------
_icon = (
    "src/optees/assets/logo/dark/optees.ico"    if sys.platform == "win32"  else
    "src/optees/assets/logo/dark/optees.icns"   if sys.platform == "darwin" else
    "src/optees/assets/logo/dark/appicon_256.png"
)

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    ["src/optees/main.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        # Bundle the entire assets directory; assets.py resolves it
        # at runtime via sys._MEIPASS / "assets" / rel.
        ("src/optees/assets", "assets"),
    ],
    hiddenimports=[
        # PySide6 SVG support — often missed by static analysis
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        # SciPy / HiGHS internals
        "scipy._lib.messagestream",
        "scipy.linalg",
        "scipy.linalg.cython_blas",
        "scipy.linalg.cython_lapack",
        "scipy.optimize._highspy",
        "scipy.optimize._linprog_highs",
        # Markdown extensions loaded by name at runtime
        "markdown.extensions.tables",
        "markdown.extensions.fenced_code",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "_tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ---------------------------------------------------------------------------
# Executable
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="optees",
    debug=False,
    strip=False,
    upx=False,          # UPX can break PySide6 binaries on some platforms
    console=False,      # no terminal window for a GUI app
    icon=_icon,
)

# ---------------------------------------------------------------------------
# Collected directory (all platforms)
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="optees",
)

# ---------------------------------------------------------------------------
# macOS .app bundle
# ---------------------------------------------------------------------------
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="optees.app",
        icon="src/optees/assets/logo/dark/optees.icns",
        bundle_identifier="com.paolopietrelli.optees",
        info_plist={
            "CFBundleName":               "Optees",
            "CFBundleDisplayName":        "Optees",
            "CFBundleVersion":            "0.1.0",
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable":    True,
            "NSPrincipalClass":           "NSApplication",
            "NSAppleScriptEnabled":       False,
            # Allow the app to run on Apple Silicon natively
            "LSMinimumSystemVersion":     "13.0",
        },
    )
