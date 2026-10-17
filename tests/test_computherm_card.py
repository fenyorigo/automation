#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from dashboard import annotate_computherm_room_thermometers


class ComputhermCardTest(unittest.TestCase):
    def test_adds_same_room_thermometer_but_excludes_trv_and_other_room(self) -> None:
        devices = [
            {"id": 1, "name": "CT400 emelet", "source_system": "computherm", "room_id": 7},
            {"id": 2, "name": "Zb kisnappali", "source_system": "zigbee2mqtt", "device_type": "temperature_sensor", "room_id": 7, "temperature_c": 19.4},
            {"id": 3, "name": "TRV-G2 Rita", "source_system": "zigbee2mqtt", "device_type": "radiator_thermostat", "room_id": 7, "temperature_c": 22.0},
            {"id": 4, "name": "Zb Rita", "source_system": "zigbee2mqtt", "device_type": "temperature_sensor", "room_id": 8, "temperature_c": 21.0},
        ]

        annotate_computherm_room_thermometers(devices)

        self.assertEqual(
            [item["name"] for item in devices[0]["room_thermometers"]],
            ["Zb kisnappali"],
        )

    def test_template_displays_room_thermometer(self) -> None:
        template = (ROOT / "app" / "templates" / "_device_card.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("További helyiségi hőmérő", template)
        self.assertIn("device.room_thermometers", template)

    def test_template_displays_clock_and_sync_button(self) -> None:
        template = (ROOT / "app" / "templates" / "_device_card.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("CT400 ideje", template)
        self.assertIn("device.computherm_day_name", template)
        self.assertIn("sync_computherm_device_clock", template)
        self.assertIn("Idő szinkronizálása", template)
        self.assertIn("Beállított heti program", template)
        self.assertIn("ct_program.get('weekday',[])", template)
        self.assertIn("ct_program.get('weekend',[])", template)
        self.assertIn("computherm-card-controls", template)
        self.assertIn("poll_device_now", template)
        self.assertIn("Kézi lekérdezés", template)
        self.assertIn("update_computherm_schedule", template)
        self.assertIn("Heti program mentése", template)
        self.assertIn('step="0.5"', template)

    def test_dashboard_validates_schedule_order_in_browser(self) -> None:
        template = (ROOT / "app" / "templates" / "dashboard.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("data-computherm-schedule", template)
        self.assertIn("current < previous", template)
        self.assertIn("setCustomValidity", template)


if __name__ == "__main__":
    unittest.main()
