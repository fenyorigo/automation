import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from dashboard import (
    OUTDOOR_MEASUREMENT_LABELS,
    OUTDOOR_SOURCE_BADGES,
    mark_climate_control_devices,
    outdoor_summary_source,
)


class OutdoorSourceLabelTest(unittest.TestCase):
    def test_zigbee_is_not_described_as_provider_measurement(self) -> None:
        self.assertEqual(OUTDOOR_SOURCE_BADGES["zigbee2mqtt"], "Zigbee eszköz")
        self.assertEqual(
            OUTDOOR_MEASUREMENT_LABELS["zigbee2mqtt"], "Saját Zigbee-mérés"
        )

    def test_web_sources_are_described_as_web_weather_data(self) -> None:
        self.assertEqual(
            OUTDOOR_MEASUREMENT_LABELS["open_meteo"], "Webes időjárási adat"
        )
        self.assertEqual(
            OUTDOOR_MEASUREMENT_LABELS["wunderground_pws"],
            "Webes időjárási adat",
        )

    def test_device_backed_source_does_not_get_duplicate_summary_card(self) -> None:
        zigbee = {"source_type": "zigbee2mqtt", "display_name": "Kültéri hőmérő"}
        self.assertIsNone(outdoor_summary_source(zigbee))

    def test_web_fallback_keeps_summary_card(self) -> None:
        open_meteo = {"source_type": "open_meteo", "display_name": "Open-Meteo"}
        self.assertIs(outdoor_summary_source(open_meteo), open_meteo)

    def test_climate_filter_marks_only_devices_in_the_decision_chain(self) -> None:
        devices = [
            {"id": 1, "source_system": "connectlife", "room_id": 10, "device_type": "climate"},
            {"id": 2, "source_system": "computherm", "room_id": 10, "device_type": "thermostat"},
            {"id": 3, "source_system": "manual", "room_id": None, "device_type": "boiler"},
            {"id": 4, "source_system": "zigbee2mqtt", "room_id": 10, "device_type": "temperature_sensor"},
            {"id": 5, "source_system": "zigbee2mqtt", "room_id": 10, "device_type": "contact_sensor"},
            {"id": 6, "source_system": "shelly_mqtt", "room_id": 10, "device_type": "temperature_sensor"},
            {"id": 7, "source_system": "zigbee2mqtt", "room_id": 99, "device_type": "temperature_sensor"},
            {"id": 8, "source_system": "zigbee2mqtt", "room_id": 10, "device_type": "power_meter"},
            {"id": 9, "source_system": "tasmota", "source_device_id": "nous-kazan", "room_id": 11, "device_type": "power_meter"},
            {"id": 10, "source_system": "tasmota", "source_device_id": "nous-mainit", "room_id": 6, "device_type": "power_meter"},
        ]
        outdoor = {
            "source_type": "zigbee2mqtt",
            "configuration": '{"device_id": 7}',
        }

        mark_climate_control_devices(devices, outdoor)

        relevant = {item["id"] for item in devices if item["climate_control_relevant"]}
        self.assertEqual(relevant, {1, 2, 3, 4, 5, 7, 9})

    def test_dashboard_climate_filter_is_the_new_default(self) -> None:
        template = (
            Path(__file__).resolve().parents[1] / "app" / "templates" / "dashboard.html"
        ).read_text(encoding="utf-8")
        self.assertIn('value="climate_control"', template)
        self.assertIn("? 'climate_control' : 'all'", template)


if __name__ == "__main__":
    unittest.main()
