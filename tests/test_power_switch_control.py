import io
import json
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from power_switch_control import control_tasmota_power, control_zigbee_power
from dashboard import (
    MANUAL_BOILER_STATE_SELECT_SQL,
    POWER_SWITCH_ALLOWLIST,
    annotate_boiler_operating_states,
    normalized_switch_power,
    reconcile_boiler_supply_state,
)


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
    def __init__(self, row=(42, 1, 1, 1)) -> None:
        self.row = row
        self.calls = []

    def execute(self, statement, parameters=None):
        if "SELECT id,manual_power_state" in statement:
            self.assert_valid_boiler_select(statement)
        self.calls.append((statement, parameters))

    @staticmethod
    def assert_valid_boiler_select(statement):
        if "FROM devices" not in statement:
            raise AssertionError("The boiler SELECT must include FROM devices")

    def fetchone(self):
        return self.row


class PowerSwitchControlTest(unittest.TestCase):
    def test_manual_boiler_state_query_selects_from_devices(self) -> None:
        self.assertIn("FROM devices", MANUAL_BOILER_STATE_SELECT_SQL)

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
        self.assertIn("'disabled' if device.switch_power is sameas true", template)
        self.assertIn("'disabled' if device.switch_power is sameas false", template)
        stylesheet = (ROOT / "app" / "static" / "dashboard.css").read_text()
        self.assertIn(".power-switch-control button:disabled", stylesheet)
        self.assertIn("background:#d9dddb !important", stylesheet)
        self.assertIn("klarstein-standby-warning", template)
        self.assertIn(".device-card.is-power-off", stylesheet)

    def test_power_switch_allowlist_is_limited_to_dedicated_supplies(self) -> None:
        self.assertEqual(len(POWER_SWITCH_ALLOWLIST), 3)
        self.assertIn(("tasmota", "nous-kazan"), POWER_SWITCH_ALLOWLIST)
        self.assertIn(("tasmota", "nous-bojler"), POWER_SWITCH_ALLOWLIST)
        self.assertIn(
            ("zigbee2mqtt", "0xa4c13811bed2ffff"), POWER_SWITCH_ALLOWLIST
        )
        self.assertNotIn(("tasmota", "nous-mainit"), POWER_SWITCH_ALLOWLIST)
        self.assertNotIn(
            ("zigbee2mqtt", "0xa4c13811554dffff"), POWER_SWITCH_ALLOWLIST
        )

    def test_tasmota_database_bits_are_normalized_to_real_booleans(self) -> None:
        self.assertIs(
            normalized_switch_power({"source_system": "tasmota", "power": 1}),
            True,
        )
        self.assertIs(
            normalized_switch_power({"source_system": "tasmota", "power": 0}),
            False,
        )
        self.assertIsNone(
            normalized_switch_power({"source_system": "tasmota", "power": None})
        )

    def test_verified_boiler_supply_cut_marks_manual_boiler_off(self) -> None:
        cursor = _BoilerCursor()

        changed = reconcile_boiler_supply_state(
            cursor,
            source_system="tasmota",
            source_device_id="nous-kazan",
            verified_power=False,
        )

        self.assertTrue(changed)
        self.assertEqual(cursor.calls[1][1], (0, 42))
        self.assertEqual(cursor.calls[2][1], (42, 1, 0))
        self.assertEqual(cursor.calls[3][1], (42,))
        self.assertEqual(cursor.calls[4][1], (42, 1, 1))

    def test_supply_restore_marks_mains_only(self) -> None:
        cursor = _BoilerCursor((42, 0, 0, 0))

        changed = reconcile_boiler_supply_state(
            cursor,
            source_system="tasmota",
            source_device_id="nous-kazan",
            verified_power=True,
        )

        self.assertTrue(changed)
        self.assertEqual(cursor.calls[1][1], (1, 42))
        self.assertEqual(len(cursor.calls), 3)

    def test_boiler_card_uses_three_single_checkboxes(self) -> None:
        template = (ROOT / "app" / "templates" / "_device_card.html").read_text()
        self.assertIn('type="checkbox" name="manual_power_state"', template)
        self.assertIn('type="checkbox" name="manual_hot_water_state"', template)
        self.assertIn('type="checkbox" name="manual_heating_state"', template)

    def test_boiler_operating_states_use_nous_supply(self) -> None:
        boiler = {
            "source_system": "manual", "device_type": "boiler",
            "manual_power_state": False, "manual_hot_water_state": True,
            "manual_heating_state": True,
        }
        supply = {
            "source_system": "tasmota", "source_device_id": "nous-kazan",
            "online": True, "switch_power": True, "temperature_c": 5,
            "measurement_at": datetime.now(UTC).replace(tzinfo=None),
            "state_at": datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1),
            "poll_interval_seconds": 120,
        }

        annotate_boiler_operating_states([boiler, supply])

        self.assertTrue(boiler["boiler_supply_power"])
        self.assertEqual(boiler["boiler_supply_source"], "Nous")
        self.assertTrue(boiler["boiler_hot_water_enabled"])
        self.assertTrue(boiler["boiler_heating_enabled"])
        self.assertTrue(boiler["boiler_panel_power_on"])
        self.assertFalse(boiler["boiler_panel_power_alert"])

    def test_powered_nous_with_fresh_zero_watts_alerts_for_panel_off(self) -> None:
        observed_at = datetime.now(UTC).replace(tzinfo=None)
        boiler = {
            "source_system": "manual", "device_type": "boiler",
            "manual_power_state": True, "manual_hot_water_state": True,
            "manual_heating_state": True,
        }
        supply = {
            "source_system": "tasmota", "source_device_id": "nous-kazan",
            "online": True, "switch_power": True, "temperature_c": 0,
            "measurement_at": observed_at, "state_at": observed_at,
            "poll_interval_seconds": 120,
        }

        annotate_boiler_operating_states([boiler, supply])

        self.assertEqual(boiler["boiler_panel_power_state"], "off")
        self.assertTrue(boiler["boiler_panel_power_alert"])
        self.assertFalse(boiler["boiler_hot_water_enabled"])
        self.assertFalse(boiler["boiler_heating_enabled"])

    def test_pre_switch_measurement_waits_instead_of_false_alert(self) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        boiler = {
            "source_system": "manual", "device_type": "boiler",
            "manual_power_state": True, "manual_hot_water_state": False,
            "manual_heating_state": False,
        }
        supply = {
            "source_system": "tasmota", "source_device_id": "nous-kazan",
            "online": True, "switch_power": True, "temperature_c": 0,
            "measurement_at": now - timedelta(seconds=10), "state_at": now,
            "poll_interval_seconds": 120,
        }

        annotate_boiler_operating_states([boiler, supply])

        self.assertEqual(boiler["boiler_panel_power_state"], "pending")
        self.assertFalse(boiler["boiler_panel_power_alert"])


if __name__ == "__main__":
    unittest.main()
