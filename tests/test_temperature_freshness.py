import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from dashboard import temperature_measurement_class


NOW = datetime(2026, 10, 8, 19, 0)


class TemperatureFreshnessTest(unittest.TestCase):
    def test_trv_is_normal_during_first_hour(self) -> None:
        self.assertEqual(
            temperature_measurement_class(
                "radiator_thermostat", NOW - timedelta(minutes=59), NOW
            ),
            "",
        )

    def test_trv_is_yellow_between_one_and_two_hours(self) -> None:
        self.assertEqual(
            temperature_measurement_class(
                "radiator_thermostat", NOW - timedelta(minutes=80), NOW
            ),
            "aging-measurement",
        )

    def test_trv_is_red_after_two_hours(self) -> None:
        self.assertEqual(
            temperature_measurement_class(
                "radiator_thermostat", NOW - timedelta(hours=2, seconds=1), NOW
            ),
            "stale-measurement",
        )

    def test_other_temperature_measurements_keep_one_hour_limit(self) -> None:
        self.assertEqual(
            temperature_measurement_class(
                "temperature_sensor", NOW - timedelta(minutes=80), NOW
            ),
            "stale-measurement",
        )


if __name__ == "__main__":
    unittest.main()
