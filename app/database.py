from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Any

import mariadb

from poll_devices import DeviceConfig, PollResult


DEVICE_METADATA = {
    "esp32": ("sensor_gateway", "WEMOS D1 Mini ESP32"),
    "computherm": ("thermostat", "Computherm E400RF-EM"),
    "connectlife": ("climate", "Hisense ConnectLife"),
}


def json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=json_default)


def maria_timestamp(iso_timestamp: str) -> str:
    return iso_timestamp.removesuffix("Z").replace("T", " ")


class Database:
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

    def persist(self, config: DeviceConfig, result: PollResult, duration_ms: int) -> None:
        cursor = self.connection.cursor()
        try:
            device_id = self._upsert_device(cursor, config, result)
            if result.success:
                for measurement in result.measurements:
                    sensor_id = self._upsert_sensor(cursor, device_id, config, measurement)
                    self._insert_measurement(cursor, sensor_id, result, measurement)
                if result.state is not None:
                    self._insert_state(cursor, device_id, result)
            self._insert_attempt(cursor, device_id, result, duration_ms)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def _source_puid(config: DeviceConfig, result: PollResult) -> str | None:
        if config.source_system == "connectlife":
            return config.auid
        return result.identity.get("mac_address") or config.mac_address

    def _upsert_device(self, cursor: mariadb.Cursor, config: DeviceConfig, result: PollResult) -> int:
        device_type, model = DEVICE_METADATA[config.source_system]
        cursor.execute(
            """
            INSERT INTO devices (
              source_system, source_device_id, source_puid, hostname, expected_ip,
              mac_address, name, device_type, model, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON DUPLICATE KEY UPDATE
              source_puid = VALUES(source_puid), hostname = VALUES(hostname),
              expected_ip = VALUES(expected_ip), mac_address = VALUES(mac_address),
              name = VALUES(name), device_type = VALUES(device_type),
              model = VALUES(model), is_active = 1
            """,
            (
                config.source_system,
                config.device_id,
                self._source_puid(config, result),
                config.hostname,
                config.expected_ip,
                config.mac_address,
                config.connectlife_name or config.device_id,
                device_type,
                model,
            ),
        )
        cursor.execute(
            "SELECT id FROM devices WHERE source_system = ? AND source_device_id = ?",
            (config.source_system, config.device_id),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"Device upsert failed for {config.device_id}")
        return int(row[0])

    @staticmethod
    def _upsert_sensor(
        cursor: mariadb.Cursor,
        device_id: int,
        config: DeviceConfig,
        measurement: dict[str, Any],
    ) -> int:
        sensor_id = str(measurement["sensor_id"])
        cursor.execute(
            """
            INSERT INTO sensors (
              room_id, device_id, source_system, source_sensor_id, name,
              sensor_type, unit, is_active
            ) VALUES (NULL, ?, ?, ?, ?, ?, ?, 1)
            ON DUPLICATE KEY UPDATE
              device_id = VALUES(device_id), name = VALUES(name),
              sensor_type = VALUES(sensor_type), unit = VALUES(unit), is_active = 1
            """,
            (
                device_id,
                config.source_system,
                sensor_id,
                f"{config.device_id} {measurement['sensor_type']}",
                measurement["sensor_type"],
                measurement.get("unit"),
            ),
        )
        cursor.execute(
            "SELECT id FROM sensors WHERE source_system = ? AND source_sensor_id = ?",
            (config.source_system, sensor_id),
        )
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"Sensor upsert failed for {sensor_id}")
        return int(row[0])

    @staticmethod
    def _insert_measurement(
        cursor: mariadb.Cursor,
        sensor_id: int,
        result: PollResult,
        measurement: dict[str, Any],
    ) -> None:
        timestamp_token = result.observed_at.replace("-", "").replace(":", "").replace(".", "")
        source_event_id = (
            f"{result.source_system}:{measurement['sensor_id']}:measurement:{timestamp_token}"
        )
        cursor.execute(
            """
            INSERT INTO sensor_readings (
              sensor_id, observed_at, value, quality, error_code,
              source_system, source_event_id, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sensor_id,
                maria_timestamp(result.observed_at),
                measurement.get("value"),
                measurement.get("quality", "invalid"),
                measurement.get("error_code"),
                result.source_system,
                source_event_id,
                json_value(measurement.get("raw", measurement)),
            ),
        )

    @staticmethod
    def _insert_state(cursor: mariadb.Cursor, device_id: int, result: PollResult) -> None:
        state = result.state or {}
        timestamp_token = result.observed_at.replace("-", "").replace(":", "").replace(".", "")
        cursor.execute(
            """
            INSERT INTO device_states (
              device_id, observed_at, power, mode, target_temperature_c,
              fan_speed, fan_mute, eco, sleep, super, swing_up_down,
              online, active, auto_mode, source_system, source_event_id, raw_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                maria_timestamp(result.observed_at),
                state.get("power"),
                state.get("mode"),
                state.get("target_temperature_c"),
                state.get("fan_speed"),
                state.get("fan_mute"),
                state.get("eco"),
                state.get("sleep"),
                state.get("super"),
                state.get("swing_up_down"),
                state.get("online"),
                state.get("active"),
                state.get("auto_mode"),
                result.source_system,
                f"{result.source_system}:{result.device_id}:state:{timestamp_token}",
                json_value(state.get("raw", state)),
            ),
        )

    @staticmethod
    def _insert_attempt(
        cursor: mariadb.Cursor,
        device_id: int,
        result: PollResult,
        duration_ms: int,
    ) -> None:
        completed = datetime.fromisoformat(result.observed_at.replace("Z", "+00:00"))
        attempted = completed - timedelta(milliseconds=max(duration_ms, 0))
        cursor.execute(
            """
            INSERT INTO poll_attempts (
              device_id, source_system, source_device_id, hostname,
              attempted_at, completed_at, duration_ms, success,
              error_code, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                result.source_system,
                result.device_id,
                result.hostname,
                attempted.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                completed.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                max(duration_ms, 0),
                result.success,
                result.error_code,
                result.error_message,
            ),
        )
