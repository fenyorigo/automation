#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import signal
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import mariadb
import paho.mqtt.client as mqtt
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SYSTEM = "shelly_mqtt"
MODEL = "Shelly H&T Gen3"
PREFIX_PATTERN = re.compile(r"^shellyhtg3-([0-9a-fA-F]{12})$")
LEGACY_DEVICE_NAMES = {
    "shellyhtg3-48f6eebb92d4": "shelly-dolgozo",
}
SUBSCRIPTIONS = (
    "+/status/temperature:0",
    "+/status/humidity:0",
    "+/status/devicepower:0",
    "+/online",
)


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def numeric_value(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field} must be finite")
    return Decimal(str(value))


def retained_event_id(topic: str, payload_bytes: bytes, sensor_type: str) -> str:
    digest = hashlib.sha256(topic.encode() + b"\0" + payload_bytes).hexdigest()
    return f"{SOURCE_SYSTEM}:retained:{sensor_type}:{digest}"


def live_event_id(prefix: str, sensor_type: str, observed_at: datetime) -> str:
    timestamp = observed_at.strftime("%Y%m%dT%H%M%S%f")
    return f"{SOURCE_SYSTEM}:{prefix}:{sensor_type}:{timestamp}"


class ShellyRepository:
    def __init__(self) -> None:
        self.connection = mariadb.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.getenv("DB_NAME", "home_automation"),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            autocommit=False,
        )

    def close(self) -> None:
        self.connection.close()

    def store_measurements(
        self,
        prefix: str,
        topic: str,
        payload: dict[str, Any],
        measurements: list[tuple[str, str, Decimal]],
        retained: bool,
        payload_bytes: bytes,
    ) -> int:
        cursor = self.connection.cursor()
        observed_at = utc_now_naive()
        try:
            device_id, room_id = self._upsert_device(cursor, prefix)
            inserted = 0
            for sensor_type, unit, value in measurements:
                sensor_id = self._upsert_sensor(
                    cursor, device_id, room_id, prefix, sensor_type, unit
                )
                event_id = (
                    retained_event_id(topic, payload_bytes, sensor_type)
                    if retained
                    else live_event_id(prefix, sensor_type, observed_at)
                )
                cursor.execute(
                    """INSERT IGNORE INTO sensor_readings
                       (sensor_id,observed_at,value,quality,error_code,source_system,
                        source_event_id,raw_payload)
                       VALUES (?,?,?,'good',NULL,?,?,?)""",
                    (
                        sensor_id, observed_at, value, SOURCE_SYSTEM, event_id,
                        json_value({"topic": topic, "payload": payload}),
                    ),
                )
                inserted += max(cursor.rowcount, 0)
            self.connection.commit()
            return inserted
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def register_online(self, prefix: str) -> None:
        cursor = self.connection.cursor()
        try:
            self._upsert_device(cursor, prefix)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def _upsert_device(self, cursor: mariadb.Cursor, prefix: str) -> tuple[int, int | None]:
        match = PREFIX_PATTERN.fullmatch(prefix)
        if match is None:
            raise ValueError("invalid Shelly H&T Gen3 prefix")
        hardware_id = match.group(1).casefold()

        cursor.execute(
            """INSERT INTO manufacturers (code,name) VALUES ('shelly','Shelly')
               ON DUPLICATE KEY UPDATE name=VALUES(name),is_active=1"""
        )
        cursor.execute("SELECT id FROM manufacturers WHERE code='shelly'")
        manufacturer_id = int(cursor.fetchone()[0])
        cursor.execute("SELECT id FROM device_types WHERE code='temperature_sensor'")
        device_type_id = int(cursor.fetchone()[0])

        cursor.execute(
            """SELECT id,room_id FROM devices
               WHERE source_system=? AND source_device_id=? FOR UPDATE""",
            (SOURCE_SYSTEM, prefix),
        )
        existing = cursor.fetchone()
        if existing is None:
            cursor.execute(
                """INSERT INTO devices
                   (room_id,zone_id,source_system,source_device_id,source_puid,name,
                    device_type,device_type_id,manufacturer_id,access_mode,
                    capability_mode,integration_role,model,ip_assignment,
                    polling_enabled,control_enabled,poll_interval_seconds,is_active)
                   VALUES (NULL,NULL,?,?,?,?, 'temperature_sensor',?,?,'network',
                           'read_only','direct',?,'dhcp',1,0,10800,1)""",
                (
                    SOURCE_SYSTEM, prefix, hardware_id, prefix,
                    device_type_id, manufacturer_id, MODEL,
                ),
            )
            device_id = int(cursor.lastrowid)
            room_id = None
        else:
            device_id, room_id = int(existing[0]), existing[1]
            cursor.execute(
                """UPDATE devices SET source_puid=?,device_type='temperature_sensor',
                   device_type_id=?,manufacturer_id=?,model=?,access_mode='network',
                   capability_mode='read_only',integration_role='direct',
                   polling_enabled=1,control_enabled=0,is_active=1 WHERE id=?""",
                (hardware_id, device_type_id, manufacturer_id, MODEL, device_id),
            )

        legacy_name = LEGACY_DEVICE_NAMES.get(prefix.casefold())
        if legacy_name:
            cursor.execute(
                """SELECT id,name,room_id,zone_id FROM devices
                   WHERE source_system='manual' AND name=? AND is_active=1 FOR UPDATE""",
                (legacy_name,),
            )
            legacy = cursor.fetchone()
            if legacy is not None:
                legacy_id, display_name, legacy_room_id, legacy_zone_id = legacy
                cursor.execute(
                    """UPDATE devices SET name=?,room_id=?,zone_id=? WHERE id=?""",
                    (display_name, legacy_room_id, legacy_zone_id, device_id),
                )
                cursor.execute(
                    "UPDATE sensors SET room_id=? WHERE device_id=?",
                    (legacy_room_id, device_id),
                )
                if legacy_room_id is not None:
                    cursor.execute(
                        """UPDATE device_room_history SET valid_to=UTC_TIMESTAMP(3)
                           WHERE device_id=? AND valid_to IS NULL""",
                        (device_id,),
                    )
                    cursor.execute(
                        """INSERT INTO device_room_history
                           (device_id,room_id,change_reason) VALUES (?,?,?)""",
                        (
                            device_id, legacy_room_id,
                            f"MQTT párosítás: {legacy_name} fizikai utódja",
                        ),
                    )
                cursor.execute("UPDATE devices SET is_active=0 WHERE id=?", (legacy_id,))
                cursor.execute("UPDATE sensors SET is_active=0 WHERE device_id=?", (legacy_id,))
                room_id = legacy_room_id
        return device_id, room_id

    @staticmethod
    def _upsert_sensor(
        cursor: mariadb.Cursor,
        device_id: int,
        room_id: int | None,
        prefix: str,
        sensor_type: str,
        unit: str,
    ) -> int:
        source_sensor_id = f"{prefix}:{sensor_type}"
        cursor.execute(
            """INSERT INTO sensors
               (room_id,device_id,source_system,source_sensor_id,name,
                sensor_type,unit,is_active)
               VALUES (?,?,?,?,?,?,?,1)
               ON DUPLICATE KEY UPDATE room_id=VALUES(room_id),device_id=VALUES(device_id),
                name=VALUES(name),sensor_type=VALUES(sensor_type),unit=VALUES(unit),
                is_active=1""",
            (
                room_id, device_id, SOURCE_SYSTEM, source_sensor_id,
                f"{prefix} {sensor_type}", sensor_type, unit,
            ),
        )
        cursor.execute(
            "SELECT id FROM sensors WHERE source_system=? AND source_sensor_id=?",
            (SOURCE_SYSTEM, source_sensor_id),
        )
        return int(cursor.fetchone()[0])


