import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from import_electricity_invoices import CYCLES, INVOICES, validate_dataset  # noqa: E402


class ElectricityInvoiceImportTests(unittest.TestCase):
    def test_dataset_is_complete_and_consistent(self):
        validate_dataset()
        self.assertEqual(20, len(INVOICES))
        self.assertEqual(20, len({item["number"] for item in INVOICES}))
        self.assertEqual(21, sum(len(item["consumption"]) for item in INVOICES))
        self.assertEqual(16, sum(len(item["settled_installments"]) for item in INVOICES))

    def test_known_pdf_duplicates_are_present_only_once(self):
        numbers = [item["number"] for item in INVOICES]
        self.assertEqual(1, numbers.count("14510917691"))
        self.assertEqual(1, numbers.count("11512318276"))

    def test_controlled_meter_is_only_a_charge(self):
        descriptions = [
            charge["description"]
            for invoice in INVOICES
            for charge in invoice["charges"]
        ]
        self.assertIn("Használaton kívüli vezérelt mérő alapdíja", descriptions)
        self.assertTrue(all(item["quantity"] > 0 for invoice in INVOICES for item in invoice["consumption"]))

    def test_three_expected_cycles_are_declared(self):
        self.assertEqual(
            ["2024-12-17", "2025-12-21", "2026-06-01"],
            [cycle[0] for cycle in CYCLES],
        )
        self.assertEqual(["settled", "settled", "open"], [cycle[2] for cycle in CYCLES])


if __name__ == "__main__":
    unittest.main()
