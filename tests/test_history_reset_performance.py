from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HistoryResetPerformanceTest(unittest.TestCase):
    def test_resettable_sensor_loader_uses_indexed_latest_reading_lookup(self) -> None:
        source = (ROOT / "app/dashboard.py").read_text(encoding="utf-8")
        function = source.split("def load_resettable_sensors()", 1)[1].split(
            "def load_analysis_overview", 1
        )[0]
        self.assertIn("ORDER BY sr.observed_at DESC", function)
        self.assertIn("LIMIT 1", function)
        self.assertNotIn("COUNT(sr.id)", function)
        self.assertNotIn("LEFT JOIN sensor_readings", function)

    def test_reset_form_uses_last_reading_as_availability_marker(self) -> None:
        template = (ROOT / "app/templates/history.html").read_text(encoding="utf-8")
        self.assertIn("'disabled' if not sensor.last_reading_at", template)
        self.assertNotIn("sensor.reading_count", template)


if __name__ == "__main__":
    unittest.main()
