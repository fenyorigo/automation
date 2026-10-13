#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ConnectLifeCardTest(unittest.TestCase):
    def test_card_shows_normalized_fan_setting(self) -> None:
        template = (ROOT / "app" / "templates" / "_device_card.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("Ventilátor-beállítás", template)
        self.assertIn("device.fan_speed == 'auto'", template)
        self.assertIn("device.fan_speed == 'quiet'", template)
        self.assertIn("Közepesen alacsony", template)
        self.assertIn("Közepesen magas", template)
        self.assertIn("device.source_system == 'connectlife'", template)
        self.assertIn("poll_device_now", template)
        self.assertIn("Kézi lekérdezés", template)
        self.assertIn("csrf_token()", template)

    def test_card_has_guarded_manual_climate_control(self) -> None:
        template = (ROOT / "app" / "templates" / "_device_card.html").read_text(
            encoding="utf-8"
        )
        dashboard = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn("Kézi klímavezérlés", template)
        self.assertIn("start_climate_from_card", template)
        self.assertIn("Kültéri határ felülbírálása", template)
        self.assertIn("data-climate-submit", template)
        self.assertIn('operation="manual_climate_control"', dashboard)
        self.assertIn("allow_running_update=True", dashboard)


if __name__ == "__main__":
    unittest.main()
