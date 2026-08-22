from datetime import datetime, timedelta
import unittest

from app.temperature_derivation import derive_temperature, ema_alpha


class TemperatureDerivationTest(unittest.TestCase):
    def test_time_based_alpha(self) -> None:
        self.assertAlmostEqual(ema_alpha(240, 240), 1 - 1 / 2.718281828459045)

    def test_first_reading_is_action_point(self) -> None:
        now = datetime(2026, 8, 22, 8, 0)
        result = derive_temperature(
            raw_value=25.0, offset_c=0.25, observed_at=now,
            tau_seconds=240, action_interval_seconds=240,
            previous_filtered=None, previous_observed_at=None, last_action_at=None,
            source_from=None, sample_count=0,
        )
        self.assertEqual(result.calibrated, 25.25)
        self.assertEqual(result.filtered, 25.25)
        self.assertEqual(result.action, 25.25)
        self.assertTrue(result.is_action_point)

    def test_intermediate_sample_updates_filter_without_publishing(self) -> None:
        start = datetime(2026, 8, 22, 8, 0)
        result = derive_temperature(
            raw_value=24.0, offset_c=0.0, observed_at=start + timedelta(minutes=2),
            tau_seconds=240, action_interval_seconds=240,
            previous_filtered=26.0, previous_observed_at=start, last_action_at=start,
            source_from=start, sample_count=1,
        )
        self.assertAlmostEqual(result.filtered, 25.2130613194)
        self.assertIsNone(result.action)
        self.assertFalse(result.is_action_point)
        self.assertEqual(result.source_from, start + timedelta(minutes=2))
        self.assertEqual(result.sample_count, 1)

    def test_action_point_uses_all_intermediate_state(self) -> None:
        start = datetime(2026, 8, 22, 8, 0)
        result = derive_temperature(
            raw_value=24.0, offset_c=0.0, observed_at=start + timedelta(minutes=4),
            tau_seconds=240, action_interval_seconds=240,
            previous_filtered=25.2130613194,
            previous_observed_at=start + timedelta(minutes=2), last_action_at=start,
            source_from=start + timedelta(minutes=2), sample_count=1,
        )
        self.assertTrue(result.is_action_point)
        self.assertAlmostEqual(result.action or 0, result.filtered)
        self.assertEqual(result.sample_count, 2)


if __name__ == "__main__":
    unittest.main()
