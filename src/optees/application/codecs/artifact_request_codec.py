from __future__ import annotations

from typing import Any

from optees.application.contracts.artifact import (
    ArtifactBatchRequest,
    ArtifactFormat,
    ArtifactRequest,
)
from optees.application.contracts.json_value import require_json_value


def artifact_batch_request_from_dict(
    requests: list[dict[str, Any]],
    *,
    contract_version: str = "1",
) -> ArtifactBatchRequest:
    """Decode one transport-neutral artifact request using the public contract."""

    decoded = []
    for item in requests:
        if not isinstance(item, dict):
            raise ValueError("every artifact request must be an object")
        artifact_type = item.get("artifact_type")
        formats = item.get("formats")
        options = item.get("options", {})
        if not isinstance(artifact_type, str):
            raise ValueError("artifact_type must be a string")
        if not isinstance(formats, list) or not all(
            isinstance(value, str) for value in formats
        ):
            raise ValueError("artifact formats must be an array of strings")
        normalized_options = require_json_value(
            options,
            path="$.artifact.requests[].options",
        )
        if not isinstance(normalized_options, dict):
            raise ValueError("artifact options must be an object")
        try:
            decoded_formats = tuple(ArtifactFormat(value) for value in formats)
        except ValueError as exc:
            raise ValueError(f"unsupported artifact format: {exc.args[0]}") from None
        decoded.append(
            ArtifactRequest(
                artifact_type=artifact_type,
                formats=decoded_formats,
                options=normalized_options,
            )
        )
    return ArtifactBatchRequest(
        tuple(decoded),
        contract_version=contract_version,
    )
