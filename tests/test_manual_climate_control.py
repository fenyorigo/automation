from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.manual_climate_control import (
    annotate_manual_climate_controls,
    manual_climate_guard,
)


NOW = datetime(2026, 10, 13, 12, 0, 0)


def climate(**values):
    result = {
        "id": 10,
        "name": "HS dolgozó",
        "source_system": "connectlife",
        "room_id": 1,
        "control_enabled": True,
        "mode": "heat",
        "target_temperature_c": 21,
        "fan_speed": "medium",
    }
    result.update(values)
    return result


def contact(name="Tuya ablak", **values):
    result = {
        "id": 20,
        "name": name,
        "source_system": "zigbee2mqtt",
        "device_type": "contact_sensor",
        "room_id": 1,
        "opening_role": "external",
        "online": True,
        "zigbee_contact_closed": True,
        "zigbee_contact_observed_at": NOW - timedelta(minutes=20),
    }
    result.update(values)
    return result


class ManualClimateControlTest(unittest.TestCase):
    def test_open_external_contact_hard_blocks(self) -> None:
        unit = climate()
        guard = manual_climate_guard(
            unit,
            [unit, contact(zigbee_contact_closed=False)],
            {"temperature_c": 10},
            "heat",
            now=NOW,
        )
        self.assertTrue(guard["hard_blocked"])
        self.assertIn("Nyitott nyílászáró", guard["blockers"][0])

    def test_open_internal_contact_does_not_block(self) -> None:
        unit = climate()
        guard = manual_climate_guard(
            unit,
            [unit, contact(opening_role="internal", zigbee_contact_closed=False)],
            {"temperature_c": 10},
            "heat",
            now=NOW,
        )
        self.assertFalse(guard["hard_blocked"])

    def test_recent_close_blocks_until_mode_specific_wait_expires(self) -> None:
        unit = climate()
        with patch.dict(
            "os.environ", {"HEATING_WINDOW_CLOSE_STABILIZATION_MINUTES": "12"}
        ):
            guard = manual_climate_guard(
                unit,
                [unit, contact(zigbee_contact_observed_at=NOW - timedelta(minutes=5))],
                {"temperature_c": 10},
                "heat",
                now=NOW,
            )
        self.assertTrue(guard["hard_blocked"])
        self.assertIn("12 perces", guard["blockers"][0])

    def test_low_outdoor_temperature_requires_override_but_is_not_hard_block(self) -> None:
        unit = climate()
        with patch.dict("os.environ", {"HEATING_CLIMATE_MIN_OUTDOOR_C": "5"}):
            guard = manual_climate_guard(
                unit, [unit], {"temperature_c": 3.5}, "heat", now=NOW
            )
        self.assertFalse(guard["hard_blocked"])
        self.assertTrue(guard["outdoor_override_required"])
        self.assertIn("3.5 °C", guard["outdoor_warning"])

    def test_cooling_uses_global_target_and_outdoor_start_limits(self) -> None:
        unit = climate(mode="cool", target_temperature_c=23)
        with patch.dict(
            "os.environ",
            {"COOLING_MIN_TARGET_C": "25", "COOLING_OUTDOOR_ENABLE_C": "28.1"},
        ):
            guard = manual_climate_guard(
                unit, [unit], {"temperature_c": 27.9}, "cool", now=NOW
            )
        self.assertEqual(guard["target_min_c"], 25)
        self.assertTrue(guard["outdoor_override_required"])

    def test_annotation_attaches_both_modes_and_normalizes_default_target(self) -> None:
        unit = climate(mode="cool", target_temperature_c=21, fan_speed="unexpected")
        devices = [unit]
        annotate_manual_climate_controls(
            devices, {"temperature_c": 29}, now=NOW
        )
        controls = unit["manual_climate_control"]
        self.assertEqual(set(controls["modes"]), {"heat", "cool"})
        self.assertEqual(controls["selected_target_c"], 25)
        self.assertEqual(controls["selected_fan_speed"], "medium")


if __name__ == "__main__":
    unittest.main()
