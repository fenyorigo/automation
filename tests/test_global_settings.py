from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import global_settings


class ReloadEnvironmentTest(unittest.TestCase):
    def test_ventilation_timing_defaults_are_ui_managed(self) -> None:
        settings = {item.key: item for item in global_settings.SETTINGS}
        self.assertEqual(settings["VENTILATION_LONG_THRESHOLD_MINUTES"].default, "5")
        self.assertEqual(
            settings["VENTILATION_CONTACT_CLOSE_DELAY_SECONDS"].default, "30"
        )
        self.assertTrue(settings["VENTILATION_LONG_THRESHOLD_MINUTES"].validator("15"))
        self.assertFalse(settings["VENTILATION_CONTACT_CLOSE_DELAY_SECONDS"].validator("2"))

    def test_cooling_observer_defaults_are_ui_managed(self) -> None:
        settings = {item.key: item for item in global_settings.SETTINGS}
        self.assertEqual(settings["COOLING_ROOM_REQUEST_ON_C"].default, "27.5")
        self.assertEqual(settings["COOLING_ROOM_REQUEST_OFF_C"].default, "27.0")
        self.assertEqual(settings["COOLING_OUTDOOR_ENABLE_C"].default, "28.1")
        self.assertEqual(settings["COOLING_OUTDOOR_DISABLE_C"].default, "27.1")
        self.assertEqual(settings["COOLING_MAX_DATA_AGE_MINUTES"].default, "180")

    def test_heating_observer_defaults_are_ui_managed(self) -> None:
        settings = {item.key: item for item in global_settings.SETTINGS}
        self.assertEqual(settings["HEATING_ROOM_REQUEST_ON_C"].default, "20.0")
        self.assertEqual(settings["HEATING_ROOM_REQUEST_OFF_C"].default, "20.5")
        self.assertEqual(settings["HEATING_CLIMATE_MIN_OUTDOOR_C"].default, "5.0")
        self.assertEqual(settings["HEATING_MIN_COP"].default, "2.5")
        self.assertEqual(settings["BOILER_PANEL_ON_MIN_POWER_W"].default, "2.0")

    def test_save_rejects_reversed_cooling_hysteresis(self) -> None:
        values = {item.key: item.default for item in global_settings.SETTINGS}
        values["COOLING_ROOM_REQUEST_ON_C"] = "26"
        values["COOLING_ROOM_REQUEST_OFF_C"] = "27"
        with self.assertRaisesRegex(ValueError, "bekapcsolási határának"):
            global_settings.save(values)

    def test_save_rejects_reversed_heating_hysteresis(self) -> None:
        values = {item.key: item.default for item in global_settings.SETTINGS}
        values["HEATING_ROOM_REQUEST_ON_C"] = "21"
        values["HEATING_ROOM_REQUEST_OFF_C"] = "20"
        with self.assertRaisesRegex(ValueError, "fűtési igény bekapcsolási"):
            global_settings.save(values)

    def test_reload_updates_values_and_reports_restart_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "POLL_TIMEOUT_SECONDS=17\nAPP_TIMEZONE=UTC\n", encoding="utf-8"
            )
            with patch.object(global_settings, "ENV_PATH", env_path), patch.dict(
                os.environ,
                {"POLL_TIMEOUT_SECONDS": "5", "APP_TIMEZONE": "Europe/Budapest"},
                clear=False,
            ):
                changed, restart_required = global_settings.reload_environment()
                self.assertEqual(os.environ["POLL_TIMEOUT_SECONDS"], "17")
                self.assertEqual(os.environ["APP_TIMEZONE"], "UTC")
                self.assertEqual(changed, ("APP_TIMEZONE", "POLL_TIMEOUT_SECONDS"))
                self.assertEqual(restart_required, ("APP_TIMEZONE",))

    def test_reload_rejects_key_without_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("POLL_TIMEOUT_SECONDS\n", encoding="utf-8")
            with patch.object(global_settings, "ENV_PATH", env_path):
                with self.assertRaisesRegex(ValueError, "Érték nélküli"):
                    global_settings.reload_environment()


if __name__ == "__main__":
    unittest.main()
