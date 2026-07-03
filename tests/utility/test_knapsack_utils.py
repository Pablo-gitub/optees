# tests/utility/test_knapsack_utils.py
import unittest

from optees.utility.knapsack_utils import (
    solve_bounded_knapsack,
    solve_fractional_knapsack,
    solve_knapsack_01,
    solve_multi_dimensional_knapsack,
    solve_unbounded_knapsack,
)


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


class TestBoundedKnapsack(unittest.TestCase):
    def test_small_example_optimal_quantities(self):
        # Best feasible choice is 2 units of A and 1 unit of B:
        # value = 2*6 + 1*10 = 22, weight = 2*2 + 1*3 = 7.
        best, quantities = solve_bounded_knapsack(
            values=[6, 10],
            weights=[2, 3],
            max_quantities=[3, 2],
            capacity=7,
        )

        self.assertAlmostEqual(best, 22.0, places=9)
        self.assertEqual(quantities, [2, 1])

    def test_zero_capacity_can_take_finite_zero_weight_items(self):
        best, quantities = solve_bounded_knapsack(
            values=[5, 10],
            weights=[0, 2],
            max_quantities=[3, 1],
            capacity=0,
        )

        self.assertAlmostEqual(best, 15.0, places=9)
        self.assertEqual(quantities, [3, 0])

    def test_empty_problem(self):
        best, quantities = solve_bounded_knapsack([], [], [], 5)

        self.assertEqual(best, 0.0)
        self.assertEqual(quantities, [])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            solve_bounded_knapsack([1, 2], [1, 2], [1], 10)

    def test_negative_max_quantity_raises(self):
        with self.assertRaises(ValueError):
            solve_bounded_knapsack([5], [1], [-1], 10)

    def test_non_integer_capacity_raises(self):
        with self.assertRaises(ValueError):
            solve_bounded_knapsack([5], [1], [2], 3.5)

        best, quantities = solve_bounded_knapsack([5], [1], [2], 2.0)
        self.assertEqual(best, 10.0)
        self.assertEqual(quantities, [2])


class TestUnboundedKnapsack(unittest.TestCase):
    def test_small_example_optimal_quantities(self):
        # Best is one copy of B and one copy of D:
        # value = 40 + 70 = 110, weight = 3 + 5 = 8.
        best, quantities = solve_unbounded_knapsack(
            values=[10, 40, 50, 70],
            weights=[1, 3, 4, 5],
            capacity=8,
        )

        self.assertAlmostEqual(best, 110.0, places=9)
        self.assertEqual(quantities, [0, 1, 0, 1])

    def test_zero_capacity_returns_zero_quantities(self):
        best, quantities = solve_unbounded_knapsack(
            values=[10, 20],
            weights=[1, 2],
            capacity=0,
        )

        self.assertEqual(best, 0.0)
        self.assertEqual(quantities, [0, 0])

    def test_zero_weight_positive_value_is_mathematically_unbounded(self):
        with self.assertRaises(ValueError):
            solve_unbounded_knapsack(
                values=[5, 10],
                weights=[0, 2],
                capacity=10,
            )

    def test_zero_weight_zero_value_is_ignored(self):
        best, quantities = solve_unbounded_knapsack(
            values=[0, 3],
            weights=[0, 2],
            capacity=5,
        )

        self.assertAlmostEqual(best, 6.0, places=9)
        self.assertEqual(quantities, [0, 2])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            solve_unbounded_knapsack([1, 2], [1], 10)

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            solve_unbounded_knapsack([5], [-1], 10)

    def test_non_integer_capacity_raises(self):
        with self.assertRaises(ValueError):
            solve_unbounded_knapsack([5], [1], 3.5)

        best, quantities = solve_unbounded_knapsack([5], [1], 2.0)
        self.assertEqual(best, 10.0)
        self.assertEqual(quantities, [2])


class TestFractionalKnapsack(unittest.TestCase):
    def test_classic_example_optimal_fractions(self):
        # Greedy by density:
        # A: 60/10 = 6, B: 100/20 = 5, C: 120/30 = 4.
        # Capacity 50 takes A and B fully, then 2/3 of C.
        best, fractions = solve_fractional_knapsack(
            values=[60, 100, 120],
            weights=[10, 20, 30],
            capacity=50,
        )

        self.assertAlmostEqual(best, 240.0, places=9)
        self.assertAlmostEqual(fractions[0], 1.0, places=9)
        self.assertAlmostEqual(fractions[1], 1.0, places=9)
        self.assertAlmostEqual(fractions[2], 2.0 / 3.0, places=9)

    def test_ties_are_deterministic_by_input_order(self):
        best, fractions = solve_fractional_knapsack(
            values=[10, 20],
            weights=[1, 2],
            capacity=2,
        )

        self.assertAlmostEqual(best, 20.0, places=9)
        self.assertEqual(fractions, [1.0, 0.5])

    def test_zero_capacity_returns_zero_fractions(self):
        best, fractions = solve_fractional_knapsack(
            values=[10, 20],
            weights=[1, 2],
            capacity=0,
        )

        self.assertEqual(best, 0.0)
        self.assertEqual(fractions, [0.0, 0.0])

    def test_empty_problem(self):
        best, fractions = solve_fractional_knapsack([], [], 5.5)

        self.assertEqual(best, 0.0)
        self.assertEqual(fractions, [])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            solve_fractional_knapsack([1, 2], [1], 10)

    def test_non_positive_weight_raises(self):
        with self.assertRaises(ValueError):
            solve_fractional_knapsack([5], [0], 10)

    def test_non_finite_capacity_raises(self):
        with self.assertRaises(ValueError):
            solve_fractional_knapsack([5], [1], float("inf"))


class TestMultiDimensionalKnapsack(unittest.TestCase):
    def test_two_resource_example_optimal_selection(self):
        # Capacities: weight <= 10, volume <= 6.
        # A + C exactly fills both resources and beats every other feasible set.
        best, selected = solve_multi_dimensional_knapsack(
            values=[8, 9, 14, 7],
            usage_matrix=[
                [4, 1.5],
                [5, 2],
                [6, 4.5],
                [3, 2],
            ],
            capacities=[10, 6],
        )

        self.assertAlmostEqual(best, 22.0, places=9)
        self.assertEqual(selected, [0, 2])

    def test_empty_item_list(self):
        best, selected = solve_multi_dimensional_knapsack(
            values=[],
            usage_matrix=[],
            capacities=[10, 6],
        )

        self.assertEqual(best, 0.0)
        self.assertEqual(selected, [])

    def test_zero_capacity_can_take_zero_usage_items(self):
        best, selected = solve_multi_dimensional_knapsack(
            values=[3, 5],
            usage_matrix=[
                [0, 0],
                [1, 0],
            ],
            capacities=[0, 0],
        )

        self.assertAlmostEqual(best, 3.0, places=9)
        self.assertEqual(selected, [0])

    def test_empty_capacities_raise(self):
        with self.assertRaises(ValueError):
            solve_multi_dimensional_knapsack([1], [[1]], [])

    def test_dimension_mismatch_raises(self):
        with self.assertRaises(ValueError):
            solve_multi_dimensional_knapsack([1], [[1, 2]], [1])

    def test_negative_usage_raises(self):
        with self.assertRaises(ValueError):
            solve_multi_dimensional_knapsack([1], [[-1]], [1])


if __name__ == "__main__":
    unittest.main()
