from __future__ import annotations

from pathlib import Path

from optees.application.codecs.knapsack_bounded_problem_codec import (
    knapsack_bounded_model_from_dict,
)
from optees.application.codecs.classification_problem_codec import (
    classification_model_from_public_dict,
)
from optees.application.codecs.classification_result_codec import (
    ClassificationResultCodec,
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
from optees.application.codecs.knapsack_multi_dimensional_problem_codec import (
    knapsack_multi_dimensional_request_from_dict,
)
from optees.application.codecs.knapsack_multi_dimensional_result_codec import (
    KnapsackMultiDimensionalResultCodec,
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
from optees.application.codecs.milp_problem_codec import milp_model_from_public_dict
from optees.application.codecs.milp_result_codec import MILPResultCodec
from optees.application.codecs.nlp_problem_codec import nlp_model_from_public_dict
from optees.application.codecs.nlp_result_codec import NLPResultCodec
from optees.application.codecs.packing_problem_codec import (
    packing_model_from_public_dict,
)
from optees.application.codecs.packing_result_codec import PackingResultCodec
from optees.application.codecs.regression_problem_codec import (
    regression_model_from_public_dict,
)
from optees.application.codecs.regression_result_codec import RegressionResultCodec
from optees.application.codecs.shortest_path_problem_codec import (
    shortest_path_model_from_public_dict,
)
from optees.application.codecs.shortest_path_result_codec import (
    ShortestPathResultCodec,
)
from optees.application.contracts.artifact import (
    ArtifactFormat,
    AvailableArtifact,
)
from optees.application.contracts.capability import CapabilityDescriptor
from optees.application.dtos.multi_dimensional_knapsack_dtos import (
    MultiDimensionalKnapsackRequest,
)
from optees.application.ports.bounded_knapsack_solver_port import (
    BoundedKnapsackSolverPort,
)
from optees.application.ports.classification_solver_port import (
    ClassificationSolverPort,
)
from optees.application.ports.fractional_knapsack_solver_port import (
    FractionalKnapsackSolverPort,
)
from optees.application.ports.knapsack_solver_port import KnapsackSolverPort
from optees.application.ports.lp_solver_port import LPSolverPort
from optees.application.ports.milp_solver_port import MILPSolverPort
from optees.application.ports.multi_dimensional_knapsack_solver_port import (
    MultiDimensionalKnapsackSolverPort,
)
from optees.application.ports.nlp_solver_port import NLPSolverPort
from optees.application.ports.packing_solver_port import PackingSolverPort
from optees.application.ports.regression_solver_port import RegressionSolverPort
from optees.application.ports.shortest_path_solver_port import ShortestPathSolverPort
from optees.application.ports.unbounded_knapsack_solver_port import (
    UnboundedKnapsackSolverPort,
)
from optees.application.services.capability_registry import (
    CapabilityRegistry,
    RegisteredCapability,
)
from optees.application.services.artifact_generation_service import (
    ArtifactGenerationService,
    ArtifactRendererRegistration,
)
from optees.application.services.analytic_artifact_visuals import (
    analytic_visual_definitions,
    analytic_visual_descriptors,
)
from optees.application.services.canonical_artifact_tables import (
    canonical_table_definitions,
    canonical_table_definitions_for,
)
from optees.application.services.categorical_artifact_visuals import (
    categorical_visual_definitions,
    categorical_visual_descriptors,
)
from optees.application.services.lp_artifact_visuals import (
    lp_visual_definitions,
    lp_visual_descriptors,
)
from optees.application.services.packing_artifact_scene import (
    packing_scene_definitions,
    packing_scene_descriptors,
)
from optees.application.services.optimization_service import OptimizationService
from optees.application.services.local_job_service import LocalJobService
from optees.application.services.report_composition_service import (
    ReportCompositionService,
)
from optees.application.validation.lp_solution_validator import (
    LPIndependentSolutionValidator,
)
from optees.application.validation.milp_solution_validator import (
    MILPIndependentSolutionValidator,
)
from optees.application.validation.regression_solution_validator import (
    RegressionIndependentSolutionValidator,
)
from optees.application.usecases.solve_bounded_knapsack_usecase import (
    SolveBoundedKnapsackUseCase,
)
from optees.application.usecases.solve_fractional_knapsack_usecase import (
    SolveFractionalKnapsackUseCase,
)
from optees.application.usecases.solve_knapsack_usecase import SolveKnapsackUseCase
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from optees.application.usecases.solve_milp_usecase import SolveMILPUseCase
from optees.application.usecases.solve_multi_dimensional_knapsack_capability_usecase import (
    MultiDimensionalResult,
    SolveMultiDimensionalKnapsackCapabilityUseCase,
)
from optees.application.usecases.solve_nlp_usecase import SolveNLPUseCase
from optees.application.usecases.solve_single_container_packing_usecase import (
    SolveSingleContainerPackingUseCase,
)
from optees.application.usecases.solve_shortest_path_usecase import (
    SolveShortestPathUseCase,
)
from optees.application.usecases.solve_unbounded_knapsack_usecase import (
    SolveUnboundedKnapsackUseCase,
)
from optees.application.usecases.train_classification_usecase import (
    TrainClassificationUseCase,
)
from optees.application.usecases.train_regression_usecase import (
    TrainRegressionUseCase,
)
from optees.composition.backend_health import (
    import_is_usable,
    scipy_highs_is_usable,
)
from optees.data.adapters.classification.numpy_classification_adapter import (
    NumpyClassificationAdapter,
)
from optees.data.adapters.graph.dijkstra_solver_adapter import DijkstraSolverAdapter
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
from optees.data.adapters.knapsack.multi_dimensional_knapsack_solver_adapter import (
    MultiDimensionalKnapsackSolverAdapter,
)
from optees.data.adapters.lp.lp_solver_adapter import LPSolverAdapter
from optees.data.adapters.milp.milp_solver_adapter import MILPSolverAdapter
from optees.data.adapters.nlp.nlp_solver_adapter import ScipyNLPSolverAdapter
from optees.data.adapters.packing.ortools_single_container_packing_adapter import (
    OrtoolsSingleContainerPackingAdapter,
)
from optees.data.adapters.regression.numpy_regression_adapter import (
    NumpyRegressionAdapter,
)
from optees.domain.entities.classification.solution import ClassificationSolution
from optees.domain.entities.graph.solution import ShortestPathSolution
from optees.domain.entities.knapsack.bounded_solution import BoundedKnapsackSolution
from optees.domain.entities.knapsack.fractional_solution import (
    FractionalKnapsackSolution,
)
from optees.domain.entities.knapsack.solution import KnapsackSolution
from optees.domain.entities.knapsack.unbounded_solution import (
    UnboundedKnapsackSolution,
)
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.entities.milp.solution import MILPSolution
from optees.domain.entities.nlp.solution import NLPSolution
from optees.domain.entities.packing.solution import PackingSolveResult
from optees.domain.entities.regression.solution import RegressionSolution
from optees.domain.models.classification.binary_classification_model import (
    BinaryClassificationModel,
)
from optees.domain.models.graph.shortest_path_model import ShortestPathModel
from optees.domain.models.knapsack.bounded_knapsack_model import BoundedKnapsackModel
from optees.domain.models.knapsack.fractional_knapsack_model import (
    FractionalKnapsackModel,
)
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model
from optees.domain.models.knapsack.unbounded_knapsack_model import (
    UnboundedKnapsackModel,
)
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.models.nlp.nlp_model import NLPModel
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.domain.models.regression.regression_model import RegressionModel
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
KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID = "knapsack.multi_dimensional"
KNAPSACK_MULTI_DIMENSIONAL_ROUTER_ID = "optees.multidimensional_router"
KNAPSACK_MULTI_DIMENSIONAL_BACKEND_IDS = (
    "internal.multidimensional_branch_and_bound",
    "ortools.linear_mixed_integer",
)
MILP_CAPABILITY_ID = "milp.linear"
MILP_ROUTER_ID = "optees.milp_router"
MILP_BACKEND_IDS = ("ortools.cbc", "ortools.cp_sat")
DIJKSTRA_CAPABILITY_ID = "graph.shortest_path.dijkstra"
DIJKSTRA_BACKEND_ID = "internal.dijkstra_heap"
NLP_CAPABILITY_ID = "nlp.continuous_local"
NLP_BACKEND_ID = "scipy.optimize.minimize"
REGRESSION_CAPABILITY_ID = "ml.regression.linear"
REGRESSION_BACKEND_ID = "numpy.linear_least_squares"
CLASSIFICATION_CAPABILITY_ID = "ml.classification.binary_logistic"
CLASSIFICATION_BACKEND_ID = "numpy.logistic_gradient_descent"
PACKING_CAPABILITY_ID = "packing.single_container_3d"
PACKING_ROUTER_ID = "optees.single_container_packing_router"
PACKING_BACKEND_IDS = ("ortools.scip", "ortools.cbc")


def create_local_optimization_service() -> OptimizationService:
    """Build the production in-process service without importing presentation code."""

    registry = CapabilityRegistry()
    registry.register(
        create_lp_registration(
            solver_port=LPSolverAdapter(),
            dependency_available=scipy_highs_is_usable(),
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
    registry.register(
        create_knapsack_multi_dimensional_registration(
            binary_solver_port=MultiDimensionalKnapsackSolverAdapter(),
            milp_solver_port=MILPSolverAdapter(),
        )
    )
    registry.register(
        create_milp_registration(
            solver_port=MILPSolverAdapter(),
            dependency_available=import_is_usable("ortools"),
        )
    )
    registry.register(
        create_dijkstra_registration(solver_port=DijkstraSolverAdapter())
    )
    registry.register(
        create_nlp_registration(
            solver_port=ScipyNLPSolverAdapter(),
            dependency_available=import_is_usable("scipy.optimize", "minimize"),
        )
    )
    registry.register(
        create_regression_registration(
            solver_port=NumpyRegressionAdapter(),
            dependency_available=import_is_usable("numpy", "linalg"),
        )
    )
    registry.register(
        create_classification_registration(
            solver_port=NumpyClassificationAdapter(),
            dependency_available=import_is_usable("numpy", "linalg"),
        )
    )
    registry.register(
        create_packing_registration(
            solver_port=OrtoolsSingleContainerPackingAdapter(),
            dependency_available=import_is_usable("ortools"),
        )
    )
    return OptimizationService(registry)


def create_local_job_service(*, capacity: int = 100) -> LocalJobService:
    from optees.application.services.job_repository import InMemoryJobRepository

    return LocalJobService(
        create_local_optimization_service(),
        repository=InMemoryJobRepository(capacity=capacity),
    )


def create_local_artifact_service(
    job_service: LocalJobService,
) -> ArtifactGenerationService:
    """Build session-local artifact orchestration with canonical result tables."""

    from optees.data.adapters.artifacts.canonical_table_renderer import (
        CanonicalTableRenderer,
    )
    from optees.data.adapters.artifacts.analytic_chart_renderer import (
        AnalyticChartRenderer,
    )
    from optees.data.adapters.artifacts.categorical_chart_renderer import (
        CategoricalChartRenderer,
    )
    from optees.data.adapters.artifacts.local_artifact_store import LocalArtifactStore
    from optees.data.adapters.artifacts.lp_feasible_region_renderer import (
        LPFeasibleRegionRenderer,
    )
    from optees.data.adapters.artifacts.packing_scene_renderer import (
        PackingSceneRenderer,
    )

    table_registrations = tuple(
        ArtifactRendererRegistration(
            capability_id=definition.capability_id,
            descriptor=definition.descriptor(),
            renderer=CanonicalTableRenderer(definition.builder),
            media_types={
                ArtifactFormat.JSON: "application/json",
                ArtifactFormat.CSV: "text/csv; charset=utf-8",
                ArtifactFormat.MARKDOWN: "text/markdown; charset=utf-8",
            },
        )
        for definition in canonical_table_definitions()
    )
    visual_registrations = tuple(
        ArtifactRendererRegistration(
            capability_id=definition.capability_id,
            descriptor=definition.descriptor(),
            renderer=LPFeasibleRegionRenderer(),
            media_types={
                ArtifactFormat.SVG: "image/svg+xml",
                ArtifactFormat.PNG: "image/png",
            },
        )
        for definition in lp_visual_definitions()
    )
    categorical_registrations = tuple(
        ArtifactRendererRegistration(
            capability_id=definition.capability_id,
            descriptor=definition.descriptor(),
            renderer=CategoricalChartRenderer(definition),
            media_types={
                ArtifactFormat.SVG: "image/svg+xml",
                ArtifactFormat.PNG: "image/png",
            },
        )
        for definition in categorical_visual_definitions()
    )
    analytic_registrations = tuple(
        ArtifactRendererRegistration(
            capability_id=definition.capability_id,
            descriptor=definition.descriptor(),
            renderer=AnalyticChartRenderer(definition),
            media_types={
                ArtifactFormat.SVG: "image/svg+xml",
                ArtifactFormat.PNG: "image/png",
            },
        )
        for definition in analytic_visual_definitions()
    )
    packing_registrations = tuple(
        ArtifactRendererRegistration(
            capability_id=definition.capability_id,
            descriptor=definition.descriptor(),
            renderer=PackingSceneRenderer(),
            media_types={
                format_: (
                    "image/png"
                    if format_ is ArtifactFormat.PNG
                    else "application/zip"
                )
                for format_ in definition.formats
            },
        )
        for definition in packing_scene_definitions()
    )
    return ArtifactGenerationService(
        job_service,
        LocalArtifactStore(),
        registrations=(
            table_registrations
            + visual_registrations
            + categorical_registrations
            + analytic_registrations
            + packing_registrations
        ),
    )


def create_local_report_service(
    job_service: LocalJobService,
    artifact_service: ArtifactGenerationService,
) -> ReportCompositionService:
    """Build bounded session-local Markdown/PDF report composition."""

    from optees.data.adapters.artifacts.local_artifact_store import LocalArtifactStore
    from optees.data.adapters.reports.pandoc_typst_report_backend import (
        PandocTypstReportBackend,
    )
    from optees.data.adapters.reports.validated_report_asset_converter import (
        ValidatedReportAssetConverter,
    )
    from optees.core.assets import asset

    report_output_bytes = 64 * 1024 * 1024
    return ReportCompositionService(
        job_service,
        artifact_service,
        LocalArtifactStore(
            max_artifact_bytes=report_output_bytes,
            max_total_bytes=256 * 1024 * 1024,
            max_artifacts=64,
        ),
        backend=PandocTypstReportBackend(
            template_path=Path(asset("reports/optees.typst")),
        ),
        asset_converter=ValidatedReportAssetConverter(),
    )


def _available_artifacts(capability_id: str) -> tuple[AvailableArtifact, ...]:
    tables = tuple(
        definition.descriptor()
        for definition in canonical_table_definitions_for(capability_id)
    )
    return (
        tables
        + lp_visual_descriptors(capability_id)
        + categorical_visual_descriptors(capability_id)
        + analytic_visual_descriptors(capability_id)
        + packing_scene_descriptors(capability_id)
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
        validate_result=LPIndependentSolutionValidator(),
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


def create_knapsack_multi_dimensional_optimization_service(
    *,
    binary_solver_port: MultiDimensionalKnapsackSolverPort,
    milp_solver_port: MILPSolverPort,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(
        create_knapsack_multi_dimensional_registration(
            binary_solver_port=binary_solver_port,
            milp_solver_port=milp_solver_port,
        )
    )
    return OptimizationService(registry)


def create_knapsack_multi_dimensional_registration(
    *,
    binary_solver_port: MultiDimensionalKnapsackSolverPort,
    milp_solver_port: MILPSolverPort,
) -> RegisteredCapability[MultiDimensionalKnapsackRequest, MultiDimensionalResult]:
    use_case = SolveMultiDimensionalKnapsackCapabilityUseCase(
        binary_solver_port,
        milp_solver_port,
    )
    codec = KnapsackMultiDimensionalResultCodec()
    return RegisteredCapability(
        descriptor=_knapsack_multi_dimensional_descriptor(),
        parse_problem=knapsack_multi_dimensional_request_from_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=KNAPSACK_MULTI_DIMENSIONAL_ROUTER_ID,
    )


def create_milp_optimization_service(
    *,
    solver_port: MILPSolverPort,
    dependency_available: bool = True,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(
        create_milp_registration(
            solver_port=solver_port,
            dependency_available=dependency_available,
        )
    )
    return OptimizationService(registry)


def create_milp_registration(
    *,
    solver_port: MILPSolverPort,
    dependency_available: bool,
) -> RegisteredCapability[MILPModel, MILPSolution]:
    use_case = SolveMILPUseCase(solver_port)
    codec = MILPResultCodec()
    return RegisteredCapability(
        descriptor=_milp_descriptor(dependency_available=dependency_available),
        parse_problem=milp_model_from_public_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=MILP_ROUTER_ID,
        validate_result=MILPIndependentSolutionValidator(),
    )


def create_dijkstra_optimization_service(
    *,
    solver_port: ShortestPathSolverPort,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(create_dijkstra_registration(solver_port=solver_port))
    return OptimizationService(registry)


def create_dijkstra_registration(
    *,
    solver_port: ShortestPathSolverPort,
) -> RegisteredCapability[ShortestPathModel, ShortestPathSolution]:
    use_case = SolveShortestPathUseCase(solver_port)
    codec = ShortestPathResultCodec()
    return RegisteredCapability(
        descriptor=_dijkstra_descriptor(),
        parse_problem=shortest_path_model_from_public_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=DIJKSTRA_BACKEND_ID,
    )


def create_nlp_optimization_service(
    *,
    solver_port: NLPSolverPort,
    dependency_available: bool = True,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(
        create_nlp_registration(
            solver_port=solver_port,
            dependency_available=dependency_available,
        )
    )
    return OptimizationService(registry)


def create_nlp_registration(
    *,
    solver_port: NLPSolverPort,
    dependency_available: bool,
) -> RegisteredCapability[NLPModel, NLPSolution]:
    use_case = SolveNLPUseCase(solver_port)
    codec = NLPResultCodec()
    return RegisteredCapability(
        descriptor=_nlp_descriptor(dependency_available=dependency_available),
        parse_problem=nlp_model_from_public_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=NLP_BACKEND_ID,
    )


def create_regression_optimization_service(
    *,
    solver_port: RegressionSolverPort,
    dependency_available: bool = True,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(
        create_regression_registration(
            solver_port=solver_port,
            dependency_available=dependency_available,
        )
    )
    return OptimizationService(registry)


def create_regression_registration(
    *,
    solver_port: RegressionSolverPort,
    dependency_available: bool,
) -> RegisteredCapability[RegressionModel, RegressionSolution]:
    use_case = TrainRegressionUseCase(solver_port)
    codec = RegressionResultCodec()
    return RegisteredCapability(
        descriptor=_regression_descriptor(
            dependency_available=dependency_available
        ),
        parse_problem=regression_model_from_public_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=REGRESSION_BACKEND_ID,
        validate_result=RegressionIndependentSolutionValidator(),
    )


def create_classification_optimization_service(
    *,
    solver_port: ClassificationSolverPort,
    dependency_available: bool = True,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(
        create_classification_registration(
            solver_port=solver_port,
            dependency_available=dependency_available,
        )
    )
    return OptimizationService(registry)


def create_classification_registration(
    *,
    solver_port: ClassificationSolverPort,
    dependency_available: bool,
) -> RegisteredCapability[BinaryClassificationModel, ClassificationSolution]:
    use_case = TrainClassificationUseCase(solver_port)
    codec = ClassificationResultCodec()
    return RegisteredCapability(
        descriptor=_classification_descriptor(
            dependency_available=dependency_available
        ),
        parse_problem=classification_model_from_public_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=CLASSIFICATION_BACKEND_ID,
    )


def create_packing_optimization_service(
    *,
    solver_port: PackingSolverPort,
    dependency_available: bool = True,
) -> OptimizationService:
    registry = CapabilityRegistry()
    registry.register(
        create_packing_registration(
            solver_port=solver_port,
            dependency_available=dependency_available,
        )
    )
    return OptimizationService(registry)


def create_packing_registration(
    *,
    solver_port: PackingSolverPort,
    dependency_available: bool,
) -> RegisteredCapability[SingleContainerPackingModel, PackingSolveResult]:
    use_case = SolveSingleContainerPackingUseCase(solver_port)
    codec = PackingResultCodec()
    return RegisteredCapability(
        descriptor=_packing_descriptor(dependency_available=dependency_available),
        parse_problem=packing_model_from_public_dict,
        execute=use_case.execute,
        serialize_result=codec.serialize,
        backend_id=PACKING_ROUTER_ID,
        cancel_execution=use_case.cancel,
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
        available_artifacts=_available_artifacts(LP_CAPABILITY_ID),
    )


def _lp_input_schema() -> dict:
    number_or_null = {"type": ["number", "null"]}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["version", "variables", "objective", "constraints"],
        "properties": {
            "version": {
                "const": "1",
                "description": "Continuous LP problem schema version.",
            },
            "variables": {
                "type": "array",
                "minItems": 1,
                "description": (
                    "Decision variables in the order used by every coefficient array. "
                    "Use null for an unbounded lower or upper bound."
                ),
                "items": {
                    "type": "object",
                    "required": ["name", "lb", "ub"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "label": {"type": "string"},
                        "lb": number_or_null,
                        "ub": number_or_null,
                    },
                },
            },
            "objective": {
                "type": "object",
                "required": ["sense", "coefficients"],
                "description": (
                    "Linear objective. coefficients must contain exactly one finite "
                    "number per variable, in variables order."
                ),
                "properties": {
                    "sense": {"enum": ["min", "max"]},
                    "coefficients": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "number"},
                    },
                    "offset": {"type": "number", "default": 0},
                },
            },
            "constraints": {
                "type": "array",
                "description": (
                    "Linear constraints. Each coefficients array must contain exactly "
                    "one finite number per variable, in variables order."
                ),
                "items": {
                    "type": "object",
                    "required": ["coefficients", "relation", "rhs"],
                    "properties": {
                        "coefficients": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "number"},
                        },
                        "relation": {"enum": ["<=", "=", ">="]},
                        "rhs": {"type": "number"},
                    },
                },
            },
        },
        "examples": [
            {
                "version": "1",
                "variables": [
                    {"name": "product_a", "label": "Product A", "lb": 0, "ub": 4},
                    {"name": "product_b", "label": "Product B", "lb": 0, "ub": 5},
                ],
                "objective": {
                    "sense": "max",
                    "coefficients": [30, 40],
                    "offset": 0,
                },
                "constraints": [
                    {"coefficients": [2, 4], "relation": "<=", "rhs": 18}
                ],
            }
        ],
    }


def _lp_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["objective", "variables", "optimal_face"],
        "properties": {
            "objective": {"type": ["number", "null"]},
            "objective_sense": {"enum": ["min", "max", None]},
            "variables": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "value"],
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "number"},
                    },
                },
            },
            "optimal_face": {
                "type": "object",
                "description": (
                    "Analysis of all solutions with the reported optimal objective. "
                    "Uniqueness is established only when analysis_status is computed, "
                    "has_alternate_optimum is false, and dimension is zero."
                ),
                "required": [
                    "analysis_status",
                    "has_alternate_optimum",
                    "dimension",
                    "ranges",
                    "varying_variables",
                    "extreme_points",
                    "auxiliary_failures",
                ],
                "properties": {
                    "analysis_status": {
                        "enum": ["computed", "partial", "skipped", "not_available"]
                    },
                    "has_alternate_optimum": {"type": ["boolean", "null"]},
                    "dimension": {"type": ["integer", "null"], "minimum": 0},
                    "ranges": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": [
                                "variable",
                                "minimum",
                                "minimum_unbounded",
                                "maximum",
                                "maximum_unbounded",
                                "width",
                                "width_unbounded",
                                "is_fixed",
                            ],
                            "properties": {
                                "variable": {"type": "string"},
                                "minimum": {"type": ["number", "null"]},
                                "minimum_unbounded": {"type": "boolean"},
                                "maximum": {"type": ["number", "null"]},
                                "maximum_unbounded": {"type": "boolean"},
                                "width": {"type": ["number", "null"]},
                                "width_unbounded": {"type": "boolean"},
                                "is_fixed": {"type": ["boolean", "null"]},
                            },
                        },
                    },
                    "varying_variables": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "extreme_points": {
                        "type": ["object", "null"],
                        "additionalProperties": {
                            "type": "object",
                            "additionalProperties": {"type": "number"},
                        },
                    },
                    "auxiliary_failures": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "range_tolerance": {"type": ["number", "null"]},
                    "skip_reason": {"type": ["string", "null"]},
                },
            },
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
        available_artifacts=_available_artifacts(KNAPSACK_ZERO_ONE_CAPABILITY_ID),
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
        available_artifacts=_available_artifacts(KNAPSACK_BOUNDED_CAPABILITY_ID),
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
        available_artifacts=_available_artifacts(KNAPSACK_UNBOUNDED_CAPABILITY_ID),
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
        available_artifacts=_available_artifacts(KNAPSACK_FRACTIONAL_CAPABILITY_ID),
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


