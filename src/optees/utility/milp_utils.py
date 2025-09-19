from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from ortools.sat.python import cp_model
from ortools.linear_solver import pywraplp

__all__ = ["solve_milp"]


def solve_milp(
    problem: Dict[str, Any], *, time_limit: Optional[float] = None
) -> Tuple[str, Optional[float], Dict[str, float], Dict[str, Any]]:
    P = _normalize(problem)

    # Se c'è una variabile continua o dati non interi -> CBC
    if _needs_cbc(P):
        return _solve_mip_cbc_mixed(P, time_limit=time_limit)

    # Altrimenti CP-SAT (tutto intero e coefficienti interi)
    model, xs = _build_model(P)
    solver, status_code = _solve_model(model, time_limit=time_limit)
    return _pack_result(solver, status_code, xs, P)


# ----------------- helpers -----------------

def _solve_mip_cbc_mixed(P, time_limit=None):
    solver = pywraplp.Solver.CreateSolver("CBC")
    if solver is None:
        return "NotSolved", None, {}, {"error": "CBC solver not available"}

    if time_limit:
        solver.SetTimeLimit(int(time_limit * 1000))

    sense = P.get("sense", "min").lower()
    c = P["c"]
    bounds = P.get("bounds", [(0, None)] * len(c))
    integrality = P.get("integrality", [None] * len(c))
    names = P.get("var_names", [f"x{i}" for i in range(len(c))])

    xs = []
    inf = solver.infinity()
    for i, (lb, ub) in enumerate(bounds):
        lb = 0.0 if lb is None else float(lb)
        ubv = inf if ub is None else float(ub)
        integ = integrality[i]
        name = names[i]
        if integ in ("B", "I"):
            if integ == "B":
                ubv = min(ubv, 1.0)
            x = solver.IntVar(lb, ubv, name)
        else:
            x = solver.NumVar(lb, ubv, name)
        xs.append(x)

    # A_eq / b_eq
    A_eq, b_eq = P.get("A_eq"), P.get("b_eq")
    if A_eq is not None and b_eq is not None:
        for row, rhs in zip(A_eq, b_eq):
            solver.Add(sum(float(a) * x for a, x in zip(row, xs)) == float(rhs))

    # A_ub / b_ub
    A_ub, b_ub = P.get("A_ub"), P.get("b_ub")
    if A_ub is not None and b_ub is not None:
        for row, rhs in zip(A_ub, b_ub):
            solver.Add(sum(float(a) * x for a, x in zip(row, xs)) <= float(rhs))

    # objective
    expr = sum(float(ci) * x for ci, x in zip(c, xs))
    if sense == "min":
        solver.Minimize(expr)
    else:
        solver.Maximize(expr)

    res = solver.Solve()

    if res == pywraplp.Solver.OPTIMAL:
        status = "Optimal"
    elif res == pywraplp.Solver.INFEASIBLE:
        status = "Infeasible"
    elif res == pywraplp.Solver.UNBOUNDED:
        status = "Unbounded"
    else:
        status = "NotSolved"

    if status == "Optimal":
        obj = solver.Objective().Value()
        xdict = {n: xs[i].solution_value() for i, n in enumerate(names)}
    else:
        obj = None
        xdict = {}

    extras = {"result_status": int(res), "wall_time_ms": solver.wall_time()}
    return status, obj, xdict, extras

def _normalize(problem: Dict[str, Any]) -> Dict[str, Any]:
    sense = (problem.get("sense", "min") or "min").lower()
    if sense not in ("min", "max"):
        raise ValueError("problem['sense'] must be 'min' or 'max'.")

    c = list(problem["c"])
    n = len(c)

    # integrality: 'B' | 'I' | None (o 'C' -> None)
    integ_in = problem.get("integrality", [None] * n)
    if len(integ_in) != n:
        raise ValueError("len(integrality) must match len(c).")
    integrality = []
    for t in integ_in:
        if t in ("B", "I", None):
            integrality.append(t)
        elif t == "C":
            integrality.append(None)
        else:
            raise ValueError(f"Unknown integrality token: {t!r}")

    bounds_in = problem.get("bounds")
    if bounds_in is None:
        bounds = [(0, None)] * n
    else:
        if len(bounds_in) != n:
            raise ValueError("len(bounds) must match len(c).")
        bounds = [(lb, ub) for (lb, ub) in bounds_in]

    names = problem.get("var_names") or [f"x{i}" for i in range(n)]
    if len(names) != n:
        raise ValueError("len(var_names) must match len(c).")

    A_eq, b_eq = problem.get("A_eq"), problem.get("b_eq")
    if (A_eq is None) ^ (b_eq is None):
        raise ValueError("A_eq and b_eq must be both present or both absent.")
    A_ub, b_ub = problem.get("A_ub"), problem.get("b_ub")
    if (A_ub is None) ^ (b_ub is None):
        raise ValueError("A_ub and b_ub must be both present or both absent.")

    return dict(
        sense=sense, c=c, n=n,
        integrality=integrality,
        bounds=bounds,
        var_names=names,
        A_eq=A_eq, b_eq=b_eq,
        A_ub=A_ub, b_ub=b_ub,
        obj_offset=float(problem.get("obj_offset", 0.0)),
    )


def _as_int(x: float, name: str) -> int:
    r = round(float(x))
    if abs(float(x) - r) > 1e-9:
        raise ValueError(f"{name} must be integer-like for CP-SAT, got {x!r}")
    return int(r)