class ShellyMessageHandler:
    def __init__(self, repository: ShellyRepository) -> None:
        self.repository = repository

    def handle(self, topic: str, payload_bytes: bytes, retained: bool = False) -> str:
        levels = topic.split("/")
        if len(levels) not in {2, 3} or PREFIX_PATTERN.fullmatch(levels[0]) is None:
            return "ignored"
        prefix = levels[0].casefold()
        if len(levels) == 2 and levels[1] == "online":
            self.repository.register_online(prefix)
            return "online_ignored"
        if len(levels) != 3 or levels[1] != "status":
            return "ignored"
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("invalid JSON payload") from error
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")

        component = levels[2]
        if component == "temperature:0":
            measurements = [("temperature", "celsius", numeric_value(payload.get("tC"), "tC"))]
        elif component == "humidity:0":
            measurements = [("humidity", "percent", numeric_value(payload.get("rh"), "rh"))]
        elif component == "devicepower:0":
            battery = payload.get("battery")
            if not isinstance(battery, dict):
                raise ValueError("battery must be an object")
            measurements = [
                ("battery", "percent", numeric_value(battery.get("percent"), "battery.percent")),
                ("battery_voltage", "volt", numeric_value(battery.get("V"), "battery.V")),
            ]
        else:
            return "ignored"
        inserted = self.repository.store_measurements(
            prefix, topic, payload, measurements, retained, payload_bytes
        )
        return f"stored:{inserted}"


def main() -> int:
    load_dotenv(ROOT / ".env")
    repository = ShellyRepository()
    handler = ShellyMessageHandler(repository)
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=os.getenv("SHELLY_MQTT_CLIENT_ID", "automation-shelly-mqtt"),
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
            print(f"MQTT connection failed: {reason_code}", flush=True)
            return
        for subscription in SUBSCRIPTIONS:
            mqtt_client.subscribe(subscription, qos=1)
        print(f"MQTT connected; subscribed to {', '.join(SUBSCRIPTIONS)}", flush=True)

    def on_message(_client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
        try:
            result = handler.handle(message.topic, message.payload, message.retain)
            if result != "ignored":
                print(f"{message.topic}: {result}", flush=True)
        except Exception as error:
            print(
                f"MQTT message error on {message.topic}: {type(error).__name__}: {error}",
                file=sys.stderr, flush=True,
            )

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(
        os.getenv("MQTT_HOST", "127.0.0.1"),
        int(os.getenv("MQTT_PORT", "1883")),
        keepalive=60,
    )
    stop_requested = False

    def stop(_signum: int, _frame: Any) -> None:
        nonlocal stop_requested
        stop_requested = True
        client.disconnect()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        client.loop_forever(retry_first_connection=True)
    finally:
        repository.close()
    return 0 if stop_requested else 1


if __name__ == "__main__":
    raise SystemExit(main())
