from __future__ import annotations

from typing import Any, Mapping

from optees.application.contracts.errors import CodedValidationError
from optees.application.contracts.capability_ids import QP_CAPABILITY_ID
from optees.domain.models.qp.qp_model import QPModel
from optees.utility.qp_json_io import qp_model_from_dict


def qp_model_from_public_dict(payload: Mapping[str, Any]) -> QPModel:
    """Decode the versioned public QP payload into a domain QPModel."""
    if not isinstance(payload, Mapping):
        raise CodedValidationError(
            f"{QP_CAPABILITY_ID} problem payload must be a JSON object",
            detail_code="qp.invalid_structure",
        )

    required = ("version", "problem_type", "variables", "objective", "constraints")
    missing = [field for field in required if field not in payload]
    if missing:
        raise CodedValidationError(
            f"{QP_CAPABILITY_ID} is missing required fields: " + ", ".join(missing),
            detail_code="qp.invalid_structure",
        )

    try:
        return qp_model_from_dict(payload)
    except ValueError as exc:
        message = str(exc)
        lowered = message.lower()
        if "asymmetric" in lowered:
            code = "qp.asymmetric_quadratic_matrix"
        elif "positive semi-definite" in lowered:
            code = "qp.non_convex_quadratic_matrix"
        elif "negative semi-definite" in lowered:
            code = "qp.non_concave_quadratic_matrix"
        elif "non-finite" in lowered or "finite number" in lowered:
            code = "qp.non_finite_value"
        elif "lower bound" in lowered and "exceeds" in lowered:
            code = "qp.invalid_bounds"
        elif "length" in lowered or "matrix rows" in lowered or "variable count" in lowered:
            code = "qp.dimension_mismatch"
        elif "unique" in lowered:
            code = "qp.duplicate_variable_name"
        elif (
            "solver_options" in lowered
            or "qp tolerance" in lowered
            or "qp max_iterations" in lowered
            or "time_limit_seconds" in lowered
            or "unsupported qp method" in lowered
        ):
            code = "qp.invalid_solver_option"
        else:
            code = "qp.invalid_structure"
        raise CodedValidationError(message, detail_code=code) from exc