def _knapsack_multi_dimensional_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID,
        title="Multi-dimensional Knapsack",
        problem_type="knapsack",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_knapsack_multi_dimensional_input_schema(),
        result_schema=_knapsack_multi_dimensional_result_schema(),
        default_options={"domain": "zero_one"},
        available=True,
        backend_candidates=KNAPSACK_MULTI_DIMENSIONAL_BACKEND_IDS,
        supports_time_limit=False,
        supports_cancellation=False,
        available_artifacts=_available_artifacts(
            KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID
        ),
    )


def _knapsack_multi_dimensional_input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "version",
            "problem_type",
            "variant",
            "domain",
            "resources",
            "items",
        ],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "knapsack"},
            "variant": {"const": "multi_dimensional"},
            "domain": {
                "enum": ["zero_one", "bounded", "unbounded", "fractional"]
            },
            "resources": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "capacity"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "capacity": {"type": "number", "minimum": 0},
                    },
                },
            },
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "value", "usage"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "value": {"type": "number", "minimum": 0},
                        "usage": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "number", "minimum": 0},
                        },
                        "max_quantity": {
                            "oneOf": [
                                {"type": "number", "minimum": 0},
                                {"const": "inf"},
                            ]
                        },
                    },
                },
            },
        },
        "allOf": [
            {
                "if": {"properties": {"domain": {"const": "bounded"}}},
                "then": {
                    "properties": {
                        "items": {
                            "items": {"required": ["max_quantity"]},
                        }
                    }
                },
            }
        ],
    }


