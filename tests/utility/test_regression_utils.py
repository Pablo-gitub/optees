from __future__ import annotations

import pytest

from optees.utility.regression_utils import solve_regression


def _linear_problem(method: str = "OLS") -> dict[str, object]:
    rows = [[float(value)] for value in range(1, 11)]
    return {
        "feature_names": ["size"],
        "target_name": "price",
        "feature_rows": rows,
        "target_values": [2.0 + 3.0 * row[0] for row in rows],
        "method": method,
        "test_fraction": 0.2,
        "random_seed": 17,
        "ridge_alpha": 1.0,
    }


def test_ols_fits_a_known_linear_relation_and_evaluates_held_out_rows() -> None:
    result = solve_regression(_linear_problem())

    assert result["status"] == "Trained"
    assert result["intercept"] == pytest.approx(2.0)
    assert result["coefficients"] == {"size": pytest.approx(3.0)}
    assert result["train_metrics"]["rmse"] == pytest.approx(0.0)
    assert result["test_metrics"]["r_squared"] == pytest.approx(1.0)
    assert len(result["predictions"]) == 10
    assert {row["partition"] for row in result["predictions"]} == {"train", "test"}


def test_split_is_reproducible_for_a_fixed_seed() -> None:
    first = solve_regression(_linear_problem())
    second = solve_regression(_linear_problem())

    assert first["predictions"] == second["predictions"]
    assert first["extras"] == {"method": "OLS", "train_count": 8, "test_count": 2, "random_seed": 17}


def test_ridge_shrinks_the_feature_coefficient() -> None:
    ols = solve_regression(_linear_problem("OLS"))
    ridge = solve_regression(_linear_problem("Ridge"))

    assert abs(ridge["coefficients"]["size"]) < abs(ols["coefficients"]["size"])


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"feature_rows": [[1.0], [2.0]], "target_values": [1.0, 2.0]}, "four"),
        ({"feature_rows": [[1.0, 2.0]] * 4, "target_values": [1.0] * 4}, "shape"),
        ({"method": "forest"}, "unsupported"),
        ({"test_fraction": 1.0}, "between"),
    ],
)
def test_solver_rejects_invalid_problem_data(changes: dict[str, object], message: str) -> None:
    problem = _linear_problem()
    problem.update(changes)

    with pytest.raises(ValueError, match=message):
        solve_regression(problem)
