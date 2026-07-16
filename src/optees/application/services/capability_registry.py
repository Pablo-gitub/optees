from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from optees.application.contracts.capability import CapabilityDescriptor
from optees.application.contracts.execution import SerializedResult
from optees.application.contracts.json_value import JsonValue


ModelT = TypeVar("ModelT")
ResultT = TypeVar("ResultT")


@dataclass(frozen=True)
class RegisteredCapability(Generic[ModelT, ResultT]):
    """Internal executable binding kept behind the public descriptor."""

    descriptor: CapabilityDescriptor
    parse_problem: Callable[[dict[str, JsonValue]], ModelT]
    execute: Callable[[ModelT], ResultT]
    serialize_result: Callable[[ResultT], SerializedResult]
    backend_id: str

    def __post_init__(self) -> None:
        if not self.backend_id.strip():
            raise ValueError("backend_id must not be empty.")


class CapabilityRegistry:
    """In-memory catalogue of explicitly composed solver capabilities."""

    def __init__(self) -> None:
        self._registrations: dict[str, RegisteredCapability[Any, Any]] = {}

    def register(self, capability: RegisteredCapability[Any, Any]) -> None:
        capability_id = capability.descriptor.capability_id
        if capability_id in self._registrations:
            raise ValueError(f"Capability '{capability_id}' is already registered.")
        self._registrations[capability_id] = capability

    def get(self, capability_id: str) -> RegisteredCapability[Any, Any] | None:
        return self._registrations.get(capability_id)

    def descriptors(self) -> tuple[CapabilityDescriptor, ...]:
        return tuple(
            registration.descriptor
            for _, registration in sorted(self._registrations.items())
        )
