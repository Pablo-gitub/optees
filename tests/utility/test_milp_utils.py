# tests/utility/test_milp_utils.py
import unittest
import importlib

# Skip intero file se OR-Tools non è installato
HAVE_ORTOOLS = importlib.util.find_spec("ortools") is not None
from optees.utility.milp_utils import solve_milp
from optees.utility.data_adapters.knapsack_burkardt_adapter import load_knapsack_burkardt


@unittest.skipUnless(HAVE_ORTOOLS, "ortools not installed")
class TestSolveMILP(unittest.TestCase):

    def test_assignment_2x2_min(self):
        # Variables: x11, x12, x21, x22 ∈ {0,1}
        # Minimize: 1*x11 + 2*x12 + 2*x21 + 1*x22
        # Row sums: x11 + x12 = 1; x21 + x22 = 1
        # Col sums: x11 + x21 = 1; x12 + x22 = 1
        c = [1, 2, 2, 1]
        A_eq = [
            [1, 1, 0, 0],  # row1
            [0, 0, 1, 1],  # row2
            [1, 0, 1, 0],  # col1
            [0, 1, 0, 1],  # col2
        ]
        b_eq = [1, 1, 1, 1]
        bounds = [(0, 1)] * 4
        integrality = ["B"] * 4
        names = ["x11", "x12", "x21", "x22"]

        prob = {
            "sense": "min",
            "c": c,
            "A_eq": A_eq, "b_eq": b_eq,
            "bounds": bounds,
            "integrality": integrality,
            "var_names": names,
        }
        status, obj, x, extras = solve_milp(prob)

        self.assertEqual(status, "Optimal")
        self.assertAlmostEqual(obj, 2.0, places=9)
        self.assertAlmostEqual(x["x11"], 1.0, places=9)
        self.assertAlmostEqual(x["x22"], 1.0, places=9)
        self.assertAlmostEqual(x["x12"], 0.0, places=9)
        self.assertAlmostEqual(x["x21"], 0.0, places=9)

    def test_knapsack_p01_max(self):
        # Usa l'istanza p01 già presente in tests/data/knapsack/p01/
        data = load_knapsack_burkardt("tests/data/knapsack/p01", "p01")
        v, w, C = data["values"], data["weights"], data["capacity"]
        sel = data["opt_selection"]
        self.assertIsNotNone(sel, "p01_s.txt is required for this test")

        n = len(v)
        prob = {
            "sense": "max",
            "c": list(v),
            "A_ub": [list(w)],   # single <= capacity
            "b_ub": [C],
            "bounds": [(0, 1)] * n,
            "integrality": ["B"] * n,
            "var_names": [f"i{k}" for k in range(n)],
        }
        status, obj, x, extras = solve_milp(prob)
        self.assertEqual(status, "Optimal")

        # expected selection and value from ground truth
        expected_idx = [i for i, s in enumerate(sel) if s == 1]
        expected_val = float(sum(v[i] for i in expected_idx))
        picked_idx = [i for i, name in enumerate(prob["var_names"]) if x.get(name, 0.0) > 0.5]

        self.assertEqual(picked_idx, expected_idx)
        self.assertAlmostEqual(obj, expected_val, places=9)

    def test_infeasible(self):
        # x1, x2 ∈ {0,1}, and x1 + x2 = 3  → infeasible
        prob = {
            "sense": "min",
            "c": [0.0, 0.0],
            "A_eq": [[1.0, 1.0]], "b_eq": [3.0],
            "bounds": [(0, 1), (0, 1)],
            "integrality": ["B", "B"],
            "var_names": ["x1", "x2"],
        }
        status, obj, x, extras = solve_milp(prob)
        self.assertEqual(status, "Infeasible")
        self.assertIsNone(obj)
        self.assertEqual(x, {})


if __name__ == "__main__":
    unittest.main()
