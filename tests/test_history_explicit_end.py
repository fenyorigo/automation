from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HistoryExplicitEndTests(unittest.TestCase):
    def test_history_window_supports_explicit_end(self) -> None:
        source = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn('if window_mode == "end":', source)
        self.assertIn("if ended_at <= started_at:", source)
        self.assertIn("range_key, history_start, history_end, window_mode", source)
        self.assertIn("range_key, local_start, local_end, window_mode", source)

    def test_history_form_exposes_mutually_exclusive_modes(self) -> None:
        template = (ROOT / "app" / "templates" / "history.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('name="window_mode"', template)
        self.assertIn('name="end"', template)
        self.assertIn("range.disabled = explicitEnd", template)
        self.assertIn("end.disabled = !explicitEnd", template)
        self.assertIn("window_mode=window_mode", template)


if __name__ == "__main__":
    unittest.main()
