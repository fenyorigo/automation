from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from app.cooling_observer import CoolingParameters, evaluate_room


NOW = datetime(2026, 9, 8, 12, 0, 0)


def device(device_id, name, source, temperature=None, **values):
    result = {
        "id": device_id,
        "name": name,
        "source_system": source,
        "device_type": values.pop("device_type", "temperature_sensor"),
        "temperature_c": temperature,
        "measurement_at": NOW - timedelta(minutes=5),
        "power": False,
        "mode": "cool",
        "target_temperature_c": 25,
    }
    result.update(values)
    return result


class CoolingObserverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.params = CoolingParameters()
        self.outdoor = {"temperature_c": 29.0}

    def test_primary_sensor_dominates_weighted_action_temperature(self) -> None:
        devices = [
            device(1, "Zb dolgozó", "zigbee2mqtt", 26.1),
            device(2, "HS dolgozó", "connectlife", 26.0),
            device(3, "CT emelet", "computherm", 25.4),
        ]
        advice = evaluate_room(devices, self.outdoor, now=NOW, params=self.params)
        self.assertAlmostEqual(advice["action_temperature_c"], 26.01)
        self.assertEqual([source["weight"] for source in advice["sources"]], [0.7, 0.2, 0.1])

    def test_hot_room_and_outdoor_temperature_would_start(self) -> None:
        devices = [
            device(1, "Zb Rita", "zigbee2mqtt", 28.0),
            device(2, "HS Rita", "connectlife", 28.0),
        ]
        advice = evaluate_room(devices, self.outdoor, now=NOW, params=self.params)
        self.assertTrue(advice["cooling_demand"])
        self.assertEqual(advice["status"], "would_start")

    def test_open_contact_blocks_start_but_preserves_demand(self) -> None:
        devices = [
            device(1, "Zb dolgozó", "zigbee2mqtt", 28.0),
            device(2, "HS dolgozó", "connectlife", 28.0),
            device(
                3,
                "Tuya erkélyajtó",
                "zigbee2mqtt",
                device_type="contact_sensor",
                zigbee_contact_closed=False,
                zigbee_contact_observed_at=NOW - timedelta(minutes=1),
            ),
        ]
        advice = evaluate_room(devices, self.outdoor, now=NOW, params=self.params)
        self.assertTrue(advice["cooling_demand"])
        self.assertEqual(advice["status"], "blocked")
        self.assertIn("Tuya erkélyajtó", advice["blockers"][0])

    def test_recent_close_blocks_until_stabilized(self) -> None:
        devices = [
            device(1, "Zb dolgozó", "zigbee2mqtt", 28.0),
            device(2, "HS dolgozó", "connectlife", 28.0),
            device(
                3,
                "Tuya ablak",
                "zigbee2mqtt",
                device_type="contact_sensor",
                zigbee_contact_closed=True,
                zigbee_contact_observed_at=NOW - timedelta(minutes=4),
            ),
        ]
        advice = evaluate_room(devices, self.outdoor, now=NOW, params=self.params)
        self.assertEqual(advice["status"], "blocked")

    def test_explicitly_unavailable_contact_blocks_even_when_closed(self) -> None:
        devices = [
            device(1, "Zb dolgozó", "zigbee2mqtt", 28.0),
            device(2, "HS dolgozó", "connectlife", 28.0),
            device(
                3,
                "Tuya ablak",
                "zigbee2mqtt",
                device_type="contact_sensor",
                zigbee_contact_closed=True,
                zigbee_contact_observed_at=NOW - timedelta(hours=3),
                online=False,
            ),
        ]
        advice = evaluate_room(devices, self.outdoor, now=NOW, params=self.params)
        self.assertEqual(advice["status"], "blocked")
        self.assertIn("Nem elérhető", advice["blockers"][0])

    def test_running_cooling_uses_lower_hysteresis_threshold(self) -> None:
        devices = [
            device(1, "Zb háló", "zigbee2mqtt", 27.2),
            device(2, "HS háló", "connectlife", 27.2, power=True),
        ]
        advice = evaluate_room(devices, self.outdoor, now=NOW, params=self.params)
        self.assertTrue(advice["cooling_demand"])
        self.assertEqual(advice["room_threshold_c"], 27.0)
        self.assertEqual(advice["status"], "would_keep_on")

    def test_stale_primary_returns_insufficient_data(self) -> None:
        primary = device(1, "Zb háló", "zigbee2mqtt", 28.0)
        primary["measurement_at"] = NOW - timedelta(hours=4)
        advice = evaluate_room(
            [primary, device(2, "HS háló", "connectlife", 28.0)],
            self.outdoor,
            now=NOW,
            params=self.params,
        )
        self.assertEqual(advice["status"], "insufficient_data")


if __name__ == "__main__":
    unittest.main()