def _build_model(P: Dict[str, Any]) -> Tuple[cp_model.CpModel, List[cp_model.IntVar]]:
    m = cp_model.CpModel()

    # variables
    xs: List[cp_model.IntVar] = []
    for i in range(P["n"]):
        kind = P["integrality"][i]
        name = P["var_names"][i]
        lb, ub = P["bounds"][i]

        if kind == "B":
            xs.append(m.NewBoolVar(name))
            continue

        lo = _as_int(0 if lb is None else lb, f"lb[{i}]")
        hi = 10**9 if ub is None else _as_int(ub, f"ub[{i}]")
        if lo > hi:
            raise ValueError(f"Invalid bounds for {name}: [{lo}, {hi}]")
        xs.append(m.NewIntVar(lo, hi, name))

    # equality constraints
    if P["A_eq"] is not None:
        if len(P["A_eq"]) != len(P["b_eq"]):
            raise ValueError("len(A_eq) must match len(b_eq).")
        for r, (row, rhs) in enumerate(zip(P["A_eq"], P["b_eq"])):
            if len(row) != P["n"]:
                raise ValueError("A_eq row length must match n.")
            coeffs = [_as_int(aij, f"A_eq[{r},{j}]") for j, aij in enumerate(row)]
            m.Add(sum(coeffs[j] * xs[j] for j in range(P["n"])) == _as_int(rhs, f"b_eq[{r}]"))

    # <= constraints
    if P["A_ub"] is not None:
        if len(P["A_ub"]) != len(P["b_ub"]):
            raise ValueError("len(A_ub) must match len(b_ub).")
        for r, (row, rhs) in enumerate(zip(P["A_ub"], P["b_ub"])):
            if len(row) != P["n"]:
                raise ValueError("A_ub row length must match n.")
            coeffs = [_as_int(aij, f"A_ub[{r},{j}]") for j, aij in enumerate(row)]
            m.Add(sum(coeffs[j] * xs[j] for j in range(P["n"])) <= _as_int(rhs, f"b_ub[{r}]"))

    # objective
    coefs = [_as_int(ci, f"c[{i}]") for i, ci in enumerate(P["c"])]
    lin = sum(coefs[i] * xs[i] for i in range(P["n"]))
    m.Minimize(lin) if P["sense"] == "min" else m.Maximize(lin)

    return m, xs


def _solve_model(model: cp_model.CpModel, *, time_limit: Optional[float]
                 ) -> Tuple[cp_model.CpSolver, int]:
    solver = cp_model.CpSolver()
    if time_limit and time_limit > 0:
        solver.parameters.max_time_in_seconds = float(time_limit)
    solver.parameters.num_search_workers = 8
    status_code = solver.Solve(model)          # <— QUI: status code dalla Solve
    return solver, status_code


def _pack_result(
    solver: cp_model.CpSolver, status_code: int, xs: List[cp_model.IntVar], P: Dict[str, Any]
) -> Tuple[str, Optional[float], Dict[str, float], Dict[str, Any]]:
    if status_code == cp_model.OPTIMAL:
        status = "Optimal"
    elif status_code == cp_model.INFEASIBLE:
        status = "Infeasible"
    else:
        status = "NotSolved"

    x_dict: Dict[str, float] = {}
    obj: Optional[float] = None
    if status == "Optimal":
        for i, v in enumerate(xs):
            x_dict[P["var_names"][i]] = float(solver.Value(v))
        obj = float(solver.ObjectiveValue() + P["obj_offset"])

    # BestObjectiveBound() è disponibile in CP-SAT recenti; difendiamoci comunque
    best_bound = None
    if hasattr(solver, "BestObjectiveBound"):
        try:
            best_bound = solver.BestObjectiveBound()
        except Exception:
            best_bound = None

    extras: Dict[str, Any] = {
        "status_code": int(status_code),
        "status_str": solver.StatusName(status_code),
        "best_bound": best_bound,
        "wall_time": solver.WallTime(),
        "conflicts": solver.NumConflicts(),
        "branches": solver.NumBranches(),
    }
    return status, obj, x_dict, extras

def _is_int_like(x: float, tol: float = 1e-9) -> bool:
    xf = float(x)
    return abs(xf - round(xf)) <= tol

def _all_data_integer(P: Dict[str, Any]) -> bool:
    # c
    if not all(_is_int_like(ci) for ci in P["c"]):
        return False
    # bounds
    for lb, ub in P["bounds"]:
        if lb is not None and not _is_int_like(lb): return False
        if ub is not None and not _is_int_like(ub): return False
    # A_eq/b_eq
    if P["A_eq"] is not None:
        if not all(all(_is_int_like(a) for a in row) for row in P["A_eq"]):
            return False
        if not all(_is_int_like(b) for b in P["b_eq"]):
            return False
    # A_ub/b_ub
    if P["A_ub"] is not None:
        if not all(all(_is_int_like(a) for a in row) for row in P["A_ub"]):
            return False
        if not all(_is_int_like(b) for b in P["b_ub"]):
            return False
    return True

def _needs_cbc(P: Dict[str, Any]) -> bool:
    has_continuous = any(t not in ("B", "I") for t in P["integrality"])
    if has_continuous:
        return True
    if not _all_data_integer(P):
        return True
    return False
