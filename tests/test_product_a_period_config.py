"""Checks for the configured Product A date windows."""

import unittest

from utils.paths import get_periods


class ProductAPeriodConfigTests(unittest.TestCase):
    def test_validation_window_matches_water_years(self):
        # I check the configured dates still span the configured full WY window.
        periods = get_periods("product_a")
        validation = periods["validation"]
        self.assertEqual(validation["start_date"], "1971-10-01")
        self.assertEqual(validation["end_date"], "2018-09-30")
        self.assertEqual(validation["start_water_year"], 1972)
        self.assertEqual(validation["end_water_year"], 2018)

    def test_training_and_validation_windows_join_at_water_year_boundary(self):
        # I keep the split-sample boundary explicit so the training and test
        # periods meet without overlapping or skipping a day.
        periods = get_periods("product_a")
        self.assertEqual(periods["training"]["end_date"], "1971-09-30")
        self.assertEqual(periods["validation"]["start_date"], "1971-10-01")

    def test_config_has_input_compilation_periods_for_product_a_modules(self):
        # I make sure each compiler that reads WGEN dates has a config entry.
        periods = get_periods("product_a")["input_compilation"]
        self.assertEqual(
            set(periods),
            {
                "calsimhydro",
                "calsimhydro_ee",
                "small_watersheds",
                "delta_channel_depletion",
            },
        )


if __name__ == "__main__":
    unittest.main()
