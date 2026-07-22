from __future__ import annotations

import pytest

from optees.application.contracts.artifact import ArtifactFormat, AvailableArtifact
from optees.application.contracts.capability import CapabilityDescriptor
from optees.application.contracts.execution import (
    MathematicalStatus,
    SerializedResult,
)
from optees.application.services.capability_registry import (
    CapabilityRegistry,
    RegisteredCapability,
)


def _registration(capability_id: str) -> RegisteredCapability[dict, dict]:
    descriptor = CapabilityDescriptor(
        capability_id=capability_id,
        title=capability_id,
        problem_type="test",
        input_schema={"type": "object"},
        result_schema={"type": "object"},
    )
    return RegisteredCapability(
        descriptor=descriptor,
        parse_problem=lambda payload: payload,
        execute=lambda model: model,
        serialize_result=lambda result: SerializedResult(
            mathematical_status=MathematicalStatus.OPTIMAL,
            result=result,
        ),
        backend_id="test.backend",
    )


def test_registry_lists_descriptors_in_stable_capability_id_order():
    registry = CapabilityRegistry()
    registry.register(_registration("z.last"))
    registry.register(_registration("a.first"))

    assert [item.capability_id for item in registry.descriptors()] == [
        "a.first",
        "z.last",
    ]


def test_registry_rejects_duplicate_capability_ids():
    registry = CapabilityRegistry()
    registry.register(_registration("lp.continuous"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_registration("lp.continuous"))


def test_unavailable_descriptor_requires_a_reason():
    with pytest.raises(ValueError, match="unavailable_reason is required"):
        CapabilityDescriptor(
            capability_id="test.unavailable",
            title="Unavailable",
            problem_type="test",
            input_schema={},
            result_schema={},
            available=False,
        )


def test_descriptor_advertises_artifacts_without_affecting_existing_defaults():
    plain = _registration("test.plain").descriptor
    descriptor = CapabilityDescriptor(
        capability_id="test.artifacts",
        title="Artifacts",
        problem_type="test",
        input_schema={},
        result_schema={},
        available_artifacts=(
            AvailableArtifact(
                artifact_type="solution_table",
                title="Solution table",
                formats=(ArtifactFormat.JSON,),
            ),
        ),
    )

    assert plain.to_dict()["available_artifacts"] == []
    assert descriptor.to_dict()["available_artifacts"][0]["artifact_type"] == (
        "solution_table"
    )


def test_cancellable_descriptor_requires_an_executable_callback():
    descriptor = CapabilityDescriptor(
        capability_id="test.cancellable",
        title="Cancellable",
        problem_type="test",
        input_schema={},
        result_schema={},
        supports_cancellation=True,
    )

    with pytest.raises(ValueError, match="cancellation callback"):
        RegisteredCapability(
            descriptor=descriptor,
            parse_problem=lambda payload: payload,
            execute=lambda model: model,
            serialize_result=lambda result: SerializedResult(
                mathematical_status=MathematicalStatus.OPTIMAL,
                result=result,
            ),
            backend_id="test.backend",
        )
