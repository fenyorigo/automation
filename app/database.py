from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any

import mariadb

from poll_devices import DeviceConfig, PollResult
from temperature_derivation import derive_temperature


DEVICE_METADATA = {
    "esp32": ("sensor_gateway", "WEMOS D1 Mini ESP32"),
    "computherm": ("thermostat", "Computherm E400RF-EM"),
    "connectlife": ("climate", "Hisense ConnectLife"),
    "tasmota": ("power_meter", "NOUS A1T / Tasmota"),
    "linux_system": ("server", "Linux system"),
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

    def polling_configs(
        self, configs: list[DeviceConfig], *, due_only: bool
    ) -> list[DeviceConfig]:
        """Return configured integrations enabled in the registry and, optionally, due now."""
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                """
                SELECT d.source_system,d.source_device_id,d.polling_enabled,
                       d.poll_interval_seconds,MAX(pa.completed_at) AS last_poll,
                       (MAX(pa.completed_at) IS NULL OR
                        TIMESTAMPADD(SECOND,d.poll_interval_seconds,MAX(pa.completed_at))
                          <= UTC_TIMESTAMP(3)) AS is_due,
                       d.hostname,d.expected_ip,d.mac_address
                FROM devices d
                LEFT JOIN poll_attempts pa ON pa.device_id=d.id
                GROUP BY d.id,d.source_system,d.source_device_id,d.polling_enabled,
                         d.poll_interval_seconds,d.hostname,d.expected_ip,d.mac_address
                """
            )
            registry = {
                (str(row[0]), str(row[1])): {
                    "enabled": bool(row[2]), "interval": int(row[3]), "last": row[4],
                    "due": bool(row[5]), "hostname": row[6], "expected_ip": row[7],
                    "mac_address": row[8]
                }
                for row in cursor.fetchall()
            }
            selected = []
            for config in configs:
                entry = registry.get((config.source_system, config.device_id))
                if entry is None:  # A config-file-only device is admitted for its first upsert.
                    selected.append(config)
                elif entry["enabled"] and (
                    not due_only or entry["due"]
                ):
                    selected.append(replace(
                        config,
                        hostname=entry["hostname"] or config.hostname,
                        expected_ip=entry["expected_ip"] or "",
                        mac_address=entry["mac_address"] or "",
                    ))
            return selected
        finally:
            cursor.close()

    def persist(
        self,
        config: DeviceConfig,
        result: PollResult,
        duration_ms: int,
        *,
        poll_origin: str = "automatic",
    ) -> None:
        if poll_origin not in {"automatic", "manual"}:
            raise ValueError(f"Unsupported poll origin: {poll_origin}")
        cursor = self.connection.cursor()
        try:
            device_id = self._upsert_device(cursor, config, result)
            if result.success:
                for measurement in result.measurements:
                    sensor_id = self._upsert_sensor(cursor, device_id, config, measurement)
                    raw_reading_id = self._insert_measurement(
                        cursor, sensor_id, result, measurement
                    )
                    self._insert_derived_temperature(
                        cursor, sensor_id, raw_reading_id, result, measurement
                    )
                if result.state is not None:
                    self._insert_state(cursor, device_id, config, result)
            self._insert_attempt(cursor, device_id, result, duration_ms, poll_origin)
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
              source_puid = COALESCE(VALUES(source_puid),source_puid),
              hostname = COALESCE(hostname,VALUES(hostname)),
              expected_ip = COALESCE(expected_ip,VALUES(expected_ip)),
              mac_address = COALESCE(mac_address,VALUES(mac_address))
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
        if config.source_system == "esp32":
            cursor.execute(
                """UPDATE sensors
                   SET is_active = 0
                   WHERE device_id = ? AND source_system = ?
                     AND source_sensor_id <> ? AND is_active = 1""",
                (device_id, config.source_system, sensor_id),
            )
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
    ) -> int:
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
        return int(cursor.lastrowid)

    @staticmethod
    def _insert_derived_temperature(
        cursor: mariadb.Cursor,
        sensor_id: int,
        raw_reading_id: int,
        result: PollResult,
        measurement: dict[str, Any],
    ) -> None:
        if (
            result.source_system != "esp32"
            or measurement.get("sensor_type") != "temperature"
            or measurement.get("value") is None
            or measurement.get("quality", "invalid") != "good"
        ):
            return
        observed_at = datetime.fromisoformat(result.observed_at.replace("Z", "+00:00")).replace(
            tzinfo=None
        )
        cursor.execute(
            """
            SELECT id,calibration_offset_c,filter_tau_seconds,
                   action_interval_seconds,calculation_version
            FROM sensor_calibrations
            WHERE sensor_id=? AND physical_configuration='copper_tube_box'
              AND decision_enabled=1 AND valid_from<=?
              AND (valid_until IS NULL OR valid_until>?)
            ORDER BY valid_from DESC,id DESC LIMIT 1
            """,
            (sensor_id, observed_at, observed_at),
        )
        calibration = cursor.fetchone()
        if calibration is None:
            return
        calibration_id, offset_c, tau_seconds, interval_seconds, version = calibration
        cursor.execute(
            """
            SELECT filtered_temperature_c,observed_at,source_from,sample_count
            FROM derived_temperature_readings
            WHERE sensor_id=? AND calibration_id=?
            ORDER BY observed_at DESC,id DESC LIMIT 1
            """,
            (sensor_id, calibration_id),
        )
        previous = cursor.fetchone()
        cursor.execute(
            """
            SELECT observed_at FROM derived_temperature_readings
            WHERE sensor_id=? AND calibration_id=? AND is_action_point=1
            ORDER BY observed_at DESC,id DESC LIMIT 1
            """,
            (sensor_id, calibration_id),
        )
        action_row = cursor.fetchone()
        derived = derive_temperature(
            raw_value=float(measurement["value"]),
            offset_c=float(offset_c),
            observed_at=observed_at,
            tau_seconds=int(tau_seconds),
            action_interval_seconds=int(interval_seconds),
            previous_filtered=float(previous[0]) if previous else None,
            previous_observed_at=previous[1] if previous else None,
            last_action_at=action_row[0] if action_row else None,
            source_from=previous[2] if previous else None,
            sample_count=int(previous[3]) if previous else 0,
        )
        cursor.execute(
            """
            INSERT INTO derived_temperature_readings
              (sensor_id,raw_reading_id,calibration_id,observed_at,
               calibrated_temperature_c,filtered_temperature_c,
               action_temperature_c,is_action_point,source_from,source_to,
               sample_count,calculation_version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                sensor_id, raw_reading_id, calibration_id, observed_at,
                derived.calibrated, derived.filtered, derived.action,
                derived.is_action_point, derived.source_from, observed_at,
                derived.sample_count, version,
            ),
        )
        derived_id = int(cursor.lastrowid)
        cursor.execute(
            """
            INSERT INTO derived_temperature_sources
              (derived_reading_id,source_sensor_id,source_reading_id,
               source_role,source_weight,accepted)
            VALUES (?,?,?,'primary',1,1)
            """,
            (derived_id, sensor_id, raw_reading_id),
        )

    @staticmethod
    def _insert_state(
        cursor: mariadb.Cursor, device_id: int, config: DeviceConfig, result: PollResult
    ) -> None:
        state = result.state or {}
        previous_power = None
        if config.source_system == "connectlife":
            cursor.execute(
                """SELECT power FROM device_states WHERE device_id=? AND power IS NOT NULL
                   ORDER BY observed_at DESC,id DESC LIMIT 1""",
                (device_id,),
            )
            previous = cursor.fetchone()
            previous_power = bool(previous[0]) if previous is not None else None
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
        current_power = state.get("power")
        if (
            config.source_system == "connectlife"
            and previous_power is not None
            and current_power is not None
            and previous_power != bool(current_power)
        ):
            Database._record_detected_climate_transition(
                cursor, device_id, bool(current_power), result, state
            )

    @staticmethod
    def _record_detected_climate_transition(
        cursor: mariadb.Cursor,
        device_id: int,
        current_power: bool,
        result: PollResult,
        state: dict[str, Any],
    ) -> None:
        observed_at = maria_timestamp(result.observed_at)
        cursor.execute("SELECT room_id FROM devices WHERE id=?", (device_id,))
        row = cursor.fetchone()
        if row is None or row[0] is None:
            return
        if current_power:
            cursor.execute(
                "SELECT 1 FROM climate_operation_events WHERE device_id=? AND ended_at IS NULL",
                (device_id,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """INSERT INTO climate_operation_events
                       (device_id,room_id,started_at,open_device_id,
                        started_target_temperature_c,note,event_origin,created_by)
                       VALUES (?,?,?,?,?,?,'state_detection',NULL)""",
                    (device_id, int(row[0]), observed_at, device_id,
                     state.get("target_temperature_c"),
                     "Periodikus lekérdezéssel észlelt bekapcsolás"),
                )
        else:
            cursor.execute(
                """UPDATE climate_operation_events
                   SET ended_at=?,open_device_id=NULL,ended_target_temperature_c=?
                   WHERE device_id=? AND ended_at IS NULL""",
                (observed_at, state.get("target_temperature_c"), device_id),
            )

    @staticmethod
    def _insert_attempt(
        cursor: mariadb.Cursor,
        device_id: int,
        result: PollResult,
        duration_ms: int,
        poll_origin: str,
    ) -> None:
        completed = datetime.fromisoformat(result.observed_at.replace("Z", "+00:00"))
        attempted = completed - timedelta(milliseconds=max(duration_ms, 0))
        cursor.execute(
            """
            INSERT INTO poll_attempts (
              device_id, source_system, source_device_id, hostname, poll_origin,
              attempted_at, completed_at, duration_ms, success,
              error_code, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                device_id,
                result.source_system,
                result.device_id,
                result.hostname,
                poll_origin,
                attempted.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                completed.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                max(duration_ms, 0),
                result.success,
                result.error_code,
                result.error_message,
            ),
        )
