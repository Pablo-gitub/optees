"""
Linear Programming (LP) utilities on top of SciPy/HiGHS.

Public surface:
- solve_lp(problem: dict, method="highs")
- pre_process_lp_data(...): stub
- perform_sensitivity_analysis(...): stub

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

try:
    # SciPy is the only dependency required for continuous LPs.
    from scipy.optimize import linprog
except Exception as e:  # allow import even if SciPy is missing
    linprog = None
    _scipy_import_error = e

__all__ = ["solve_lp", "pre_process_lp_data", "perform_sensitivity_analysis"]


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

    # Validate and normalize input problem into an internal structure.
    lp = _normalize_problem(problem)

    # Prepare arguments for SciPy's linprog.
    args = _build_linprog_args(lp)

    # Execute solver (isolated to keep error handling contained).
    res = _call_linprog(args, method=method)

    # Map SciPy result into our unified output tuple.
    return _postprocess_result(lp, res)


# ---------- Private helpers (single responsibility) ----------

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


def _postprocess_result(
    lp: Dict[str, Any],
    res
) -> Tuple[str, Optional[float], Dict[str, float], Dict[str, Any]]:
    """
    Map SciPy result to the unified (status, objective, x_dict, extras) tuple.

    Parameters
    ----------
    lp : dict
        Normalized internal LP dict from _normalize_problem.
    res : scipy.optimize.OptimizeResult | object
        Result of linprog (or the fallback _Fail object).

    Returns
    -------
    status : str
        One of {"Optimal", "Infeasible", "Unbounded", "NotSolved"}.
    objective : float | None
        Optimal objective value (including obj_offset), or None.
    x_dict : dict[str, float]
        Mapping variable name -> value for optimal solutions; {} otherwise.
    extras : dict
        Diagnostics: message, iterations, status_code, success flag,
        and HiGHS marginals/residuals if available.
    """
    status = _map_status(res)

    if status == "Optimal" and getattr(res, "x", None) is not None:
        obj = float(res.fun)
        # Restore original "max" sense if we had flipped the objective.
        if lp["flip_obj"]:
            obj = -obj
        obj += lp["obj_offset"]
        x_dict = {name: float(val) for name, val in zip(lp["var_names"], res.x.tolist())}
    else:
        obj = None
        x_dict = {}

    extras: Dict[str, Any] = {
        "message": getattr(res, "message", None),
        "nit": getattr(res, "nit", None),
        "crossover_nit": getattr(res, "crossover_nit", None),
        "status_code": getattr(res, "status", None),
        "success": getattr(res, "success", None),
    }
    _attach_highs_marginals(res, extras)
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


# ---------- Stubs (to be implemented later) ----------

def pre_process_lp_data(
    problem: Dict[str, Any],
    *,
    normalize: bool = True,
    scale: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    [Stub] Lightweight pre-processing hook.

    Parameters
    ----------
    problem : dict
        Canonical LP dictionary.
    normalize : bool, optional
        If True, normalize obvious patterns (e.g., clean bounds).
    scale : bool, optional
        If True, apply simple scaling (TBD).

    Returns
    -------
    new_problem : dict
        Possibly modified canonical LP dictionary.
    info : dict
        Metadata about the transformation (rows/cols kept, scaling factors, etc.).
    """
    return problem, {"rows_kept": None, "cols_kept": None, "scaling": None}


def perform_sensitivity_analysis(
    status: str,
    extras: Dict[str, Any],
) -> Dict[str, Any]:
    """
    [Stub] Turn HiGHS marginals into user-friendly sensitivity outputs.

    Parameters
    ----------
    status : str
        Solve status ("Optimal", "Infeasible", etc.). Sensitivity is only meaningful if "Optimal".
    extras : dict
        The `extras` dictionary returned by `solve_lp` (may contain HiGHS marginals).

    Returns
    -------
    dict
        Structured sensitivity data (shadow prices, reduced costs, ranges, ...).
        Empty dict for non-optimal cases or if marginals are not available.
    """
    return {}
