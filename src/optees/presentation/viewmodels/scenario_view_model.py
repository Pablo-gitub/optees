"""View-model for the linear scenario min-max / max-min desktop workflow.

The view-model is the only presentation object that talks to the application
layer. It builds the frozen public problem payload from already validated form
input, submits it to the registered capability through ``OptimizationService``,
and republishes the returned envelope verbatim.

It deliberately owns no mathematics: reduction, solving, guarantee derivation,
binding-scenario selection and independent validation all belong to the
application and domain layers behind the capability registration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from optees.application.contracts.capability_ids import (
    SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID,
    SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID,
)

# Public orientation tokens frozen by the contract. They are paired with their
# capability ID here so the UI can never present one orientation under the
# other's identity.
MIN_MAX_LOSS_ORIENTATION = "minimize_maximum_loss"
MAX_MIN_REWARD_ORIENTATION = "maximize_minimum_reward"

ORIENTATION_BY_CAPABILITY: dict[str, str] = {
    SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID: MIN_MAX_LOSS_ORIENTATION,
    SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID: MAX_MIN_REWARD_ORIENTATION,
}

CAPABILITY_IDS: tuple[str, ...] = (
    SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID,
    SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID,
)

PROBLEM_VERSION = "1"
PROBLEM_TYPE = "linear_scenario"


class SupportsSolve(Protocol):
    """The slice of ``OptimizationService`` this view-model depends on."""

    def solve(self, capability_id: str, payload: dict[str, Any]) -> object: ...

    def list_capabilities(self) -> tuple[dict[str, Any], ...]: ...


@dataclass(frozen=True)
class ScenarioVariableInput:
    """One decision variable exactly as the user declared it."""

    name: str
    label: str = ""
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    integrality: str = "C"


@dataclass(frozen=True)
class ScenarioConstraintInput:
    name: str
    coefficients: tuple[float, ...]
    relation: str
    rhs: float


@dataclass(frozen=True)
class ScenarioInput:
    scenario_id: str
    label: str
    coefficients: tuple[float, ...]
    offset: float = 0.0


@dataclass(frozen=True)
class ScenarioOptionsInput:
    tolerance: Optional[float] = None
    binding_tolerance: Optional[float] = None
    time_limit_seconds: Optional[float] = None


@dataclass(frozen=True)
class ScenarioFormInput:
    """A complete, ordered form snapshot ready to become a public payload."""

    variables: tuple[ScenarioVariableInput, ...]
    scenarios: tuple[ScenarioInput, ...]
    constraints: tuple[ScenarioConstraintInput, ...] = ()
    shared_objective_coefficients: Optional[tuple[float, ...]] = None
    shared_objective_offset: Optional[float] = None
    options: ScenarioOptionsInput = field(default_factory=ScenarioOptionsInput)


class _WorkerSignals(QObject):
    completed = Signal(int, object)
    failed = Signal(int, str)


class _SolveWorker(QRunnable):
    """Runs one capability submission off the GUI thread."""

    def __init__(
        self,
        service: SupportsSolve,
        capability_id: str,
        payload: dict[str, Any],
        generation: int,
    ) -> None:
        super().__init__()
        self._service = service
        self._capability_id = capability_id
        self._payload = payload
        self._generation = generation
        self.signals = _WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            outcome = self._service.solve(self._capability_id, self._payload)
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            self.signals.failed.emit(self._generation, str(exc))
            return
        self.signals.completed.emit(self._generation, outcome)


def build_problem_payload(
    form: ScenarioFormInput,
    *,
    orientation: str,
) -> dict[str, Any]:
    """Assemble the frozen public problem DTO from ordered form input.

    Declared variable, constraint and scenario order is preserved exactly. No
    value is rescaled, reordered or sign-flipped: the orientation is carried as
    an explicit token so the capability decoder can reject a mismatch.
    """
    if orientation not in ORIENTATION_BY_CAPABILITY.values():
        raise ValueError(f"unsupported orientation {orientation!r}")

    payload: dict[str, Any] = {
        "version": PROBLEM_VERSION,
        "problem_type": PROBLEM_TYPE,
        "orientation": orientation,
        "variables": [
            {
                "name": variable.name,
                "label": variable.label,
                "lower_bound": variable.lower_bound,
                "upper_bound": variable.upper_bound,
                "integrality": variable.integrality,
            }
            for variable in form.variables
        ],
        "scenarios": [
            {
                "id": scenario.scenario_id,
                "label": scenario.label,
                "coefficients": list(scenario.coefficients),
                "offset": scenario.offset,
            }
            for scenario in form.scenarios
        ],
    }

    if form.constraints:
        payload["shared_constraints"] = [
            {
                "name": constraint.name,
                "coefficients": list(constraint.coefficients),
                "relation": constraint.relation,
                "rhs": constraint.rhs,
            }
            for constraint in form.constraints
        ]

    if form.shared_objective_coefficients is not None:
        shared: dict[str, Any] = {"coefficients": list(form.shared_objective_coefficients)}
        if form.shared_objective_offset is not None:
            shared["offset"] = form.shared_objective_offset
        payload["shared_objective"] = shared

    options: dict[str, Any] = {}
    if form.options.tolerance is not None:
        options["tolerance"] = form.options.tolerance
    if form.options.binding_tolerance is not None:
        options["binding_tolerance"] = form.options.binding_tolerance
    if form.options.time_limit_seconds is not None:
        options["time_limit_seconds"] = form.options.time_limit_seconds
    if options:
        payload["options"] = options

    return payload


class ScenarioViewModel(QObject):
    """Owns orientation selection and asynchronous capability submission."""

    #: Emitted with the ``ExecutionEnvelope`` returned by the application layer.
    succeeded = Signal(object)
    #: Emitted with the ``StructuredError`` returned by the application layer.
    rejected = Signal(object)
    #: Emitted when the submission itself raised before producing an outcome.
    failed = Signal(str)
    #: Emitted with ``True`` while a submission is in flight.
    busy_changed = Signal(bool)
    orientation_changed = Signal(str)

    def __init__(
        self,
        service: SupportsSolve | None = None,
        parent: QObject | None = None,
        *,
        thread_pool: QThreadPool | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._capability_id = SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID
        self._generation = 0
        self._busy = False
        self._thread_pool = thread_pool
        self._last_payload: dict[str, Any] | None = None

    # -- wiring ---------------------------------------------------------
    def set_service(self, service: SupportsSolve | None) -> None:
        self._service = service

    @property
    def service(self) -> SupportsSolve | None:
        return self._service

    # -- orientation ----------------------------------------------------
    @property
    def capability_id(self) -> str:
        return self._capability_id

    @property
    def orientation(self) -> str:
        return ORIENTATION_BY_CAPABILITY[self._capability_id]

    def set_capability_id(self, capability_id: str) -> None:
        if capability_id not in ORIENTATION_BY_CAPABILITY:
            raise ValueError(f"unknown scenario capability {capability_id!r}")
        if capability_id == self._capability_id:
            return
        self._capability_id = capability_id
        self.orientation_changed.emit(self.orientation)

    def capability_descriptor(self, capability_id: str | None = None) -> dict[str, Any] | None:
        """Return the registered descriptor, or ``None`` when unavailable."""
        if self._service is None:
            return None
        wanted = capability_id or self._capability_id
        for descriptor in self._service.list_capabilities():
            if descriptor.get("id") == wanted:
                return descriptor
        return None

    def is_available(self, capability_id: str | None = None) -> bool:
        descriptor = self.capability_descriptor(capability_id)
        return bool(descriptor and descriptor.get("available"))

    def unavailable_reason(self, capability_id: str | None = None) -> str | None:
        descriptor = self.capability_descriptor(capability_id)
        if descriptor is None:
            return None
        reason = descriptor.get("unavailable_reason")
        return str(reason) if reason else None

    # -- submission -----------------------------------------------------
    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def last_payload(self) -> dict[str, Any] | None:
        """The exact payload most recently submitted, for inspection and export."""
        return self._last_payload

    def submit(self, form: ScenarioFormInput) -> None:
        """Submit ``form`` under the selected orientation, asynchronously."""
        if self._service is None:
            self.failed.emit("no optimization service is configured")
            return

        payload = build_problem_payload(form, orientation=self.orientation)
        self._last_payload = payload
        self._generation += 1
        generation = self._generation
        self._set_busy(True)

        worker = _SolveWorker(self._service, self._capability_id, payload, generation)
        worker.signals.completed.connect(self._on_completed)
        worker.signals.failed.connect(self._on_failed)
        pool = self._thread_pool or QThreadPool.globalInstance()
        pool.start(worker)

    def cancel(self) -> None:
        """Abandon the in-flight submission.

        The registered scenario capabilities do not advertise cancellation, so
        this discards the pending outcome instead of claiming the solver was
        interrupted. Bumping the generation makes the late result stale.
        """
        if not self._busy:
            return
        self._generation += 1
        self._set_busy(False)

    def _is_current(self, generation: int) -> bool:
        return generation == self._generation

    def _set_busy(self, busy: bool) -> None:
        if busy == self._busy:
            return
        self._busy = busy
        self.busy_changed.emit(busy)

    def _on_completed(self, generation: int, outcome: object) -> None:
        if not self._is_current(generation):
            return
        self._set_busy(False)
        # Imported lazily so the view-model stays importable without Qt-free
        # application contracts being resolved at module import time.
        from optees.application.contracts.errors import StructuredError

        if isinstance(outcome, StructuredError):
            self.rejected.emit(outcome)
        else:
            self.succeeded.emit(outcome)

    def _on_failed(self, generation: int, detail: str) -> None:
        if not self._is_current(generation):
            return
        self._set_busy(False)
        self.failed.emit(detail)
