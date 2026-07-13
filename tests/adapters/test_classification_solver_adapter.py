from __future__ import annotations

from optees.data.adapters.classification.numpy_classification_adapter import NumpyClassificationAdapter


def test_adapter_returns_a_normalized_success_response() -> None:
    result = NumpyClassificationAdapter().solve(
        {
            "feature_names": ["x"],
            "target_name": "class",
            "feature_rows": [[0], [1], [2], [4], [5], [6]],
            "target_values": ["no", "no", "no", "yes", "yes", "yes"],
        }
    )

    assert result["status"] == "Trained"
    assert result["positive_label"] == "yes"


def test_adapter_normalizes_solver_failures() -> None:
    result = NumpyClassificationAdapter().solve({})

    assert result["status"] == "Failed"
    assert result["extras"]["message"]  # type: ignore[index]
