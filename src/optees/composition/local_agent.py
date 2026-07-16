from __future__ import annotations

from importlib.util import find_spec

from optees.application.codecs.knapsack_bounded_problem_codec import (
    knapsack_bounded_model_from_dict,
)
from optees.application.codecs.knapsack_bounded_result_codec import (
    KnapsackBoundedResultCodec,
)
from optees.application.codecs.knapsack_fractional_problem_codec import (
    knapsack_fractional_model_from_dict,
)
from optees.application.codecs.knapsack_fractional_result_codec import (
    KnapsackFractionalResultCodec,
)
from optees.application.codecs.knapsack_unbounded_problem_codec import (
    knapsack_unbounded_model_from_dict,
)
from optees.application.codecs.knapsack_unbounded_result_codec import (
    KnapsackUnboundedResultCodec,
)
from optees.application.codecs.knapsack_zero_one_problem_codec import (
    knapsack_zero_one_model_from_dict,
)
from optees.application.codecs.knapsack_zero_one_result_codec import (
    KnapsackZeroOneResultCodec,
)
from optees.application.codecs.lp_result_codec import LPResultCodec
from optees.application.contracts.capability import CapabilityDescriptor
from optees.application.ports.bounded_knapsack_solver_port import (
    BoundedKnapsackSolverPort,
)
from optees.application.ports.fractional_knapsack_solver_port import (
    FractionalKnapsackSolverPort,
)
from optees.application.ports.knapsack_solver_port import KnapsackSolverPort
from optees.application.ports.lp_solver_port import LPSolverPort
from optees.application.ports.unbounded_knapsack_solver_port import (
    UnboundedKnapsackSolverPort,
)
from optees.application.services.capability_registry import (
    CapabilityRegistry,
    RegisteredCapability,
)
from optees.application.services.optimization_service import OptimizationService
from optees.application.usecases.solve_bounded_knapsack_usecase import (
    SolveBoundedKnapsackUseCase,
)
from optees.application.usecases.solve_fractional_knapsack_usecase import (
    SolveFractionalKnapsackUseCase,
)
from optees.application.usecases.solve_knapsack_usecase import SolveKnapsackUseCase
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from optees.application.usecases.solve_unbounded_knapsack_usecase import (
    SolveUnboundedKnapsackUseCase,
)
from optees.data.adapters.knapsack.bounded_knapsack_solver_adapter import (
    BoundedKnapsackSolverAdapter,
)
from optees.data.adapters.knapsack.fractional_knapsack_solver_adapter import (
    FractionalKnapsackSolverAdapter,
)
from optees.data.adapters.knapsack.knapsack_solver_adapter import KnapsackSolverAdapter
from optees.data.adapters.knapsack.unbounded_knapsack_solver_adapter import (
    UnboundedKnapsackSolverAdapter,
)
from optees.data.adapters.lp.lp_solver_adapter import LPSolverAdapter
from optees.domain.entities.knapsack.bounded_solution import BoundedKnapsackSolution
from optees.domain.entities.knapsack.fractional_solution import (
    FractionalKnapsackSolution,
)
from optees.domain.entities.knapsack.solution import KnapsackSolution
from optees.domain.entities.knapsack.unbounded_solution import (
    UnboundedKnapsackSolution,
)
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.models.knapsack.bounded_knapsack_model import BoundedKnapsackModel
from optees.domain.models.knapsack.fractional_knapsack_model import (
    FractionalKnapsackModel,
)
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model
from optees.domain.models.knapsack.unbounded_knapsack_model import (
    UnboundedKnapsackModel,
)
from optees.domain.models.lp.lp_model import LPModel
from optees.utility.lp_json_io import lp_model_from_dict


LP_CAPABILITY_ID = "lp.continuous"
LP_BACKEND_ID = "scipy.highs"
KNAPSACK_ZERO_ONE_CAPABILITY_ID = "knapsack.zero_one"
KNAPSACK_ZERO_ONE_BACKEND_ID = "internal.dynamic_programming"
KNAPSACK_BOUNDED_CAPABILITY_ID = "knapsack.bounded"
KNAPSACK_BOUNDED_BACKEND_ID = "internal.bounded_dynamic_programming"
KNAPSACK_UNBOUNDED_CAPABILITY_ID = "knapsack.unbounded"
KNAPSACK_UNBOUNDED_BACKEND_ID = "internal.unbounded_dynamic_programming"
KNAPSACK_FRACTIONAL_CAPABILITY_ID = "knapsack.fractional"
KNAPSACK_FRACTIONAL_BACKEND_ID = "internal.fractional_greedy_density"


