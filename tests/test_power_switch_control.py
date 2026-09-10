import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from power_switch_control import control_tasmota_power, control_zigbee_power
from dashboard import POWER_SWITCH_ALLOWLIST, reconcile_boiler_after_supply_cut


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class _PublishInfo:
    def wait_for_publish(self, timeout=None):
        return True


class _ReasonCode:
    is_failure = False


class _MqttMessage:
    def __init__(self, payload: bytes, retained: bool = False) -> None:
        self.payload = payload
        self.retain = retained


class _FakeMqttClient:
    def __init__(self, *args, retained=False, **kwargs) -> None:
        self.on_connect = None
        self.on_message = None
        self.retained = retained
        self.published = None

    def username_pw_set(self, *_args):
        pass

    def connect(self, *_args, **_kwargs):
        self.on_connect(self, None, None, _ReasonCode(), None)

    def loop_start(self):
        pass

    def loop_stop(self):
        pass

    def subscribe(self, *_args, **_kwargs):
        return (0, 1)

    def publish(self, topic, payload, qos):
        self.published = (topic, payload, qos)
        requested = json.loads(payload)["state"]
        self.on_message(
            self, None,
            _MqttMessage(json.dumps({"state": requested}).encode(), self.retained),
        )
        return _PublishInfo()

    def disconnect(self):
        pass


class _BoilerCursor:
    def __init__(self, row=(42, 1)) -> None:
        self.row = row
        self.calls = []

    def execute(self, statement, parameters=None):
        self.calls.append((statement, parameters))

    def fetchone(self):
        return self.row


class PowerSwitchControlTest(unittest.TestCase):
    @patch("power_switch_control.urllib.request.urlopen")
    def test_tasmota_switch_is_verified_by_fresh_status_read(self, urlopen) -> None:
        urlopen.side_effect = [
            _Response(json.dumps({"StatusSTS": {"POWER": "ON"}}).encode()),
            _Response(json.dumps({"POWER": "OFF"}).encode()),
            _Response(json.dumps({"StatusSTS": {"POWER": "OFF"}}).encode()),
        ]

        result = control_tasmota_power("plug.home", False)

        self.assertEqual(result.status, "verified")
        self.assertTrue(result.preflight_power)
        self.assertFalse(result.verified_power)
        self.assertIn("Power%20Off", urlopen.call_args_list[1].args[0])

    @patch("power_switch_control.urllib.request.urlopen")
    def test_tasmota_does_not_send_command_when_already_in_requested_state(
        self, urlopen
    ) -> None:
        urlopen.return_value = _Response(
            json.dumps({"StatusSTS": {"POWER": "ON"}}).encode()
        )

        result = control_tasmota_power("plug.home", True)

        self.assertEqual(result.status, "verified")
        self.assertEqual(urlopen.call_count, 1)

    @patch("power_switch_control.urllib.request.urlopen", side_effect=OSError("down"))
    def test_tasmota_transport_failure_is_reported(self, _urlopen) -> None:
        result = control_tasmota_power("plug.home", False)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.error_code, "OSError")

    @patch("power_switch_control.mqtt.Client")
    def test_zigbee_switch_waits_for_live_matching_state(self, client_class) -> None:
        client = _FakeMqttClient()
        client_class.return_value = client

        result = control_zigbee_power("Smart Plug emelet", False, timeout=0.01)

        self.assertEqual(result.status, "verified")
        self.assertFalse(result.verified_power)
        self.assertEqual(
            client.published,
            ('zigbee2mqtt/Smart Plug emelet/set', '{"state": "OFF"}', 1),
        )

    @patch("power_switch_control.mqtt.Client")
    def test_zigbee_retained_state_does_not_verify_command(self, client_class) -> None:
        client_class.return_value = _FakeMqttClient(retained=True)

        result = control_zigbee_power("Smart Plug emelet", True, timeout=0.01)

        self.assertEqual(result.status, "unverified")
        self.assertIsNone(result.verified_power)

    def test_ui_contains_server_side_off_confirmation(self) -> None:
        template = (ROOT / "app" / "templates" / "_device_card.html").read_text()
        self.assertIn("power-off-confirmation", template)
        self.assertIn('name="confirmation_token"', template)
        self.assertIn("Igen, kikapcsolom", template)

    def test_power_switch_allowlist_is_limited_to_boiler_supply(self) -> None:
        self.assertEqual(len(POWER_SWITCH_ALLOWLIST), 1)
        self.assertIn(("tasmota", "nous-kazan"), POWER_SWITCH_ALLOWLIST)
        self.assertNotIn(("tasmota", "nous-mainit"), POWER_SWITCH_ALLOWLIST)

    def test_verified_boiler_supply_cut_marks_manual_boiler_off(self) -> None:
        cursor = _BoilerCursor()

        changed = reconcile_boiler_after_supply_cut(
            cursor,
            source_system="tasmota",
            source_device_id="nous-kazan",
            verified_power=False,
        )

        self.assertTrue(changed)
        self.assertEqual(cursor.calls[1][1], (42,))
        self.assertEqual(cursor.calls[2][1], (42,))

    def test_supply_restore_does_not_claim_boiler_panel_is_on(self) -> None:
        cursor = _BoilerCursor()

        changed = reconcile_boiler_after_supply_cut(
            cursor,
            source_system="tasmota",
            source_device_id="nous-kazan",
            verified_power=True,
        )

        self.assertFalse(changed)
        self.assertEqual(cursor.calls, [])


if __name__ == "__main__":
    unittest.main()
