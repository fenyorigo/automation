import unittest

from dashboard import (
    OUTDOOR_MEASUREMENT_LABELS,
    OUTDOOR_SOURCE_BADGES,
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


if __name__ == "__main__":
    unittest.main()
