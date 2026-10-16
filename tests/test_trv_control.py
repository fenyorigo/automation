#!/usr/bin/env python3

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from trv_control import control_trv_settings
from dashboard import trv_setting_value_matches


class FakeReasonCode:
    is_failure = False


class FakeMessage:
    retain = False

    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")


class TrvControlTest(unittest.TestCase):
    def test_pending_value_comparison_handles_numeric_and_text_values(self) -> None:
        self.assertTrue(trv_setting_value_matches("LOCK", "lock"))
        self.assertTrue(trv_setting_value_matches(100, 100.0))
        self.assertFalse(trv_setting_value_matches("UNLOCK", "LOCK"))

    @patch("trv_control.mqtt.Client")
    def test_verifies_requested_properties(self, client_class: MagicMock) -> None:
        client = client_class.return_value

        def connect(*_args, **_kwargs):
            client.on_connect(client, None, None, FakeReasonCode(), None)

        requested = {
            "smart_temperature_control": "OFF",
            "child_lock": "LOCK",
            "heating_valve_position": 100,
            "idle_valve_position": 100,
        }

        def publish(_topic, payload, qos):
            self.assertEqual(json.loads(payload), requested)
            client.on_message(client, None, FakeMessage(requested))
            info = MagicMock()
            info.wait_for_publish.return_value = None
            return info

        client.connect.side_effect = connect
        client.publish.side_effect = publish
        result = control_trv_settings("TRV-G2 Rita", requested, timeout=0.05)
        self.assertEqual(result.status, "verified")
        self.assertEqual(result.verified_state["child_lock"], "LOCK")

    @patch("trv_control.mqtt.Client")
    def test_ignores_retained_state_and_reports_unverified(
        self, client_class: MagicMock
    ) -> None:
        client = client_class.return_value

        def connect(*_args, **_kwargs):
            client.on_connect(client, None, None, FakeReasonCode(), None)

        def publish(_topic, _payload, qos):
            message = FakeMessage({"smart_temperature_control": "OFF"})
            message.retain = True
            client.on_message(client, None, message)
            info = MagicMock()
            info.wait_for_publish.return_value = None
            return info

        client.connect.side_effect = connect
        client.publish.side_effect = publish
        result = control_trv_settings(
            "TRV-G2 Rita", {"smart_temperature_control": "OFF"}, timeout=0.01
        )
        self.assertEqual(result.status, "unverified")
        self.assertIsNone(result.verified_state)


if __name__ == "__main__":
    unittest.main()
