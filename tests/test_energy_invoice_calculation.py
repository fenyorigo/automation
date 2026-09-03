#!/usr/bin/env python3

import os
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
os.environ.setdefault("DB_PASSWORD", "test")

from dashboard import (
    complete_charge_gross,
    complete_gas_consumption_values,
    complete_invoice_gross,
    mj_to_kwh,
)


class EnergyInvoiceCalculationTest(unittest.TestCase):
    def test_calculates_invoice_gross_from_net_and_vat_amount(self):
        self.assertEqual(
            complete_invoice_gross(Decimal("33849"), Decimal("8659"), None),
            Decimal("42508.00"),
        )

    def test_calculates_charge_gross_from_net_and_vat_rate(self):
        self.assertEqual(
            complete_charge_gross(Decimal("9834"), Decimal("27"), None),
            Decimal("12489.18"),
        )

    def test_explicit_gross_overrides_calculation(self):
        self.assertEqual(
            complete_charge_gross(Decimal("9834"), Decimal("27"), Decimal("12489")),
            Decimal("12489"),
        )

    def test_converts_mj_to_kwh_with_global_factor(self):
        self.assertEqual(mj_to_kwh(Decimal("6508")), Decimal("1807.78"))

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
