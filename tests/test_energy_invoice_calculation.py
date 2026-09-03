#!/usr/bin/env python3

import os
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
os.environ.setdefault("DB_PASSWORD", "test")

from dashboard import complete_gas_consumption_values


class EnergyInvoiceCalculationTest(unittest.TestCase):
    def test_calculates_values_using_invoice_rounding(self):
        values = complete_gas_consumption_values(
            Decimal("148"), Decimal("1.0000"), Decimal("35.37")
        )
        self.assertEqual(
            values,
            (Decimal("1.0000"), Decimal("148.00"), Decimal("35.37"), Decimal("5235")),
        )

    def test_defaults_factor_and_preserves_explicit_invoice_values(self):
        values = complete_gas_consumption_values(
            Decimal("36"), None, Decimal("35.37"), Decimal("36.01"), Decimal("1274")
        )
        self.assertEqual(
            values,
            (Decimal("1"), Decimal("36.01"), Decimal("35.37"), Decimal("1274")),
        )

    def test_requires_positive_heating_value(self):
        with self.assertRaises(ValueError):
            complete_gas_consumption_values(Decimal("10"), None, None)


if __name__ == "__main__":
    unittest.main()
