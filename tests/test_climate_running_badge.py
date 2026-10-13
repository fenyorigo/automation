#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ClimateRunningBadgeTest(unittest.TestCase):
    def test_primary_room_sensor_card_shows_verified_climate_mode(self) -> None:
        template = (ROOT / "app" / "templates" / "_device_card.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("Hűtés folyamatban", template)
        self.assertIn("Fűtés folyamatban", template)
        self.assertIn("device.cooling_advice.climate_available", template)
        self.assertIn("device.heating_advice.climate_available", template)
        self.assertIn(
            "device.cooling_advice.cooling_demand and not device.cooling_advice.cooling_active",
            template,
        )
        self.assertIn(
            "device.heating_advice.heating_demand and not device.heating_advice.heating_active",
            template,
        )


if __name__ == "__main__":
    unittest.main()
