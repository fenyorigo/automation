from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import global_settings


class ReloadEnvironmentTest(unittest.TestCase):
    def test_reload_updates_values_and_reports_restart_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "POLL_TIMEOUT_SECONDS=17\nAPP_TIMEZONE=UTC\n", encoding="utf-8"
            )
            with patch.object(global_settings, "ENV_PATH", env_path), patch.dict(
                os.environ,
                {"POLL_TIMEOUT_SECONDS": "5", "APP_TIMEZONE": "Europe/Budapest"},
                clear=False,
            ):
                changed, restart_required = global_settings.reload_environment()
                self.assertEqual(os.environ["POLL_TIMEOUT_SECONDS"], "17")
                self.assertEqual(os.environ["APP_TIMEZONE"], "UTC")
                self.assertEqual(changed, ("APP_TIMEZONE", "POLL_TIMEOUT_SECONDS"))
                self.assertEqual(restart_required, ("APP_TIMEZONE",))

    def test_reload_rejects_key_without_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text("POLL_TIMEOUT_SECONDS\n", encoding="utf-8")
            with patch.object(global_settings, "ENV_PATH", env_path):
                with self.assertRaisesRegex(ValueError, "Érték nélküli"):
                    global_settings.reload_environment()


if __name__ == "__main__":
    unittest.main()
