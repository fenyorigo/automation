import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from climate_control import (
    FAN_CONTROL_SETTLE_SECONDS,
    FAN_STABLE_CONFIRMATIONS,
    FAN_VERIFICATION_INTERVAL_SECONDS,
    control_climate,
)
import scheduled_climate


class FakeAppliance:
    def __init__(self, *, power: int = 0, mode: str = "2") -> None:
        self.wifi_id = "test-wifi"
        self.puid = "test-puid"
        self.status_list = {
            "t_power": power,
            "t_work_mode": mode,
            "t_temp": "25",
            "t_fan_speed": "0",
            "t_fan_mute": "0",
        }


class FakeApi:
    appliance = FakeAppliance()
    last_properties = None
    updates = []
    rejected_fan_values = set()
    transient_fan_reads = None
    transient_fan_fallback = "0"
    fan_reads_remaining = None

    def __init__(self, username, password) -> None:
        pass

    async def get_appliances(self):
        if type(self).fan_reads_remaining is not None:
            if type(self).fan_reads_remaining == 0:
                self.appliance.status_list["t_fan_speed"] = type(self).transient_fan_fallback
                type(self).fan_reads_remaining = None
            else:
                type(self).fan_reads_remaining -= 1
        return [self.appliance]

    async def update_appliance(self, puid, properties):
        type(self).last_properties = properties
        type(self).updates.append(properties.copy())
        applied = properties.copy()
        if applied.get("t_fan_speed") in type(self).rejected_fan_values:
            applied["t_fan_speed"] = "0"
        self.appliance.status_list.update(applied)
        if "t_fan_speed" in properties and type(self).transient_fan_reads is not None:
            type(self).fan_reads_remaining = type(self).transient_fan_reads


class ClimateServiceControlTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeApi.appliance = FakeAppliance()
        FakeApi.last_properties = None
        FakeApi.updates = []
        FakeApi.rejected_fan_values = set()
        FakeApi.transient_fan_reads = None
        FakeApi.transient_fan_fallback = "0"
        FakeApi.fan_reads_remaining = None

    @patch.dict(os.environ, {"CONNECTLIFE_USERNAME": "u", "CONNECTLIFE_PASSWORD": "p"})
    @patch("climate_control.asyncio.sleep", new_callable=AsyncMock)
    @patch("climate_control.ConnectLifeApi", FakeApi)
    def test_service_command_sets_heat_mode_and_verifies_it(self, _sleep) -> None:
        result = asyncio.run(control_climate(
            "test-wifi", True, 30, "high", mode="heat", allow_running_update=True
        ))
        self.assertEqual(result.status, "verified")
        self.assertEqual(result.verified["mode"], "heat")
        self.assertEqual(len(FakeApi.updates), 2)
        self.assertEqual(FakeApi.updates[0]["t_work_mode"], "1")
        self.assertNotIn("t_fan_speed", FakeApi.updates[0])
        self.assertEqual(
            FakeApi.updates[1],
            {"t_fan_speed": "9", "t_fan_speed_s": "9", "t_fan_mute": "0"},
        )
        self.assertIn(((FAN_CONTROL_SETTLE_SECONDS,), {}), _sleep.call_args_list)

    @patch.dict(os.environ, {"CONNECTLIFE_USERNAME": "u", "CONNECTLIFE_PASSWORD": "p"})
    @patch("climate_control.asyncio.sleep", new_callable=AsyncMock)
    @patch("climate_control.ConnectLifeApi", FakeApi)
    def test_skips_second_write_when_started_fan_already_matches(self, _sleep) -> None:
        FakeApi.appliance.status_list["t_fan_speed"] = "7"

        result = asyncio.run(control_climate(
            "test-wifi", True, 20, "medium", mode="heat",
            allow_running_update=True,
        ))

        self.assertEqual(result.status, "verified")
        self.assertEqual(len(FakeApi.updates), 1)
        self.assertNotIn("t_fan_speed", FakeApi.updates[0])
        self.assertNotIn(((FAN_CONTROL_SETTLE_SECONDS,), {}), _sleep.call_args_list)

    @patch.dict(os.environ, {"CONNECTLIFE_USERNAME": "u", "CONNECTLIFE_PASSWORD": "p"})
    @patch("climate_control.asyncio.sleep", new_callable=AsyncMock)
    @patch("climate_control.ConnectLifeApi", FakeApi)
    def test_reports_two_step_progress_and_observed_states(self, _sleep) -> None:
        phases = []

        async def progress(phase, state):
            phases.append((phase, None if state is None else state["fan_speed"]))

        result = asyncio.run(control_climate(
            "test-wifi", True, 20, "medium", mode="heat",
            allow_running_update=True, progress=progress,
        ))

        self.assertEqual(result.status, "verified")
        self.assertEqual(
            [phase for phase, _ in phases],
            [
                "preflight", "power_mode_target", "verify_power",
                "stabilizing_fan", "setting_fan",
                *(["confirming_fan"] * FAN_STABLE_CONFIRMATIONS),
            ],
        )
        self.assertIn(((FAN_VERIFICATION_INTERVAL_SECONDS,), {}), _sleep.call_args_list)

    @patch.dict(os.environ, {"CONNECTLIFE_USERNAME": "u", "CONNECTLIFE_PASSWORD": "p"})
    @patch("climate_control.asyncio.sleep", new_callable=AsyncMock)
    @patch("climate_control.ConnectLifeApi", FakeApi)
    def test_retries_fan_write_then_restores_original_level_on_failure(self, _sleep) -> None:
        FakeApi.appliance = FakeAppliance(power=1, mode="1")
        FakeApi.appliance.status_list["t_temp"] = "20"
        FakeApi.appliance.status_list["t_fan_speed"] = "7"
        FakeApi.rejected_fan_values = {"6"}

        result = asyncio.run(control_climate(
            "test-wifi", True, 20, "medium_low", mode="heat",
            allow_running_update=True,
        ))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.verified["fan_speed"], "medium")
        self.assertIn("visszaállítottuk", result.error_message)
        fan_writes = [item["t_fan_speed"] for item in FakeApi.updates if "t_fan_speed" in item]
        self.assertEqual(fan_writes, ["6", "6", "6", "7"])

    @patch.dict(os.environ, {"CONNECTLIFE_USERNAME": "u", "CONNECTLIFE_PASSWORD": "p"})
    @patch("climate_control.asyncio.sleep", new_callable=AsyncMock)
    @patch("climate_control.ConnectLifeApi", FakeApi)
    def test_transient_fan_echo_is_not_accepted_as_verified(self, _sleep) -> None:
        FakeApi.appliance = FakeAppliance(power=1, mode="1")
        FakeApi.appliance.status_list["t_temp"] = "20"
        FakeApi.appliance.status_list["t_fan_speed"] = "0"
        FakeApi.transient_fan_reads = 1

        result = asyncio.run(control_climate(
            "test-wifi", True, 20, "medium", mode="heat",
            allow_running_update=True,
        ))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "fan_verification_failed")
        fan_writes = [item["t_fan_speed"] for item in FakeApi.updates if "t_fan_speed" in item]
        self.assertEqual(fan_writes, ["7", "7", "7"])

    @patch.dict(os.environ, {"CONNECTLIFE_USERNAME": "u", "CONNECTLIFE_PASSWORD": "p"})
    @patch("climate_control.ConnectLifeApi", FakeApi)
    def test_rejects_unknown_mode_before_write(self) -> None:
        result = asyncio.run(control_climate(
            "test-wifi", True, 25, "auto", mode="invalid", allow_running_update=True
        ))
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.error_code, "invalid_mode")
        self.assertIsNone(FakeApi.last_properties)

    @patch.dict(os.environ, {"CLIMATE_SERVICE_MODE": "true"})
    @patch("scheduled_climate._claim_due_program")
    def test_service_mode_suspends_scheduled_commands(self, claim) -> None:
        processed = asyncio.run(scheduled_climate.process_due_climate_schedules())
        self.assertEqual(processed, 0)
        claim.assert_not_called()


if __name__ == "__main__":
    unittest.main()
