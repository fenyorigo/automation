from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class Esp32HistoryViewTests(unittest.TestCase):
    def test_dashboard_links_to_historic_esp32_view_without_inline_switch(self) -> None:
        template = (ROOT / "app/templates/dashboard.html").read_text(encoding="utf-8")

        self.assertIn("url_for('esp32_history')", template)
        self.assertIn("ESP32 (historikus)", template)
        self.assertNotIn("ESP32 hőmérséklet típusa", template)

    def test_historic_view_has_raw_and_action_temperature_switch(self) -> None:
        template = (ROOT / "app/templates/esp32_history.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("Nyers mérés", template)
        self.assertIn("Cselekedeti", template)
        self.assertIn("Megőrzött utolsó értékek", template)
        self.assertIn("url_for('history')", template)


if __name__ == "__main__":
    unittest.main()
