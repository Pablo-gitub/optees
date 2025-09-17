# tests/utility/test_io_knapsack_param.py
import os
import glob
import unittest

from src.optees.utility.io_knapsack import load_knapsack_burkardt
from src.optees.utility.knapsack_utils import solve_knapsack_01
# se preferisci il re-export:
# from src.optees.utility.lp_utils import solve_knapsack as solve_knapsack_01

# Root directory per la discovery; puoi sovrascriverlo via env var
ROOT = os.environ.get("KNAP_BURK_ROOT", "tests/data/knapsack")

def _discover_instances(root: str):
    """
    Find every '<inst>_c.txt' under 'root', and return (dir_path, inst) tuples
    only if the matching *_w.txt and *_p.txt also exist.
    """
    pattern = os.path.join(root, "**", "*_c.txt")
    found = []
    for c_path in glob.glob(pattern, recursive=True):
        dir_path = os.path.dirname(c_path)
        inst = os.path.basename(c_path)[:-len("_c.txt")]  # strip suffix
        w_path = os.path.join(dir_path, f"{inst}_w.txt")
        p_path = os.path.join(dir_path, f"{inst}_p.txt")
        if os.path.exists(w_path) and os.path.exists(p_path):
            found.append((dir_path, inst))
    return found


class TestKnapsackBurkardtParam(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = _discover_instances(ROOT)

    def test_discovered_instances(self):
        if not self.cases:
            self.skipTest(f"No Burkardt-style instances found under {ROOT}")

        for dir_path, inst in self.cases:
            with self.subTest(instance=inst, folder=dir_path):
                data = load_knapsack_burkardt(dir_path, inst)
                v, w, C = data["values"], data["weights"], data["capacity"]
                best, idx = solve_knapsack_01(v, w, C)

                # capacity feasibility
                total_w = sum(w[i] for i in idx)
                self.assertLessEqual(total_w, C, "Capacity violated")

                # if optimal selection provided, verify exact match + value
                sel = data.get("opt_selection")
                if sel is not None:
                    expected_idx = [i for i, s in enumerate(sel) if s == 1]
                    self.assertEqual(idx, expected_idx, "Selected indices mismatch vs ground truth")
                    expected_val = float(sum(v[i] for i in expected_idx))
                    self.assertAlmostEqual(best, expected_val, places=9, msg="Objective mismatch")
                else:
                    # otherwise, at least objective equals sum of chosen values
                    recomputed = float(sum(v[i] for i in idx))
                    self.assertAlmostEqual(best, recomputed, places=9, msg="Objective recomputation mismatch")


if __name__ == "__main__":
    unittest.main()