def create_local_optimization_service() -> OptimizationService:
    """Build the production in-process service without importing presentation code."""

    registry = CapabilityRegistry()
    registry.register(
        create_lp_registration(
            solver_port=LPSolverAdapter(),
            dependency_available=find_spec("scipy") is not None,
        )
    )
    registry.register(
        create_knapsack_zero_one_registration(
            solver_port=KnapsackSolverAdapter(),
        )
    )
    registry.register(
        create_knapsack_bounded_registration(
            solver_port=BoundedKnapsackSolverAdapter(),
        )
    )
    registry.register(
        create_knapsack_unbounded_registration(
            solver_port=UnboundedKnapsackSolverAdapter(),
        )
    )
    registry.register(
        create_knapsack_fractional_registration(
            solver_port=FractionalKnapsackSolverAdapter(),
        )
    )
    return OptimizationService(registry)


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


def create_knapsack_zero_one_optimization_service(
    *,
    solver_port: KnapsackSolverPort,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(
        create_knapsack_zero_one_registration(solver_port=solver_port)
    )
    return OptimizationService(registry)


def create_knapsack_zero_one_registration(
    *,
    solver_port: KnapsackSolverPort,
) -> RegisteredCapability[Knapsack01Model, KnapsackSolution]:
    use_case = SolveKnapsackUseCase(solver_port)
    codec = KnapsackZeroOneResultCodec()
    return RegisteredCapability(
        descriptor=_knapsack_zero_one_descriptor(),
        parse_problem=knapsack_zero_one_model_from_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=KNAPSACK_ZERO_ONE_BACKEND_ID,
    )


def create_knapsack_bounded_optimization_service(
    *,
    solver_port: BoundedKnapsackSolverPort,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(create_knapsack_bounded_registration(solver_port=solver_port))
    return OptimizationService(registry)


def create_knapsack_bounded_registration(
    *,
    solver_port: BoundedKnapsackSolverPort,
) -> RegisteredCapability[BoundedKnapsackModel, BoundedKnapsackSolution]:
    use_case = SolveBoundedKnapsackUseCase(solver_port)
    codec = KnapsackBoundedResultCodec()
    return RegisteredCapability(
        descriptor=_knapsack_bounded_descriptor(),
        parse_problem=knapsack_bounded_model_from_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=KNAPSACK_BOUNDED_BACKEND_ID,
    )


def create_knapsack_unbounded_optimization_service(
    *,
    solver_port: UnboundedKnapsackSolverPort,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(create_knapsack_unbounded_registration(solver_port=solver_port))
    return OptimizationService(registry)


def create_knapsack_unbounded_registration(
    *,
    solver_port: UnboundedKnapsackSolverPort,
) -> RegisteredCapability[UnboundedKnapsackModel, UnboundedKnapsackSolution]:
    use_case = SolveUnboundedKnapsackUseCase(solver_port)
    codec = KnapsackUnboundedResultCodec()
    return RegisteredCapability(
        descriptor=_knapsack_unbounded_descriptor(),
        parse_problem=knapsack_unbounded_model_from_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=KNAPSACK_UNBOUNDED_BACKEND_ID,
    )


def create_knapsack_fractional_optimization_service(
    *,
    solver_port: FractionalKnapsackSolverPort,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(create_knapsack_fractional_registration(solver_port=solver_port))
    return OptimizationService(registry)


def create_knapsack_fractional_registration(
    *,
    solver_port: FractionalKnapsackSolverPort,
) -> RegisteredCapability[FractionalKnapsackModel, FractionalKnapsackSolution]:
    use_case = SolveFractionalKnapsackUseCase(solver_port)
    codec = KnapsackFractionalResultCodec()
    return RegisteredCapability(
        descriptor=_knapsack_fractional_descriptor(),
        parse_problem=knapsack_fractional_model_from_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=KNAPSACK_FRACTIONAL_BACKEND_ID,
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


def _knapsack_zero_one_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=KNAPSACK_ZERO_ONE_CAPABILITY_ID,
        title="0/1 Knapsack",
        problem_type="knapsack",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_knapsack_zero_one_input_schema(),
        result_schema=_knapsack_zero_one_result_schema(),
        default_options={},
        available=True,
        backend_candidates=(KNAPSACK_ZERO_ONE_BACKEND_ID,),
        supports_time_limit=False,
        supports_cancellation=False,
    )


def _knapsack_zero_one_input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["version", "problem_type", "variant", "capacity", "items"],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "knapsack"},
            "variant": {"enum": ["zero_one", "0/1", "binary"]},
            "capacity": {"type": "integer", "minimum": 0},
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "value", "weight"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "value": {"type": "number", "minimum": 0},
                        "weight": {"type": "integer", "minimum": 0},
                    },
                },
            },
        },
    }


