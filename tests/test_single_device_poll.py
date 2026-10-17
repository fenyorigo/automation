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
from poll_scheduler import run_cycle, run_device_cycle  # noqa: E402


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

    def test_automatic_cycle_enables_computherm_clock_sync(self) -> None:
        config = DeviceConfig(
            source_system="computherm",
            hostname="ct400.home",
            expected_ip="192.168.0.10",
            mac_address="00:11:22:33:44:55",
            device_id="ct400-test",
            device_type_code="0x4ead",
        )
        result = PollResult(
            source_system="computherm",
            device_id="ct400-test",
            hostname="ct400.home",
            observed_at="2026-10-17T10:00:00.000Z",
            success=True,
        )
        selector = MagicMock()
        selector.polling_configs.return_value = [config]
        database = MagicMock()
        with (
            patch("poll_scheduler.polling_cycle_lock", return_value=nullcontext()),
            patch("poll_scheduler.load_devices", return_value=[config]),
            patch(
                "poll_scheduler.poll_all", AsyncMock(return_value=[result])
            ) as poll,
            patch("poll_scheduler.Database", side_effect=[selector, database]),
        ):
            asyncio.run(
                run_cycle(5.0, poll_outdoor=False, poll_origin="automatic")
            )

        poll.assert_awaited_once_with(
            [config], 5.0, synchronize_computherm_clock=True
        )

    def test_manual_cycle_does_not_enable_computherm_clock_sync(self) -> None:
        config = DeviceConfig(
            source_system="computherm",
            hostname="ct400.home",
            expected_ip="192.168.0.10",
            mac_address="00:11:22:33:44:55",
            device_id="ct400-test",
            device_type_code="0x4ead",
        )
        result = PollResult(
            source_system="computherm",
            device_id="ct400-test",
            hostname="ct400.home",
            observed_at="2026-10-17T10:00:00.000Z",
            success=True,
        )
        selector = MagicMock()
        selector.polling_configs.return_value = [config]
        database = MagicMock()
        with (
            patch("poll_scheduler.polling_cycle_lock", return_value=nullcontext()),
            patch("poll_scheduler.load_devices", return_value=[config]),
            patch(
                "poll_scheduler.poll_all", AsyncMock(return_value=[result])
            ) as poll,
            patch("poll_scheduler.Database", side_effect=[selector, database]),
        ):
            asyncio.run(
                run_cycle(5.0, poll_outdoor=False, poll_origin="manual")
            )

        poll.assert_awaited_once_with(
            [config], 5.0, synchronize_computherm_clock=False
        )


if __name__ == "__main__":
    unittest.main()
