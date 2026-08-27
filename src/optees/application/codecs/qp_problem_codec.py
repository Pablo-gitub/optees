from __future__ import annotations

from typing import Any, Mapping

from optees.application.contracts.capability_ids import QP_CAPABILITY_ID
from optees.domain.models.qp.qp_model import QPModel
from optees.utility.qp_json_io import qp_model_from_dict


def qp_model_from_public_dict(payload: Mapping[str, Any]) -> QPModel:
    """Decode the versioned public QP payload into a domain QPModel."""
    if not isinstance(payload, Mapping):
        raise ValueError(f"{QP_CAPABILITY_ID} problem payload must be a JSON object")

    required = ("variables", "objective")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            f"{QP_CAPABILITY_ID} is missing required fields: " + ", ".join(missing)
        )

    return qp_model_from_dict(payload)
