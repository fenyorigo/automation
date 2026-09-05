from datetime import datetime
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, "app")
os.environ.setdefault("DB_PASSWORD", "test")

from dashboard import load_energy_reading_edit_context


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


if __name__ == "__main__":
    unittest.main()
