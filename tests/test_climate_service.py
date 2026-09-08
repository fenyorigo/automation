import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from climate_control import control_climate
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

    def __init__(self, username, password) -> None:
        pass

    async def get_appliances(self):
        return [self.appliance]

    async def update_appliance(self, puid, properties):
        type(self).last_properties = properties
        self.appliance.status_list.update(properties)


class ClimateServiceControlTests(unittest.TestCase):
    def setUp(self) -> None:
        FakeApi.appliance = FakeAppliance()
        FakeApi.last_properties = None

    @patch.dict(os.environ, {"CONNECTLIFE_USERNAME": "u", "CONNECTLIFE_PASSWORD": "p"})
    @patch("climate_control.asyncio.sleep", new_callable=AsyncMock)
    @patch("climate_control.ConnectLifeApi", FakeApi)
    def test_service_command_sets_heat_mode_and_verifies_it(self, _sleep) -> None:
        result = asyncio.run(control_climate(
            "test-wifi", True, 30, "high", mode="heat", allow_running_update=True
        ))
        self.assertEqual(result.status, "verified")
        self.assertEqual(result.verified["mode"], "heat")
        self.assertEqual(FakeApi.last_properties["t_work_mode"], "1")

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
