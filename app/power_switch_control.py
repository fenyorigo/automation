from __future__ import annotations

import json
import os
import secrets
import threading
import urllib.request
from dataclasses import dataclass
from typing import Any

import paho.mqtt.client as mqtt


@dataclass(frozen=True)
class PowerSwitchResult:
    status: str
    preflight_power: bool | None
    verified_power: bool | None
    error_code: str | None = None
    error_message: str | None = None


def _tasmota_power(hostname: str, timeout: float) -> bool:
    url = f"http://{hostname}/cm?cmnd=Status%2011"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.load(response)
    value = str((payload.get("StatusSTS") or {}).get("POWER", "")).upper()
    if value not in {"ON", "OFF"}:
        raise ValueError("A Tasmota válaszából hiányzik a reléállapot.")
    return value == "ON"


def control_tasmota_power(
    hostname: str, requested_power: bool, timeout: float = 5.0
) -> PowerSwitchResult:
    try:
        before = _tasmota_power(hostname, timeout)
        if before == requested_power:
            return PowerSwitchResult("verified", before, before)
        command = "On" if requested_power else "Off"
        url = f"http://{hostname}/cm?cmnd=Power%20{command}"
        with urllib.request.urlopen(url, timeout=timeout) as response:
            json.load(response)
        after = _tasmota_power(hostname, timeout)
        if after != requested_power:
            return PowerSwitchResult(
                "failed", before, after, "verification_failed",
                "A Tasmota visszaolvasott reléállapota nem egyezik a kéréssel.",
            )
        return PowerSwitchResult("verified", before, after)
    except Exception as error:
        return PowerSwitchResult(
            "failed", locals().get("before"), None, type(error).__name__, str(error)
        )


def control_zigbee_power(
    friendly_name: str, requested_power: bool, timeout: float = 8.0
) -> PowerSwitchResult:
    base_topic = os.getenv("ZIGBEE2MQTT_BASE_TOPIC", "zigbee2mqtt").rstrip("/")
    state_topic = f"{base_topic}/{friendly_name}"
    set_topic = f"{state_topic}/set"
    connected = threading.Event()
    command_sent = threading.Event()
    verified = threading.Event()
    observed: dict[str, bool | None] = {"power": None}
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"automation-power-switch-{secrets.token_hex(4)}",
        protocol=mqtt.MQTTv311,
    )
    username = os.getenv("MQTT_USERNAME")
    if username:
        client.username_pw_set(username, os.getenv("MQTT_PASSWORD"))

    def on_connect(
        mqtt_client: mqtt.Client, _userdata: Any, _flags: Any,
        reason_code: Any, _properties: Any,
    ) -> None:
        if reason_code.is_failure:
            return
        mqtt_client.subscribe(state_topic, qos=1)
        connected.set()

    def on_message(
        _client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage
    ) -> None:
        if message.retain or not command_sent.is_set():
            return
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        value = str(payload.get("state", "")).upper()
        if value not in {"ON", "OFF"}:
            return
        observed["power"] = value == "ON"
        if observed["power"] == requested_power:
            verified.set()

    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(
            os.getenv("MQTT_HOST", "127.0.0.1"),
            int(os.getenv("MQTT_PORT", "1883")),
            keepalive=30,
        )
        client.loop_start()
        if not connected.wait(timeout):
            return PowerSwitchResult(
                "failed", None, None, "mqtt_connect_timeout",
                "Nem jött létre időben az MQTT-kapcsolat.",
            )
        command_sent.set()
        info = client.publish(
            set_topic,
            json.dumps({"state": "ON" if requested_power else "OFF"}),
            qos=1,
        )
        info.wait_for_publish(timeout=timeout)
        if not verified.wait(timeout):
            return PowerSwitchResult(
                "unverified", None, observed["power"], "verification_timeout",
                "A parancs elküldve, de nem érkezett vissza igazoló állapot.",
            )
        return PowerSwitchResult("verified", None, observed["power"])
    except Exception as error:
        return PowerSwitchResult(
            "failed", None, observed["power"], type(error).__name__, str(error)
        )
    finally:
        try:
            client.disconnect()
        finally:
            client.loop_stop()
