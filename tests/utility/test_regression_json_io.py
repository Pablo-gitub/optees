from __future__ import annotations

import json
from pathlib import Path

import pytest

from optees.domain.value_objects.regression.regression_method import RegressionMethod
from optees.utility.regression_json_io import (
    regression_model_from_dict,
    regression_model_from_file,
    regression_model_to_dict,
    regression_model_to_file,
)


HOUSING_DATA = {
    "version": "1",
    "problem_type": "regression",
    "dataset": {
        "feature_names": ["floor_area", "rooms"],
        "target_name": "price",
        "rows": [
            {"features": [40, 1], "target": 100},
            {"features": [50, 2], "target": 130},
            {"features": [60, 2], "target": 150},
            {"features": [70, 3], "target": 180},
            {"features": [80, 3], "target": 200},
        ],
    },
    "training_options": {
        "method": "Ridge",
        "test_fraction": 0.4,
        "random_seed": 7,
        "ridge_alpha": 2.5,
    },
}


def test_imports_regression_json_through_the_domain_model() -> None:
    model = regression_model_from_dict(HOUSING_DATA)

    assert model.dataset.feature_names == ("floor_area", "rooms")
    assert model.dataset.target_name == "price"
    assert model.dataset.row_count == 5
    assert model.options.method is RegressionMethod.RIDGE
    assert model.options.ridge_alpha == 2.5


def test_round_trip_preserves_dataset_and_training_options() -> None:
    original = regression_model_from_dict(HOUSING_DATA)

    restored = regression_model_from_dict(regression_model_to_dict(original))

    assert restored == original
    assert regression_model_to_dict(restored)["problem_type"] == "regression"


def test_file_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "housing-regression.json"
    model = regression_model_from_dict(HOUSING_DATA)

    regression_model_to_file(model, path)
    restored = regression_model_from_file(path)

    assert restored == model
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == "1"


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({**HOUSING_DATA, "version": "2"}, "version"),
        ({**HOUSING_DATA, "problem_type": "classification"}, "problem_type"),
        ({**HOUSING_DATA, "dataset": {"feature_names": ["x"], "target_name": "y", "rows": []}}, "four"),
        ({**HOUSING_DATA, "training_options": {"method": "forest"}}, "method"),
        (
            {
                **HOUSING_DATA,
                "dataset": {
                    "feature_names": ["x"],
                    "target_name": "y",
                    "rows": [{"features": [1], "target": 1}] * 4,
                },
                "training_options": {"test_fraction": 1},
            },
            "test_fraction",
        ),
    ],
)
def test_rejects_invalid_regression_json(data: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        regression_model_from_dict(data)


def test_rejects_invalid_json_file(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid Regression JSON"):
        regression_model_from_file(path)
