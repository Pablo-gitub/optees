from __future__ import annotations

import pytest

from optees.utility.classification_utils import solve_classification


def _problem() -> dict[str, object]:
    return {
        "feature_names": ["x1", "x2"],
        "target_name": "approved",
        "feature_rows": [[0, 0], [0, 1], [1, 0], [1, 1], [3, 3], [3, 4], [4, 3], [4, 4]],
        "target_values": ["no", "no", "no", "no", "yes", "yes", "yes", "yes"],
        "method": "LogisticRegression",
        "test_fraction": 0.25,
        "random_seed": 17,
        "learning_rate": 0.1,
        "max_iterations": 2_000,
        "l2_alpha": 0.0,
    }


def test_logistic_regression_solves_a_linearly_separable_reference_case() -> None:
    result = solve_classification(_problem())

    assert result["status"] == "Trained"
    assert result["negative_label"] == "no"
    assert result["positive_label"] == "yes"
    assert result["train_metrics"]["accuracy"] == pytest.approx(1.0)  # type: ignore[index]
    assert result["test_metrics"]["accuracy"] == pytest.approx(1.0)  # type: ignore[index]
    assert result["test_confusion"] == {
        "true_negative": 1,
        "false_positive": 0,
        "false_negative": 0,
        "true_positive": 1,
    }
    assert len(result["predictions"]) == 8  # type: ignore[arg-type]


def test_split_and_predictions_are_reproducible_for_the_same_seed() -> None:
    first = solve_classification(_problem())
    second = solve_classification(_problem())

    assert first["predictions"] == second["predictions"]
    assert first["coefficients"] == second["coefficients"]


def test_test_partition_is_stratified() -> None:
    result = solve_classification(_problem())
    test_rows = [row for row in result["predictions"] if row["partition"] == "test"]  # type: ignore[index]

    assert {row["actual"] for row in test_rows} == {"no", "yes"}


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("target_values", ["no", "no", "no", "no", "yes", "yes", "yes", "maybe"]),
        ("feature_rows", [[0], [0], [1], [1], [3], [3], [4], [4]]),
        ("learning_rate", 0),
    ],
)
def test_solver_rejects_invalid_binary_problem_data(key: str, value: object) -> None:
    problem = _problem()
    problem[key] = value

    with pytest.raises(ValueError):
        solve_classification(problem)
