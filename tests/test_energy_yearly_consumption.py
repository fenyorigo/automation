from datetime import datetime
from decimal import Decimal
import sys
import unittest

sys.path.insert(0, "app")

from dashboard import billing_period_consumption, yearly_meter_consumption


class YearlyMeterConsumptionTest(unittest.TestCase):
    def test_billing_period_uses_november_baseline(self) -> None:
        self.assertEqual(
            billing_period_consumption(Decimal("29826"), Decimal("27332")),
            Decimal("2494"),
        )

    def test_billing_period_requires_baseline(self) -> None:
        self.assertIsNone(billing_period_consumption(Decimal("29826"), None))

    def test_uses_actual_first_reading_within_31_days(self) -> None:
        result = yearly_meter_consumption(
            datetime(2026, 1, 1), datetime(2026, 1, 6), Decimal("100"),
            Decimal("130"), datetime(2025, 12, 5), Decimal("90"),
        )
        self.assertEqual(result, (Decimal("30"), datetime(2026, 1, 6), False))

    def test_estimates_january_first_for_late_first_reading(self) -> None:
        result = yearly_meter_consumption(
            datetime(2026, 1, 1), datetime(2026, 2, 2), Decimal("226"),
            Decimal("300"), datetime(2025, 12, 1), Decimal("100"),
        )
        self.assertEqual(result, (Decimal("138.000"), datetime(2026, 1, 1), True))

    def test_late_first_reading_falls_back_without_previous_year(self) -> None:
        result = yearly_meter_consumption(
            datetime(2026, 1, 1), datetime(2026, 5, 31), Decimal("250"),
            Decimal("300"), None, None,
        )
        self.assertEqual(result, (Decimal("50"), datetime(2026, 5, 31), False))


if __name__ == "__main__":
    unittest.main()
