from __future__ import annotations

from typing import Protocol, TypeVar

from optees.application.contracts.execution import SerializedResult


ResultT = TypeVar("ResultT", contravariant=True)


class ResultSerializerPort(Protocol[ResultT]):
    capability_id: str
    result_schema_version: str

    def serialize(self, result: ResultT) -> SerializedResult:
        """Map one domain-specific result to its public versioned payload."""
        ...
