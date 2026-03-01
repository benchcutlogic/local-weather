import sys
import types
import unittest
from pathlib import Path

# Stub heavy optional deps so we can import grib2_reader in lightweight test env
sys.modules.setdefault("numpy", types.ModuleType("numpy"))
sys.modules.setdefault("xarray", types.ModuleType("xarray"))
sys.modules.setdefault("fsspec", types.ModuleType("fsspec"))

# Allow importing grib2_reader/config from services/ingest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from grib2_reader import _match_idx_entry


class TestIdxLevelMatching(unittest.TestCase):
    def test_height_above_ground_does_not_match_mb_level(self):
        cfg = {"shortName": "2t", "typeOfLevel": "heightAboveGround", "level": "2"}
        bad_entry = {"var_name": "TMP", "level": "2 mb"}
        self.assertFalse(_match_idx_entry(bad_entry, cfg))

    def test_height_above_ground_matches_exact_level(self):
        cfg = {"shortName": "2t", "typeOfLevel": "heightAboveGround", "level": "2"}
        good_entry = {"var_name": "TMP", "level": "2 m above ground"}
        self.assertTrue(_match_idx_entry(good_entry, cfg))

    def test_wind_10m_above_ground_matches(self):
        cfg = {"shortName": "10u", "typeOfLevel": "heightAboveGround", "level": "10"}
        entry = {"var_name": "UGRD", "level": "10 m above ground"}
        self.assertTrue(_match_idx_entry(entry, cfg))

    def test_surface_field_matches_surface(self):
        cfg = {"shortName": "cape", "typeOfLevel": "surface"}
        entry = {"var_name": "CAPE", "level": "surface"}
        self.assertTrue(_match_idx_entry(entry, cfg))


if __name__ == "__main__":
    unittest.main()
