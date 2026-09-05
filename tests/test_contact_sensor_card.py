#!/usr/bin/env python3

import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from dashboard import zigbee_freshness_status


class ContactSensorCardTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 5, 18, 0)

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

    def test_sleeping_contact_is_warning_but_still_available(self):
        self.assertEqual(
            zigbee_freshness_status(
                "contact_sensor", "EndDevice", "online",
                self.now - timedelta(days=1), self.now,
            ),
            ("warning", "Régi állapotjelzés", True),
        )

    def test_explicitly_offline_contact_is_unavailable_even_with_fresh_data(self):
        self.assertEqual(
            zigbee_freshness_status(
                "contact_sensor", "EndDevice", "offline",
                self.now - timedelta(minutes=1), self.now,
            ),
            ("offline", "Zigbee eszköz nem elérhető", False),
        )

    def test_fresh_contact_is_green(self):
        self.assertEqual(
            zigbee_freshness_status(
                "contact_sensor", "EndDevice", "online",
                self.now - timedelta(hours=2), self.now,
            ),
            ("online", "Zigbee", True),
        )

    def test_other_zigbee_end_device_keeps_freshness_failure(self):
        self.assertEqual(
            zigbee_freshness_status(
                "temperature_sensor", "EndDevice", "online",
                self.now - timedelta(hours=3), self.now,
            ),
            ("offline", "Nincs friss Zigbee-adat", False),
        )


if __name__ == "__main__":
    unittest.main()
