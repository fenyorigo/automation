from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from database import Database  # noqa: E402
from poll_devices import DeviceConfig, poll_computherm  # noqa: E402


class FakeThermostat:
    def __init__(self, minute: int = 10) -> None:
        self.state = {
            "power": 1,
            "active": 0,
            "auto_mode": 1,
            "room_temp": 19.5,
            "thermostat_temp": 19.0,
            "dayofweek": 6,
            "hour": 12,
            "min": minute,
            "sec": 0,
        }
        self.time_calls: list[tuple[int, int, int, int]] = []
        self.timeout = 0

    def auth(self) -> None:
        pass

    def get_full_status(self) -> dict:
        return dict(self.state)

    def set_time(self, hour: int, minute: int, second: int, day: int) -> None:
        self.time_calls.append((hour, minute, second, day))
        self.state.update(hour=hour, min=minute, sec=second, dayofweek=day)


def config() -> DeviceConfig:
    return DeviceConfig(
        source_system="computherm",
        hostname="ct400.home",
        expected_ip="192.168.0.10",
        mac_address="00:11:22:33:44:55",
        device_id="ct400-test",
        device_type_code="0x4ead",
    )


class ComputhermAutomaticClockSyncTest(unittest.TestCase):
    local_zone = ZoneInfo("Europe/Budapest")

    def test_more_than_five_minutes_is_synchronized_and_recorded(self) -> None:
        device = FakeThermostat(minute=10)
        times = [
            datetime(2026, 10, 17, 12, 0, 0, tzinfo=self.local_zone),
            datetime(2026, 10, 17, 12, 0, 1, tzinfo=self.local_zone),
        ]
        with (
            patch("poll_devices.broadlink.gendevice", return_value=device),
            patch("poll_devices.budapest_now", side_effect=times),
        ):
            result = poll_computherm(config(), 5, synchronize_clock=True)

        self.assertTrue(result.success)
        self.assertEqual(device.time_calls, [(12, 0, 1, 6)])
        event = result.state["clock_sync"]
        self.assertTrue(event["success"])
        self.assertEqual(event["drift_seconds"], 600)
        self.assertEqual(result.state["raw"]["min"], 0)

    def test_exactly_five_minutes_does_not_write(self) -> None:
        device = FakeThermostat(minute=5)
        with (
            patch("poll_devices.broadlink.gendevice", return_value=device),
            patch(
                "poll_devices.budapest_now",
                return_value=datetime(
                    2026, 10, 17, 12, 0, 0, tzinfo=self.local_zone
                ),
            ),
        ):
            result = poll_computherm(config(), 5, synchronize_clock=True)

        self.assertTrue(result.success)
        self.assertEqual(device.time_calls, [])
        self.assertNotIn("clock_sync", result.state)

    def test_ui_managed_minute_threshold_is_applied(self) -> None:
        device = FakeThermostat(minute=10)
        with (
            patch("poll_devices.broadlink.gendevice", return_value=device),
            patch(
                "poll_devices.budapest_now",
                return_value=datetime(
                    2026, 10, 17, 12, 0, 0, tzinfo=self.local_zone
                ),
            ),
            patch.dict(
                os.environ,
                {"COMPUTHERM_CLOCK_SYNC_THRESHOLD_MINUTES": "15"},
            ),
        ):
            result = poll_computherm(config(), 5, synchronize_clock=True)

        self.assertEqual(device.time_calls, [])
        self.assertNotIn("clock_sync", result.state)

    def test_failed_sync_keeps_valid_measurement(self) -> None:
        class BrokenClock(FakeThermostat):
            def set_time(self, hour: int, minute: int, second: int, day: int) -> None:
                raise RuntimeError("write failed")

        device = BrokenClock(minute=10)
        times = [
            datetime(2026, 10, 17, 12, 0, 0, tzinfo=self.local_zone),
            datetime(2026, 10, 17, 12, 0, 1, tzinfo=self.local_zone),
        ]
        with (
            patch("poll_devices.broadlink.gendevice", return_value=device),
            patch("poll_devices.budapest_now", side_effect=times),
        ):
            result = poll_computherm(config(), 5, synchronize_clock=True)

        self.assertTrue(result.success)
        self.assertEqual(result.measurements[0]["value"], 19.5)
        self.assertFalse(result.state["clock_sync"]["success"])
        self.assertIn("write failed", result.state["clock_sync"]["error_message"])

    def test_database_audit_insert_uses_clock_sync_event(self) -> None:
        class Cursor:
            def __init__(self) -> None:
                self.calls = []

            def execute(self, sql, parameters) -> None:
                self.calls.append((sql, parameters))

        device = FakeThermostat(minute=10)
        times = [
            datetime(2026, 10, 17, 12, 0, 0, tzinfo=self.local_zone),
            datetime(2026, 10, 17, 12, 0, 1, tzinfo=self.local_zone),
        ]
        with (
            patch("poll_devices.broadlink.gendevice", return_value=device),
            patch("poll_devices.budapest_now", side_effect=times),
        ):
            result = poll_computherm(config(), 5, synchronize_clock=True)
        cursor = Cursor()

        Database._insert_computherm_clock_sync(cursor, 42, config(), result)

        self.assertEqual(len(cursor.calls), 1)
        self.assertIn("INSERT INTO computherm_clock_syncs", cursor.calls[0][0])
        self.assertEqual(cursor.calls[0][1][0], 42)


if __name__ == "__main__":
    unittest.main()
