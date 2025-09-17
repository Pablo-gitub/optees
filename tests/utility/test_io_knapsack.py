# tests/utility/test_io_knapsack.py
import os
import unittest
import numpy as np

from optees.utility.data_adapters.knapsack_burkardt_adapter import load_knapsack_burkardt
from optees.utility.knapsack_utils import solve_knapsack_01
# in alternativa, se hai re-export:
# from src.optees.utility.lp_utils import solve_knapsack as solve_knapsack_01

P01_DIR = "tests/data/knapsack/p01"
P01_INST = "p01"

@unittest.skipUnless(
    os.path.exists(os.path.join(P01_DIR, f"{P01_INST}_c.txt")),
    "p01 files not found",
)
class TestKnapsackBurkardt(unittest.TestCase):
    def test_p01_optimal_matches_selection(self):
        data = load_knapsack_burkardt(P01_DIR, P01_INST)
        v, w, C = data["values"], data["weights"], data["capacity"]
        sel = data["opt_selection"]
        self.assertIsNotNone(sel, "p01_s.txt (optimal selection) is required for this test")

        best_value, idx = solve_knapsack_01(v, w, C)

        # expected indices from selection vector
        expected_idx = [i for i, s in enumerate(sel) if s == 1]
        self.assertEqual(idx, expected_idx)

        # expected objective value
        expected_value = float(sum(v[i] for i in expected_idx))
        self.assertAlmostEqual(best_value, expected_value, places=9)

        # quick feasibility check on capacity
        total_w = sum(w[i] for i in idx)
        self.assertLessEqual(total_w, C)
