from __future__ import annotations
import sys
from importlib.resources import files
from pathlib import Path


def asset(rel: str) -> str:
    """
    Return an absolute filesystem path to an asset inside 'optees/assets'.
    Works in editable installs, pip-installed wheels, and PyInstaller bundles.
    """
    # PyInstaller onedir/onefile bundle
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return str(Path(sys._MEIPASS) / "assets" / rel)
    try:
        # packaged (PEP 561 resources)
        return str(files("optees.assets").joinpath(rel))
    except Exception:
        # dev-mode fallback
        return str(Path(__file__).resolve().parents[1] / "assets" / rel)
