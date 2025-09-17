import os
import unittest
from src.optees.utility.io_lpnetlib import load_lpnetlib_mat
from src.optees.utility.lp_utils import solve_lp

AFIRO = "tests/data/lp/lpnetlib_mat/lp_afiro.mat"
FV47 = "tests/data/lp/lpnetlib_mat/lp_25fv47.mat"

class TestLPNetlibAdapter(unittest.TestCase):

    @unittest.skipUnless(os.path.exists(AFIRO), "lp_afiro.mat non trovato")
    def test_afiro_mat_smoke(self):
        problem = load_lpnetlib_mat(AFIRO)
        status, obj, x, extras = solve_lp(problem)
        self.assertEqual(status, "Optimal")
        self.assertIsInstance(obj, float)
        self.assertGreater(len(x), 0)

    @unittest.skipUnless(os.path.exists(FV47), "lp_25fv47.mat non trovato")
    def test_25fv47_mat_smoke(self):
        problem = load_lpnetlib_mat(FV47)
        status, obj, x, extras = solve_lp(problem)
        self.assertEqual(status, "Optimal")
        self.assertIsInstance(obj, float)
