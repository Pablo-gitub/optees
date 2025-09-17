# tests/utility/test_knapsack_utils.py
import unittest
from optees.utility.knapsack_utils import solve_knapsack_01


class TestKnapsack01(unittest.TestCase):
    def test_small_example_optimal(self):
        # Classic tiny instance:
        # values=[3,4,5,6], weights=[2,3,4,5], capacity=5
        # Best is items {0,1} -> value=7, weight=5
        v = [3, 4, 5, 6]
        w = [2, 3, 4, 5]
        C = 5
        best, idx = solve_knapsack_01(v, w, C)
        self.assertAlmostEqual(best, 7.0, places=9)
        self.assertEqual(idx, [0, 1])

    def test_zero_capacity(self):
        v = [10, 20]
        w = [1, 2]
        best, idx = solve_knapsack_01(v, w, 0)
        self.assertEqual(best, 0.0)
        self.assertEqual(idx, [])

    def test_all_too_heavy(self):
        v = [10, 20]
        w = [100, 200]
        best, idx = solve_knapsack_01(v, w, 50)
        self.assertEqual(best, 0.0)
        self.assertEqual(idx, [])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            solve_knapsack_01([1, 2], [1], 10)

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            solve_knapsack_01([5], [-1], 10)

    def test_non_integer_capacity_raises(self):
        with self.assertRaises(ValueError):
            solve_knapsack_01([5], [1], 3.5)  # not an integer
        # 3.0 is allowed since it's an integer float
        best, idx = solve_knapsack_01([5], [1], 3.0)
        self.assertEqual(best, 5.0)
        self.assertEqual(idx, [0])


if __name__ == "__main__":
    unittest.main()
