from __future__ import annotations

import importlib
import importlib.util
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
            _require_missing_extra(
                directory,
                "optees.main",
                "Install optees[desktop].",
            )
            _require_missing_extra(
                directory,
                "optees.local_server",
                "Install optees[local-service].",
                environment={
                    "OPTEES_LOCAL_SERVER_TOKEN": "distribution-smoke-" + "x" * 32,
                },
            )
            _require_missing_extra(
                directory,
                "optees.mcp_entrypoint",
                "Install optees[mcp].",
            )

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
        forecasting = next(
            item for item in payload["capabilities"] if item["id"] == "ml.forecasting.univariate"
        )
        solved = subprocess.run(
            [sys.executable, "-m", "optees.cli", "solve", "ml.forecasting.univariate"],
            cwd=Path(directory),
            input=json.dumps(forecasting["example_problem"]),
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(solved.stdout)
        if result.get("validation", {}).get("status") != "verified":
            raise RuntimeError("Installed CLI did not return an independently verified solve.")
    print(json.dumps({"ok": True, "profile": profile, "capabilities": 16}))
    return 0


def _require_missing_extra(
    directory: str,
    module_name: str,
    expected_hint: str,
    *,
    environment: dict[str, str] | None = None,
) -> None:
    process_environment = dict(os.environ)
    process_environment.update(environment or {})
    completed = subprocess.run(
        [sys.executable, "-m", module_name],
        cwd=Path(directory),
        env=process_environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if completed.returncode != 2 or expected_hint not in completed.stderr:
        raise RuntimeError(
            f"{module_name} did not return its bounded missing-extra diagnostic: "
            f"exit={completed.returncode}, stderr={completed.stderr!r}"
        )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
