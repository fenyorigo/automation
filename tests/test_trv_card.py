#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TrvCardTest(unittest.TestCase):
    def test_dashboard_loads_trv_properties(self) -> None:
        source = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn("AS trv_local_temperature_c", source)
        self.assertIn("AS trv_target_temperature_c", source)
        self.assertIn("AS trv_valve_position_percent", source)
        self.assertIn("AS trv_calibration_status", source)

    def test_card_marks_radiator_temperature_as_non_controlling(self) -> None:
        template = (ROOT / "app" / "templates" / "_device_card.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("device.device_type == 'radiator_thermostat'", template)
        self.assertIn("Radiátorközeli mérés", template)
        self.assertIn("aktív gázfűtés alatt nem vezérlési alap", template)
        self.assertIn("device.trv_valve_position_percent", template)
        self.assertIn("device.trv_fault_code", template)


if __name__ == "__main__":
    unittest.main()
