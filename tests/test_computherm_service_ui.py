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

    def test_service_page_can_safely_return_to_normal_mode(self) -> None:
        template = (ROOT / "app/templates/service_tests.html").read_text(
            encoding="utf-8"
        )
        source = (ROOT / "app/dashboard.py").read_text(encoding="utf-8")
        self.assertIn("Gázkazánszerviz lezárása", template)
        self.assertIn("{% if active_by_device %}disabled{% endif %}", template)
        self.assertIn(
            '@app.post("/service-tests/boiler-service-mode/disable")', source
        )
        self.assertIn(
            'set_global_setting_value("BOILER_SERVICE_MODE", "false")', source
        )

    def test_clock_time_is_captured_after_connection_and_preflight(self) -> None:
        source = (ROOT / "app/dashboard.py").read_text(encoding="utf-8")
        route = source[source.index('def sync_computherm_device_clock'):]
        self.assertLess(route.index("connect_computherm("), route.index("local_now()"))
        self.assertLess(route.index("computherm_snapshot(control)"), route.index("local_now()"))

    def test_single_device_poll_accepts_computherm(self) -> None:
        source = (ROOT / "app/dashboard.py").read_text(encoding="utf-8")
        self.assertIn(
            'device["source_system"] not in {"connectlife", "computherm"}',
            source,
        )
        self.assertIn('str(device["source_system"])', source)

    def test_schedule_update_is_verified_and_audited(self) -> None:
        source = (ROOT / "app/dashboard.py").read_text(encoding="utf-8")
        self.assertIn(
            '@app.post("/devices/<int:device_id>/computherm/schedule")', source
        )
        self.assertIn("set_computherm_weekly_program", source)
        self.assertIn("computherm_schedule_changes", source)
        migration = (
            ROOT
            / "SQL/migrations/058_home_automation_v1.57_to_v1.58.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE computherm_schedule_changes", migration)

    def test_interactive_config_includes_broadlink_device_name(self) -> None:
        source = (ROOT / "app/dashboard.py").read_text(encoding="utf-8")
        config_helper = source[
            source.index("def computherm_config"):
            source.index("def computherm_schedule_from_form")
        ]
        self.assertIn(
            'values["source_device_id"] = config.device_id', config_helper
        )


if __name__ == "__main__":
    unittest.main()
