from __future__ import annotations

import pytest

from optees.domain.entities.classification.dataset import ClassificationDataset
from optees.domain.models.classification.binary_classification_model import (
    BinaryClassificationModel,
    ClassificationOptions,
)
from optees.utility.classification_json_io import (
    classification_model_from_dict,
    classification_model_to_dict,
)


def _model() -> BinaryClassificationModel:
    return BinaryClassificationModel(
        ClassificationDataset.from_rows(
            feature_names=("income",),
            target_name="approved",
            rows=(
                ((20,), "no"), ((25,), "no"), ((30,), "no"),
                ((70,), "yes"), ((75,), "yes"), ((80,), "yes"),
            ),
        ),
        ClassificationOptions(test_fraction=1 / 3, random_seed=5, l2_alpha=0.2),
    )


def test_json_round_trip_preserves_dataset_and_options() -> None:
    restored = classification_model_from_dict(classification_model_to_dict(_model()))

    assert restored == _model()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(version="2"),
        lambda value: value.update(problem_type="regression"),
        lambda value: value.update(dataset={}),
        lambda value: value["dataset"]["rows"].__setitem__(0, {"features": [20], "target": 1}),
    ],
)
def test_json_rejects_invalid_schema(mutate) -> None:
    data = classification_model_to_dict(_model())
    mutate(data)

    with pytest.raises(ValueError):
        classification_model_from_dict(data)