def _knapsack_zero_one_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "objective",
            "selected_indices",
            "selected_items",
            "total_value",
            "total_weight",
            "remaining_capacity",
        ],
        "properties": {
            "objective": {"type": ["number", "null"]},
            "selected_indices": {"type": "array", "items": {"type": "integer"}},
            "selected_items": {"type": "array"},
            "total_value": {"type": "number"},
            "total_weight": {"type": "integer"},
            "remaining_capacity": {"type": ["integer", "null"]},
        },
    }


def _knapsack_bounded_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=KNAPSACK_BOUNDED_CAPABILITY_ID,
        title="Bounded Knapsack",
        problem_type="knapsack",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_knapsack_bounded_input_schema(),
        result_schema=_knapsack_bounded_result_schema(),
        default_options={},
        available=True,
        backend_candidates=(KNAPSACK_BOUNDED_BACKEND_ID,),
        supports_time_limit=False,
        supports_cancellation=False,
    )


def _knapsack_bounded_input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["version", "problem_type", "variant", "capacity", "items"],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "knapsack"},
            "variant": {"const": "bounded"},
            "capacity": {"type": "integer", "minimum": 0},
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "value", "weight", "max_quantity"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "value": {"type": "number", "minimum": 0},
                        "weight": {"type": "integer", "minimum": 0},
                        "max_quantity": {"type": "integer", "minimum": 0},
                    },
                },
            },
        },
    }


def _knapsack_bounded_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "objective",
            "quantities",
            "selected_indices",
            "selected_items",
            "total_value",
            "total_weight",
            "remaining_capacity",
        ],
        "properties": {
            "objective": {"type": ["number", "null"]},
            "quantities": {"type": "array", "items": {"type": "integer"}},
            "selected_indices": {"type": "array", "items": {"type": "integer"}},
            "selected_items": {"type": "array"},
            "total_value": {"type": "number"},
            "total_weight": {"type": "integer"},
            "remaining_capacity": {"type": ["integer", "null"]},
        },
    }


def _knapsack_unbounded_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=KNAPSACK_UNBOUNDED_CAPABILITY_ID,
        title="Unbounded Knapsack",
        problem_type="knapsack",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_knapsack_unbounded_input_schema(),
        result_schema=_knapsack_unbounded_result_schema(),
        default_options={},
        available=True,
        backend_candidates=(KNAPSACK_UNBOUNDED_BACKEND_ID,),
        supports_time_limit=False,
        supports_cancellation=False,
    )


def _knapsack_unbounded_input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["version", "problem_type", "variant", "capacity", "items"],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "knapsack"},
            "variant": {"const": "unbounded"},
            "capacity": {"type": "integer", "minimum": 0},
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "value", "weight"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "value": {"type": "number", "minimum": 0},
                        "weight": {"type": "integer", "minimum": 0},
                    },
                },
            },
        },
    }


def _knapsack_unbounded_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "objective",
            "quantities",
            "selected_indices",
            "selected_items",
            "total_value",
            "total_weight",
            "remaining_capacity",
        ],
        "properties": {
            "objective": {"type": ["number", "null"]},
            "quantities": {"type": "array", "items": {"type": "integer"}},
            "selected_indices": {"type": "array", "items": {"type": "integer"}},
            "selected_items": {"type": "array"},
            "total_value": {"type": "number"},
            "total_weight": {"type": "integer"},
            "remaining_capacity": {"type": ["integer", "null"]},
        },
    }


def _knapsack_fractional_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=KNAPSACK_FRACTIONAL_CAPABILITY_ID,
        title="Fractional Knapsack",
        problem_type="knapsack",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_knapsack_fractional_input_schema(),
        result_schema=_knapsack_fractional_result_schema(),
        default_options={},
        available=True,
        backend_candidates=(KNAPSACK_FRACTIONAL_BACKEND_ID,),
        supports_time_limit=False,
        supports_cancellation=False,
    )


def _knapsack_fractional_input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["version", "problem_type", "variant", "capacity", "items"],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "knapsack"},
            "variant": {"const": "fractional"},
            "capacity": {"type": "number", "minimum": 0},
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "value", "weight"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "value": {"type": "number", "minimum": 0},
                        "weight": {"type": "number", "exclusiveMinimum": 0},
                    },
                },
            },
        },
    }


def _knapsack_fractional_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "objective",
            "fractions",
            "selected_indices",
            "selected_items",
            "total_value",
            "total_weight",
            "remaining_capacity",
        ],
        "properties": {
            "objective": {"type": ["number", "null"]},
            "fractions": {
                "type": "array",
                "items": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "selected_indices": {"type": "array", "items": {"type": "integer"}},
            "selected_items": {"type": "array"},
            "total_value": {"type": "number"},
            "total_weight": {"type": "number"},
            "remaining_capacity": {"type": ["number", "null"]},
        },
    }
