from __future__ import annotations

import pytest

from optees.domain.entities.classification.dataset import ClassificationDataset
from optees.domain.models.classification.binary_classification_model import (
    BinaryClassificationModel,
    ClassificationOptions,
)
from optees.domain.value_objects.classification.classification_method import ClassificationMethod


def _dataset() -> ClassificationDataset:
    return ClassificationDataset.from_rows(
        feature_names=("x1", "x2"),
        target_name="approved",
        rows=(
            ((0, 0), "no"),
            ((0, 1), "no"),
            ((1, 0), "no"),
            ((1, 1), "no"),
            ((3, 3), "yes"),
            ((3, 4), "yes"),
            ((4, 3), "yes"),
            ((4, 4), "yes"),
        ),
    )


def test_dataset_keeps_sorted_binary_labels() -> None:
    assert _dataset().labels == ("no", "yes")
    assert _dataset().row_count == 8


@pytest.mark.parametrize(
    "rows",
    [
        (((0,), "no"), ((1,), "yes"), ((2,), "no"), ((3,), "yes"), ((4,), "no")),
        (((0,), "no"), ((1,), "yes"), ((2,), "no"), ((3,), "yes"), ((4,), "no"), ((5,), "maybe")),
        (((0,), "no"), ((1,), "yes"), ((2,), "yes"), ((3,), "yes"), ((4,), "yes"), ((5,), "yes")),
    ],
)
def test_dataset_rejects_insufficient_or_non_binary_labels(rows) -> None:
    with pytest.raises(ValueError):
        ClassificationDataset.from_rows(feature_names=("x",), target_name="class", rows=rows)


def test_options_normalize_logistic_alias() -> None:
    options = ClassificationOptions(method="logistic", test_fraction=0.25, l2_alpha=0)

    assert options.method is ClassificationMethod.LOGISTIC_REGRESSION
    assert options.l2_alpha == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"test_fraction": 1},
        {"learning_rate": 0},
        {"max_iterations": 0},
        {"l2_alpha": -0.1},
        {"random_seed": -1},
    ],
)
def test_options_reject_invalid_training_parameters(kwargs) -> None:
    with pytest.raises(ValueError):
        ClassificationOptions(**kwargs)


def test_model_requires_classification_dataset() -> None:
    with pytest.raises(ValueError):
        BinaryClassificationModel(dataset=object())  # type: ignore[arg-type]
