"""
Linear Programming (LP) utilities on top of SciPy/HiGHS.

Public surface:
- solve_lp(problem: dict, method="highs")
- pre_process_lp_data(...): conservative constraint cleanup
- perform_sensitivity_analysis(...): HiGHS marginal summary

The solver is source-agnostic: adapters must supply the canonical `problem` dict.

Canonical LP dict (what adapters must produce)
----------------------------------------------
problem = {
    "sense": "min" | "max",
    "c": list[float],                       # objective coefficients
    "A_ub": list[list[float]] | None,       # optional, <= constraints (rows)
    "b_ub": list[float]         | None,     # optional, RHS for A_ub
    "A_eq": list[list[float]] | None,       # optional, == constraints (rows)
    "b_eq": list[float]         | None,     # optional, RHS for A_eq
    "bounds": list[[lb, ub]]    | None,     # optional, per-variable bounds (None => ±inf).
                                             # Default is (0, +inf) for every variable.
    "var_names": list[str]      | None,     # optional, defaults to ["x0","x1",...]
    "obj_offset": float         | 0.0       # optional constant added to objective
}
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, List
import numpy as np
# Optional sparse support (LPNetlib matrices are often CSR)
try:
    import scipy.sparse as sp
except Exception:
    sp = None  # handle gracefully if SciPy.sparse is not available


try:
    # SciPy is the only dependency required for continuous LPs.
    from scipy.optimize import linprog
except Exception as e:  # allow import even if SciPy is missing
    linprog = None
    _scipy_import_error = e

__all__ = ["solve_lp", "pre_process_lp_data", "perform_sensitivity_analysis"]

_PREPROCESS_MAX_DENSE_ELEMENTS = 2_000_000
_DEFAULT_OPTIMAL_RANGE_MAX_VARS = 50


# ---------- Public API (thin orchestrator) ----------

def solve_lp(
    problem: Dict[str, Any],
    *,
    method: str = "highs",
) -> Tuple[str, Optional[float], Dict[str, float], Dict[str, Any]]:
    """
    Solve a continuous LP using SciPy/HiGHS.

    Parameters
    ----------
    problem : dict
        Canonical LP dictionary (see module docstring for fields).
    method : str, optional
        One of {"highs", "highs-ds", "highs-ipm"}. Defaults to "highs".

    Returns
    -------
    status : str
        One of {"Optimal", "Infeasible", "Unbounded", "NotSolved"}.
    objective : float | None
        Optimal objective value if solved; otherwise None.
    x_dict : dict[str, float]
        Mapping variable name -> value (only if status == "Optimal").
    extras : dict
        Additional diagnostic info (e.g., solver message, iterations, HiGHS marginals if present).

    Raises
    ------
    RuntimeError
        If SciPy is not available.
    ValueError
        If inputs are inconsistent (shape/length mismatches, invalid sense, etc.).
    """
    if linprog is None:
        raise RuntimeError(f"SciPy not available: {str(_scipy_import_error)}")

    # --- NEW: run lightweight pre-processing to clean constraints ---
    problem_pp, pp_info = pre_process_lp_data(problem, normalize=True, scale=False)

    # Validate and normalize input problem into an internal structure.
    lp = _normalize_problem(problem_pp)

    # Prepare arguments for SciPy's linprog.
    args = _build_linprog_args(lp)

    # Execute solver (isolated to keep error handling contained).
    res = _call_linprog(args, method=method)

    # Map SciPy result into our unified output tuple.
    status, obj, x_dict, extras = _postprocess_result(lp, res, method=method)

    # --- NEW: surface pre-processing info for transparency/UX ---
    extras.setdefault("preprocess", pp_info)

    return status, obj, x_dict, extras



# ---------- Private helpers (single responsibility) ----------

def _to_dense_array(M) -> Optional[np.ndarray]:
    """
    Return a dense numpy.ndarray from either a dense-like input or a SciPy sparse matrix.
    Keeps None as None. Ensures dtype=float.
    """
    if M is None:
        return None
    if sp is not None and sp.issparse(M):
        # .toarray() returns a dense ndarray with the right shape
        return M.toarray().astype(float, copy=False)
    # np.asarray on lists/tuples/ndarrays
    return np.asarray(M, dtype=float)


def _too_large_to_densify(M, *, max_elements: int = _PREPROCESS_MAX_DENSE_ELEMENTS) -> bool:
    """Return True when a sparse matrix is too large for safe dense preprocessing."""
    if sp is None or M is None or not sp.issparse(M):
        return False
    rows, cols = M.shape
    return int(rows) * int(cols) > max_elements


def _normalize_problem(problem: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize inputs; compute derived fields.

    Parameters
    ----------
    problem : dict
        Canonical LP dictionary.

    Returns
    -------
    dict
        Normalized internal representation with keys:
        - c, A_ub, b_ub, A_eq, b_eq
        - bounds (list of (lb, ub))
        - var_names (list of str)
        - flip_obj (bool; True if original sense was "max")
        - obj_offset (float)
    """
    _validate_problem(problem)

    sense = str(problem.get("sense", "min")).lower()
    flip_obj = (sense == "max")

    c = np.asarray(problem["c"], dtype=float)
    n = int(c.shape[0])

    # Optional matrices/vectors (dense or scipy.sparse are both fine).
    A_ub = problem.get("A_ub", None)
    b_ub = problem.get("b_ub", None)
    A_eq = problem.get("A_eq", None)
    b_eq = problem.get("b_eq", None)

    # Bounds: default (0, +inf). Convert incoming bounds to floats/None.
    bounds_in = problem.get("bounds")
    if bounds_in is None:
        bounds: List[Tuple[Optional[float], Optional[float]]] = [(0.0, None)] * n
    else:
        if len(bounds_in) != n:
            raise ValueError("len(bounds) must match len(c).")
        bounds = [
            (None if lb is None else float(lb),
             None if ub is None else float(ub))
            for (lb, ub) in bounds_in
        ]

    # Variable names: either validate the provided list, or autogenerate.
    var_names = problem.get("var_names")
    if var_names is not None:
        if len(var_names) != n:
            raise ValueError("len(var_names) must match len(c).")
        var_names = list(map(str, var_names))
    else:
        var_names = [f"x{i}" for i in range(n)]

    obj_offset = float(problem.get("obj_offset", 0.0))

    return {
        "c": c,
        "A_ub": A_ub, "b_ub": b_ub,
        "A_eq": A_eq, "b_eq": b_eq,
        "bounds": bounds,
        "var_names": var_names,
        "flip_obj": flip_obj,
        "obj_offset": obj_offset,
        "compute_optimal_ranges": problem.get("compute_optimal_ranges", "auto"),
        "optimal_range_max_vars": int(problem.get("optimal_range_max_vars", _DEFAULT_OPTIMAL_RANGE_MAX_VARS)),
    }


