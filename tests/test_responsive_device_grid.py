from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ResponsiveDeviceGridTest(unittest.TestCase):
    def test_dashboard_uses_wide_responsive_device_grid(self) -> None:
        template = (ROOT / "app/templates/dashboard.html").read_text(
            encoding="utf-8"
        )
        stylesheet = (ROOT / "app/static/dashboard.css").read_text(
            encoding="utf-8"
        )

        self.assertIn('class="dashboard-page ', template)
        self.assertIn(".dashboard-page { --content-max-width: 1840px; }", stylesheet)
        self.assertIn(
            "repeat(auto-fill, minmax(min(100%, 300px), 1fr))",
            stylesheet,
        )
        self.assertIn("container-type:inline-size", stylesheet)
        self.assertIn("font-size: clamp(2.4rem, 15cqi, 4.6rem)", stylesheet)
        self.assertNotIn("repeat(3, minmax(0, 1fr))", stylesheet)


if __name__ == "__main__":
    unittest.main()
