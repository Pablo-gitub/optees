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

from PyInstaller.utils.hooks import get_package_paths

_project_root = Path(SPECPATH).resolve()
sys.path.insert(0, str(_project_root / "src"))

from optees.core.build_metadata import macos_info_plist

# ---------------------------------------------------------------------------
# Platform icon
# ---------------------------------------------------------------------------
_icon = (
    "src/optees/assets/logo/dark/optees.ico"    if sys.platform == "win32"  else
    "src/optees/assets/logo/dark/optees.icns"   if sys.platform == "darwin" else
    "src/optees/assets/logo/dark/appicon_256.png"
)

# The Windows OR-Tools wheel stores its complete native dependency set under
# ortools/.libs. That directory is not a normal DLL search path, so PyInstaller
# can otherwise miss ortools.dll or resolve same-named dependencies from the
# build runner. Collect the wheel-owned files explicitly and verify their
# presence before Analysis starts.
_ortools_libs = []
if sys.platform == "win32":
    _ortools_package_dir = Path(get_package_paths("ortools")[1])
    _ortools_libs_dir = _ortools_package_dir / ".libs"
    _ortools_libs = sorted(
        path for path in _ortools_libs_dir.glob("*") if path.is_file()
    )
    if not any(path.name.lower() == "ortools.dll" for path in _ortools_libs):
        raise SystemExit(
            "optees.spec: ortools.dll was not found in "
            f"{_ortools_libs_dir}; contents: {[path.name for path in _ortools_libs]}"
        )

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    ["src/optees/main.py"],
    pathex=["src"],
    binaries=[(str(path), ".") for path in _ortools_libs],
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
        # Optional local solver service, dispatched by the packaged GUI binary.
        "optees.local_server",
        "optees.interfaces.http.local_api",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "_tkinter"],
    noarchive=False,
)

if _ortools_libs:
    # Analysis may have discovered same-named DLLs elsewhere on the runner.
    # Remove every competing destination and make the wheel copies authoritative.
    _ortools_names = {path.name.lower() for path in _ortools_libs}
    a.binaries = [
        entry
        for entry in a.binaries
        if Path(entry[0]).name.lower() not in _ortools_names
    ]
    a.binaries += [
        (path.name, str(path), "BINARY") for path in _ortools_libs
    ]

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
        info_plist=macos_info_plist(),
    )
