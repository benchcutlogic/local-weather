import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prompt_builder import select_models_for_horizon, _horizon_bucket


class TestHorizonBlendRules(unittest.TestCase):
    def test_immediate_horizon_prefers_hrrr_then_nam(self):
        available = {"GFS", "NAM", "HRRR"}
        selected = select_models_for_horizon(available, "immediate_0_6h")
        self.assertEqual(selected[:3], ["HRRR", "NAM", "GFS"])

    def test_short_horizon_prefers_nam_over_gfs(self):
        available = {"GFS", "NAM"}
        selected = select_models_for_horizon(available, "short_6_48h")
        self.assertEqual(selected[:2], ["NAM", "GFS"])

    def test_extended_horizon_prefers_ecmwf_then_gfs(self):
        available = {"GFS", "ECMWF", "NAM"}
        selected = select_models_for_horizon(available, "extended_48h_plus")
        self.assertEqual(selected[:3], ["ECMWF", "GFS", "NAM"])

    def test_bucket_logic(self):
        self.assertEqual(_horizon_bucket(2), "immediate_0_6h")
        self.assertEqual(_horizon_bucket(24), "short_6_48h")
        self.assertEqual(_horizon_bucket(72), "extended_48h_plus")
        self.assertEqual(_horizon_bucket(None), "unknown")


if __name__ == "__main__":
    unittest.main()
