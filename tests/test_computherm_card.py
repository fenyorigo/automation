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


if __name__ == "__main__":
    unittest.main()
