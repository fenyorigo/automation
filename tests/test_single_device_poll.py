#!/usr/bin/env python3

import asyncio
from contextlib import nullcontext
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from poll_devices import DeviceConfig, PollResult  # noqa: E402
from poll_scheduler import run_device_cycle  # noqa: E402


class SingleDevicePollTest(unittest.TestCase):
    def test_selected_connectlife_device_is_polled_and_persisted(self) -> None:
        config = DeviceConfig(
            source_system="connectlife",
            hostname="",
            expected_ip="",
            mac_address="",
            device_id="hisense-office",
            connectlife_name="Dolgozó",
        )
        result = PollResult(
            source_system="connectlife",
            device_id="hisense-office",
            hostname="",
            observed_at="2026-10-13T10:00:00.000Z",
            success=True,
            duration_ms=123,
            state={"fan_speed": "medium"},
        )
        database = MagicMock()
        with (
            patch("poll_scheduler.polling_cycle_lock", return_value=nullcontext()),
            patch("poll_scheduler.load_devices", return_value=[config]),
            patch("poll_scheduler.poll_all", AsyncMock(return_value=[result])) as poll,
            patch("poll_scheduler.Database", return_value=database),
        ):
            actual = asyncio.run(
                run_device_cycle(
                    "connectlife", "hisense-office", 5.0, poll_origin="manual"
                )
            )

        self.assertIs(actual, result)
        poll.assert_awaited_once_with([config], 5.0)
        database.persist.assert_called_once_with(
            config, result, 123, poll_origin="manual"
        )
        database.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
