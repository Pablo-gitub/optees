"""Versioned JSON import/export for educational binary classification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from optees.domain.entities.classification.dataset import ClassificationDataset
from optees.domain.models.classification.binary_classification_model import (
    BinaryClassificationModel,
    ClassificationOptions,
)
from optees.domain.value_objects.classification.classification_method import ClassificationMethod


CLASSIFICATION_JSON_VERSION = "1"
CLASSIFICATION_PROBLEM_TYPE = "binary_classification"


def classification_model_from_dict(data: Mapping[str, object]) -> BinaryClassificationModel:
    if not isinstance(data, Mapping):
        raise ValueError("Classification JSON root must be an object")
    if str(data.get("version", "")) != CLASSIFICATION_JSON_VERSION:
        raise ValueError(f"unsupported Classification JSON version: {data.get('version')!r}")
    if str(data.get("problem_type", "")).strip().lower() != CLASSIFICATION_PROBLEM_TYPE:
        raise ValueError(f"problem_type must be {CLASSIFICATION_PROBLEM_TYPE!r}")
    try:
        return BinaryClassificationModel(
            dataset=_parse_dataset(data.get("dataset")),
            options=_parse_options(data.get("training_options", {})),
        )
    except ValueError as exc:
        raise ValueError(f"invalid Classification model: {exc}") from exc


def classification_model_to_dict(model: BinaryClassificationModel) -> dict[str, object]:
    return {
        "version": CLASSIFICATION_JSON_VERSION,
        "problem_type": CLASSIFICATION_PROBLEM_TYPE,
        "dataset": {
            "feature_names": list(model.dataset.feature_names),
            "target_name": model.dataset.target_name,
            "rows": [
                {"features": list(features), "target": target}
                for features, target in zip(model.dataset.feature_rows, model.dataset.target_values, strict=True)
            ],
        },
        "training_options": {
            "method": model.options.method.value,
            "test_fraction": model.options.test_fraction,
            "random_seed": model.options.random_seed,
            "learning_rate": model.options.learning_rate,
            "max_iterations": model.options.max_iterations,
            "l2_alpha": model.options.l2_alpha,
        },
    }


def classification_model_from_file(path: str | Path) -> BinaryClassificationModel:
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read Classification JSON file: {exc}") from exc
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid Classification JSON: {exc}") from exc
    return classification_model_from_dict(data)


def classification_model_to_file(model: BinaryClassificationModel, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(classification_model_to_dict(model), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _parse_dataset(value: object) -> ClassificationDataset:
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
    parsed_rows: list[tuple[list[object], str]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"dataset.rows[{index}] must be an object")
        features = row.get("features")
        target = row.get("target")
        if not isinstance(features, list):
            raise ValueError(f"dataset.rows[{index}].features must be an array")
        if not isinstance(target, str):
            raise ValueError(f"dataset.rows[{index}].target must be a string")
        parsed_rows.append((features, target))
    return ClassificationDataset.from_rows(
        feature_names=feature_names,
        target_name=target_name,
        rows=parsed_rows,
    )


def _parse_options(value: object) -> ClassificationOptions:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise ValueError("training_options must be an object")
    try:
        return ClassificationOptions(
            method=ClassificationMethod.from_str(value.get("method", "LogisticRegression")),
            test_fraction=value.get("test_fraction", 0.25),
            random_seed=value.get("random_seed", 42),
            learning_rate=value.get("learning_rate", 0.1),
            max_iterations=value.get("max_iterations", 2_000),
            l2_alpha=value.get("l2_alpha", 0.0),
        )
    except ValueError as exc:
        raise ValueError(f"training_options: {exc}") from exc
