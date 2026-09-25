from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ElectricHeaterCardTest(unittest.TestCase):
    def test_external_meter_note_uses_compact_type_size(self) -> None:
        template = (ROOT / "app/templates/_device_card.html").read_text(
            encoding="utf-8"
        )
        stylesheet = (ROOT / "app/static/dashboard.css").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'class="external-meter-note">Külső fogyasztásmérővel',
            template,
        )
        self.assertIn(
            ".manual-state .external-meter-note { font-size:.7rem;",
            stylesheet,
        )


if __name__ == "__main__":
    unittest.main()
