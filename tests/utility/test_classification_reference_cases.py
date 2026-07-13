from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.utility.classification_utils import solve_classification


def test_included_binary_classification_reference_case() -> None:
    path = Path(__file__).parents[1] / "data" / "classification" / "reference_cases.json"
    case = json.loads(path.read_text(encoding="utf-8"))["linearly_separable_2d"]
    problem = {
        "feature_names": case["feature_names"],
        "target_name": case["target_name"],
        "feature_rows": [row["features"] for row in case["rows"]],
        "target_values": [row["target"] for row in case["rows"]],
        **case["training_options"],
    }

    result = solve_classification(problem)

    assert result["train_metrics"]["accuracy"] == pytest.approx(case["expected"]["train_accuracy"])  # type: ignore[index]
    assert result["test_metrics"]["accuracy"] == pytest.approx(case["expected"]["test_accuracy"])  # type: ignore[index]
