from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np
import scipy.sparse as sp

from optees.application.ports.qp_solver_port import QPSolverPort


def _has_feasible_candidate(
    candidate: Any,
    rows: list[list[float]],
    lower: list[float],
    upper: list[float],
    *,
    tolerance: float,
) -> bool:
    """Accept an early-stopped candidate only after a primal-feasibility check."""
    if candidate is None:
        return False
    x = np.asarray(candidate, dtype=float)
    if x.ndim != 1 or not np.all(np.isfinite(x)):
        return False
    if not rows:
        return True
    matrix = np.asarray(rows, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != x.shape[0]:
        return False
    activity = matrix @ x
    lower_arr = np.asarray(lower, dtype=float)
    upper_arr = np.asarray(upper, dtype=float)
    return bool(
        np.all(activity >= lower_arr - tolerance) and np.all(activity <= upper_arr + tolerance)
    )


class OSQPSolverAdapter(QPSolverPort):
    """Concrete adapter that interfaces with the OSQP solver library."""

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        try:
            import osqp
        except ImportError as exc:
            return {
                "status": "NotSolved",
                "mathematical_status": "not_solved",
                "termination_reason": "dependency_failure",
                "objective": None,
                "x": {},
                "dual_values": None,
                "kkt_residuals": None,
                "extras": {
                    "backend": "osqp",
                    "backend_version": None,
                    "message": f"OSQP is not installed: {exc}",
                    "success": False,
                },
            }

        sense = str(problem.get("sense", "min")).strip().lower()
        is_max = sense == "max"
        var_names: List[str] = list(problem.get("variables", []))
        n = len(var_names)

        # Raw matrix Q, vector c, offset alpha
        raw_Q = np.array(problem.get("Q", np.zeros((n, n), dtype=float)), dtype=float)
        raw_c = np.array(problem.get("c", np.zeros(n, dtype=float)), dtype=float)
        raw_offset = float(problem.get("offset", 0.0))

        # Objective transformation for minimization vs maximization:
        # min 0.5 x^T Q x + c^T x + alpha
        # For max: maximize f(x) <=> minimize -f(x) = 0.5 x^T (-Q) x + (-c)^T x - alpha
        if is_max:
            P_mat = -raw_Q
            q_vec = -raw_c
        else:
            P_mat = raw_Q
            q_vec = raw_c

        # Convert P to upper triangular CSC matrix as expected by OSQP
        P_csc = sp.triu(P_mat, format="csc")

        # Build constraints and bounds
        constraints = problem.get("constraints", [])
        m_cons = len(constraints)
        bounds = problem.get("bounds", [(None, None)] * n)

        A_rows = []
        l_bounds = []
        u_bounds = []

        # 1. Explicit linear constraints
        for cons in constraints:
            coefs = [float(v) for v in cons.get("coefs", [0.0] * n)]
            rhs_val = float(cons.get("rhs", 0.0))
            rel = str(cons.get("relation", "<=")).strip()
            A_rows.append(coefs)
            if rel == "=":
                l_bounds.append(rhs_val)
                u_bounds.append(rhs_val)
            elif rel == "<=":
                l_bounds.append(-np.inf)
                u_bounds.append(rhs_val)
            elif rel == ">=":
                l_bounds.append(rhs_val)
                u_bounds.append(np.inf)
            else:
                # Default to <= if unrecognized
                l_bounds.append(-np.inf)
                u_bounds.append(rhs_val)

        # 2. Box bounds (as identity rows)
        has_bounds = False
        for i in range(n):
            lb, ub = bounds[i] if i < len(bounds) else (None, None)
            if lb is not None or ub is not None:
                has_bounds = True
            row = [0.0] * n
            row[i] = 1.0
            A_rows.append(row)
            l_bounds.append(float(lb) if lb is not None else -np.inf)
            u_bounds.append(float(ub) if ub is not None else np.inf)

        total_rows = len(A_rows)
        if total_rows > 0 and (m_cons > 0 or has_bounds):
            A_csc = sp.csc_matrix(np.array(A_rows, dtype=float))
            l_arr = np.array(l_bounds, dtype=float)
            u_arr = np.array(u_bounds, dtype=float)
        else:
            A_csc = None
            l_arr = None
            u_arr = None

        options = problem.get("options", {})
        tol = float(options.get("tolerance", 1e-7))
        max_iter = int(options.get("max_iterations", 4000))
        time_limit = float(options.get("time_limit_seconds", 60.0))

        prob = osqp.OSQP()
        setup_kwargs: Dict[str, Any] = {
            "P": P_csc,
            "q": q_vec,
            "verbose": False,
            "eps_abs": tol,
            "eps_rel": tol,
            "eps_prim_inf": tol,
            "eps_dual_inf": tol,
            "max_iter": max_iter,
            "time_limit": time_limit,
            "polish": True,
        }
        if A_csc is not None:
            setup_kwargs["A"] = A_csc
            setup_kwargs["l"] = l_arr
            setup_kwargs["u"] = u_arr

        try:
            prob.setup(**setup_kwargs)
            res = prob.solve()
        except Exception as exc:
            return {
                "status": "NotSolved",
                "mathematical_status": "not_solved",
                "termination_reason": "internal_error",
                "objective": None,
                "x": {},
                "dual_values": None,
                "kkt_residuals": None,
                "extras": {
                    "backend": "osqp",
                    "backend_version": getattr(osqp, "__version__", None),
                    "message": str(exc),
                    "success": False,
                },
            }

        osqp_status = str(res.info.status).strip().lower()
        status_val = int(res.info.status_val)
        backend_version = getattr(osqp, "__version__", None)

        diagnostics = {
            "backend": "osqp",
            "backend_version": backend_version,
            "status": res.info.status,
            "status_code": status_val,
            "iterations": int(res.info.iter),
            "solve_time_seconds": float(res.info.solve_time),
            "setup_time_seconds": float(res.info.setup_time),
            "pri_res": float(res.info.pri_res) if res.info.pri_res is not None else None,
            "dua_res": float(res.info.dua_res) if res.info.dua_res is not None else None,
        }

        # Map OSQP status to Optees status and termination reason
        if osqp_status in ("solved", "solved inaccurate"):
            is_optimal = osqp_status == "solved"
            status = "Optimal" if is_optimal else "Feasible"
            math_status = "optimal" if is_optimal else "feasible"
            termination_reason = "completed"

            x_arr = np.array(res.x, dtype=float) if res.x is not None else np.zeros(n, dtype=float)
            x_dict = {var_names[i]: float(x_arr[i]) for i in range(n)}

            # Recompute objective in original sense
            f_val = 0.5 * float(x_arr.T @ raw_Q @ x_arr) + float(raw_c.T @ x_arr) + raw_offset

            # Extract dual values
            y_arr = np.array(res.y, dtype=float) if res.y is not None else None
            dual_dict: Optional[Dict[str, Any]] = None
            if (
                y_arr is not None
                and A_csc is not None
                and len(y_arr) == total_rows
                and total_rows > 0
            ):
                # Multipliers for linear constraints (0 .. m_cons - 1)
                cons_duals = []
                for i in range(m_cons):
                    y_i = float(y_arr[i])
                    cons_duals.append(y_i)

                # Multipliers for bounds (m_cons .. m_cons + n - 1)
                lb_duals = []
                ub_duals = []
                for i in range(n):
                    idx = m_cons + i
                    y_i = float(y_arr[idx])
                    # In OSQP, y_i <= 0 means lower bound is active (multiplier -y_i >= 0),
                    # y_i >= 0 means upper bound is active (multiplier y_i >= 0).
                    z_lb = max(0.0, -y_i)
                    z_ub = max(0.0, y_i)
                    lb_duals.append(z_lb)
                    ub_duals.append(z_ub)

                dual_dict = {
                    "constraints": cons_duals,
                    "lower_bounds": lb_duals,
                    "upper_bounds": ub_duals,
                }

            kkt_dict = {
                "primal_residual": float(res.info.pri_res)
                if res.info.pri_res is not None
                else None,
                "dual_residual": float(res.info.dua_res) if res.info.dua_res is not None else None,
                "duality_gap": None,
                "complementarity_residual": None,
            }

            return {
                "status": status,
                "mathematical_status": math_status,
                "termination_reason": termination_reason,
                "objective": f_val,
                "x": x_dict,
                "dual_values": dual_dict,
                "kkt_residuals": kkt_dict,
                "extras": diagnostics,
            }

        elif "primal infeasible" in osqp_status:
            return {
                "status": "Infeasible",
                "mathematical_status": "infeasible",
                "termination_reason": "completed",
                "objective": None,
                "x": {},
                "dual_values": None,
                "kkt_residuals": None,
                "extras": diagnostics,
            }

        elif "dual infeasible" in osqp_status:
            return {
                "status": "Unbounded",
                "mathematical_status": "unbounded",
                "termination_reason": "completed",
                "objective": None,
                "x": {},
                "dual_values": None,
                "kkt_residuals": None,
                "extras": diagnostics,
            }

        elif "iteration" in osqp_status:
            # Check if there is a finite candidate
            has_candidate = _has_feasible_candidate(
                res.x, A_rows, l_bounds, u_bounds, tolerance=tol
            )
            status = "Feasible" if has_candidate else "NotSolved"
            math_status = "feasible" if has_candidate else "not_solved"
            x_dict = {var_names[i]: float(res.x[i]) for i in range(n)} if has_candidate else {}
            f_val = None
            if has_candidate:
                x_arr = np.array(res.x, dtype=float)
                f_val = 0.5 * float(x_arr.T @ raw_Q @ x_arr) + float(raw_c.T @ x_arr) + raw_offset
            return {
                "status": status,
                "mathematical_status": math_status,
                "termination_reason": "iteration_limit",
                "objective": f_val,
                "x": x_dict,
                "dual_values": None,
                "kkt_residuals": None,
                "extras": diagnostics,
            }

        elif "time limit" in osqp_status or "time" in osqp_status:
            has_candidate = _has_feasible_candidate(
                res.x, A_rows, l_bounds, u_bounds, tolerance=tol
            )
            status = "Feasible" if has_candidate else "NotSolved"
            math_status = "feasible" if has_candidate else "not_solved"
            x_dict = {var_names[i]: float(res.x[i]) for i in range(n)} if has_candidate else {}
            f_val = None
            if has_candidate:
                x_arr = np.array(res.x, dtype=float)
                f_val = 0.5 * float(x_arr.T @ raw_Q @ x_arr) + float(raw_c.T @ x_arr) + raw_offset
            return {
                "status": status,
                "mathematical_status": math_status,
                "termination_reason": "time_limit",
                "objective": f_val,
                "x": x_dict,
                "dual_values": None,
                "kkt_residuals": None,
                "extras": diagnostics,
            }

        else:
            return {
                "status": "NotSolved",
                "mathematical_status": "not_solved",
                "termination_reason": "internal_error",
                "objective": None,
                "x": {},
                "dual_values": None,
                "kkt_residuals": None,
                "extras": diagnostics,
            }
