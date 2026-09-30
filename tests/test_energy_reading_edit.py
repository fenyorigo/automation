from datetime import datetime
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, "app")
os.environ.setdefault("DB_PASSWORD", "test")

from dashboard import (
    load_energy_invoice_context,
    load_energy_invoice_edit_context,
    load_energy_reading_edit_context,
)


class EnergyReadingEditTest(unittest.TestCase):
    @patch("dashboard.connect_database")
    def test_edit_context_selects_actual_meter_type_and_local_year(self, connect) -> None:
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value = cursor
        cursor.fetchone.return_value = (
            "gas",
            datetime(2025, 12, 31, 23, 30),
        )
        connect.return_value = connection

        self.assertEqual(load_energy_reading_edit_context(42), ("gas", 2026))
        cursor.execute.assert_called_once()
        cursor.close.assert_called_once()
        connection.close.assert_called_once()

    @patch("dashboard.connect_database")
    def test_missing_reading_returns_none(self, connect) -> None:
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value = cursor
        cursor.fetchone.return_value = None
        connect.return_value = connection

        self.assertIsNone(load_energy_reading_edit_context(999))


class EnergyInvoiceEditTest(unittest.TestCase):
    @patch("dashboard.connect_database")
    def test_invoice_context_selects_actual_energy_status_and_year(self, connect) -> None:
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value = cursor
        cursor.fetchone.return_value = ("electricity", "open", 2026)
        connect.return_value = connection

        self.assertEqual(load_energy_invoice_context(42), ("electricity", "open", 2026))
        cursor.close.assert_called_once()
        connection.close.assert_called_once()

    @patch("dashboard.load_energy_invoice_context")
    @patch("dashboard.connect_database")
    def test_charge_edit_resolves_its_parent_invoice(self, connect, invoice_context) -> None:
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value = cursor
        cursor.fetchone.return_value = (73,)
        connect.return_value = connection
        invoice_context.return_value = ("electricity", "open", 2026)

        self.assertEqual(
            load_energy_invoice_edit_context("edit_charge", 99),
            ("electricity", "open", 2026),
        )
        invoice_context.assert_called_once_with(73)
        self.assertIn("energy_invoice_charge_lines", cursor.execute.call_args.args[0])

    @patch("dashboard.load_energy_invoice_context")
    @patch("dashboard.connect_database")
    def test_charge_view_resolves_its_parent_invoice(self, connect, invoice_context) -> None:
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value = cursor
        cursor.fetchone.return_value = (73,)
        connect.return_value = connection
        invoice_context.return_value = ("electricity", "open", 2026)

        self.assertEqual(
            load_energy_invoice_edit_context("view_charge", 99),
            ("electricity", "open", 2026),
        )
        invoice_context.assert_called_once_with(73)
        self.assertIn("energy_invoice_charge_lines", cursor.execute.call_args.args[0])

    @patch("dashboard.connect_database")
    def test_invoice_without_cycle_uses_all_status_filter(self, connect) -> None:
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value = cursor
        cursor.fetchone.return_value = ("electricity", None, 2026)
        connect.return_value = connection

        self.assertEqual(load_energy_invoice_context(42), ("electricity", "all", 2026))


if __name__ == "__main__":
    unittest.main()
