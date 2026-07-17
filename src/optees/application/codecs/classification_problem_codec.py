from __future__ import annotations

from optees.application.contracts.json_value import JsonValue
from optees.domain.models.classification.binary_classification_model import (
    BinaryClassificationModel,
)
from optees.utility.classification_json_io import classification_model_from_dict


def classification_model_from_public_dict(
    payload: dict[str, JsonValue],
) -> BinaryClassificationModel:
    required = ("version", "problem_type", "dataset")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            "ml.classification.binary_logistic is missing required fields: "
            + ", ".join(missing)
        )
    return classification_model_from_dict(payload)