def _knapsack_multi_dimensional_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "objective",
            "quantities",
            "selected_indices",
            "selected_items",
            "total_value",
            "resources",
        ],
        "properties": {
            "objective": {"type": ["number", "null"]},
            "quantities": {
                "type": "array",
                "items": {"type": "number", "minimum": 0},
            },
            "selected_indices": {"type": "array", "items": {"type": "integer"}},
            "selected_items": {"type": "array"},
            "total_value": {"type": "number"},
            "resources": {"type": "array"},
        },
    }


def _milp_descriptor(*, dependency_available: bool) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=MILP_CAPABILITY_ID,
        title="Mixed-integer linear programming",
        problem_type="mixed_integer_linear_programming",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_milp_input_schema(),
        result_schema=_milp_result_schema(),
        default_options={},
        available=dependency_available,
        unavailable_reason=(
            None
            if dependency_available
            else "OR-Tools is required by the MILP backends."
        ),
        backend_candidates=MILP_BACKEND_IDS,
        supports_time_limit=True,
        supports_cancellation=False,
        available_artifacts=_available_artifacts(MILP_CAPABILITY_ID),
    )


def _milp_input_schema() -> dict:
    number_or_null = {"type": ["number", "null"]}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["version", "variables", "objective", "constraints"],
        "properties": {
            "version": {"const": "1"},
            "variables": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "label": {"type": "string"},
                        "lb": number_or_null,
                        "ub": number_or_null,
                        "integrality": {
                            "enum": [
                                "C",
                                "I",
                                "B",
                                "continuous",
                                "integer",
                                "binary",
                            ]
                        },
                    },
                },
            },
            "objective": {
                "type": "object",
                "required": ["sense", "coefficients"],
                "properties": {
                    "sense": {"enum": ["min", "max"]},
                    "coefficients": {
                        "type": "array",
                        "items": number_or_null,
                    },
                    "offset": number_or_null,
                },
            },
            "constraints": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["coefficients", "relation", "rhs"],
                    "properties": {
                        "coefficients": {
                            "type": "array",
                            "items": number_or_null,
                        },
                        "relation": {"enum": ["<=", "=", ">="]},
                        "rhs": number_or_null,
                    },
                },
            },
            "solver": {
                "type": ["object", "null"],
                "properties": {
                    "time_limit": number_or_null,
                    "mip_gap": number_or_null,
                },
            },
        },
    }


