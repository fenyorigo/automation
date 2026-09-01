import json
import unittest
from datetime import UTC

from zigbee2mqtt_service import (
    ZigbeeMessageHandler,
    inferred_device_type,
    parse_last_seen,
    sensor_descriptors,
)


PLUG = {
    "friendly_name": "Smart Plug földszint",
    "ieee_address": "0xa4c138115778ffff",
    "manufacturer": "SONOFF",
    "model_id": "S60ZBTPF",
    "type": "Router",
    "supported": True,
    "interview_completed": True,
    "definition": {
        "exposes": [
            {"access": 1, "label": "Energy", "property": "energy", "type": "numeric", "unit": "kWh"},
            {"features": [{"access": 7, "label": "State", "property": "state", "type": "binary"}], "type": "switch"},
            {"access": 7, "category": "config", "label": "Power-on behavior", "property": "power_on_behavior", "type": "enum"},
            {"access": 5, "label": "Current", "property": "current", "type": "numeric", "unit": "A"},
            {"access": 5, "label": "Voltage", "property": "voltage", "type": "numeric", "unit": "V"},
            {"access": 5, "label": "Power", "property": "power", "type": "numeric", "unit": "W"},
            {"access": 7, "label": "Outlet control protect", "property": "outlet_control_protect", "type": "binary"},
            {"access": 2, "label": "Inching time", "property": "inching_time", "type": "numeric", "unit": "seconds"},
            {"access": 1, "category": "diagnostic", "label": "Linkquality", "property": "linkquality", "type": "numeric", "unit": "lqi"},
        ]
    },
}

THERMOMETER = {
    "friendly_name": "Dolgozó hőmérő",
    "ieee_address": "0x00124b0026ffffff",
    "manufacturer": "SONOFF",
    "model_id": "SNZB-02P",
    "type": "EndDevice",
    "supported": True,
    "interview_completed": True,
    "definition": {
        "exposes": [
            {"access": 5, "label": "Battery", "property": "battery", "type": "numeric", "unit": "%"},
            {"access": 5, "label": "Temperature", "property": "temperature", "type": "numeric", "unit": "°C"},
            {"access": 5, "label": "Humidity", "property": "humidity", "type": "numeric", "unit": "%"},
            {"access": 7, "category": "config", "label": "Temperature calibration", "property": "temperature_calibration", "type": "numeric", "unit": "°C"},
            {"access": 1, "category": "diagnostic", "label": "Linkquality", "property": "linkquality", "type": "numeric", "unit": "lqi"},
        ]
    },
}


class FakeRepository:
    def __init__(self) -> None:
        self.calls = []

    def sync_devices(self, devices):
        self.calls.append(("sync", devices))
        return len(devices)

    def cache_state(self, friendly_name, topic, payload, retained):
        self.calls.append(("cache", friendly_name, topic, payload, retained))
        return True

    def set_availability(self, friendly_name, availability):
        self.calls.append(("availability", friendly_name, availability))
        return True

    def mark_removed(self, ieee):
        self.calls.append(("removed", ieee))


class ZigbeeDiscoveryTest(unittest.TestCase):
    def test_extracts_only_published_measurement_properties(self) -> None:
        descriptors = {item["property"]: item for item in sensor_descriptors(PLUG)}
        self.assertEqual(
            set(descriptors), {"energy", "state", "current", "voltage", "power", "linkquality"}
        )
        self.assertEqual(descriptors["energy"]["sensor_type"], "energy_total")
        self.assertEqual(descriptors["energy"]["unit"], "kilowatt_hour")
        self.assertEqual(descriptors["state"]["unit"], "boolean")
        self.assertEqual(inferred_device_type(PLUG, list(descriptors.values())), "power_meter")

    def test_identifies_temperature_humidity_sensor(self) -> None:
        descriptors = {item["property"]: item for item in sensor_descriptors(THERMOMETER)}
        self.assertEqual(set(descriptors), {"battery", "temperature", "humidity", "linkquality"})
        self.assertEqual(descriptors["temperature"]["unit"], "celsius")
        self.assertEqual(descriptors["humidity"]["unit"], "percent")
        self.assertEqual(
            inferred_device_type(THERMOMETER, list(descriptors.values())),
            "temperature_sensor",
        )

    def test_routes_bridge_discovery_and_device_state(self) -> None:
        repository = FakeRepository()
        handler = ZigbeeMessageHandler(repository)
        result = handler.handle(
            "zigbee2mqtt/bridge/devices", json.dumps([PLUG]).encode(), retained=True
        )
        self.assertEqual(result, "discovered:1")
        result = handler.handle(
            "zigbee2mqtt/Smart Plug földszint",
            json.dumps({"power": 0, "last_seen": "2026-08-31T06:15:23.851Z"}).encode(),
        )
        self.assertEqual(result, "cached")
        self.assertEqual(repository.calls[-1][1], "Smart Plug földszint")

    def test_routes_availability_and_removal(self) -> None:
        repository = FakeRepository()
        handler = ZigbeeMessageHandler(repository)
        self.assertEqual(
            handler.handle(
                "zigbee2mqtt/Smart Plug emelet/availability", b"online"
            ),
            "availability",
        )
        self.assertEqual(
            handler.handle(
                "zigbee2mqtt/bridge/event",
                b'{"type":"device_leave","data":{"ieee_address":"0x1234"}}',
            ),
            "removed",
        )
        self.assertEqual(repository.calls[-1], ("removed", "0x1234"))

    def test_parses_iso_and_epoch_last_seen(self) -> None:
        iso = parse_last_seen("2026-08-31T06:15:23.851Z")
        epoch = parse_last_seen(iso.replace(tzinfo=UTC).timestamp())
        self.assertEqual(iso, epoch)


if __name__ == "__main__":
    unittest.main()
