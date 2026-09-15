from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


PROFILE_IMPORTS = {
    "core": (),
    "local-service": ("fastapi", "pydantic", "uvicorn", "matplotlib"),
    "mcp": ("mcp", "pydantic", "matplotlib"),
    "desktop": ("PySide6", "certifi", "matplotlib", "markdown"),
    "all": ("PySide6", "fastapi", "mcp", "matplotlib"),
}


def main(argv: list[str] | None = None) -> int:
    if not argv or len(argv) != 1 or argv[0] not in PROFILE_IMPORTS:
        raise SystemExit("usage: smoke_python_distribution.py PROFILE")
    profile = argv[0]
    with tempfile.TemporaryDirectory(prefix="optees-wheel-smoke-") as directory:
        os.environ.setdefault("MPLCONFIGDIR", directory)
        for module_name in PROFILE_IMPORTS[profile]:
            importlib.import_module(module_name)

        if profile == "core":
            for module_name in ("PySide6", "fastapi", "mcp", "matplotlib"):
                if importlib.util.find_spec(module_name) is not None:
                    raise RuntimeError(f"Core environment unexpectedly contains {module_name}.")

        completed = subprocess.run(
            [sys.executable, "-m", "optees.cli", "list-capabilities"],
            cwd=Path(directory),
            check=True,
            capture_output=True,
            text=True,
        )
    payload = json.loads(completed.stdout)
    if payload.get("contract_version") != "1" or len(payload.get("capabilities", [])) != 16:
        raise RuntimeError("Installed CLI did not expose the expected capability inventory.")
    print(json.dumps({"ok": True, "profile": profile, "capabilities": 16}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
