from __future__ import annotations

from optees.application.contracts.capability_ids import NLP_CAPABILITY_ID
from optees.application.contracts.json_value import JsonValue
from optees.domain.models.nlp.nlp_model import NLPModel
from optees.utility.nlp_json_io import nlp_model_from_dict


def nlp_model_from_public_dict(payload: dict[str, JsonValue]) -> NLPModel:
    required = ("version", "problem_type", "variables", "objective")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            f"{NLP_CAPABILITY_ID} is missing required fields: "
            + ", ".join(missing)
        )
    return nlp_model_from_dict(payload)
