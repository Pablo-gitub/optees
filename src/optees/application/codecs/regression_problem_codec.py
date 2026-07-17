from __future__ import annotations

from optees.application.contracts.json_value import JsonValue
from optees.domain.models.regression.regression_model import RegressionModel
from optees.utility.regression_json_io import regression_model_from_dict


def regression_model_from_public_dict(
    payload: dict[str, JsonValue],
) -> RegressionModel:
    required = ("version", "problem_type", "dataset")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            "ml.regression.linear is missing required fields: "
            + ", ".join(missing)
        )
    return regression_model_from_dict(payload)
