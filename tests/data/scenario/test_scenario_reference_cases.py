from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from optees.application.codecs.scenario_problem_codec import (
    CodedValidationError,
    scenario_max_min_reward_model_from_public_dict,
    scenario_min_max_loss_model_from_public_dict,
)
from optees.application.contracts.capability_ids import (
    SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID,
    SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID,
)
from optees.application.contracts.execution import ExecutionEnvelope
from optees.application.validation.scenario_solution_validator import (
    ScenarioIndependentSolutionValidator,
)
from optees.composition.local_agent import create_local_optimization_service
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.entities.scenario.scenario_value import ScenarioValue
from optees.domain.models.scenario.scenario_result import (
    ScenarioResult,
    ScenarioSolveStatus,
)
from optees.domain.value_objects.lp.solve_status import SolveStatus
from optees.domain.value_objects.lp.solver_diagnostics import SolverDiagnostics


FIXTURES_DIR = Path(__file__).resolve().parent
REFERENCE_CASES_FILE = FIXTURES_DIR / "reference_cases.json"
MANIFEST_FILE = FIXTURES_DIR / "manifest.json"
README_FILE = FIXTURES_DIR / "README.md"


def load_bundle() -> dict:
    with open(REFERENCE_CASES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_manifest() -> dict:
    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def test_scenario_manifest_integrity_and_determinism() -> None:
    manifest = load_manifest()
    assert manifest["manifest_version"] == "1"
    assert manifest["optees_version"] == "0.10.2"
    assert manifest["implementation_baseline_commit"] == "d6fa7afecca8dae9755741ed37db09308fcdde6c"
    assert set(manifest["capability_ids"]) == {
        SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID,
        SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID,
    }

    recorded_files = manifest["files"]
    file_paths = [item["path"] for item in recorded_files]
    assert file_paths == sorted(file_paths), "Manifest files must be sorted deterministically."

    # Check that recorded files match the data files on disk
    expected_files = {"README.md", "reference_cases.json"}
    assert set(file_paths) == expected_files

    # Recompute byte hashes
    for item in recorded_files:
        rel_path = item["path"]
        expected_sha = item["sha256"]
        actual_bytes = (FIXTURES_DIR / rel_path).read_bytes()
        actual_sha = hashlib.sha256(actual_bytes).hexdigest().lower()
        assert actual_sha == expected_sha, f"SHA-256 mismatch for file '{rel_path}'."

    # Recompute aggregate hash
    lines = [f"{item['sha256']}  {item['path']}\n" for item in recorded_files]
    aggregate_text = "".join(lines)
    recomputed_aggregate = hashlib.sha256(aggregate_text.encode("utf-8")).hexdigest().lower()
    assert manifest["aggregate_sha256"] == recomputed_aggregate


def test_scenario_manifest_detects_mutation() -> None:
    manifest = load_manifest()
    original_ref_bytes = REFERENCE_CASES_FILE.read_bytes()
    mutated_bytes = original_ref_bytes + b" "

    mutated_sha = hashlib.sha256(mutated_bytes).hexdigest().lower()
    assert mutated_sha != manifest["files"][1]["sha256"]

    # Altering the entry alters the aggregate hash
    recorded_files = copy.deepcopy(manifest["files"])
    recorded_files[1]["sha256"] = mutated_sha
    lines = [f"{item['sha256']}  {item['path']}\n" for item in recorded_files]
    mutated_aggregate = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest().lower()
    assert mutated_aggregate != manifest["aggregate_sha256"]


def test_scenario_manifest_rejects_missing_and_extra_files() -> None:
    manifest = load_manifest()
    recorded_paths = {item["path"] for item in manifest["files"]}

    # Reject missing file
    for path in recorded_paths:
        file_path = FIXTURES_DIR / path
        assert file_path.is_file(), f"Recorded file '{path}' is missing from disk."

    # Reject unexpected data files in fixture directory (ignoring python scripts and manifest itself)
    actual_data_files = {
        p.name
        for p in FIXTURES_DIR.iterdir()
        if p.is_file() and p.name not in ("manifest.json",) and not p.name.endswith(".py")
    }
    assert actual_data_files == recorded_paths, (
        "Fixture directory contains unexpected untracked data files."
    )


def test_scenario_bundle_metadata() -> None:
    bundle = load_bundle()
    assert bundle["fixture_format_version"] == "1"
    assert set(bundle["capability_ids"]) == {
        SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID,
        SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID,
    }
    assert bundle["problem_schema_version"] == "1"
    assert bundle["result_schema_version"] == "1"
    assert bundle["optees_version"] == "0.10.2"
    assert bundle["implementation_baseline_commit"] == "d6fa7afecca8dae9755741ed37db09308fcdde6c"
    assert "limitations" in bundle
    assert "feasible_incumbent_and_timeout" in bundle["limitations"]
    assert "non-deterministically" in bundle["limitations"]["feasible_incumbent_and_timeout"]


@pytest.mark.parametrize(
    "case",
    [c for c in load_bundle()["cases"] if c["kind"] == "analytic_reference_case"],
    ids=lambda c: c["id"],
)
def test_analytic_reference_cases(case: dict) -> None:
    capability_id = case["capability_id"]
    problem = case["problem"]
    expected_status = case["backend_delivery"]["expected_mathematical_status"]
    expected_res = case["expected_public_result"]

    # 1. Decode problem with production codec
    if capability_id == SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID:
        model = scenario_min_max_loss_model_from_public_dict(problem)
    else:
        model = scenario_max_min_reward_model_from_public_dict(problem)
    assert model.orientation.value == expected_res["orientation"]

    # 2. Solve problem via production local optimization service
    service = create_local_optimization_service()
    envelope = service.solve(capability_id, problem)
    assert isinstance(envelope, ExecutionEnvelope)
    assert envelope.capability_id == capability_id
    assert envelope.mathematical_status.value == expected_status

    if expected_status == "optimal":
        analytic = case["analytic_solution"]
        assert envelope.result is not None
        assert envelope.result["orientation"] == expected_res["orientation"]
        assert envelope.result["guaranteed_value"] == pytest.approx(
            analytic["guaranteed_value"], abs=1e-5, rel=1e-5
        )
        assert envelope.result["binding_scenario_ids"] == analytic["binding_scenario_ids"]

        # Check variable values
        var_dict = {item["name"]: item["value"] for item in envelope.result["variables"]}
        for var_name, expected_val in analytic["variables"].items():
            assert var_dict[var_name] == pytest.approx(expected_val, abs=1e-5, rel=1e-5)

        # Check scenario values
        scen_dict = {
            item["scenario_id"]: (item["value"], item["is_binding"])
            for item in envelope.result["scenario_values"]
        }
        for scen_id, expected_val in analytic["scenario_values"].items():
            assert scen_id in scen_dict
            assert scen_dict[scen_id][0] == pytest.approx(expected_val, abs=1e-5, rel=1e-5)
            assert scen_dict[scen_id][1] == (scen_id in analytic["binding_scenario_ids"])

        # Check independent validation
        assert envelope.validation is not None
        assert envelope.validation.status.value == case["expected_validation"]["status"]
    else:
        # Infeasible or unbounded: no candidate
        assert envelope.result is not None
        assert envelope.result["guaranteed_value"] is None
        assert envelope.result["variables"] == []
        assert envelope.result["scenario_values"] == []
        assert envelope.result["binding_scenario_ids"] == []
        assert envelope.validation is not None
        assert envelope.validation.status.value == "not_available"


@pytest.mark.parametrize(
    "case",
    [c for c in load_bundle()["cases"] if c["kind"] == "invalid_problem_probe"],
    ids=lambda c: c["id"],
)
def test_invalid_problem_probes(case: dict) -> None:
    capability_id = case["capability_id"]
    expected_error = case["expected_error"]

    if case["id"] == "invalid_problem_non_finite_input":
        # Base case with injected NaN
        base_case = next(c for c in load_bundle()["cases"] if c["id"] == case["base_case_id"])
        problem = copy.deepcopy(base_case["problem"])
        problem["scenarios"][0]["coefficients"][0] = float("nan")
    else:
        problem = case["problem"]

    with pytest.raises(CodedValidationError) as exc_info:
        if capability_id == SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID:
            scenario_min_max_loss_model_from_public_dict(problem)
        else:
            scenario_max_min_reward_model_from_public_dict(problem)

    err = exc_info.value
    assert err.detail_code == expected_error["detail_code"]
    if "path" in expected_error:
        assert err.path == expected_error["path"]


@pytest.mark.parametrize(
    "case",
    [c for c in load_bundle()["cases"] if c["kind"] == "tampered_validation_probe"],
    ids=lambda c: c["id"],
)
def test_tampered_validation_probes(case: dict) -> None:
    base_case = next(c for c in load_bundle()["cases"] if c["id"] == case["base_case_id"])
    problem = base_case["problem"]
    model = scenario_min_max_loss_model_from_public_dict(problem)

    # Base valid components
    analytic = base_case["analytic_solution"]
    tampering = case["tampering"]
    target = tampering["target"]
    tampered_val = tampering["tampered_value"]

    var_dict = copy.deepcopy(analytic["variables"])
    scen_values = [
        ScenarioValue(
            scen_id,
            val,
            scen_id in analytic["binding_scenario_ids"],
        )
        for scen_id, val in analytic["scenario_values"].items()
    ]
    guaranteed_value = float(analytic["guaranteed_value"])
    binding_ids = tuple(analytic["binding_scenario_ids"])
    aux_val = float(analytic["guaranteed_value"])
    lp_obj = float(analytic["guaranteed_value"])

    if target == "variables":
        var_dict["x1"] = tampered_val
    elif target == "scenario_values":
        scen_values[0] = ScenarioValue("s1", tampered_val, True)
    elif target == "guaranteed_value":
        guaranteed_value = tampered_val
    elif target == "binding_scenario_ids":
        binding_ids = tuple(tampered_val)
    elif target == "auxiliary_value":
        aux_val = tampered_val
    elif target == "delegated_solution.objective":
        lp_obj = tampered_val

    delegated_lp = LPSolution(
        status=SolveStatus.OPTIMAL,
        objective=lp_obj,
        values={
            "x1": var_dict.get("x1", 37.0 / 7.0),
            "x2": var_dict.get("x2", 33.0 / 7.0),
            "_aux_theta": aux_val,
        },
        diagnostics=SolverDiagnostics(method="highs", status_code=0, success=True),
        extras={},
    )

    tampered_result = ScenarioResult(
        status=ScenarioSolveStatus.OPTIMAL,
        orientation=model.orientation,
        original_variable_order=("x1", "x2"),
        scenario_order=("s1", "s2", "s3"),
        guaranteed_value=guaranteed_value,
        variables=var_dict,
        scenario_values=tuple(scen_values),
        binding_scenario_ids=binding_ids,
        delegated_solution=delegated_lp,
        auxiliary_variable_name="_aux_theta",
        auxiliary_value=aux_val,
    )

    validator = ScenarioIndependentSolutionValidator()
    validation_report = validator(model, tampered_result)

    assert validation_report.status.value == "failed"
    exp_code = case["expected_validation"]["primary_violation_code"]
    exp_check = case["expected_validation"]["primary_violation_check"]
    assert any(v.code == exp_code for v in validation_report.violations), (
        f"Expected violation code '{exp_code}' not found in {[v.code for v in validation_report.violations]}"
    )
    failed_checks = [c.code for c in validation_report.checks if c.status.value == "failed"]
    assert exp_check in failed_checks, f"Expected check '{exp_check}' to fail in {failed_checks}"


def test_delivery_dependency_unavailable_probe() -> None:
    bundle = load_bundle()
    probe_case = next(c for c in bundle["cases"] if c["kind"] == "delivery_probe")
    assert probe_case["id"] == "delivery_dependency_unavailable"
    assert probe_case["delivery_error"]["code"] == "dependency_unavailable"
