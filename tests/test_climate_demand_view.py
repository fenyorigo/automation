import unittest
from pathlib import Path
from unittest.mock import patch
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from dashboard import load_active_climate_room_groups, load_climate_demand_room_groups


class ClimateDemandViewTest(unittest.TestCase):
    @patch("dashboard.load_room_groups")
    def test_only_demanding_thermometers_are_grouped(self, room_groups) -> None:
        heating = {"id": 1, "heating_advice": {"heating_demand": True}}
        cooling = {"id": 2, "cooling_advice": {"cooling_demand": True}}
        served = {
            "id": 4,
            "heating_advice": {"heating_demand": True, "heating_active": True},
        }
        idle = {
            "id": 3,
            "heating_advice": {"heating_demand": False},
            "cooling_advice": {"cooling_demand": False},
        }
        room_groups.return_value = [
            {
                "name": "Emelet",
                "rooms": [
                    {"room_name": "Dolgozó", "devices": [heating]},
                    {"room_name": "Háló", "devices": []},
                ],
            }
        ]

        result = load_climate_demand_room_groups([heating, cooling, idle, served])

        room_groups.assert_called_once_with([heating, cooling])
        self.assertEqual([room["room_name"] for room in result[0]["rooms"]], ["Dolgozó"])

    @patch("dashboard.load_room_groups")
    def test_active_view_contains_heating_and_cooling_in_progress(self, room_groups) -> None:
        heating = {"id": 1, "heating_advice": {"heating_active": True}}
        cooling = {"id": 2, "cooling_advice": {"cooling_active": True}}
        idle = {"id": 3, "heating_advice": {"heating_active": False}}
        room_groups.return_value = [
            {
                "name": "Emelet",
                "rooms": [{"room_name": "Dolgozó", "devices": [heating, cooling]}],
            }
        ]

        result = load_active_climate_room_groups([heating, cooling, idle])

        room_groups.assert_called_once_with([heating, cooling])
        self.assertEqual(len(result[0]["rooms"][0]["devices"]), 2)

    def test_dashboard_offers_room_grouped_active_demand_view(self) -> None:
        template = (ROOT / "app" / "templates" / "dashboard.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("Aktív hőigény", template)
        self.assertIn("Fűtés/hűtés folyamatban", template)
        self.assertIn("demand_room_groups", template)
        self.assertIn("Jelenleg nincs ki nem szolgált fűtési vagy hűtési igény.", template)
        self.assertIn("Jelenleg nincs folyamatban fűtés vagy hűtés.", template)


if __name__ == "__main__":
    unittest.main()