def _milp_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["objective", "variables"],
        "properties": {
            "objective": {"type": ["number", "null"]},
            "variables": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "value"],
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "number"},
                    },
                },
            },
        },
    }


def _dijkstra_descriptor() -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=DIJKSTRA_CAPABILITY_ID,
        title="Dijkstra shortest path",
        problem_type="shortest_path",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_dijkstra_input_schema(),
        result_schema=_dijkstra_result_schema(),
        default_options={"directed": True},
        available=True,
        backend_candidates=(DIJKSTRA_BACKEND_ID,),
        supports_time_limit=False,
        supports_cancellation=False,
        available_artifacts=_available_artifacts(DIJKSTRA_CAPABILITY_ID),
    )


def _dijkstra_input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "version",
            "problem_type",
            "directed",
            "vertices",
            "edges",
            "source",
            "destination",
        ],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "shortest_path"},
            "directed": {"type": "boolean"},
            "vertices": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "label": {"type": "string"},
                    },
                },
            },
            "edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["from", "to", "weight"],
                    "properties": {
                        "from": {"type": "string", "minLength": 1},
                        "to": {"type": "string", "minLength": 1},
                        "weight": {"type": "number", "minimum": 0},
                    },
                },
            },
            "source": {"type": "string", "minLength": 1},
            "destination": {"type": "string", "minLength": 1},
        },
    }


