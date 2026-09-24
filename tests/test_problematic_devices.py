#!/usr/bin/env python3

import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from dashboard import dashboard_device_counts, mark_problematic_devices


class ProblematicDevicesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 9, 24, 14, 0, 0)

    def test_trv_fault_is_problematic_even_after_successful_calibration(self) -> None:
        devices = [{
            "source_system": "zigbee2mqtt",
            "device_type": "radiator_thermostat",
            "trv_fault_code": "valve_adjustment_issue_detected",
            "trv_calibration_status": "success",
            "zigbee_availability": "online",
            "mqtt_message_at": self.now,
        }]

        mark_problematic_devices(devices, self.now)

        self.assertTrue(devices[0]["problematic"])
        self.assertEqual(devices[0]["problem_reasons"], ["Szelepbeállítás szükséges"])

    def test_old_contact_report_is_not_a_problem_while_available(self) -> None:
        devices = [{
            "source_system": "zigbee2mqtt",
            "device_type": "contact_sensor",
            "zigbee_availability": "online",
            "mqtt_message_at": self.now - timedelta(days=7),
        }]

        mark_problematic_devices(devices, self.now)

        self.assertFalse(devices[0]["problematic"])

    def test_unavailable_contact_is_problematic(self) -> None:
        devices = [{
            "source_system": "zigbee2mqtt",
            "device_type": "contact_sensor",
            "zigbee_availability": "offline",
        }]

        mark_problematic_devices(devices, self.now)

        self.assertTrue(devices[0]["problematic"])

    def test_very_old_non_contact_zigbee_device_is_problematic(self) -> None:
        devices = [{
            "source_system": "zigbee2mqtt",
            "device_type": "temperature_sensor",
            "zigbee_availability": "online",
            "mqtt_message_at": self.now - timedelta(hours=25),
        }]

        mark_problematic_devices(devices, self.now)

        self.assertIn("Több mint 24 órája nem érkezett Zigbee-adat", devices[0]["problem_reasons"])

    def test_disabled_polling_failure_is_not_reported(self) -> None:
        devices = [{
            "source_system": "tasmota",
            "device_type": "power_meter",
            "polling_enabled": False,
            "is_manual_visual": False,
            "online": False,
        }]

        mark_problematic_devices(devices, self.now)

        self.assertFalse(devices[0]["problematic"])

    def test_dashboard_has_problem_filter(self) -> None:
        template = (ROOT / "app" / "templates" / "dashboard.html").read_text(
            encoding="utf-8"
        )
        card = (ROOT / "app" / "templates" / "_device_card.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('<option value="problematic">Problémás eszközök</option>', template)
        self.assertIn('data-problematic="{{ \'true\' if device.problematic else \'false\' }}"', card)

    def test_dashboard_counts_monitored_manual_and_offline_separately(self) -> None:
        devices = [
            {"polling_enabled": True, "online": True, "is_manual_visual": False},
            {"polling_enabled": True, "online": False, "is_manual_visual": False},
            {"polling_enabled": False, "online": None, "is_manual_visual": True},
            {"polling_enabled": False, "online": False, "is_manual_visual": False},
        ]

        self.assertEqual(dashboard_device_counts(devices), (1, 2, 1, 1))


if __name__ == "__main__":
    unittest.main()
