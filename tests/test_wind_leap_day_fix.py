"""Focused checks for the historical wind leap-day adjustment."""

import ast
import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_DATES = pd.date_range("1948-02-28", "1948-03-01", freq="D")


def load_add_wind_function(relative_path: str):
    """I load only add_wind so tests do not run a script's full data loop."""
    source_path = REPO_ROOT / relative_path
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "add_wind"
    )
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {"os": os, "pd": pd}
    exec(compile(ast.fix_missing_locations(module), str(source_path), "exec"), namespace)
    return namespace["add_wind"]


class WindLeapDayTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)
        self.historical = load_add_wind_function(
            "mod_forcing/vic/_1_append_wind_wgen_hist.py"
        )
        self.stochastic = load_add_wind_function(
            "mod_forcing/vic/_1_append_wind_wgen_stochastic.py"
        )
        self._write_climate_files()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_climate_files(self):
        pd.DataFrame(
            {
                "year": TEST_DATES.year,
                "month": TEST_DATES.month,
                "day": TEST_DATES.day,
                "pr": [1, 1, 1],
                "tmax": [2, 2, 2],
                "tmin": [0, 0, 0],
            }
        ).to_csv(self.folder / "meteo_test", sep=" ", header=False, index=False)

    def _write_wind(self, values):
        pd.DataFrame(
            {"column_1": [0] * 3, "column_2": [0] * 3,
             "column_3": [0] * 3, "wind": [float(value) for value in values]}
        ).to_csv(self.folder / "data_test", sep=" ", header=False, index=False)

    def _run_historical(self, values):
        self._write_wind(values)
        return self.historical(
            "data_test", "meteo_test", wind_dir=str(self.folder),
            climate_dir=str(self.folder), wind_date_start="1948-02-28",
            wind_date_end="1948-03-01",
        )["wind"].tolist()

    def _run_stochastic(self, values):
        self._write_wind(values)
        wgen = pd.DataFrame(
            {"column_1": [0] * 3, "column_2": [0] * 3,
             "column_3": [0] * 3, "pr": [1] * 3,
             "tmax": [2] * 3, "tmin": [0] * 3}
        )
        wgen.to_csv(self.folder / "meteo_test", sep=" ", header=False, index=False)
        sampled_dates = pd.DataFrame({"resmplDatesLoc": TEST_DATES})
        result = self.stochastic(
            "data_test", str(self.folder), str(self.folder), sampled_dates,
            hist_date_start="1948-02-28", hist_date_end="1948-03-01",
        )
        self.assertIsNotNone(result)
        return result["wind"].tolist()

    def test_historical_zero_feb_29_uses_neighbor_average(self):
        # I confirm Feb 29 is the mean and the neighboring Feb 28 zero is unchanged.
        self.assertEqual(self._run_historical([0, 0, 3]), [0.0, 1.5, 3.0])

    def test_historical_nonzero_feb_29_is_preserved(self):
        # I confirm the adjustment does not overwrite a nonzero leap-day value.
        self.assertEqual(self._run_historical([0, 4, 3]), [0.0, 4.0, 3.0])

    def test_stochastic_zero_feb_29_uses_neighbor_average(self):
        # I apply the same expected check to the stochastic WGEN script.
        self.assertEqual(self._run_stochastic([0, 0, 3]), [0.0, 1.5, 3.0])

    def test_stochastic_nonzero_feb_29_is_preserved(self):
        # I confirm stochastic processing leaves nonzero leap-day wind unchanged.
        self.assertEqual(self._run_stochastic([0, 4, 3]), [0.0, 4.0, 3.0])


if __name__ == "__main__":
    unittest.main()
