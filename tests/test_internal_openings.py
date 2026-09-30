from __future__ import annotations

import unittest

from app.thermal_zones import connected_room_groups


def internal(room_id: int, connected_room_id: int, closed: bool, **values):
    contact = {
        "device_type": "contact_sensor",
        "opening_role": "internal",
        "room_id": room_id,
        "connected_room_id": connected_room_id,
        "zigbee_contact_closed": closed,
        "online": True,
    }
    contact.update(values)
    return contact


class InternalOpeningTest(unittest.TestCase):
    def test_three_open_doors_form_one_children_wing(self) -> None:
        contacts = [
            internal(1, 4, False),
            internal(2, 4, False),
            internal(3, 4, False),
        ]
        self.assertEqual(connected_room_groups([1, 2, 3, 4], contacts), [{1, 2, 3, 4}])

    def test_closed_rita_door_separates_only_rita(self) -> None:
        contacts = [
            internal(1, 4, True),
            internal(2, 4, False),
            internal(3, 4, False),
        ]
        self.assertEqual(connected_room_groups([1, 2, 3, 4], contacts), [{1}, {2, 3, 4}])

    def test_only_one_open_door_connects_only_that_room(self) -> None:
        contacts = [
            internal(1, 4, True),
            internal(2, 4, False),
            internal(3, 4, True),
        ]
        self.assertEqual(connected_room_groups([1, 2, 3, 4], contacts), [{1}, {2, 4}, {3}])

    def test_all_closed_leaves_every_room_separate(self) -> None:
        contacts = [internal(1, 4, True), internal(2, 4, True), internal(3, 4, True)]
        self.assertEqual(connected_room_groups([1, 2, 3, 4], contacts), [{1}, {2}, {3}, {4}])

    def test_unavailable_open_contact_does_not_join_rooms(self) -> None:
        contacts = [internal(1, 4, False, online=False)]
        self.assertEqual(connected_room_groups([1, 4], contacts), [{1}, {4}])

    def test_registry_and_collector_encode_non_blocking_role(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        collector = (root / "app" / "zigbee2mqtt_service.py").read_text()
        registry = (root / "app" / "templates" / "locations.html").read_text()
        card = (root / "app" / "templates" / "_device_card.html").read_text()
        stylesheet = (root / "app" / "static" / "dashboard.css").read_text()
        self.assertIn("d.opening_role='external'", collector)
        self.assertIn('value="internal"', registry)
        self.assertIn("Belső ajtó · nem blokkol", card)
        self.assertIn("internal-opening-provenance", card)
        self.assertIn(".internal-opening-provenance { margin:10px 0 16px; }", stylesheet)


if __name__ == "__main__":
    unittest.main()
