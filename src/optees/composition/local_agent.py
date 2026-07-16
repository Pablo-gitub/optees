from __future__ import annotations

from importlib.util import find_spec

from optees.application.codecs.lp_result_codec import LPResultCodec
from optees.application.contracts.capability import CapabilityDescriptor
from optees.application.ports.lp_solver_port import LPSolverPort
from optees.application.services.capability_registry import (
    CapabilityRegistry,
    RegisteredCapability,
)
from optees.application.services.optimization_service import OptimizationService
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from optees.data.adapters.lp.lp_solver_adapter import LPSolverAdapter
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.models.lp.lp_model import LPModel
from optees.utility.lp_json_io import lp_model_from_dict


LP_CAPABILITY_ID = "lp.continuous"
LP_BACKEND_ID = "scipy.highs"


def create_local_optimization_service() -> OptimizationService:
    """Build the production in-process service without importing presentation code."""

    return create_lp_optimization_service(
        solver_port=LPSolverAdapter(),
        dependency_available=find_spec("scipy") is not None,
    )


def create_lp_optimization_service(
    *,
    solver_port: LPSolverPort,
    dependency_available: bool = True,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(
        create_lp_registration(
            solver_port=solver_port,
            dependency_available=dependency_available,
        )
    )
    return OptimizationService(registry)


def create_lp_registration(
    *,
    solver_port: LPSolverPort,
    dependency_available: bool = True,
) -> RegisteredCapability[LPModel, LPSolution]:
    use_case = SolveLPUseCase(solver_port)
    codec = LPResultCodec()
    return RegisteredCapability(
        descriptor=_lp_descriptor(dependency_available=dependency_available),
        parse_problem=lp_model_from_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=LP_BACKEND_ID,
    )


def _lp_descriptor(*, dependency_available: bool) -> CapabilityDescriptor:
    unavailable_reason = (
        None
        if dependency_available
        else "SciPy is required by the continuous LP backend."
    )
    return CapabilityDescriptor(
        capability_id=LP_CAPABILITY_ID,
        title="Continuous linear programming",
        problem_type="linear_programming",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_lp_input_schema(),
        result_schema=_lp_result_schema(),
        default_options={"method": "highs"},
        available=dependency_available,
        unavailable_reason=unavailable_reason,
        backend_candidates=(LP_BACKEND_ID,),
        supports_time_limit=False,
        supports_cancellation=False,
    )


def _lp_input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["version", "variables", "objective", "constraints"],
        "properties": {
            "version": {"const": "1"},
            "variables": {"type": "array", "minItems": 1},
            "objective": {"type": "object"},
            "constraints": {"type": "array"},
        },
    }


def _lp_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["objective", "variables", "optimal_face"],
        "properties": {
            "objective": {"type": ["number", "null"]},
            "objective_sense": {"type": ["string", "null"]},
            "variables": {"type": "array"},
            "optimal_face": {"type": "object"},
        },
    }