def _validate_problem(problem: Dict[str, Any]) -> None:
    """
    Light, source-agnostic validation of the canonical LP dict.

    Parameters
    ----------
    problem : dict
        Canonical LP dictionary.

    Raises
    ------
    ValueError
        If required fields are missing or (A,b) pairs are inconsistent.
    """
    if "c" not in problem:
        raise ValueError("Missing 'c' in problem.")
    sense = str(problem.get("sense", "min")).lower()
    if sense not in ("min", "max"):
        raise ValueError("problem['sense'] must be 'min' or 'max'.")

    # Helper to ensure A/b are provided together (or both omitted).
    def _pair(A, b, tag: str):
        if (A is None) ^ (b is None):
            raise ValueError(f"{tag}: A and b must be both provided or both omitted.")

    _pair(problem.get("A_ub"), problem.get("b_ub"), "A_ub/b_ub")
    _pair(problem.get("A_eq"), problem.get("b_eq"), "A_eq/b_eq")


def _build_linprog_args(lp: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare arguments for scipy.optimize.linprog.

    Parameters
    ----------
    lp : dict
        Normalized internal LP dict from _normalize_problem.

    Returns
    -------
    dict
        Arguments (c, A_ub, b_ub, A_eq, b_eq, bounds) ready for linprog.
    """
    # If original sense was "max", flip the objective to a minimization.
    c_eff = -lp["c"] if lp["flip_obj"] else lp["c"]
    return {
        "c": c_eff,
        "A_ub": lp["A_ub"],
        "b_ub": lp["b_ub"],
        "A_eq": lp["A_eq"],
        "b_eq": lp["b_eq"],
        "bounds": lp["bounds"],
    }


def _call_linprog(args: Dict[str, Any], *, method: str):
    """
    Call SciPy's linprog, catching setup/runtime exceptions.

    Parameters
    ----------
    args : dict
        Prepared arguments for linprog (see _build_linprog_args).
    method : str
        One of {"highs", "highs-ds", "highs-ipm"}.

    Returns
    -------
    scipy.optimize.OptimizeResult | object
        The SciPy result if the call succeeds; otherwise a minimal object
        carrying {status=None, success=False, message=str(error)}.
    """
    try:
        return linprog(
            args["c"],
            A_ub=args["A_ub"], b_ub=args["b_ub"],
            A_eq=args["A_eq"], b_eq=args["b_eq"],
            bounds=args["bounds"],
            method=method,
        )
    except Exception as e:
        # Build a minimal result-like object carrying the error.
        class _Fail:  # noqa: N801 (compact, internal type)
            status = None
            success = False
            message = str(e)
            nit = None
            crossover_nit = None
        return _Fail()

def _objective_hyperplane_from_result(lp: Dict[str, Any], res) -> Tuple[np.ndarray, float]:
    """
    Build (c_eq, z_for_eq) so that c_eq^T x = z_for_eq represents the optimal objective hyperplane.
    The constant obj_offset does not affect the hyperplane because it does not depend on x.
    """
    c = lp["c"].astype(float, copy=False)
    if lp["flip_obj"]:
        # Original was max c^T x, HiGHS minimized -c^T x, so res.fun = -(c^T x*)
        z_no_offset = -float(res.fun)
    else:
        # Original was min c^T x, so res.fun = c^T x*
        z_no_offset = float(res.fun)
    # Always use c (not -c): we want c^T x = c^T x*
    return c, z_no_offset


def _stack_with_objective_hyperplane(A_eq, b_eq, c_eq: np.ndarray, z_for_eq: float):
    """
    Append the objective hyperplane to A_eq/b_eq preserving sparse/dense type.
    Returns (A_eq2, b_eq2).
    """
    row = c_eq.reshape(1, -1)
    if A_eq is None:
        return row, np.array([z_for_eq], dtype=float)
    if sp is not None and sp.issparse(A_eq):
        A2 = sp.vstack([A_eq, sp.csr_matrix(row)])
        b2 = np.hstack([np.asarray(b_eq, dtype=float), [z_for_eq]])
        return A2, b2
    # dense
    A2 = np.vstack([_to_dense_array(A_eq), row])
    b2 = np.hstack([np.asarray(b_eq, dtype=float), [z_for_eq]])
    return A2, b2


def _solve_on_optimal_face(lp: Dict[str, Any], res, c_new: np.ndarray, *,
                           method: str = "highs"):
    """
    Re-solve the LP on the optimal face with a new objective.

    Mathematics:
      If the original LP has optimal value z*, every optimal solution lies in
      the face F* = {x feasible | c^T x = z*}.  Adding c^T x = z* to the
      original constraints lets us optimize any linear probe d^T x over F*.
      Probing with d=e_i and d=-e_i gives the minimum and maximum admissible
      optimal value of variable x_i.
    """
    c_eq, z_for_eq = _objective_hyperplane_from_result(lp, res)
    A_eq2, b_eq2 = _stack_with_objective_hyperplane(lp.get("A_eq"), lp.get("b_eq"), c_eq, z_for_eq)

    try:
        return linprog(
            c_new,
            A_ub=lp.get("A_ub"), b_ub=lp.get("b_ub"),
            A_eq=A_eq2, b_eq=b_eq2,
            bounds=lp.get("bounds"), method=method,
        )
    except Exception:
        class _Fail:  # noqa: N801
            status = None
            success = False
            message = "Could not solve auxiliary LP on optimal face."
            x = None
        return _Fail()


def _clean_small_float(value: float, *, tol: float = 1e-9) -> float:
    if np.isfinite(value) and abs(value) <= tol:
        return 0.0
    return float(value)


def _point_to_map(var_names: List[str], xvec: np.ndarray, *, value_tol: float = 1e-9) -> Dict[str, float]:
    return {
        name: _clean_small_float(float(v), tol=value_tol)
        for name, v in zip(var_names, xvec.tolist())
    }


def _should_compute_optimal_ranges(lp: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    mode = lp.get("compute_optimal_ranges", "auto")
    n = len(lp["var_names"])
    max_vars = int(lp.get("optimal_range_max_vars", _DEFAULT_OPTIMAL_RANGE_MAX_VARS))

    if isinstance(mode, str):
        mode_l = mode.lower()
        if mode_l in {"always", "true", "yes", "on"}:
            return True, None
        if mode_l in {"never", "false", "no", "off"}:
            return False, "disabled by problem option"

    if mode is True:
        return True, None
    if mode is False:
        return False, "disabled by problem option"

    if n > max_vars:
        return False, f"model has {n} variables; automatic range analysis limit is {max_vars}"
    return True, None


def _compute_optimal_variable_ranges(
    lp: Dict[str, Any],
    res,
    *,
    method: str = "highs",
    value_tol: float = 1e-9,
    range_tol: float = 1e-8,
) -> Dict[str, Any]:
    """
    Compute per-variable ranges over the optimal face.

    Mathematics:
      Let F* be the optimal face of the feasible polyhedron:
          F* = {x | Ax <= b, Aeq x = beq, bounds, c^T x = z*}.
      For each variable x_i, solve two auxiliary LPs:
          l_i = min {x_i | x in F*}
          u_i = max {x_i | x in F*}.
      The interval [l_i, u_i] is the exact range of admissible optimal values
      for x_i.  If any interval has positive width, or is unbounded, then the
      optimal solution is not unique.
    """
    var_names: List[str] = lp["var_names"]
    n = len(var_names)
    ranges: Dict[str, Dict[str, Any]] = {}
    endpoint_points: Dict[str, Dict[str, Dict[str, float]]] = {}
    varying_variables: List[str] = []
    aux_failures: List[str] = []

    for i, name in enumerate(var_names):
        e_i = np.zeros(n, dtype=float)
        e_i[i] = 1.0

        r_min = _solve_on_optimal_face(lp, res, e_i, method=method)
        r_max = _solve_on_optimal_face(lp, res, -e_i, method=method)

        min_value: Optional[float]
        max_value: Optional[float]
        min_point = None
        max_point = None

        if getattr(r_min, "status", None) == 3:
            min_value = float("-inf")
        elif getattr(r_min, "status", None) == 0 and getattr(r_min, "success", False) and getattr(r_min, "x", None) is not None:
            min_value = _clean_small_float(float(r_min.x[i]), tol=value_tol)
            min_point = _point_to_map(var_names, r_min.x, value_tol=value_tol)
        else:
            min_value = None
            aux_failures.append(f"{name}:min")

        if getattr(r_max, "status", None) == 3:
            max_value = float("inf")
        elif getattr(r_max, "status", None) == 0 and getattr(r_max, "success", False) and getattr(r_max, "x", None) is not None:
            max_value = _clean_small_float(float(r_max.x[i]), tol=value_tol)
            max_point = _point_to_map(var_names, r_max.x, value_tol=value_tol)
        else:
            max_value = None
            aux_failures.append(f"{name}:max")

        if min_value is None or max_value is None:
            width = None
            is_varying = False
        elif not np.isfinite(min_value) or not np.isfinite(max_value):
            width = float("inf")
            is_varying = True
        else:
            width = max(0.0, float(max_value - min_value))
            is_varying = width > range_tol

        ranges[name] = {
            "min": min_value,
            "max": max_value,
            "width": width,
            "is_fixed": not is_varying if width is not None else None,
        }

        if is_varying:
            varying_variables.append(name)
        if min_point is not None or max_point is not None:
            endpoint_points[name] = {}
            if min_point is not None:
                endpoint_points[name]["min"] = min_point
            if max_point is not None:
                endpoint_points[name]["max"] = max_point

    # Keep a compact A/B pair for 2-D/legacy UI by choosing the widest finite
    # interval.  The authoritative result is still the per-variable range map.
    extreme_points = None
    extreme_pivot = None
    finite_candidates = [
        (name, info["width"])
        for name, info in ranges.items()
        if isinstance(info.get("width"), (int, float)) and np.isfinite(info["width"]) and info["width"] > range_tol
    ]
    if finite_candidates:
        pivot_name, _ = max(finite_candidates, key=lambda item: item[1])
        extreme_pivot = pivot_name
        endpoints = endpoint_points.get(pivot_name, {})
        if "min" in endpoints and "max" in endpoints:
            extreme_points = {"A": endpoints["min"], "B": endpoints["max"]}

    return {
        "ranges": ranges,
        "endpoint_points": endpoint_points,
        "extreme_points": extreme_points,
        "extreme_pivot": extreme_pivot,
        "varying_variables": varying_variables,
        # Backwards-compatible name used by older presentation code/tests.
        "zero_reduced_cost_vars": varying_variables,
        "has_alternate_optimum": bool(varying_variables),
        "range_tol": range_tol,
        "auxiliary_failures": aux_failures,
    }


def _estimate_dimension_from_range_endpoints(lp: Dict[str, Any], alt_info: Dict[str, Any]) -> Optional[int]:
    """
    Estimate the affine dimension spanned by auxiliary range endpoints.

    This is preferable to using active constraints at one solver-returned
    optimum: a simplex method may return an endpoint of an optimal segment,
    where extra bounds are active even though they are not active on the whole
    optimal face.
    """
    points = []
    endpoint_points = alt_info.get("endpoint_points") or {}
    for by_var in endpoint_points.values():
        if not isinstance(by_var, dict):
            continue
        for point in by_var.values():
            if not isinstance(point, dict):
                continue
            try:
                points.append([float(point[name]) for name in lp["var_names"]])
            except Exception:
                continue

    if len(points) >= 2:
        P = np.asarray(points, dtype=float)
        base = P[0, :]
        D = P[1:, :] - base
        rank = int(np.linalg.matrix_rank(D, tol=1e-10))
        if rank == 0 and alt_info.get("has_alternate_optimum", False):
            return 1
        return rank

    if alt_info.get("has_alternate_optimum", False):
        return 1
    return 0


def _estimate_optimal_face_dimension(
    lp: Dict[str, Any],
    res,
    *,
    active_tol: float = 1e-8,
) -> Optional[int]:
    """
    Estimate the dimension of the optimal face:
      dim = n_vars - rank(G),
    where G stacks the normals of:
      - all equality constraints A_eq,
      - all *active* inequality constraints (rows of A_ub with slack ~ 0),
      - all active variable bounds,
      - the (effective) objective row.

    Returns:
      dim (int) if computable, or None if needed data is missing.
    """
    # Need residuals/slacks to know which inequalities are active
    ine = getattr(res, "ineqlin", None)
    eql = getattr(res, "eqlin", None)
    if ine is None or eql is None:
        return None

    # Grab shapes and matrices
    n = int(lp["c"].shape[0])
    Aeq = lp.get("A_eq")
    Aub = lp.get("A_ub")
    if _too_large_to_densify(Aeq) or _too_large_to_densify(Aub):
        return None
    Aeq_d = _to_dense_array(Aeq) if Aeq is not None else None
    Aub_d = _to_dense_array(Aub) if Aub is not None else None

    # Build the objective row as *the normal of the optimal hyperplane*:
    # If 'max' was flipped, the effective objective minimized was -c, so the
    # hyperplane normal to add is (-c), matching res.fun definition.
    c_eff = (-lp["c"]) if lp["flip_obj"] else lp["c"]
    rows = []

    # All equality rows are always "active"
    if Aeq_d is not None and Aeq_d.size > 0:
        rows.append(Aeq_d)

    # Active inequalities: slack ~ 0
    ri = getattr(ine, "residual", None)  # slacks for A_ub
    if Aub_d is not None and ri is not None:
        ri_arr = np.asarray(ri, dtype=float).ravel()
        if ri_arr.shape[0] == Aub_d.shape[0]:
            active_mask = ri_arr <= active_tol
            if np.any(active_mask):
                rows.append(Aub_d[active_mask, :])

    # Active bounds are also equalities on the optimal face.  Without these
    # rows, a vertex created only by variable bounds (e.g. min x+y, x,y>=0)
    # would be incorrectly estimated as a positive-dimensional face.
    bound_rows = []
    lower = getattr(res, "lower", None)
    upper = getattr(res, "upper", None)
    rl = getattr(lower, "residual", None) if lower is not None else None
    ru = getattr(upper, "residual", None) if upper is not None else None
    if rl is not None:
        for i, slack in enumerate(np.asarray(rl, dtype=float).ravel()[:n]):
            if np.isfinite(slack) and slack <= active_tol:
                row = np.zeros(n, dtype=float)
                row[i] = 1.0
                bound_rows.append(row)
    if ru is not None:
        for i, slack in enumerate(np.asarray(ru, dtype=float).ravel()[:n]):
            if np.isfinite(slack) and slack <= active_tol:
                row = np.zeros(n, dtype=float)
                row[i] = 1.0
                bound_rows.append(row)
    if bound_rows:
        rows.append(np.vstack(bound_rows))

    # Add the objective hyperplane normal
    rows.append(np.asarray(c_eff, dtype=float).reshape(1, -1))

    if not rows:
        return None

    G = np.vstack([_to_dense_array(R) for R in rows])
    # Numerical rank
    r = np.linalg.matrix_rank(G, tol=1e-10)
    dim = max(0, n - int(r))
    return dim


def _postprocess_result(
    lp: Dict[str, Any],
    res,
    *,
    method: str,
) -> Tuple[str, Optional[float], Dict[str, float], Dict[str, Any]]:
    """
    Map SciPy result to the unified (status, objective, x_dict, extras) tuple.
    Also attaches HiGHS marginals (if present) and a light-weight check for
    alternate optimal solutions (multiple optima).
    """
    status = _map_status(res)

    # Compute objective value and variable mapping, if optimal
    if status == "Optimal" and getattr(res, "x", None) is not None:
        obj = float(res.fun)
        # Undo objective flip for original 'max' problems
        if lp["flip_obj"]:
            obj = -obj
        obj += lp["obj_offset"]
        x_dict = {name: float(val) for name, val in zip(lp["var_names"], res.x.tolist())}
    else:
        obj = None
        x_dict = {}

    # Base diagnostics always available to the UI
    extras: Dict[str, Any] = {
        "message": getattr(res, "message", None),
        "nit": getattr(res, "nit", None),
        "crossover_nit": getattr(res, "crossover_nit", None),
        "status_code": getattr(res, "status", None),
        "success": getattr(res, "success", None),
        "method": method,
    }

    # Attach HiGHS marginals/residuals if SciPy exposed them
    _attach_highs_marginals(res, extras)

    if status == "Optimal":
        # The authoritative alternate-optimum analysis is geometric:
        # solve min/max x_i on the optimal face c^T x = z*.  Marginals are kept
        # in extras for diagnostics, but they are not enough to decide uniqueness
        # because basic variables often have zero bound marginals even at a
        # unique optimum.
        should_compute_ranges, skip_reason = _should_compute_optimal_ranges(lp)
        if should_compute_ranges:
            extras["alt_opt"] = _compute_optimal_variable_ranges(
                lp, res, method=method, value_tol=1e-9, range_tol=1e-8
            )
            dim = _estimate_dimension_from_range_endpoints(lp, extras["alt_opt"])
            if dim is None:
                dim = _estimate_optimal_face_dimension(lp, res, active_tol=1e-8)
            if dim is not None:
                extras["alt_opt"]["dimension"] = int(dim)
                if dim >= 1:
                    extras["alt_opt"]["has_alternate_optimum"] = True
        else:
            extras["alt_opt"] = {
                "has_alternate_optimum": False,
                "ranges": {},
                "varying_variables": [],
                "zero_reduced_cost_vars": [],
                "dimension": None,
                "range_skipped": True,
                "range_skip_reason": skip_reason,
            }

    if status == "Optimal":
        extras["var_names"] = lp["var_names"]
        extras["bounds"] = lp["bounds"]
        extras["x_values"] = getattr(res, "x", None).tolist() if getattr(res, "x", None) is not None else None
        extras["objective_sense"] = "max" if lp["flip_obj"] else "min"

    return status, obj, x_dict, extras


def _map_status(res) -> str:
    """
    Unify SciPy status codes into the project's 4-state outcome.

    Parameters
    ----------
    res : scipy.optimize.OptimizeResult | object

    Returns
    -------
    str
        "Optimal", "Infeasible", "Unbounded", or "NotSolved".
    """
    code = getattr(res, "status", None)
    success = getattr(res, "success", False)
    if code == 0 and success:
        return "Optimal"
    if code == 2:
        return "Infeasible"
    if code == 3:
        return "Unbounded"
    return "NotSolved"


def _attach_highs_marginals(res, extras: Dict[str, Any]) -> None:
    """
    Attach HiGHS marginals/residuals to `extras` if present.

    Parameters
    ----------
    res : scipy.optimize.OptimizeResult | object
        SciPy result; in recent versions, HiGHS exposes marginals in
        attributes: eqlin, ineqlin, lower, upper (each with .marginals/.residual).
    extras : dict
        The dictionary to be augmented with marginal/residual information.
    """
    def _grab(name: str):
        v = getattr(res, name, None)
        if v is None:
            return None
        return {
            "marginals": getattr(v, "marginals", None),
            "residual": getattr(v, "residual", None),
        }

    for key in ("eqlin", "ineqlin", "lower", "upper"):
        g = _grab(key)
        if g is not None:
            extras[key] = g

def _dedupe_proportional_inequalities(
    A: np.ndarray, b: np.ndarray, tol: float = 1e-10
) -> Tuple[np.ndarray, np.ndarray, int]:
    """
    Deduplicate proportional rows (same direction in coefficient space).
    For each direction, keep the tightest RHS (minimum along the same normalized normal).
    This is a safe reduction for <=-type inequalities of the form a^T x <= b.

    Important: opposite normals are not duplicates.  The pair x <= 1 and
    -x <= -2 represents x <= 1 and x >= 2, which is infeasible; merging them
    would change the feasible set.
    """
    m, n = A.shape

    # Normalize each row to a canonical representation: unit direction with stable sign
    # We also compute the effective b' associated with the normalized normal: since
    # (a^T x <= b) and a' = a / ||a||, we define b' = b / ||a||.
    keys: Dict[Tuple[int, ...], Tuple[int, float]] = {}  # direction key -> (row_index, b_prime_kept)
    zero_keep_indices: List[int] = []

    for i in range(m):
        a = A[i, :]
        norm = np.linalg.norm(a, ord=2)
        if norm <= tol:
            # Zero row: either infeasible (if b < 0) or redundant (if b >= 0). Keep if b < 0?
            # We conservatively drop non-restrictive zero-rows with b >= 0; if b < 0 this LP is infeasible,
            # but we prefer to leave detection to the solver. Keep the row as-is in that case.
            if b[i] >= 0:
                continue
            else:
                zero_keep_indices.append(i)
                continue

        a_norm = a / norm
        b_prime = b[i] / norm

        # Build a hashable key by quantizing to tolerance
        # (Floating point hashing is tricky; quantization is robust here.)
        quant = np.round(a_norm / max(tol, 1e-12)).astype(int)
        key = tuple(quant.tolist())

        if key not in keys:
            keys[key] = (i, b_prime)
        else:
            kept_idx, kept_bprime = keys[key]
            # Keep the tightest inequality along this direction: min(b')
            if b_prime < kept_bprime - 1e-14:
                # Current row is tighter: replace previously kept row
                keys[key] = (i, b_prime)
                # mark previous as removed and current as kept (handled by final collect)

    # Collect final row indices to keep (from keys)
    keep_indices = sorted(zero_keep_indices + [idx for (idx, _bp) in keys.values()])
    A_new = A[keep_indices, :]
    b_new = b[keep_indices]
    removed = int(m - len(keep_indices))
    return A_new, b_new, removed


def _reduce_equalities_preserving_feasibility(
    A: np.ndarray,
    b: np.ndarray,
    *,
    tol: float = 1e-10,
) -> Tuple[np.ndarray, np.ndarray, int, int]:
    """
    Remove only equality rows that are truly redundant.

    Mathematics:
      An equality row a^T x = beta is redundant with previously kept rows
      only if the augmented row [a | beta] lies in the row span of the kept
      augmented system [A_kept | b_kept].  If a is dependent but [a | beta]
      is not, the system is inconsistent; we keep the row so the solver can
      correctly report infeasibility.
    """
    keep_indices: List[int] = []
    inconsistent_dependents = 0

    for i in range(A.shape[0]):
        a = A[i, :].reshape(1, -1)
        beta = np.array([[float(b[i])]], dtype=float)

        if np.linalg.norm(a, ord=2) <= tol:
            if abs(float(b[i])) > tol:
                keep_indices.append(i)
                inconsistent_dependents += 1
            continue

        if not keep_indices:
            keep_indices.append(i)
            continue

        kept_A = A[keep_indices, :]
        kept_b = b[keep_indices].reshape(-1, 1)

        rank_A = np.linalg.matrix_rank(kept_A, tol=tol)
        rank_A_new = np.linalg.matrix_rank(np.vstack([kept_A, a]), tol=tol)
        if rank_A_new > rank_A:
            keep_indices.append(i)
            continue

        kept_aug = np.hstack([kept_A, kept_b])
        row_aug = np.hstack([a, beta])
        rank_aug = np.linalg.matrix_rank(kept_aug, tol=tol)
        rank_aug_new = np.linalg.matrix_rank(np.vstack([kept_aug, row_aug]), tol=tol)
        if rank_aug_new > rank_aug:
            keep_indices.append(i)
            inconsistent_dependents += 1

    keep_indices = sorted(keep_indices)
    removed = int(A.shape[0] - len(keep_indices))
    return A[keep_indices, :], b[keep_indices], removed, inconsistent_dependents


# ---------- Analysis helpers ----------

def pre_process_lp_data(
    problem: Dict[str, Any],
    *,
    normalize: bool = True,
    scale: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Lightweight pre-processing: drops redundant constraints safely.
    - Equality constraints (A_eq): remove only rows whose full augmented
      equation [a | b] is implied by the kept rows.
    - Inequality constraints (A_ub <= b_ub): deduplicate only positive
      proportional rows and keep the tightest RHS along the same normal.
    """
    # Work on a shallow copy to avoid mutating caller's dict
    p = dict(problem)

    c = np.asarray(p["c"], dtype=float)
    n = int(c.shape[0])

    A_eq = p.get("A_eq", None)
    b_eq = p.get("b_eq", None)
    A_ub = p.get("A_ub", None)
    b_ub = p.get("b_ub", None)

    info: Dict[str, Any] = {
        "rows_kept": {"eqlin": None, "ineqlin": None},
        "rows_removed": {"eqlin": None, "ineqlin": None},
        "notes": [],
        "scaling": None,
    }

    # --- Equality constraints: keep a row-basis (independent rows) ---
    if A_eq is not None and b_eq is not None:
        if _too_large_to_densify(A_eq):
            info["notes"].append("Skipped equality preprocessing for large sparse matrix.")
        else:
            Aeq = _to_dense_array(A_eq)
            beq = np.asarray(b_eq, dtype=float)
            if Aeq.ndim != 2 or Aeq.shape[1] != n or beq.shape[0] != Aeq.shape[0]:
                raise ValueError("A_eq/b_eq shape mismatch in pre_process_lp_data.")

            Aeq_new, beq_new, removed, inconsistent = _reduce_equalities_preserving_feasibility(
                Aeq, beq, tol=1e-10
            )
            if removed > 0:
                info["notes"].append(f"Removed {removed} redundant equality rows.")
            if inconsistent > 0:
                info["notes"].append(
                    f"Kept {inconsistent} dependent equality rows because their RHS is inconsistent."
                )
            info["rows_kept"]["eqlin"] = int(Aeq_new.shape[0])
            info["rows_removed"]["eqlin"] = removed

            p["A_eq"] = Aeq_new
            p["b_eq"] = beq_new

    # --- Inequality constraints: dedupe proportional rows (safe) ---
    if A_ub is not None and b_ub is not None:
        if _too_large_to_densify(A_ub):
            info["notes"].append("Skipped inequality preprocessing for large sparse matrix.")
        else:
            Aub = _to_dense_array(A_ub)
            bub = np.asarray(b_ub, dtype=float)
            if Aub.ndim != 2 or Aub.shape[1] != n or bub.shape[0] != Aub.shape[0]:
                raise ValueError("A_ub/b_ub shape mismatch in pre_process_lp_data.")

            Aub_new, bub_new, removed = _dedupe_proportional_inequalities(Aub, bub, tol=1e-10)
            if removed > 0:
                info["notes"].append(f"Removed {removed} proportional duplicate inequality rows.")
            info["rows_kept"]["ineqlin"] = int(Aub_new.shape[0])
            info["rows_removed"]["ineqlin"] = int(Aub.shape[0] - Aub_new.shape[0])

            p["A_ub"] = Aub_new
            p["b_ub"] = bub_new

    # Optionally, future: scaling (not implemented)
    if scale:
        info["notes"].append("Scaling requested but not implemented; skipped.")

    return p, info



def perform_sensitivity_analysis(
    status: str,
    extras: Dict[str, Any],
    *,
    tol_slack: float = 1e-9,
    tol_rc: float = 1e-8,
) -> Dict[str, Any]:
    """
    Build a user-facing sensitivity snapshot using HiGHS marginals
    surfaced by SciPy's linprog (method='highs').

    Returns a structured dict with:
      - constraint shadow prices and slacks (eq/ineq)
      - per-variable basic/nonbasic hints and near-zero reduced-cost proxy
      - a compact "summary" for direct UI use

    Notes:
      * SciPy/HiGHS exposes, if available:
          extras["eqlin"]  -> {"marginals": [...], "residual": [...]}
          extras["ineqlin"]-> {"marginals": [...], "residual": [...]}
          extras["lower"]  -> {"marginals": [...], "residual": [...]}
          extras["upper"]  -> {"marginals": [...], "residual": [...]}
        Here:
          - "marginals" are dual prices for the associated constraints
            (KKT multipliers). For variables, "lower"/"upper" marginals
            are duals for the bound constraints x_i >= lb and x_i <= ub.
          - "residual" are primal slacks (>=0 for <= constraints; ==0 for eq).
      * SciPy does not expose reduced costs directly; we use a lightweight proxy:
            rc_proxy_i = argmin_{bound in {lower,upper}} |bound_marginal_i|
        and mark "near zero" if rc_proxy_i <= tol_rc. This is only a
        diagnostic hint; uniqueness is decided in solve_lp by optimizing
        variable ranges on the optimal face.

    If status != "Optimal" or required marginals are missing, returns {}.
    """
    if status != "Optimal":
        return {}

    eqlin = extras.get("eqlin")
    ineqlin = extras.get("ineqlin")
    lower = extras.get("lower")
    upper = extras.get("upper")

    if not (eqlin and ineqlin and lower and upper):
        # Sensitivity unavailable (backend/version did not expose marginals)
        return {}

    var_names: List[str] = extras.get("var_names") or []
    bounds: List[Tuple[Optional[float], Optional[float]]] = extras.get("bounds") or []
    x_values: Optional[List[float]] = extras.get("x_values")
    sense: str = extras.get("objective_sense", "min")

    ml = np.asarray(lower.get("marginals", []), dtype=float)
    mu = np.asarray(upper.get("marginals", []), dtype=float)
    rl = np.asarray(lower.get("residual", []), dtype=float)   # distance to lower bound
    ru = np.asarray(upper.get("residual", []), dtype=float)   # distance to upper bound

    me = np.asarray(eqlin.get("marginals", []), dtype=float)   # shadow prices (eq)
    re = np.asarray(eqlin.get("residual", []), dtype=float)    # slacks (should be ~0)
    mi = np.asarray(ineqlin.get("marginals", []), dtype=float) # shadow prices (ineq)
    ri = np.asarray(ineqlin.get("residual", []), dtype=float)  # slacks (>=0)

    n_vars = len(ml)
    # Guard against inconsistent shapes
    if n_vars == 0 or n_vars != len(mu):
        return {}

    # --- Constraint sensitivity ---
    constraints_eq = []
    for idx in range(len(me)):
        sp = float(me[idx])
        slack = float(re[idx]) if idx < len(re) else float("nan")
        constraints_eq.append({
            "index": idx,
            "shadow_price": sp,
            "slack": slack,
            "binding": abs(slack) <= tol_slack,
            "type": "eq",
        })

    constraints_ineq = []
    for idx in range(len(mi)):
        sp = float(mi[idx])
        slack = float(ri[idx]) if idx < len(ri) else float("nan")
        constraints_ineq.append({
            "index": idx,
            "shadow_price": sp,
            "slack": slack,
            "binding": slack <= tol_slack,  # <=-type: binding if slack ~ 0
            "type": "ineq",
        })

    # --- Variable-level sensitivity ---
    variables = []
    for i in range(n_vars):
        name = var_names[i] if i < len(var_names) else f"x{i}"
        lb, ub = bounds[i] if i < len(bounds) else (None, None)

        # Activity with respect to bounds
        slack_lb = float(rl[i]) if i < len(rl) else float("nan")
        slack_ub = float(ru[i]) if i < len(ru) else float("nan")
        at_lower = (not np.isnan(slack_lb)) and (slack_lb <= tol_slack)
        at_upper = (not np.isnan(slack_ub)) and (slack_ub <= tol_slack)

        # Reduced-cost proxy from bound marginals (near-zero -> indifference)
        d_lower = abs(float(ml[i])) if i < len(ml) else float("inf")
        d_upper = abs(float(mu[i])) if i < len(mu) else float("inf")
        rc_proxy = min(d_lower, d_upper)  # non-negative
        near_zero_rc = rc_proxy <= tol_rc

        variables.append({
            "index": i,
            "name": name,
            "value": None if x_values is None or i >= len(x_values) else float(x_values[i]),
            "lower_bound": lb,
            "upper_bound": ub,
            "at_lower_bound": at_lower,
            "at_upper_bound": at_upper,
            "dual_lower_bound": float(ml[i]) if i < len(ml) else None,
            "dual_upper_bound": float(mu[i]) if i < len(mu) else None,
            "reduced_cost_proxy": rc_proxy,
            "near_zero_reduced_cost": near_zero_rc,
        })

    # --- Summary (good for UI badges / chips) ---
    num_binding_eq = sum(1 for c in constraints_eq if c["binding"])
    num_binding_ineq = sum(1 for c in constraints_ineq if c["binding"])
    num_indifferent_vars = sum(1 for v in variables if v["near_zero_reduced_cost"])

    summary = {
        "objective_sense": sense,
        "binding_constraints": {
            "eq": num_binding_eq,
            "ineq": num_binding_ineq,
            "total": num_binding_eq + num_binding_ineq,
        },
        "indifferent_variables_near_zero_rc": num_indifferent_vars,
        # Reuse the earlier detection if present
        "has_alternate_optimum": bool(
            extras.get("alt_opt", {}).get("has_alternate_optimum", num_indifferent_vars > 0)
        ),
    }

    return {
        "summary": summary,
        "constraints": {
            "equality": constraints_eq,
            "inequality": constraints_ineq,
        },
        "variables": variables,
    }
