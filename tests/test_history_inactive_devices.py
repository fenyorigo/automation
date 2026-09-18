from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HistoryInactiveDevicesTest(unittest.TestCase):
    def test_loader_keeps_inactive_temperature_devices(self) -> None:
        source = (ROOT / "app/dashboard.py").read_text(encoding="utf-8")
        function = source.split("def load_history_devices()", 1)[1].split(
            "def load_history_presets", 1
        )[0]
        self.assertIn("d.is_active", function)
        self.assertIn("AS has_readings", function)
        self.assertNotIn("d.is_active = 1", function)
        self.assertNotIn("s.is_active = 1", function)

    def test_template_separates_active_and_inactive_devices(self) -> None:
        template = (ROOT / "app/templates/history.html").read_text(encoding="utf-8")
        self.assertIn("Aktív eszközök", template)
        self.assertIn("Inaktivált eszközök", template)
        self.assertIn("device.has_readings", template)


if __name__ == "__main__":
    unittest.main()
