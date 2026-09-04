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
    complete_charge_amounts,
    complete_charge_metadata,
    complete_gas_consumption_values,
    complete_invoice_gross,
    complete_invoice_payable,
    mj_to_kwh,
)


class EnergyInvoiceCalculationTest(unittest.TestCase):
    def test_charge_category_fills_description_and_unit(self):
        self.assertEqual(
            complete_charge_metadata("market_energy", "rossz név", None),
            ("Versenypiaci költségeket tükröző ár", "MJ"),
        )
        self.assertEqual(
            complete_charge_metadata("base_fee", "", None),
            ("Háztartási alapdíj", "hó"),
        )

    def test_service_preserves_selected_name_and_uses_month_unit(self):
        self.assertEqual(
            complete_charge_metadata("service", "OtthonSOS Garancia Médium", None),
            ("OtthonSOS Garancia Médium", "hó"),
        )

    def test_historic_service_preserves_otthonsos_plusz(self):
        self.assertEqual(
            complete_charge_metadata("service", "OtthonSOS Plusz", None),
            ("OtthonSOS Plusz", "hó"),
        )

    def test_calculates_invoice_gross_from_net_and_vat_amount(self):
        self.assertEqual(
            complete_invoice_gross(Decimal("33849"), Decimal("8659"), None),
            Decimal("42508.00"),
        )

    def test_invoice_rounding_is_already_in_provider_gross(self):
        self.assertEqual(
            complete_invoice_payable(Decimal("42508"), Decimal("-1"), None),
            Decimal("42508.00"),
        )

    def test_settlement_offsets_fill_provider_descriptions_without_unit(self):
        self.assertEqual(
            complete_charge_metadata("settled_energy_offset", "", "MJ"),
            ("Részszámlákban elszámolt energiadíj", None),
        )
        self.assertEqual(
            complete_charge_metadata("settled_base_fee_offset", "", "hó"),
            ("Részszámlákban elszámolt alapdíj", None),
        )

    def test_settlement_offset_keeps_negative_amounts(self):
        self.assertEqual(
            complete_charge_amounts(
                "settled_energy_offset", None, None, Decimal("-367415"), None, None,
            ),
            (Decimal("-367415"), Decimal("27"), Decimal("-466617")),
        )

    def test_calculates_charge_net_and_gross_as_whole_forints(self):
        self.assertEqual(
            complete_charge_amounts(
                "discounted_energy", Decimal("4359"), Decimal("2.256"),
                None, None, None,
            ),
            (Decimal("9834"), Decimal("27"), Decimal("12489")),
        )

    def test_service_defaults_to_zero_vat(self):
        self.assertEqual(
            complete_charge_amounts(
                "service", Decimal("1"), Decimal("790"), None, None, None,
            ),
            (Decimal("790"), Decimal("0"), Decimal("790")),
        )

    def test_explicit_amounts_are_stored_as_whole_forints(self):
        self.assertEqual(
            complete_charge_amounts(
                "other", None, None, Decimal("100.49"), Decimal("27"), Decimal("999.99"),
            ),
            (Decimal("100"), Decimal("27"), Decimal("127")),
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

    def test_energy_script_guards_empty_location_hash(self):
        template = (ROOT / "app" / "templates" / "energy.html").read_text(encoding="utf-8")
        self.assertIn(
            "window.location.hash ? document.querySelector(window.location.hash) : null",
            template,
        )
        self.assertIn("settled_energy_offset", template)
        self.assertIn("create_energy_invoice_settled_installment", template)


if __name__ == "__main__":
    unittest.main()
