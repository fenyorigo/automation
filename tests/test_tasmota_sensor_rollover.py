from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.database import Database


class RecordingCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, statement: str, parameters: tuple[object, ...]) -> None:
        self.calls.append((statement, parameters))

    def fetchone(self) -> tuple[int]:
        return (321,)


class TasmotaSensorRolloverTest(unittest.TestCase):
    def test_old_same_type_channel_is_inactivated_after_device_id_change(self) -> None:
        cursor = RecordingCursor()
        config = SimpleNamespace(source_system="tasmota", device_id="nous-bojler")

        sensor_id = Database._upsert_sensor(
            cursor,
            119649,
            config,
            {
                "sensor_id": "tasmota:nous-bojler:power",
                "sensor_type": "power",
                "unit": "watt",
            },
        )

        self.assertEqual(sensor_id, 321)
        self.assertIn("sensor_type = ?", cursor.calls[0][0])
        self.assertEqual(
            cursor.calls[0][1],
            (119649, "tasmota", "power", "tasmota:nous-bojler:power"),
        )


if __name__ == "__main__":
    unittest.main()
