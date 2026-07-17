from __future__ import annotations

from optees.application.contracts.json_value import JsonValue
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.utility.packing_json_io import packing_model_from_dict


def packing_model_from_public_dict(
    payload: dict[str, JsonValue],
) -> SingleContainerPackingModel:
    required = (
        "version",
        "problem_type",
        "variant",
        "selection_policy",
        "gravity_mode",
        "container",
        "items",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            "packing.single_container_3d is missing required fields: "
            + ", ".join(missing)
        )
    return packing_model_from_dict(payload)