def _dijkstra_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["distance", "path", "hop_count"],
        "properties": {
            "distance": {"type": ["number", "null"]},
            "path": {"type": "array", "items": {"type": "string"}},
            "hop_count": {"type": "integer", "minimum": 0},
        },
    }


def _nlp_descriptor(*, dependency_available: bool) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=NLP_CAPABILITY_ID,
        title="Continuous local nonlinear optimization",
        problem_type="nonlinear_programming",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_nlp_input_schema(),
        result_schema=_nlp_result_schema(),
        default_options={
            "method": "BFGS",
            "max_iterations": 1000,
            "tolerance": 1e-8,
        },
        available=dependency_available,
        unavailable_reason=(
            None
            if dependency_available
            else "SciPy is required by the continuous NLP backend."
        ),
        backend_candidates=(NLP_BACKEND_ID,),
        supports_time_limit=False,
        supports_cancellation=False,
        available_artifacts=_available_artifacts(NLP_CAPABILITY_ID),
    )


def _nlp_input_schema() -> dict:
    optional_number = {"type": ["number", "null"]}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["version", "problem_type", "variables", "objective"],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "nonlinear_programming"},
            "variables": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "initial"],
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "label": {"type": "string"},
                        "lb": optional_number,
                        "ub": optional_number,
                        "initial": {"type": "number"},
                    },
                },
            },
            "objective": {
                "type": "object",
                "required": ["sense", "expression"],
                "properties": {
                    "sense": {"enum": ["min", "max"]},
                    "expression": {"type": "string", "minLength": 1},
                },
            },
            "solver_options": {
                "type": ["object", "null"],
                "properties": {
                    "method": {"enum": ["BFGS", "Nelder-Mead", "L-BFGS-B"]},
                    "max_iterations": {"type": "integer", "minimum": 1},
                    "tolerance": {
                        "type": ["number", "null"],
                        "exclusiveMinimum": 0,
                    },
                },
            },
        },
    }


