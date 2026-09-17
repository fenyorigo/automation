from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PollStatusMarkerTest(unittest.TestCase):
    def test_status_uses_same_attempt_timestamp_as_dashboard(self) -> None:
        source = (ROOT / "app/dashboard.py").read_text(encoding="utf-8")
        start = source.index("def poll_status():")
        end = source.index("\n\n@app.get", start)
        function = source[start:end]
        self.assertIn("MAX(pa.attempted_at)", function)
        self.assertIn("WHERE d.is_active=1", function)
        self.assertNotIn("MAX(completed_at)", function)

    def test_latest_value_indexes_are_registered_as_a_migration(self) -> None:
        migration = (
            ROOT / "sql/migrations/049_home_automation_v1.48_to_v1.49.sql"
        ).read_text(encoding="utf-8")
        runner = (ROOT / "app/migrate_database.py").read_text(encoding="utf-8")
        for index in (
            "idx_sensors_device_active_type",
            "idx_sensor_time_id",
            "idx_device_state_time_id",
            "idx_poll_attempts_device_time_id",
        ):
            self.assertIn(index, migration)
        self.assertIn("v1_49_dashboard_latest_value_indexes", runner)

    def test_expensive_latest_value_queries_are_source_guarded(self) -> None:
        source = (ROOT / "app/dashboard.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(
            source.count("CASE WHEN d.source_system='tasmota'"), 3
        )
        self.assertGreaterEqual(
            source.count("CASE WHEN d.source_system='linux_system'"), 3
        )
        self.assertGreaterEqual(
            source.count("CASE WHEN d.source_system='shelly_mqtt'"), 4
        )


if __name__ == "__main__":
    unittest.main()
