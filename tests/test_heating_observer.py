from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from app.heating_observer import HeatingParameters, annotate_upstairs_heating, evaluate_room


NOW = datetime(2026, 12, 8, 12, 0, 0)


def device(device_id, name, source, temperature=None, room_id=1, **values):
    result = {
        "id": device_id,
        "name": name,
        "source_system": source,
        "device_type": values.pop("device_type", "temperature_sensor"),
        "room_id": room_id,
        "room_name": values.pop("room_name", "Dolgozó"),
        "zone_name": values.pop("zone_name", "Emelet"),
        "temperature_c": temperature,
        "measurement_at": NOW - timedelta(minutes=5),
        "poll_success": True,
        "power": False,
        "active": False,
        "mode": "heat",
        "target_temperature_c": 20,
    }
    result.update(values)
    return result


class HeatingObserverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.params = HeatingParameters()

    def test_cold_room_is_climate_eligible_above_outdoor_limit(self) -> None:
        result = evaluate_room(
            [
                device(1, "Zb dolgozó", "zigbee2mqtt", 19.0),
                device(2, "HS dolgozó", "connectlife", 19.5),
                device(3, "CT400 emelet", "computherm", 19.2),
            ],
            {"temperature_c": 7.0},
            now=NOW,
            params=self.params,
        )
        self.assertAlmostEqual(result["action_temperature_c"], 19.12)
        self.assertTrue(result["heating_demand"])
        self.assertEqual(result["status"], "climate_eligible")

    def test_low_outdoor_temperature_selects_gas(self) -> None:
        result = evaluate_room(
            [
                device(1, "Zb háló", "zigbee2mqtt", 19.0),
                device(2, "HS háló", "connectlife", 19.0),
            ],
            {"temperature_c": 2.0},
            now=NOW,
            params=self.params,
        )
        self.assertEqual(result["status"], "gas_required")

    def test_open_window_blocks_room_without_selecting_gas(self) -> None:
        result = evaluate_room(
            [
                device(1, "Zb dolgozó", "zigbee2mqtt", 19.0),
                device(2, "HS dolgozó", "connectlife", 19.0),
                device(
                    3,
                    "Tuya erkélyajtó",
                    "zigbee2mqtt",
                    device_type="contact_sensor",
                    zigbee_contact_closed=False,
                    zigbee_contact_observed_at=NOW,
                ),
            ],
            {"temperature_c": 2.0},
            now=NOW,
            params=self.params,
        )
        self.assertEqual(result["status"], "blocked")

    def test_heating_hysteresis_uses_off_threshold_while_active(self) -> None:
        result = evaluate_room(
            [
                device(1, "Zb háló", "zigbee2mqtt", 20.3),
                device(2, "HS háló", "connectlife", 20.3, power=True),
            ],
            {"temperature_c": 7.0},
            now=NOW,
            params=self.params,
        )
        self.assertTrue(result["heating_demand"])
        self.assertEqual(result["room_threshold_c"], 20.5)

    def test_one_ineligible_demanded_room_selects_gas_for_whole_zone(self) -> None:
        devices = [
            device(1, "Zb dolgozó", "zigbee2mqtt", 19.0, room_id=1),
            device(2, "HS dolgozó", "connectlife", 19.0, room_id=1),
            device(3, "Zb háló", "zigbee2mqtt", 19.0, room_id=2, room_name="Háló"),
            device(
                4,
                "HS háló",
                "connectlife",
                19.0,
                room_id=2,
                room_name="Háló",
                poll_success=False,
            ),
            device(
                5,
                "CT400 emelet",
                "computherm",
                19.0,
                room_id=1,
                active=True,
            ),
            device(
                6,
                "Bosch 7000i",
                "manual",
                room_id=9,
                room_name="Kazánház",
                zone_name="Földszint",
                device_type="boiler",
                managed_manually=True,
                manual_power_state=False,
            ),
        ]
        advice = annotate_upstairs_heating(devices, {"temperature_c": 7.0})
        self.assertEqual(advice["preferred_source"], "gas")
        self.assertTrue(advice["boiler_action_required"])
        thermostat = next(item for item in devices if item["source_system"] == "computherm")
        self.assertTrue(thermostat["boiler_status"]["heating_unavailable"])

    def test_all_actionable_rooms_prefer_climate_and_never_mixed(self) -> None:
        devices = [
            device(1, "Zb dolgozó", "zigbee2mqtt", 19.0, room_id=1),
            device(2, "HS dolgozó", "connectlife", 19.0, room_id=1),
            device(3, "Zb háló", "zigbee2mqtt", 19.0, room_id=2, room_name="Háló"),
            device(4, "HS háló", "connectlife", 19.0, room_id=2, room_name="Háló"),
        ]
        advice = annotate_upstairs_heating(devices, {"temperature_c": 7.0})
        self.assertEqual(advice["preferred_source"], "climate")
        self.assertFalse(advice["mixed_operation_allowed"])


if __name__ == "__main__":
    unittest.main()
