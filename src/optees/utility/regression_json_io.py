"""Versioned JSON import/export for educational regression models.

Schema v1 keeps a numeric table separate from the chosen estimator:

.. code-block:: json

  {
    "version": "1",
    "problem_type": "regression",
    "dataset": {
      "feature_names": ["floor_area"],
      "target_name": "price",
      "rows": [{"features": [50], "target": 120000}]
    },
    "training_options": {
      "method": "OLS", "test_fraction": 0.2,
      "random_seed": 42, "ridge_alpha": 1.0
    }
  }

Readers always construct the domain model, so imported data cannot bypass the
same finite-number, shape, split, and method validation used by the UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from optees.domain.entities.regression.dataset import RegressionDataset
from optees.domain.models.regression.regression_model import RegressionModel, RegressionOptions
from optees.domain.value_objects.regression.regression_method import RegressionMethod


REGRESSION_JSON_VERSION = "1"
REGRESSION_PROBLEM_TYPE = "regression"


def regression_model_from_dict(data: Mapping[str, object]) -> RegressionModel:
    """Build a regression model from a schema-v1 JSON-compatible object."""
    if not isinstance(data, Mapping):
        raise ValueError("Regression JSON root must be an object")
    if str(data.get("version", "")) != REGRESSION_JSON_VERSION:
        raise ValueError(f"unsupported Regression JSON version: {data.get('version')!r}")
    if str(data.get("problem_type", "")).strip().lower() != REGRESSION_PROBLEM_TYPE:
        raise ValueError(f"problem_type must be {REGRESSION_PROBLEM_TYPE!r}")
    try:
        return RegressionModel(
            dataset=_parse_dataset(data.get("dataset")),
            options=_parse_options(data.get("training_options", {})),
        )
    except ValueError as exc:
        raise ValueError(f"invalid Regression model: {exc}") from exc


def regression_model_to_dict(model: RegressionModel) -> dict[str, object]:
    """Serialize a validated regression model to its schema-v1 representation."""
    return {
        "version": REGRESSION_JSON_VERSION,
        "problem_type": REGRESSION_PROBLEM_TYPE,
        "dataset": {
            "feature_names": list(model.dataset.feature_names),
            "target_name": model.dataset.target_name,
            "rows": [
                {"features": list(features), "target": target}
                for features, target in zip(
                    model.dataset.feature_rows,
                    model.dataset.target_values,
                    strict=True,
                )
            ],
        },
        "training_options": {
            "method": model.options.method.value,
            "test_fraction": model.options.test_fraction,
            "random_seed": model.options.random_seed,
            "ridge_alpha": model.options.ridge_alpha,
        },
    }


def regression_model_from_file(path: str | Path) -> RegressionModel:
    """Load a regression formulation from a UTF-8 JSON file."""
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read Regression JSON file: {exc}") from exc
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid Regression JSON: {exc}") from exc
    return regression_model_from_dict(data)


def regression_model_to_file(model: RegressionModel, path: str | Path) -> None:
    """Write a validated regression model as formatted UTF-8 JSON."""
    Path(path).write_text(
        json.dumps(regression_model_to_dict(model), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _parse_dataset(value: object) -> RegressionDataset:
    if not isinstance(value, Mapping):
        raise ValueError("dataset must be an object")
    feature_names = value.get("feature_names")
    target_name = value.get("target_name")
    rows = value.get("rows")
    if not isinstance(feature_names, list) or not all(isinstance(name, str) for name in feature_names):
        raise ValueError("dataset.feature_names must be an array of strings")
    if not isinstance(target_name, str):
        raise ValueError("dataset.target_name must be a string")
    if not isinstance(rows, list):
        raise ValueError("dataset.rows must be an array")

    parsed_rows: list[tuple[list[object], object]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"dataset.rows[{index}] must be an object")
        features = row.get("features")
        if not isinstance(features, list):
            raise ValueError(f"dataset.rows[{index}].features must be an array")
        if "target" not in row:
            raise ValueError(f"dataset.rows[{index}].target is required")
        parsed_rows.append((features, row["target"]))
    return RegressionDataset.from_rows(
        feature_names=feature_names,
        target_name=target_name,
        rows=parsed_rows,
    )


def _parse_options(value: object) -> RegressionOptions:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise ValueError("training_options must be an object")
    try:
        return RegressionOptions(
            method=RegressionMethod.from_str(value.get("method", RegressionMethod.OLS.value)),
            test_fraction=value.get("test_fraction", 0.2),  # domain validates number and range
            random_seed=value.get("random_seed", 42),
            ridge_alpha=value.get("ridge_alpha", 1.0),
        )
    except ValueError as exc:
        raise ValueError(f"training_options: {exc}") from exc
