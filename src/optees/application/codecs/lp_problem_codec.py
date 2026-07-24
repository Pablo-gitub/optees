from __future__ import annotations

from optees.application.contracts.capability_ids import LP_CAPABILITY_ID
from optees.application.contracts.json_value import JsonValue
from optees.domain.models.lp.lp_model import LPModel
from optees.utility.lp_json_io import lp_model_from_dict


def lp_model_from_public_dict(payload: dict[str, JsonValue]) -> LPModel:
    """Decode the versioned public LP payload through the shared LP parser."""

    required = ("version", "variables", "objective", "constraints")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            f"{LP_CAPABILITY_ID} is missing required fields: " + ", ".join(missing)
        )
    return lp_model_from_dict(payload)
