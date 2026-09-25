from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from scheduled_power import water_heater_schedule_details


class WaterHeaterScheduleTest(unittest.TestCase):
    def details(self, hour: int, minute: int = 0):
        now = datetime(2026, 9, 22, hour, minute, tzinfo=ZoneInfo("Europe/Budapest"))
        with patch.dict(
            os.environ,
            {
                "APP_TIMEZONE": "Europe/Budapest",
                "WATER_HEATER_SCHEDULE_ENABLED": "true",
                "WATER_HEATER_ON_TIME": "05:00",
                "WATER_HEATER_OFF_TIME": "12:00",
            },
            clear=False,
        ):
            return water_heater_schedule_details(now)

    def test_daytime_window_is_on_from_start_until_end(self) -> None:
        self.assertFalse(self.details(4, 59)["desired_power"])
        self.assertTrue(self.details(5, 0)["desired_power"])
        self.assertTrue(self.details(11, 59)["desired_power"])
        self.assertFalse(self.details(12, 0)["desired_power"])

    def test_overnight_window_is_supported(self) -> None:
        now = datetime(2026, 9, 22, 23, 0, tzinfo=ZoneInfo("Europe/Budapest"))
        with patch.dict(
            os.environ,
            {
                "WATER_HEATER_SCHEDULE_ENABLED": "true",
                "WATER_HEATER_ON_TIME": "22:00",
                "WATER_HEATER_OFF_TIME": "06:00",
            },
            clear=False,
        ):
            self.assertTrue(water_heater_schedule_details(now)["desired_power"])

    def test_disabled_schedule_keeps_desired_state_informational_only(self) -> None:
        with patch.dict(
            os.environ,
            {"WATER_HEATER_SCHEDULE_ENABLED": "false"},
            clear=False,
        ):
            details = water_heater_schedule_details(
                datetime(2026, 9, 22, 7, 0, tzinfo=ZoneInfo("Europe/Budapest"))
            )
        self.assertFalse(details["enabled"])

    def test_dashboard_mentions_authoritative_automation_window(self) -> None:
        template = (ROOT / "app/templates/_device_card.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("Engedélyezett időablak", template)
        self.assertIn("Program {{ 'aktív'", template)
        self.assertIn("A program nem vezérli a dugaljat", template)


if __name__ == "__main__":
    unittest.main()
