from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _project_metadata() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]


def _dependency_names(requirements: list[str]) -> set[str]:
    return {
        requirement.split("[", 1)[0]
        .split("<", 1)[0]
        .split(">", 1)[0]
        .split("=", 1)[0]
        .strip()
        .lower()
        for requirement in requirements
    }


def test_core_metadata_excludes_optional_delivery_dependencies():
    project = _project_metadata()

    assert _dependency_names(project["dependencies"]) == {
        "numpy",
        "scipy",
        "statsmodels",
        "ortools",
        "osqp",
    }


def test_runtime_extras_are_independently_complete():
    extras = _project_metadata()["optional-dependencies"]

    assert {"pyside6", "certifi", "matplotlib", "markdown"} <= _dependency_names(extras["desktop"])
    assert {"fastapi", "pydantic", "uvicorn", "matplotlib"} <= _dependency_names(
        extras["local-service"]
    )
    assert {"mcp", "pydantic", "matplotlib"} <= _dependency_names(extras["mcp"])
    assert _dependency_names(extras["plot"]) == {"matplotlib"}
    assert (
        _dependency_names(extras["desktop"])
        | _dependency_names(extras["local-service"])
        | _dependency_names(extras["mcp"])
    ) <= _dependency_names(extras["all"])


def test_mcp_script_uses_optional_dependency_boundary():
    project = _project_metadata()

    assert project["scripts"]["optees-mcp"] == "optees.mcp_entrypoint:main"


def test_package_data_excludes_python_cache_artifacts():
    with (ROOT / "pyproject.toml").open("rb") as stream:
        setuptools = tomllib.load(stream)["tool"]["setuptools"]

    package_data = set(setuptools["package-data"]["optees.assets"])
    exclusions = set(setuptools["exclude-package-data"]["optees.assets"])
    assert setuptools["include-package-data"] is False
    assert "**/*" not in package_data
    assert {"__pycache__/*", "*/__pycache__/*", "*.pyc", "*/*.pyc"} <= exclusions


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
