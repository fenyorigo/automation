#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TrvCardTest(unittest.TestCase):
    def test_dashboard_loads_trv_properties(self) -> None:
        source = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn("AS trv_local_temperature_c", source)
        self.assertIn("AS trv_target_temperature_c", source)
        self.assertIn("AS trv_heating_valve_position_percent", source)
        self.assertIn("AS trv_idle_valve_position_percent", source)
        self.assertIn("AS trv_pid_control", source)
        self.assertIn("AS trv_child_lock", source)
        self.assertIn("AS trv_temporary_mode", source)
        self.assertIn("AS trv_thermostat_linkage", source)
        self.assertIn("AS trv_calibration_status", source)

    def test_card_marks_radiator_temperature_as_non_controlling(self) -> None:
        template = (ROOT / "app" / "templates" / "_device_card.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("device.device_type == 'radiator_thermostat'", template)
        self.assertIn("Radiátorközeli mérés", template)
        self.assertIn("aktív gázfűtés alatt nem vezérlési alap", template)
        self.assertIn("device.trv_heating_valve_position_percent", template)
        self.assertIn("device.trv_idle_valve_position_percent", template)
        self.assertIn("PID vezérlés", template)
        self.assertIn("Gyerekzár", template)
        self.assertIn("Ablakfigyelés", template)
        self.assertIn("Ideiglenes mód", template)
        self.assertIn("Termosztát-link", template)
        self.assertIn("update_trv_settings", template)
        self.assertIn("Parancs elküldve", template)
        self.assertIn("A legutóbbi parancs nem igazolt", template)
        self.assertIn("device.trv_fault_code", template)

    def test_route_validates_and_audits_trv_settings(self) -> None:
        source = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn('/devices/<int:device_id>/trv-settings', source)
        self.assertIn('"smart_temperature_control": pid', source)
        self.assertIn('heating_valve_position=heating_position', source)
        self.assertIn('idle_valve_position=idle_position', source)
        self.assertIn('"trv_settings"', source)
        self.assertIn("trv_setting_requests", source)
        self.assertIn("annotate_trv_setting_requests(devices)", source)


if __name__ == "__main__":
    unittest.main()
