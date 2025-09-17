# tests/utility/test_lp_utils.py
import os
import unittest
import numpy as np

from optees.utility.lp_utils import solve_lp
from optees.utility.data_adapters.lpnetlib_adapter import load_lpnetlib_mat


# -----------------------------
# Tiny unit tests (toy models)
# -----------------------------
class TestSolveLP(unittest.TestCase):
    def test_feasible_min_optimal(self):
        # Min z = 3x + 2y
        # s.t. x + y >= 4  ->  -x - y <= -4
        #      x, y >= 0
        problem = {
            "sense": "min",
            "c": [3.0, 2.0],
            "A_ub": [[-1.0, -1.0]],
            "b_ub": [-4.0],
            "bounds": [[0.0, None], [0.0, None]],
            "var_names": ["x", "y"],
        }
        status, obj, x, extras = solve_lp(problem, method="highs")
        self.assertEqual(status, "Optimal")
        self.assertIsInstance(obj, float)
        # expected: x=0, y=4, obj=8
        self.assertAlmostEqual(obj, 8.0, places=6)
        self.assertAlmostEqual(x["x"], 0.0, places=6)
        self.assertAlmostEqual(x["y"], 4.0, places=6)

    def test_feasible_max_optimal(self):
        # Max z = 3x + 2y
        # s.t. x + y <= 4; x <= 2; y <= 3; x,y >= 0
        problem = {
            "sense": "max",
            "c": [3.0, 2.0],
            "A_ub": [
                [1.0, 1.0],
                [1.0, 0.0],
                [0.0, 1.0],
            ],
            "b_ub": [4.0, 2.0, 3.0],
            "bounds": [[0.0, None], [0.0, None]],
            "var_names": ["x", "y"],
        }
        status, obj, x, extras = solve_lp(problem, method="highs")
        self.assertEqual(status, "Optimal")
        # expected: x=2, y=2, z=10
        self.assertAlmostEqual(obj, 10.0, places=6)
        self.assertAlmostEqual(x["x"], 2.0, places=6)
        self.assertAlmostEqual(x["y"], 2.0, places=6)

    def test_infeasible(self):
        # Infeasible: x <= 0 but bound forces x >= 1
        problem = {
            "sense": "min",
            "c": [1.0, 1.0],
            "A_ub": [[1.0, 0.0]],
            "b_ub": [0.0],
            "bounds": [[1.0, None], [0.0, None]],
            "var_names": ["x", "y"],
        }
        status, obj, x, extras = solve_lp(problem, method="highs")
        self.assertEqual(status, "Infeasible")
        self.assertIsNone(obj)
        self.assertEqual(x, {})

    def test_unbounded(self):
        # Unbounded (MAX): Max z = x + y, s.t. y <= x, x,y >= 0
        problem = {
            "sense": "max",
            "c": [1.0, 1.0],
            "A_ub": [[-1.0, 1.0]],
            "b_ub": [0.0],
            "bounds": [[0.0, None], [0.0, None]],
            "var_names": ["x", "y"],
        }
        status, obj, x, extras = solve_lp(problem, method="highs")
        self.assertEqual(status, "Unbounded")
        self.assertIsNone(obj)
        self.assertEqual(x, {})

class TestSolveLPGuards(unittest.TestCase):
    def test_shape_pair_guard(self):
        with self.assertRaises(ValueError):
            solve_lp({"sense":"min","c":[1,2],"A_ub":[[1,0]], "bounds":[(0,None),(0,None)]})
        with self.assertRaises(ValueError):
            solve_lp({"sense":"min","c":[1,2],"b_ub":[1.0],      "bounds":[(0,None),(0,None)]})

    def test_var_names_length_guard(self):
        with self.assertRaises(ValueError):
            solve_lp({"sense":"min","c":[1,2],"var_names":["x0"],"bounds":[(0,None),(0,None)]})

    def test_bounds_length_guard(self):
        with self.assertRaises(ValueError):
            solve_lp({"sense":"min","c":[1,2],"bounds":[(0,None)]})

    def test_obj_offset_is_added(self):
        problem = {"sense":"min","c":[1.0,0.0],"bounds":[(0,None),(0,None)],"obj_offset":5.0}
        status, obj, x, _ = solve_lp(problem)
        self.assertEqual(status,"Optimal")
        self.assertAlmostEqual(obj, 5.0, places=9)  # x=0, so 1*0 + 5


