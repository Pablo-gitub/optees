from __future__ import annotations

from threading import Lock
from typing import Any, Callable, Dict, List, Tuple

from optees.application.ports.packing_solver_port import PackingSolverPort

try:
    from ortools.linear_solver import pywraplp

    _ORTOOLS_ERROR = None
except Exception as exc:  # pragma: no cover - exercised only without dependency
    pywraplp = None
    _ORTOOLS_ERROR = exc


class OrtoolsSingleContainerPackingAdapter(PackingSolverPort):
    """Exact orthogonal 3D packing formulation solved through OR-Tools."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._active_solver = None
        self._cancel_requested = False

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = _solve(problem, self._register_solver)
            with self._lock:
                cancel_requested = self._cancel_requested
            if cancel_requested:
                extras = dict(result.get("extras", {}) or {})
                extras["termination_reason"] = "cancelled"
                result["extras"] = extras
            return result
        except Exception as exc:
            return {
                "status": "NotSolved",
                "objective": None,
                "placements": (),
                "excluded_instance_ids": (),
                "extras": {
                    "backend": None,
                    "message": str(exc),
                    "solve_role": problem.get("solve_role", "requested"),
                },
            }
        finally:
            with self._lock:
                self._active_solver = None
                self._cancel_requested = False

    def cancel(self) -> bool:
        with self._lock:
            self._cancel_requested = True
            solver = self._active_solver
        if solver is None:
            return True
        try:
            return bool(solver.InterruptSolve())
        except Exception:
            return False

    def _register_solver(self, solver: Any) -> None:
        with self._lock:
            self._active_solver = solver
            cancel_requested = self._cancel_requested
        if cancel_requested:
            solver.InterruptSolve()


def _solve(
    problem: Dict[str, Any],
    register_solver: Callable[[Any], None] | None = None,
) -> Dict[str, Any]:
    if pywraplp is None:
        raise RuntimeError(f"OR-Tools is not available: {_ORTOOLS_ERROR}")

    container = dict(problem["container"])
    container_dimensions = _dimension_tuple(container.get("dimensions"), "container dimensions")
    container_capacities = {
        str(name).casefold(): _non_negative(value, f"container capacity {name!r}")
        for name, value in dict(container.get("capacities", {})).items()
    }
    items = [_normalize_item(raw, index) for index, raw in enumerate(problem.get("items", ()))]
    if not items:
        raise ValueError("packing problem requires at least one item")

    solver = pywraplp.Solver.CreateSolver("SCIP")
    backend = "scip"
    if solver is None:
        solver = pywraplp.Solver.CreateSolver("CBC")
        backend = "cbc"
    if solver is None:
        raise RuntimeError("neither SCIP nor CBC is available")
    if register_solver is not None:
        register_solver(solver)
    time_limit = problem.get("time_limit")
    if time_limit is not None and float(time_limit) > 0:
        solver.SetTimeLimit(int(float(time_limit) * 1000))
    mip_gap = problem.get("mip_gap")
    mip_gap_applied = False
    if mip_gap is not None and float(mip_gap) > 0 and backend == "scip":
        mip_gap_applied = bool(
            solver.SetSolverSpecificParametersAsString(
                f"limits/gap = {float(mip_gap):.17g}"
            )
        )

    length, width, height = container_dimensions
    load = []
    coordinates = []
    orientation_vars: List[List[Any]] = []

    for index, item in enumerate(items):
        loaded = solver.BoolVar(f"loaded_{index}")
        x = solver.NumVar(0.0, length, f"x_{index}")
        y = solver.NumVar(0.0, width, f"y_{index}")
        z = solver.NumVar(0.0, height, f"z_{index}")
        rotations = [
            solver.BoolVar(f"orientation_{index}_{orientation_index}")
            for orientation_index in range(len(item["orientations"]))
        ]
        solver.Add(sum(rotations) == loaded)
        if problem.get("all_items_required", False):
            solver.Add(loaded == 1)

        oriented_length = sum(
            orientation["dimensions"][0] * rotations[o]
            for o, orientation in enumerate(item["orientations"])
        )
        oriented_width = sum(
            orientation["dimensions"][1] * rotations[o]
            for o, orientation in enumerate(item["orientations"])
        )
        oriented_height = sum(
            orientation["dimensions"][2] * rotations[o]
            for o, orientation in enumerate(item["orientations"])
        )
        solver.Add(x + oriented_length <= length * loaded)
        solver.Add(y + oriented_width <= width * loaded)
        solver.Add(z + oriented_height <= height * loaded)

        load.append(loaded)
        coordinates.append((x, y, z))
        orientation_vars.append(rotations)

    for resource_name, capacity in container_capacities.items():
        solver.Add(
            sum(item["consumptions"].get(resource_name, 0.0) * load[i] for i, item in enumerate(items))
            <= capacity
        )

    separation_count = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            relations = [solver.BoolVar(f"separate_{i}_{j}_{axis}") for axis in range(6)]
            separation_count += len(relations)
            for relation in relations:
                solver.Add(relation <= load[i])
                solver.Add(relation <= load[j])
            solver.Add(sum(relations) >= load[i] + load[j] - 1)

            xi, yi, zi = coordinates[i]
            xj, yj, zj = coordinates[j]
            di = _oriented_dimension_expressions(items[i], orientation_vars[i])
            dj = _oriented_dimension_expressions(items[j], orientation_vars[j])
            solver.Add(xi + di[0] <= xj + length * (1 - relations[0]))
            solver.Add(xj + dj[0] <= xi + length * (1 - relations[1]))
            solver.Add(yi + di[1] <= yj + width * (1 - relations[2]))
            solver.Add(yj + dj[1] <= yi + width * (1 - relations[3]))
            solver.Add(zi + di[2] <= zj + height * (1 - relations[4]))
            solver.Add(zj + dj[2] <= zi + height * (1 - relations[5]))

    solver.Maximize(sum(item["value"] * load[index] for index, item in enumerate(items)))
    result_status = solver.Solve()
    status = _status(result_status)

    placements = []
    excluded = []
    if status in {"Optimal", "Feasible"}:
        for index, item in enumerate(items):
            if load[index].solution_value() < 0.5:
                excluded.append(item["instance_id"])
                continue
            orientation_index = max(
                range(len(orientation_vars[index])),
                key=lambda candidate: orientation_vars[index][candidate].solution_value(),
            )
            orientation = item["orientations"][orientation_index]
            dx, dy, dz = orientation["dimensions"]
            x, y, z = coordinates[index]
            placements.append(
                {
                    "instance_id": item["instance_id"],
                    "item_id": item["item_id"],
                    "item_name": item["item_name"],
                    "unit_index": item["unit_index"],
                    "orientation_code": orientation["code"],
                    "x": x.solution_value(),
                    "y": y.solution_value(),
                    "z": z.solution_value(),
                    "length": dx,
                    "width": dy,
                    "height": dz,
                    "value": item["value"],
                }
            )
        objective = solver.Objective().Value()
    else:
        objective = None

    best_bound = _best_bound(solver) if status in {"Optimal", "Feasible"} else None
    extras = {
        "backend": backend,
        "result_status": int(result_status),
        "wall_time_ms": solver.wall_time(),
        "nodes": _safe_int_call(solver, "nodes"),
        "best_bound": best_bound,
        "relative_gap": _relative_gap(objective, best_bound),
        "mip_gap_requested": problem.get("mip_gap"),
        "mip_gap_applied": mip_gap_applied,
        "solve_role": problem.get("solve_role", "requested"),
        "variable_count": solver.NumVariables(),
        "constraint_count": solver.NumConstraints(),
        "item_pair_count": len(items) * (len(items) - 1) // 2,
        "separation_binary_count": separation_count,
    }
    if _reached_time_limit(status, time_limit, extras["wall_time_ms"]):
        extras["termination_reason"] = "time_limit"
    return {
        "status": status,
        "objective": objective,
        "placements": tuple(placements),
        "excluded_instance_ids": tuple(excluded),
        "extras": extras,
    }


def _reached_time_limit(status: str, time_limit: object, wall_time_ms: object) -> bool:
    if status not in {"Feasible", "NotSolved"} or time_limit is None:
        return False
    try:
        limit_ms = float(time_limit) * 1000.0
        elapsed_ms = float(wall_time_ms)
    except (TypeError, ValueError, OverflowError):
        return False
    return limit_ms > 0 and elapsed_ms >= limit_ms * 0.9


def _normalize_item(raw: object, index: int) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"items[{index}] must be an object")
    orientations = []
    for orientation_index, orientation_raw in enumerate(raw.get("orientations", ())):
        if not isinstance(orientation_raw, dict):
            raise ValueError(f"items[{index}].orientations[{orientation_index}] must be an object")
        orientations.append(
            {
                "code": str(orientation_raw["code"]),
                "dimensions": _dimension_tuple(
                    orientation_raw.get("dimensions"),
                    f"items[{index}].orientations[{orientation_index}].dimensions",
                ),
            }
        )
    if not orientations:
        raise ValueError(f"items[{index}] requires at least one orientation")
    return {
        "instance_id": str(raw["instance_id"]),
        "item_id": str(raw["item_id"]),
        "item_name": str(raw["item_name"]),
        "unit_index": int(raw["unit_index"]),
        "value": _non_negative(raw.get("value"), f"items[{index}].value"),
        "orientations": orientations,
        "consumptions": {
            str(name).casefold(): _non_negative(
                value, f"items[{index}].consumptions[{name!r}]"
            )
            for name, value in dict(raw.get("consumptions", {})).items()
        },
    }


def _oriented_dimension_expressions(item: Dict[str, Any], variables: List[Any]) -> Tuple[Any, Any, Any]:
    return tuple(
        sum(orientation["dimensions"][axis] * variables[o] for o, orientation in enumerate(item["orientations"]))
        for axis in range(3)
    )  # type: ignore[return-value]


def _dimension_tuple(value: object, label: str) -> Tuple[float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must contain exactly three values")
    dimensions = tuple(_positive(part, f"{label}[{index}]") for index, part in enumerate(value))
    return dimensions  # type: ignore[return-value]


def _positive(value: object, label: str) -> float:
    parsed = _non_negative(value, label)
    if parsed <= 0:
        raise ValueError(f"{label} must be positive")
    return parsed


def _non_negative(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite non-negative number")
    parsed = float(value)  # type: ignore[arg-type]
    if parsed < 0 or parsed == float("inf") or parsed != parsed:
        raise ValueError(f"{label} must be a finite non-negative number")
    return parsed


def _status(result_status: int) -> str:
    if result_status == pywraplp.Solver.OPTIMAL:
        return "Optimal"
    if result_status == pywraplp.Solver.FEASIBLE:
        return "Feasible"
    if result_status == pywraplp.Solver.INFEASIBLE:
        return "Infeasible"
    if result_status == pywraplp.Solver.UNBOUNDED:
        return "Unbounded"
    return "NotSolved"


def _best_bound(solver: Any) -> float | None:
    try:
        return float(solver.Objective().BestBound())
    except Exception:
        return None


def _safe_int_call(value: object, method_name: str) -> int | None:
    try:
        return int(getattr(value, method_name)())
    except Exception:
        return None


def _relative_gap(objective: float | None, bound: float | None) -> float | None:
    if objective is None or bound is None:
        return None
    return abs(objective - bound) / max(1.0, abs(objective))
