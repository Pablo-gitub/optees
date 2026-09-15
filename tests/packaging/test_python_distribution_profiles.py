from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_core_service_and_solve_do_not_import_optional_delivery_stacks():
    probe = """
import json
import sys

from optees.composition.local_agent import create_local_optimization_service

service = create_local_optimization_service()
outcome = service.solve(
    "knapsack.zero_one",
    {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "zero_one",
        "capacity": 5,
        "items": [
            {"name": "A", "value": 6, "weight": 2},
            {"name": "B", "value": 10, "weight": 4},
            {"name": "C", "value": 5, "weight": 3},
        ],
    },
)
optional_roots = (
    "PySide6",
    "fastapi",
    "uvicorn",
    "pydantic",
    "mcp",
    "matplotlib",
    "markdown",
)
loaded = sorted(
    root
    for root in optional_roots
    if any(name == root or name.startswith(root + ".") for name in sys.modules)
)
print(
    json.dumps(
        {
            "loaded_optional_roots": loaded,
            "mathematical_status": outcome.mathematical_status.value,
            "objective": outcome.result["objective"],
        }
    )
)
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT / "src")

    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {
        "loaded_optional_roots": [],
        "mathematical_status": "optimal",
        "objective": 11.0,
    }