def _nlp_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["objective", "variables", "local_candidate"],
        "properties": {
            "objective": {"type": ["number", "null"]},
            "variables": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "value"],
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "number"},
                    },
                },
            },
            "local_candidate": {"type": "boolean"},
        },
    }


def _regression_descriptor(*, dependency_available: bool) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=REGRESSION_CAPABILITY_ID,
        title="Educational linear regression",
        problem_type="regression",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_regression_input_schema(),
        result_schema=_regression_result_schema(),
        default_options={
            "method": "OLS",
            "test_fraction": 0.2,
            "random_seed": 42,
            "ridge_alpha": 1.0,
        },
        available=dependency_available,
        unavailable_reason=(
            None
            if dependency_available
            else "NumPy is required by the regression backend."
        ),
        backend_candidates=(REGRESSION_BACKEND_ID,),
        supports_time_limit=False,
        supports_cancellation=False,
        available_artifacts=_available_artifacts(REGRESSION_CAPABILITY_ID),
    )


def _regression_input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["version", "problem_type", "dataset"],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "regression"},
            "dataset": _supervised_dataset_schema(
                target_schema={"type": "number"},
                minimum_rows=4,
            ),
            "training_options": {
                "type": ["object", "null"],
                "properties": {
                    "method": {"enum": ["OLS", "Ridge"]},
                    "test_fraction": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                        "exclusiveMaximum": 1,
                    },
                    "random_seed": {"type": "integer", "minimum": 0},
                    "ridge_alpha": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                    },
                },
            },
        },
    }


