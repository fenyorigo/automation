from __future__ import annotations

import json
import os
import secrets
import threading
from dataclasses import dataclass
from typing import Any

import paho.mqtt.client as mqtt


@dataclass(frozen=True)
class TrvControlResult:
    status: str
    verified_state: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


def _same_value(actual: Any, expected: Any) -> bool:
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return abs(float(actual) - float(expected)) < 0.01
        except (TypeError, ValueError):
            return False
    return str(actual).strip().casefold() == str(expected).strip().casefold()


def control_trv_settings(
    friendly_name: str,
    requested: dict[str, Any],
    timeout: float = 10.0,
) -> TrvControlResult:
    """Publish writable TRV properties and verify a fresh device state message."""
    if not requested:
        return TrvControlResult(
            "failed", error_code="empty_request",
            error_message="Nincs elküldhető TRV-beállítás.",
        )

    base_topic = os.getenv("ZIGBEE2MQTT_BASE_TOPIC", "zigbee2mqtt").rstrip("/")
    state_topic = f"{base_topic}/{friendly_name}"
    connected = threading.Event()
    command_sent = threading.Event()
    verified = threading.Event()
    latest: dict[str, Any] = {}
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"automation-trv-control-{secrets.token_hex(4)}",
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
        if not isinstance(payload, dict):
            return
        latest.update(payload)
        if all(
            key in latest and _same_value(latest[key], value)
            for key, value in requested.items()
        ):
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
            return TrvControlResult(
                "failed", error_code="mqtt_connect_timeout",
                error_message="Nem jött létre időben az MQTT-kapcsolat.",
            )
        command_sent.set()
        info = client.publish(
            f"{state_topic}/set",
            json.dumps(requested, ensure_ascii=False),
            qos=1,
        )
        info.wait_for_publish(timeout=timeout)
        if not verified.wait(timeout):
            return TrvControlResult(
                "unverified", verified_state=dict(latest) or None,
                error_code="verification_timeout",
                error_message=(
                    "A parancs elküldve, de a TRV nem igazolta vissza időben. "
                    "Elemes eszköznél rövid gombnyomás után érdemes újrapróbálni."
                ),
            )
        return TrvControlResult("verified", verified_state=dict(latest))
    except Exception as error:
        return TrvControlResult(
            "failed", verified_state=dict(latest) or None,
            error_code=type(error).__name__, error_message=str(error),
        )
    finally:
        try:
            client.disconnect()
        finally:
            client.loop_stop()
