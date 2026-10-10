import unittest
from datetime import UTC, datetime

from measurement_retention import (
    previous_calendar_month_start_utc,
    tasmota_keeps_monthly_history,
    zigbee_property_has_time_series,
)


class MeasurementRetentionTest(unittest.TestCase):
    def test_keeps_current_and_previous_budapest_calendar_month(self) -> None:
        cutoff = previous_calendar_month_start_utc(
            datetime(2026, 10, 10, 12, tzinfo=UTC)
        )
        self.assertEqual(cutoff, datetime(2026, 8, 31, 22))

    def test_handles_january_year_boundary(self) -> None:
        cutoff = previous_calendar_month_start_utc(
            datetime(2027, 1, 15, 12, tzinfo=UTC)
        )
        self.assertEqual(cutoff, datetime(2026, 11, 30, 23))

    def test_only_two_it_plugs_keep_monthly_history(self) -> None:
        self.assertTrue(tasmota_keeps_monthly_history("nous-mainit"))
        self.assertTrue(tasmota_keeps_monthly_history("nous-auxit"))
        self.assertFalse(tasmota_keeps_monthly_history("nous-bojler"))

    def test_zigbee_power_meter_values_remain_cache_only(self) -> None:
        for property_name in ("power", "current", "voltage", "energy"):
            self.assertFalse(
                zigbee_property_has_time_series("power_meter", property_name)
            )
        self.assertTrue(zigbee_property_has_time_series("power_meter", "contact"))
        self.assertTrue(zigbee_property_has_time_series("temperature_sensor", "voltage"))


if __name__ == "__main__":
    unittest.main()