def _regression_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "trained_model",
            "intercept",
            "coefficients",
            "feature_scaling",
            "decision_threshold",
            "train_metrics",
            "test_metrics",
            "predictions",
        ],
        "properties": {
            "trained_model": {"type": "boolean"},
            "intercept": {"type": ["number", "null"]},
            "coefficients": _coefficient_schema(),
            "feature_scaling": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["feature", "mean", "scale"],
                    "properties": {
                        "feature": {"type": "string"},
                        "mean": {"type": ["number", "null"]},
                        "scale": {"type": ["number", "null"]},
                    },
                },
            },
            "decision_threshold": {"const": 0.5},
            "train_metrics": _regression_metrics_schema(),
            "test_metrics": _regression_metrics_schema(),
            "predictions": {"type": "array"},
        },
    }


def _classification_descriptor(
    *, dependency_available: bool
) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=CLASSIFICATION_CAPABILITY_ID,
        title="Educational binary logistic classification",
        problem_type="binary_classification",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_classification_input_schema(),
        result_schema=_classification_result_schema(),
        default_options={
            "method": "LogisticRegression",
            "test_fraction": 0.25,
            "random_seed": 42,
            "learning_rate": 0.1,
            "max_iterations": 2000,
            "l2_alpha": 0.0,
        },
        available=dependency_available,
        unavailable_reason=(
            None
            if dependency_available
            else "NumPy is required by the binary classification backend."
        ),
        backend_candidates=(CLASSIFICATION_BACKEND_ID,),
        supports_time_limit=False,
        supports_cancellation=False,
        available_artifacts=_available_artifacts(CLASSIFICATION_CAPABILITY_ID),
    )


def _classification_input_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["version", "problem_type", "dataset"],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "binary_classification"},
            "dataset": _supervised_dataset_schema(
                target_schema={"type": "string", "minLength": 1},
                minimum_rows=6,
            ),
            "training_options": {
                "type": ["object", "null"],
                "properties": {
                    "method": {"const": "LogisticRegression"},
                    "test_fraction": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                        "exclusiveMaximum": 1,
                    },
                    "random_seed": {"type": "integer", "minimum": 0},
                    "learning_rate": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                    },
                    "max_iterations": {"type": "integer", "minimum": 1},
                    "l2_alpha": {"type": "number", "minimum": 0},
                },
            },
        },
    }


def _classification_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "trained_model",
            "negative_label",
            "positive_label",
            "intercept",
            "coefficients",
            "train_metrics",
            "test_metrics",
            "train_confusion",
            "test_confusion",
            "predictions",
        ],
        "properties": {
            "trained_model": {"type": "boolean"},
            "negative_label": {"type": "string"},
            "positive_label": {"type": "string"},
            "intercept": {"type": ["number", "null"]},
            "coefficients": _coefficient_schema(),
            "train_metrics": _classification_metrics_schema(),
            "test_metrics": _classification_metrics_schema(),
            "train_confusion": _confusion_schema(),
            "test_confusion": _confusion_schema(),
            "predictions": {"type": "array"},
        },
    }


def _supervised_dataset_schema(
    *,
    target_schema: dict,
    minimum_rows: int,
) -> dict:
    return {
        "type": "object",
        "required": ["feature_names", "target_name", "rows"],
        "properties": {
            "feature_names": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "minLength": 1},
            },
            "target_name": {"type": "string", "minLength": 1},
            "rows": {
                "type": "array",
                "minItems": minimum_rows,
                "items": {
                    "type": "object",
                    "required": ["features", "target"],
                    "properties": {
                        "features": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "number"},
                        },
                        "target": target_schema,
                    },
                },
            },
        },
    }


