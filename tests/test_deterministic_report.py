from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from deterministic_report import generate_report  # noqa: E402


class DeterministicReportTest(unittest.TestCase):
    def base_facts(self) -> dict:
        return {
            "window": {
                "started_at": "2026-08-15T08:00:00Z",
                "ended_at": "2026-08-15T09:00:00Z",
            },
            "temperature_series": [],
            "climate_events": [],
            "ventilation_events": [],
            "common_esp32_drop_events": [],
            "outdoor_summary": None,
            "operator_observation": None,
        }

    def test_missing_measurements_are_warning(self) -> None:
        report = generate_report(self.base_facts())
        self.assertEqual(report["severity"], "warning")
        self.assertIn("nem található", report["report_text"])

    def test_sensor_values_are_formatted_from_evidence(self) -> None:
        facts = self.base_facts()
        facts["temperature_series"] = [{
            "device": "esp32-kisnappali", "source": "esp32", "room": "Kis nappali",
            "zone": "Emelet", "sample_count": 30, "minimum_c": 25.1,
            "maximum_c": 26.2, "average_c": 25.7, "net_change_c": -0.4,
        }]
        report = generate_report(facts)
        self.assertEqual(report["severity"], "info")
        self.assertIn("esp32-kisnappali", report["report_text"])
        self.assertIn("átlag 25.7 °C", report["report_text"])

    def test_common_drops_are_summarized_once(self) -> None:
        facts = self.base_facts()
        facts["temperature_series"] = [{
            "device": "esp32-1", "source": "esp32", "room": "Dolgozó", "zone": "Emelet",
            "sample_count": 2, "minimum_c": 25.0, "maximum_c": 25.2,
            "average_c": 25.1, "net_change_c": -0.2,
        }]
        facts["common_esp32_drop_events"] = [
            {"device_count": 3, "mean_change_c": -0.2, "minute_utc": "2026-08-15T08:10:00Z"},
            {"device_count": 4, "mean_change_c": -0.5, "minute_utc": "2026-08-15T08:20:00Z"},
        ]
        report = generate_report(facts)
        common = [item for item in report["findings"] if item["rule_id"] == "common_esp32_drop_v1"]
        self.assertEqual(len(common), 1)
        self.assertIn("2 olyan mérési időpont", common[0]["message"])
        self.assertEqual(common[0]["evidence"]["strongest_event"]["mean_change_c"], -0.5)


if __name__ == "__main__":
    unittest.main()
