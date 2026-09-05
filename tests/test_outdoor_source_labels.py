import unittest

from dashboard import OUTDOOR_MEASUREMENT_LABELS, OUTDOOR_SOURCE_BADGES


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


if __name__ == "__main__":
    unittest.main()
