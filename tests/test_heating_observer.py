from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from app.heating_observer import (
    HeatingParameters,
    annotate_ground_floor_heating,
    annotate_upstairs_heating,
    evaluate_room,
)


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
        self.assertAlmostEqual(result["action_temperature_c"], 19.10)
        self.assertEqual(
            [(source["name"], source["weight"]) for source in result["sources"]],
            [("Zb dolgozó", 0.5), ("CT400 emelet", 0.5)],
        )
        self.assertTrue(result["heating_demand"])
        self.assertEqual(result["status"], "climate_eligible")

    def test_computherm_in_another_room_does_not_affect_action_temperature(self) -> None:
        result = evaluate_room(
            [
                device(1, "Zb háló", "zigbee2mqtt", 19.0, room_id=2),
                device(2, "HS háló", "connectlife", 19.5, room_id=2),
                device(3, "CT400 emelet", "computherm", 22.0, room_id=1),
            ],
            {"temperature_c": 7.0},
            now=NOW,
            params=self.params,
        )
        self.assertAlmostEqual(result["action_temperature_c"], 19.10)
        self.assertEqual(
            [source["name"] for source in result["sources"]],
            ["Zb háló", "HS háló"],
        )

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

    def test_ground_floor_thermostat_gets_gas_only_advice(self) -> None:
        devices = [
            device(
                1, "CT400 földszint", "computherm", 20.0,
                zone_name="Földszint", room_name="Földszinti nappali", active=True,
            ),
            device(
                2, "Bosch 7000i", "manual", room_id=9, room_name="Kazánház",
                zone_name="Földszint", device_type="boiler",
                managed_manually=True, manual_power_state=False,
            ),
        ]

        advice = annotate_ground_floor_heating(devices)

        self.assertEqual(advice["preferred_source"], "gas")
        self.assertTrue(advice["boiler_action_required"])
        self.assertFalse(advice["climate_selection"])
        self.assertIs(devices[0]["heating_zone_advice"], advice)

    def test_ground_floor_reports_active_gas_heating(self) -> None:
        devices = [
            device(1, "CT400 földszint", "computherm", zone_name="Földszint", active=True),
            device(
                2, "Bosch 7000i", "manual", zone_name="Földszint",
                device_type="boiler", manual_power_state=True,
            ),
        ]
        advice = annotate_ground_floor_heating(devices)
        self.assertEqual(advice["status"], "gas")
        self.assertFalse(advice["boiler_action_required"])

    def test_ground_floor_uses_same_room_zigbee_and_computherm_average(self) -> None:
        devices = [
            device(
                1, "CT400 földszint", "computherm", 19.3,
                room_id=7, room_name="Vendégszoba", zone_name="Földszint",
                active=False,
            ),
            device(
                2, "Zb vendégszoba", "zigbee2mqtt", 18.9,
                room_id=7, room_name="Vendégszoba", zone_name="Földszint",
            ),
            device(
                3, "Zb másik szoba", "zigbee2mqtt", 25.0,
                room_id=8, room_name="Nappali", zone_name="Földszint",
            ),
        ]

        advice = annotate_ground_floor_heating(devices)

        self.assertAlmostEqual(advice["action_temperature_c"], 19.1)
        self.assertEqual(
            [(source["name"], source["weight"]) for source in advice["sources"]],
            [("Zb vendégszoba", 0.5), ("CT400 földszint", 0.5)],
        )
        self.assertTrue(advice["automation_heating_demand"])
        self.assertFalse(advice["thermostat_calling"])
        self.assertEqual(advice["status"], "automation_demand")
        self.assertTrue(devices[1]["heating_advice"]["heating_demand"])


if __name__ == "__main__":
    unittest.main()
