#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContactSensorCardTest(unittest.TestCase):
    def test_dashboard_loads_contact_and_tamper_properties(self):
        source = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn("AS zigbee_contact_closed", source)
        self.assertIn("AS zigbee_tamper", source)

    def test_contact_card_has_no_temperature_rendering(self):
        template = (ROOT / "app" / "templates" / "_device_card.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("device.device_type == 'contact_sensor'", template)
        self.assertIn("device.zigbee_contact_closed", template)
        self.assertIn("device.zigbee_tamper", template)
        self.assertIn("Csukva", template)
        self.assertIn("Nyitva", template)


if __name__ == "__main__":
    unittest.main()
