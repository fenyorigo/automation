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


if __name__ == "__main__":
    unittest.main()
