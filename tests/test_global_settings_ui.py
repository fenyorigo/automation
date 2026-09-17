from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GlobalSettingsUiTest(unittest.TestCase):
    def test_service_mode_labels_are_highlighted_in_red(self) -> None:
        template = (ROOT / "app/templates/global_settings.html").read_text(
            encoding="utf-8"
        )
        stylesheet = (ROOT / "app/static/dashboard.css").read_text(
            encoding="utf-8"
        )
        self.assertIn("CLIMATE_SERVICE_MODE", template)
        self.assertIn("BOILER_SERVICE_MODE", template)
        self.assertIn("service-mode-setting", template)
        self.assertIn(".service-mode-setting > .setting-label", stylesheet)
        self.assertIn("color:#b42318", stylesheet)


if __name__ == "__main__":
    unittest.main()