# ---------------------------------------
# Smoke tests from LPnetlib (.mat files)
# ---------------------------------------
LP_DIR = "tests/data/lp/lpnetlib_mat"  # adjust if your folder is 'test/...'

AFIRO = os.path.join(LP_DIR, "lp_afiro.mat")
FV47  = os.path.join(LP_DIR, "lp_25fv47.mat")


class TestLPNetlibMAT(unittest.TestCase):
    TOL = 1e-6

    @unittest.skipUnless(os.path.exists(AFIRO), "lp_afiro.mat not found")
    def test_afiro_from_mat(self):
        problem = load_lpnetlib_mat(AFIRO)  # returns canonical dict (min, c, A_eq/A_ub, bounds, obj_offset?)
        status, obj, x, extras = solve_lp(problem, method="highs")
        self.assertEqual(status, "Optimal")
        self.assertIsInstance(obj, float)
        self._assert_feasible(problem, x, tol=self.TOL)
        self._assert_objective_consistency(problem, obj, x, tol=1e-7)

    @unittest.skipUnless(os.path.exists(FV47), "lp_25fv47.mat not found")
    def test_25fv47_from_mat(self):
        problem = load_lpnetlib_mat(FV47)
        status, obj, x, extras = solve_lp(problem, method="highs")
        self.assertEqual(status, "Optimal")
        self.assertIsInstance(obj, float)
        self._assert_feasible(problem, x, tol=self.TOL)
        self._assert_objective_consistency(problem, obj, x, tol=1e-7)

    # ---------- helpers for feasibility & objective checks ----------

    def _assert_feasible(self, problem, x_dict, *, tol: float):
        """Check Ax=b (eq), Ax<=b (ub) and variable bounds within tolerance."""
        # build x vector in declared variable order
        names = problem.get("var_names") or [f"x{i}" for i in range(len(problem["c"]))]
        x = np.array([x_dict[n] for n in names], dtype=float)

        # equality constraints
        A_eq = problem.get("A_eq")
        b_eq = np.asarray(problem.get("b_eq", []), dtype=float) if problem.get("b_eq") is not None else None
        if A_eq is not None and b_eq is not None:
            r = A_eq @ x - b_eq
            self.assertLessEqual(float(np.max(np.abs(r))), tol, "Eq constraints violated")

        # inequality constraints (<=)
        A_ub = problem.get("A_ub")
        b_ub = np.asarray(problem.get("b_ub", []), dtype=float) if problem.get("b_ub") is not None else None
        if A_ub is not None and b_ub is not None:
            r = A_ub @ x - b_ub
            self.assertLessEqual(float(np.max(r)), tol, "Ub constraints violated")

        # variable bounds
        bounds = problem.get("bounds")
        if bounds is not None:
            for i, (lb, ub) in enumerate(bounds):
                xi = float(x[i])
                if lb is not None:
                    self.assertGreaterEqual(xi + tol, lb, f"Lower bound violated at index {i}")
                if ub is not None and np.isfinite(ub):
                    self.assertLessEqual(xi - tol, ub, f"Upper bound violated at index {i}")

    def _assert_objective_consistency(self, problem, obj_reported: float, x_dict, *, tol: float):
        """Check reported objective equals c·x (+ obj_offset if present)."""
        names = problem.get("var_names") or [f"x{i}" for i in range(len(problem["c"]))]
        x = np.array([x_dict[n] for n in names], dtype=float)
        c = np.asarray(problem["c"], dtype=float)
        offset = float(problem.get("obj_offset", 0.0))
        obj_recomputed = float(c @ x + offset)
        self.assertAlmostEqual(obj_reported, obj_recomputed, delta=tol)
