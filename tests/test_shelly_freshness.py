import unittest
from datetime import datetime, timedelta

from dashboard import shelly_freshness_status


class ShellyFreshnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 9, 1, 18, 0, 0)

    def status_after(self, age: timedelta):
        return shelly_freshness_status(self.now - age, self.now)

    def test_fresh_for_first_hour(self) -> None:
        self.assertEqual(self.status_after(timedelta(hours=1)), ("online", "Friss mérés", True))

    def test_sleeping_from_one_to_two_hours(self) -> None:
        self.assertEqual(
            self.status_after(timedelta(hours=1, seconds=1)),
            ("warning", "Alvó", True),
        )
        self.assertEqual(self.status_after(timedelta(hours=2)), ("warning", "Alvó", True))

    def test_delayed_from_two_to_four_hours(self) -> None:
        self.assertEqual(
            self.status_after(timedelta(hours=2, seconds=1)),
            ("delayed", "Jelentés késik", True),
        )
        self.assertEqual(
            self.status_after(timedelta(hours=4)),
            ("delayed", "Jelentés késik", True),
        )

    def test_stale_after_four_hours_or_without_measurement(self) -> None:
        self.assertEqual(
            self.status_after(timedelta(hours=4, seconds=1)),
            ("offline", "Nincs friss mérés", False),
        )
        self.assertEqual(shelly_freshness_status(None, self.now), ("offline", "Nincs mérés", False))


if __name__ == "__main__":
    unittest.main()
