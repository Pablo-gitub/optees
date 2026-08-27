from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.application.contracts.capability_ids import QP_CAPABILITY_ID
from optees.application.contracts.execution import ExecutionEnvelope
from optees.composition.local_agent import create_local_optimization_service


ROOT = Path(__file__).resolve().parents[3]
CASES_FILE = ROOT / "tests" / "data" / "qp" / "reference_cases.json"


def load_reference_cases() -> list[dict]:
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["cases"]


@pytest.mark.parametrize(
    "case",
    load_reference_cases(),
    ids=lambda c: c["id"],
)
def test_qp_reference_case(case: dict) -> None:
    service = create_local_optimization_service()
    problem = case["problem"]
    expected = case["expected"]

    envelope = service.solve(QP_CAPABILITY_ID, problem)
    assert isinstance(envelope, ExecutionEnvelope)
    assert envelope.capability_id == QP_CAPABILITY_ID
    assert envelope.mathematical_status.value == expected["mathematical_status"]

    if expected["objective"] is not None:
        assert envelope.result is not None
        assert envelope.result["objective"] == pytest.approx(
            expected["objective"], rel=1e-4, abs=1e-4
        )
        values = {item["name"]: item["value"] for item in envelope.result["variables"]}
        for var_name, exp_val in expected["variables"].items():
            assert values[var_name] == pytest.approx(exp_val, rel=1e-4, abs=1e-4)

    if "validation_status" in expected and envelope.validation is not None:
        assert envelope.validation.status.value == expected["validation_status"]
