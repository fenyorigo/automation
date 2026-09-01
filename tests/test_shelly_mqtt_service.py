import json
import unittest
from datetime import datetime
from decimal import Decimal

from shelly_mqtt_service import (
    ShellyMessageHandler,
    live_event_id,
    retained_event_id,
)


PREFIX = "shellyhtg3-48f6eebb92d4"


class FakeRepository:
    def __init__(self) -> None:
        self.calls = []

    def store_measurements(
        self, prefix, topic, payload, measurements, retained, payload_bytes
    ):
        self.calls.append(
            ("measurements", prefix, topic, payload, measurements, retained, payload_bytes)
        )
        return len(measurements)

    def register_online(self, prefix):
        self.calls.append(("online", prefix))


class ShellyMessageHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeRepository()
        self.handler = ShellyMessageHandler(self.repository)

    def test_routes_separate_temperature_and_humidity_messages(self) -> None:
        temperature = b'{"id":0,"tC":32.6,"tF":90.7}'
        humidity = b'{"id":0,"rh":67.9}'
        self.assertEqual(
            self.handler.handle(f"{PREFIX}/status/temperature:0", temperature),
            "stored:1",
        )
        self.assertEqual(
            self.repository.calls[-1][4],
            [("temperature", "celsius", Decimal("32.6"))],
        )
        self.assertEqual(
            self.handler.handle(f"{PREFIX}/status/humidity:0", humidity),
            "stored:1",
        )
        self.assertEqual(
            self.repository.calls[-1][4],
            [("humidity", "percent", Decimal("67.9"))],
        )

    def test_device_power_creates_two_independent_measurements(self) -> None:
        payload = b'{"id":0,"battery":{"V":5.68,"percent":84},"external":{"present":false}}'
        self.assertEqual(
            self.handler.handle(f"{PREFIX}/status/devicepower:0", payload),
            "stored:2",
        )
        self.assertEqual(
            self.repository.calls[-1][4],
            [
                ("battery", "percent", Decimal("84")),
                ("battery_voltage", "volt", Decimal("5.68")),
            ],
        )

    def test_ignores_other_mqtt_devices_and_online_value(self) -> None:
        self.assertEqual(
            self.handler.handle("unrelated/status/temperature:0", b'{"tC":21}'),
            "ignored",
        )
        self.assertEqual(self.handler.handle(f"{PREFIX}/online", b"false"), "online_ignored")
        self.assertEqual(self.repository.calls[-1], ("online", PREFIX))

    def test_retained_id_is_stable_but_live_id_uses_arrival_time(self) -> None:
        topic = f"{PREFIX}/status/temperature:0"
        payload = json.dumps({"id": 0, "tC": 20.0}).encode()
        self.assertEqual(
            retained_event_id(topic, payload, "temperature"),
            retained_event_id(topic, payload, "temperature"),
        )
        first = live_event_id(PREFIX, "temperature", datetime(2026, 9, 1, 10, 0, 0, 1))
        second = live_event_id(PREFIX, "temperature", datetime(2026, 9, 1, 10, 0, 0, 2))
        self.assertNotEqual(first, second)

    def test_rejects_missing_or_non_numeric_measurement(self) -> None:
        with self.assertRaises(ValueError):
            self.handler.handle(f"{PREFIX}/status/temperature:0", b'{"id":0}')
        with self.assertRaises(ValueError):
            self.handler.handle(f"{PREFIX}/status/humidity:0", b'{"rh":"67.9"}')


if __name__ == "__main__":
    unittest.main()
