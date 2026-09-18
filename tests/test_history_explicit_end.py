import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class HistoryExplicitEndTests(unittest.TestCase):
    def test_date_only_boundaries_default_to_midnight(self) -> None:
        source = (ROOT / "app" / "dashboard.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        functions = [
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in {"combine_history_boundary", "split_history_boundary"}
        ]
        namespace: dict[str, object] = {}
        exec(compile(ast.Module(body=functions, type_ignores=[]), "dashboard.py", "exec"), namespace)
        combine = namespace["combine_history_boundary"]
        split = namespace["split_history_boundary"]
        self.assertEqual(combine("2026-08-01"), "2026-08-01T00:00")
        self.assertEqual(combine("2026-08-01", "13:45"), "2026-08-01T13:45")
        self.assertEqual(split("2026-08-01T13:45"), ("2026-08-01", "13:45"))

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
        self.assertIn('type="date" name="start"', template)
        self.assertIn('type="time" name="end_time"', template)
        self.assertIn("range.disabled = explicitEnd", template)
        self.assertIn("end.disabled = !explicitEnd", template)
        self.assertIn("window_mode=window_mode", template)


if __name__ == "__main__":
    unittest.main()
