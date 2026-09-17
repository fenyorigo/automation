from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ComputhermServiceUiTest(unittest.TestCase):
    def test_each_thermostat_uses_its_own_active_test(self) -> None:
        template = (ROOT / "app/templates/service_tests.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("active_by_device.get(device.id)", template)
        self.assertNotIn("Másik termosztáton aktív teszt fut", template)

    def test_route_locks_only_the_selected_thermostat_test(self) -> None:
        source = (ROOT / "app/dashboard.py").read_text(encoding="utf-8")
        self.assertIn(
            'WHERE device_id=? AND status IN (\'active\',\'heat_requested\',\'heat_suppressed\')',
            source,
        )
        self.assertIn('"active_by_device":active_by_device', source)


if __name__ == "__main__":
    unittest.main()
