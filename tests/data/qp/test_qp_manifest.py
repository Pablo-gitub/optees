from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import pytest

from optees import __version__
from optees.application.codecs.qp_problem_codec import qp_model_from_public_dict
from optees.application.contracts.capability_ids import QP_CAPABILITY_ID
from optees.application.contracts.execution import ExecutionEnvelope
from optees.composition.local_agent import (
    _qp_descriptor,
    create_local_optimization_service,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
QP_DATA_DIR = Path(__file__).resolve().parent
MANIFEST_FILE = QP_DATA_DIR / "manifest.json"


def load_manifest() -> dict:
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_qp_manifest_integrity_and_determinism() -> None:
    manifest = load_manifest()

    assert manifest["manifest_version"] == "1"
    assert manifest["path_base"] == "repository_root"
    assert manifest["optees_version"] == __version__
    assert manifest["capability_id"] == QP_CAPABILITY_ID
    assert manifest["capability_ids"] == [QP_CAPABILITY_ID]

    # Baseline commit must be a valid 40-character lowercase hex string
    baseline_commit = manifest["implementation_baseline_commit"]
    assert re.fullmatch(r"[0-9a-f]{40}", baseline_commit) is not None

    recorded_files = manifest["files"]
    paths = [item["path"] for item in recorded_files]
    assert paths == sorted(paths), "Manifest paths must be sorted deterministically."

    expected_paths = {
        "examples/qp_resource_allocation_2variables.json",
        "tests/data/qp/README.md",
        "tests/data/qp/reference_cases.json",
    }
    assert set(paths) == expected_paths

    for item in recorded_files:
        rel_path = item["path"]
        expected_sha = item["sha256"]
        full_path = REPO_ROOT / rel_path
        assert full_path.is_file(), f"Covered file {rel_path} must exist within the repository."
        actual_bytes = full_path.read_bytes()
        actual_sha = hashlib.sha256(actual_bytes).hexdigest().lower()
        assert actual_sha == expected_sha, f"SHA-256 mismatch for covered file {rel_path}."

    # Recompute aggregate hash exactly as specified
    lines = [f"{item['sha256']}  {item['path']}\n" for item in recorded_files]
    aggregate_text = "".join(lines)
    recomputed_aggregate = hashlib.sha256(aggregate_text.encode("utf-8")).hexdigest().lower()
    assert manifest["aggregate_sha256"] == recomputed_aggregate


def test_qp_manifest_versions_match_production_discovery() -> None:
    manifest = load_manifest()
    descriptor = _qp_descriptor(dependency_available=True)

    assert manifest["capability_id"] == descriptor.capability_id
    assert manifest["contract_version"] == descriptor.contract_version
    assert manifest["problem_schema_version"] == descriptor.problem_schema_version
    assert manifest["result_schema_version"] == descriptor.result_schema_version


def test_qp_manifest_corruption_and_mutation_detection() -> None:
    manifest = load_manifest()
    ref_path = REPO_ROOT / "tests" / "data" / "qp" / "reference_cases.json"
    original_bytes = ref_path.read_bytes()
    mutated_bytes = original_bytes + b" "

    mutated_sha = hashlib.sha256(mutated_bytes).hexdigest().lower()
    ref_entry = next(
        f for f in manifest["files"] if f["path"] == "tests/data/qp/reference_cases.json"
    )
    assert mutated_sha != ref_entry["sha256"]

    # In-memory mutation altering entry hash alters aggregate
    recorded_files = copy.deepcopy(manifest["files"])
    for item in recorded_files:
        if item["path"] == "tests/data/qp/reference_cases.json":
            item["sha256"] = mutated_sha
    lines = [f"{item['sha256']}  {item['path']}\n" for item in recorded_files]
    mutated_aggregate = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest().lower()
    assert mutated_aggregate != manifest["aggregate_sha256"]

    # In-memory alteration of file path alters aggregate
    recorded_files_path = copy.deepcopy(manifest["files"])
    recorded_files_path[0]["path"] = "examples/tampered_name.json"
    lines_path = [f"{item['sha256']}  {item['path']}\n" for item in recorded_files_path]
    mutated_path_aggregate = hashlib.sha256("".join(lines_path).encode("utf-8")).hexdigest().lower()
    assert mutated_path_aggregate != manifest["aggregate_sha256"]


def test_qp_standalone_example_solves_optimally() -> None:
    example_file = REPO_ROOT / "examples" / "qp_resource_allocation_2variables.json"
    assert example_file.is_file()

    with open(example_file, "r", encoding="utf-8") as f:
        problem = json.load(f)

    # Validate problem structure through production codec
    model = qp_model_from_public_dict(problem)
    assert len(model.variables) == 2
    assert len(model.constraints) == 1

    # Solve through production optimization service
    service = create_local_optimization_service()
    envelope = service.solve(QP_CAPABILITY_ID, problem)
    assert isinstance(envelope, ExecutionEnvelope)
    assert envelope.capability_id == QP_CAPABILITY_ID
    assert envelope.mathematical_status.value == "optimal"

    assert envelope.result is not None
    assert envelope.result["objective"] == pytest.approx(-0.08, abs=1e-4, rel=1e-4)

    # Decision variables sum to 1.0 (allocation equality constraint)
    var_values = {v["name"]: v["value"] for v in envelope.result["variables"]}
    assert set(var_values.keys()) == {"w_primary", "w_secondary"}
    assert sum(var_values.values()) == pytest.approx(1.0, abs=1e-4, rel=1e-4)

    # Independent validation verification
    assert envelope.validation is not None
    assert envelope.validation.status.value == "verified"