def _coefficient_schema() -> dict:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["feature", "value"],
            "properties": {
                "feature": {"type": "string"},
                "value": {"type": "number"},
            },
        },
    }


def _regression_metrics_schema() -> dict:
    return {
        "type": "object",
        "required": ["mae", "mse", "rmse", "r_squared"],
        "properties": {
            key: {"type": ["number", "null"]}
            for key in ("mae", "mse", "rmse", "r_squared")
        },
    }


def _classification_metrics_schema() -> dict:
    return {
        "type": "object",
        "required": ["accuracy", "precision", "recall", "f1"],
        "properties": {
            key: {"type": ["number", "null"]}
            for key in ("accuracy", "precision", "recall", "f1")
        },
    }


def _confusion_schema() -> dict:
    fields = (
        "true_negative",
        "false_positive",
        "false_negative",
        "true_positive",
    )
    return {
        "type": "object",
        "required": list(fields),
        "properties": {
            key: {"type": "integer", "minimum": 0} for key in fields
        },
    }


def _packing_descriptor(*, dependency_available: bool) -> CapabilityDescriptor:
    return CapabilityDescriptor(
        capability_id=PACKING_CAPABILITY_ID,
        title="Orthogonal single-container 3D packing",
        problem_type="packing",
        contract_version="1",
        problem_schema_version="1",
        result_schema_version="1",
        input_schema=_packing_input_schema(),
        result_schema=_packing_result_schema(),
        default_options={
            "selection_policy": "optional",
            "gravity_mode": "simple",
        },
        available=dependency_available,
        unavailable_reason=(
            None
            if dependency_available
            else "OR-Tools is required by the exact 3D packing backend."
        ),
        backend_candidates=PACKING_BACKEND_IDS,
        supports_time_limit=True,
        supports_cancellation=True,
        available_artifacts=_available_artifacts(PACKING_CAPABILITY_ID),
    )


def _packing_input_schema() -> dict:
    dimensions = {
        "type": "object",
        "required": ["length", "width", "height"],
        "properties": {
            axis: {"type": "number", "exclusiveMinimum": 0}
            for axis in ("length", "width", "height")
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "version",
            "problem_type",
            "variant",
            "selection_policy",
            "gravity_mode",
            "container",
            "items",
        ],
        "properties": {
            "version": {"const": "1"},
            "problem_type": {"const": "packing"},
            "variant": {"const": "single_container_3d"},
            "selection_policy": {"enum": ["optional", "all_required"]},
            "gravity_mode": {"enum": ["none", "simple"]},
            "container": {
                "type": "object",
                "required": ["id", "name", "dimensions", "capacities"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "name": {"type": "string", "minLength": 1},
                    "dimensions": dimensions,
                    "capacities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "limit"],
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "limit": {"type": "number", "minimum": 0},
                            },
                        },
                    },
                },
            },
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": [
                        "id",
                        "name",
                        "dimensions",
                        "value",
                        "quantity",
                        "rotation_policy",
                        "allowed_orientations",
                        "consumptions",
                    ],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "name": {"type": "string", "minLength": 1},
                        "dimensions": dimensions,
                        "value": {"type": "number", "minimum": 0},
                        "quantity": {"type": "integer", "minimum": 1},
                        "rotation_policy": {
                            "enum": [
                                "fixed",
                                "keep_upright",
                                "x_only",
                                "y_only",
                                "z_only",
                                "any_orthogonal",
                                "custom",
                            ]
                        },
                        "allowed_orientations": {
                            "type": "array",
                            "items": {
                                "enum": [
                                    "LWH",
                                    "LHW",
                                    "WLH",
                                    "WHL",
                                    "HLW",
                                    "HWL",
                                ]
                            },
                        },
                        "consumptions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["name", "amount"],
                                "properties": {
                                    "name": {"type": "string", "minLength": 1},
                                    "amount": {"type": "number", "minimum": 0},
                                },
                            },
                        },
                    },
                },
            },
            "solver_options": {
                "type": ["object", "null"],
                "properties": {
                    "time_limit": {
                        "type": ["number", "null"],
                        "exclusiveMinimum": 0,
                    },
                    "mip_gap": {
                        "type": ["number", "null"],
                        "minimum": 0,
                        "exclusiveMaximum": 1,
                    },
                },
            },
        },
    }


def _packing_result_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["requested", "recovery"],
        "properties": {
            "requested": _packing_solution_schema(),
            "recovery": {
                "oneOf": [_packing_solution_schema(), {"type": "null"}]
            },
        },
    }


def _packing_solution_schema() -> dict:
    return {
        "type": "object",
        "required": [
            "objective",
            "total_value",
            "used_volume",
            "placements",
            "excluded_instance_ids",
        ],
        "properties": {
            "objective": {"type": ["number", "null"]},
            "total_value": {"type": "number", "minimum": 0},
            "used_volume": {"type": "number", "minimum": 0},
            "placements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "instance_id",
                        "item_id",
                        "item_name",
                        "unit_index",
                        "orientation_code",
                        "position",
                        "dimensions",
                        "value",
                    ],
                },
            },
            "excluded_instance_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }
