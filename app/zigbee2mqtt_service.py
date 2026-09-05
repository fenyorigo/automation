#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import signal
import sys
import threading
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import mariadb
import paho.mqtt.client as mqtt
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SYSTEM = "zigbee2mqtt"
DEFAULT_BASE_TOPIC = "zigbee2mqtt"
OUTDOOR_SENSOR_MODELS = {"SNZB-02WD"}
TIME_SERIES_PROPERTIES = {"temperature", "humidity", "battery"}
EVENT_SERIES_PROPERTIES = {"contact"}
STORED_SENSOR_PROPERTIES = TIME_SERIES_PROPERTIES | EVENT_SERIES_PROPERTIES

UNIT_NAMES = {
    "%": "percent",
    "A": "ampere",
    "V": "volt",
    "W": "watt",
    "kWh": "kilowatt_hour",
    "°C": "celsius",
    "C": "celsius",
    "lqi": "lqi",
    "mV": "millivolt",
    "seconds": "seconds",
}

SENSOR_TYPE_NAMES = {
    "battery": "battery",
    "battery_low": "battery_low",
    "contact": "contact",
    "current": "current",
    "energy": "energy_total",
    "energy_month": "energy_month",
    "energy_today": "energy_today",
    "energy_yesterday": "energy_yesterday",
    "humidity": "humidity",
    "linkquality": "linkquality",
    "occupancy": "occupancy",
    "power": "power",
    "state": "state",
    "tamper": "tamper",
    "temperature": "temperature",
    "voltage": "voltage",
}


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def json_value(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def parse_last_seen(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            divisor = 1000 if value > 10_000_000_000 else 1
            return datetime.fromtimestamp(float(value) / divisor, UTC).replace(tzinfo=None)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).replace(tzinfo=None)
    except (OverflowError, TypeError, ValueError):
        return None


def registry_code(value: str) -> str:
    code = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return code[:50] or "other"


def is_outdoor_temperature_sensor(model_id: Any) -> bool:
    return str(model_id or "").upper() in OUTDOOR_SENSOR_MODELS


def iter_exposes(exposes: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    """Yield published primitive properties from a Zigbee2MQTT exposes tree."""
    for expose in exposes:
        features = expose.get("features")
        if isinstance(features, list):
            yield from iter_exposes(item for item in features if isinstance(item, dict))
        access = expose.get("access")
        if (
            not isinstance(access, int)
            or access & 1 == 0
            or expose.get("category") == "config"
            or expose.get("type") not in {"numeric", "binary"}
            or not expose.get("property")
        ):
            continue
        yield expose


def sensor_descriptors(device: dict[str, Any]) -> list[dict[str, str | None]]:
    definition = device.get("definition") or {}
    found: dict[str, dict[str, str | None]] = {}
    for expose in iter_exposes(definition.get("exposes") or []):
        property_name = str(expose["property"])
        if property_name not in SENSOR_TYPE_NAMES:
            continue
        found[property_name] = {
            "property": property_name,
            "label": str(expose.get("label") or expose.get("name") or property_name),
            "sensor_type": SENSOR_TYPE_NAMES[property_name],
            "unit": UNIT_NAMES.get(str(expose.get("unit")), str(expose.get("unit")))
            if expose.get("unit") is not None
            else ("boolean" if expose.get("type") == "binary" else None),
        }
    return list(found.values())


def inferred_device_type(device: dict[str, Any], sensors: list[dict[str, str | None]]) -> str:
    properties = {str(item["property"]) for item in sensors}
    if {"power", "energy", "current"} & properties:
        return "power_meter"
    if "contact" in properties:
        return "contact_sensor"
    if "temperature" in properties:
        return "temperature_sensor"
    if str(device.get("type", "")).casefold() == "router":
        return "zigbee_router"
    return "other"


def scalar_values(value: Any) -> tuple[Decimal | None, str | None]:
    if isinstance(value, bool):
        return Decimal(int(value)), "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return Decimal(str(value)), str(value)
        except InvalidOperation:
            return None, str(value)
    if isinstance(value, str):
        return None, value[:255]
    return None, None


def time_series_event_id(
    ieee_address: str, property_name: str, observed_at: datetime
) -> str:
    timestamp = observed_at.strftime("%Y%m%dT%H%M%S%f")
    return f"{SOURCE_SYSTEM}:{ieee_address}:{property_name}:{timestamp}"


def contact_state_changed(previous: Decimal | None, current: Decimal | None) -> bool:
    """Return true only for an initial or genuine boolean contact-state observation."""
    return current in {Decimal(0), Decimal(1)} and previous != current


def ventilation_long_threshold_seconds() -> int:
    return int(os.getenv("VENTILATION_LONG_THRESHOLD_MINUTES", "5")) * 60


def ventilation_close_delay_seconds() -> int:
    return int(os.getenv("VENTILATION_CONTACT_CLOSE_DELAY_SECONDS", "30"))


class ZigbeeRepository:
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

    def sync_devices(self, devices: list[dict[str, Any]]) -> int:
        cursor = self.connection.cursor()
        count = 0
        try:
            for device in devices:
                if device.get("type") == "Coordinator" or not device.get("ieee_address"):
                    continue
                self._sync_device(cursor, device)
                count += 1
            self.connection.commit()
            return count
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def _sync_device(self, cursor: mariadb.Cursor, device: dict[str, Any]) -> int:
        ieee = str(device["ieee_address"]).casefold()
        friendly_name = str(device.get("friendly_name") or ieee)
        manufacturer = str(
            device.get("manufacturer") or (device.get("definition") or {}).get("vendor") or "Other"
        )
        manufacturer_code = registry_code(manufacturer)
        sensors = sensor_descriptors(device)
        device_type = inferred_device_type(device, sensors)
        model = device.get("model_id") or (device.get("definition") or {}).get("model")

        cursor.execute(
            "INSERT INTO manufacturers (code,name) VALUES (?,?) "
            "ON DUPLICATE KEY UPDATE name=VALUES(name),is_active=1",
            (manufacturer_code, manufacturer[:100]),
        )
        cursor.execute("SELECT id FROM manufacturers WHERE code=?", (manufacturer_code,))
        manufacturer_id = int(cursor.fetchone()[0])
        cursor.execute("SELECT id FROM device_types WHERE code=?", (device_type,))
        type_row = cursor.fetchone()
        if type_row is None:
            cursor.execute(
                "INSERT INTO device_types (code,name) VALUES (?,?)",
                (device_type, device_type.replace("_", " ").title()),
            )
            device_type_id = int(cursor.lastrowid)
        else:
            device_type_id = int(type_row[0])

        cursor.execute(
            "SELECT id,name FROM devices WHERE source_system=? AND source_puid=? FOR UPDATE",
            (SOURCE_SYSTEM, ieee),
        )
        existing = cursor.fetchone()
        if existing is None:
            cursor.execute(
                """INSERT INTO devices
                   (room_id,zone_id,source_system,source_device_id,source_puid,name,
                    device_type,model,device_type_id,manufacturer_id,access_mode,
                    capability_mode,integration_role,ip_assignment,polling_enabled,
                    control_enabled,poll_interval_seconds,is_active)
                   VALUES (NULL,NULL,?,?,?,?,?,?,?,?,?,'read_only','direct',
                           'not_applicable',1,0,600,1)""",
                (
                    SOURCE_SYSTEM, ieee, ieee, friendly_name, device_type, model,
                    device_type_id, manufacturer_id, "network",
                ),
            )
            device_id = int(cursor.lastrowid)
        else:
            device_id = int(existing[0])
            cursor.execute(
                "SELECT friendly_name FROM zigbee2mqtt_devices WHERE device_id=?",
                (device_id,),
            )
            previous = cursor.fetchone()
            update_display_name = previous is not None and existing[1] == previous[0]
            cursor.execute(
                """UPDATE devices SET source_device_id=?,model=?,device_type=?,
                   device_type_id=?,manufacturer_id=?,is_active=1,
                   name=IF(?, ?, name) WHERE id=?""",
                (
                    ieee, model, device_type, device_type_id, manufacturer_id,
                    update_display_name, friendly_name, device_id,
                ),
            )

        cursor.execute(
            """INSERT INTO zigbee2mqtt_devices
               (device_id,ieee_address,friendly_name,model_id,manufacturer,power_source,
                zigbee_type,supported,interview_completed,definition_json,
                last_discovered_at,removed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,UTC_TIMESTAMP(3),NULL)
               ON DUPLICATE KEY UPDATE friendly_name=VALUES(friendly_name),
                model_id=VALUES(model_id),manufacturer=VALUES(manufacturer),
                power_source=VALUES(power_source),zigbee_type=VALUES(zigbee_type),
                supported=VALUES(supported),interview_completed=VALUES(interview_completed),
                definition_json=VALUES(definition_json),
                last_discovered_at=UTC_TIMESTAMP(3),removed_at=NULL""",
            (
                device_id, ieee, friendly_name, model, manufacturer,
                device.get("power_source"), device.get("type"), bool(device.get("supported")),
                bool(device.get("interview_completed")), json_value(device.get("definition")),
            ),
        )

        cursor.execute(
            "UPDATE sensors SET is_active=0 WHERE device_id=? AND source_system=?",
            (device_id, SOURCE_SYSTEM),
        )
        if is_outdoor_temperature_sensor(model):
            cursor.execute(
                """SELECT numeric_value,source_observed_at,received_at,raw_payload
                   FROM zigbee2mqtt_property_cache
                   WHERE device_id=? AND property_name='temperature'""",
                (device_id,),
            )
            cached_temperature = cursor.fetchone()
            if cached_temperature is not None and cached_temperature[0] is not None:
                observed_at = cached_temperature[1] or cached_temperature[2]
                cached_raw = cached_temperature[3]
                self._cache_outdoor_temperature(
                    cursor, device_id, ieee, friendly_name,
                    {"temperature": cached_temperature[0]}, observed_at,
                    cached_temperature[2],
                    cached_raw if isinstance(cached_raw, str) else json_value(cached_raw),
                )
        cursor.execute("SELECT room_id FROM devices WHERE id=?", (device_id,))
        room_id = cursor.fetchone()[0]
        for sensor in sensors:
            source_sensor_id = f"{ieee}:{sensor['property']}"
            cursor.execute(
                """INSERT INTO sensors
                   (room_id,device_id,source_system,source_sensor_id,name,sensor_type,unit,is_active)
                   VALUES (?,?,?,?,?,?,?,1)
                   ON DUPLICATE KEY UPDATE device_id=VALUES(device_id),
                    room_id=VALUES(room_id),name=VALUES(name),sensor_type=VALUES(sensor_type),
                    unit=VALUES(unit),is_active=1""",
                (
                    room_id, device_id, SOURCE_SYSTEM, source_sensor_id,
                    f"{friendly_name} {sensor['label']}", sensor["sensor_type"], sensor["unit"],
                ),
            )
        self._bootstrap_time_series(cursor, device_id, ieee)
        return device_id

    def _bootstrap_time_series(
        self, cursor: mariadb.Cursor, device_id: int, ieee_address: str
    ) -> None:
        placeholders = ",".join("?" for _ in STORED_SENSOR_PROPERTIES)
        cursor.execute(
            f"""SELECT property_name,numeric_value,source_observed_at,received_at,
                       raw_payload
                  FROM zigbee2mqtt_property_cache
                 WHERE device_id=? AND property_name IN ({placeholders})""",
            (device_id, *sorted(STORED_SENSOR_PROPERTIES)),
        )
        for property_name, value, source_at, received_at, raw_payload in cursor.fetchall():
            if value is None:
                continue
            raw = raw_payload if isinstance(raw_payload, str) else json_value(raw_payload)
            self._insert_sensor_reading(
                cursor, device_id, ieee_address, str(property_name), Decimal(str(value)),
                source_at or received_at, raw,
            )

    @staticmethod
    def _insert_sensor_reading(
        cursor: mariadb.Cursor,
        device_id: int,
        ieee_address: str,
        property_name: str,
        value: Decimal,
        observed_at: datetime,
        raw_payload: str,
    ) -> None:
        if property_name not in STORED_SENSOR_PROPERTIES:
            return
        cursor.execute(
            """SELECT id FROM sensors
               WHERE device_id=? AND source_system=? AND source_sensor_id=?
                 AND is_active=1""",
            (device_id, SOURCE_SYSTEM, f"{ieee_address}:{property_name}"),
        )
        sensor = cursor.fetchone()
        if sensor is None:
            return
        cursor.execute(
            """INSERT IGNORE INTO sensor_readings
               (sensor_id,observed_at,value,quality,error_code,source_system,
                source_event_id,raw_payload)
               VALUES (?,?,?,'good',NULL,?,?,?)""",
            (
                int(sensor[0]), observed_at, value, SOURCE_SYSTEM,
                time_series_event_id(ieee_address, property_name, observed_at),
                raw_payload,
            ),
        )

    @staticmethod
    def _selected_outdoor_temperature(
        cursor: mariadb.Cursor,
    ) -> tuple[int | None, Decimal | None]:
        cursor.execute(
            """SELECT s.id,o.temperature_c
               FROM outdoor_temperature_sources s
               JOIN outdoor_temperature_observations o ON o.id=(
                 SELECT o2.id FROM outdoor_temperature_observations o2
                 WHERE o2.source_id=s.id
                 ORDER BY o2.observed_at DESC,o2.id DESC LIMIT 1
               )
               WHERE s.is_active=1
                 AND o.observed_at >= UTC_TIMESTAMP(3) - INTERVAL s.max_age_minutes MINUTE
               ORDER BY s.priority LIMIT 1"""
        )
        row = cursor.fetchone()
        return (int(row[0]), Decimal(str(row[1]))) if row else (None, None)

    @staticmethod
    def _room_has_open_contact(
        cursor: mariadb.Cursor, room_id: int, excluded_device_id: int | None = None
    ) -> bool:
        sql = """SELECT 1
                   FROM devices d
                   JOIN zigbee2mqtt_devices z ON z.device_id=d.id
                   JOIN zigbee2mqtt_property_cache c
                     ON c.device_id=d.id AND c.property_name='contact'
                  WHERE d.room_id=? AND d.is_active=1
                    AND d.device_type='contact_sensor' AND c.numeric_value=0"""
        params: list[Any] = [room_id]
        if excluded_device_id is not None:
            sql += " AND d.id<>?"
            params.append(excluded_device_id)
        sql += " LIMIT 1"
        cursor.execute(sql, tuple(params))
        return cursor.fetchone() is not None

    def _apply_contact_transition(
        self,
        cursor: mariadb.Cursor,
        device_id: int,
        contact_value: Decimal,
        observed_at: datetime,
    ) -> None:
        cursor.execute("SELECT room_id FROM devices WHERE id=? AND is_active=1", (device_id,))
        device = cursor.fetchone()
        if device is None or device[0] is None:
            return
        room_id = int(device[0])
        cursor.execute(
            """SELECT id,event_origin,started_by_device_id
               FROM ventilation_events WHERE open_room_id=? FOR UPDATE""",
            (room_id,),
        )
        event = cursor.fetchone()
        if contact_value == 0:
            if event is not None:
                if event[1] == "zigbee_contact":
                    cursor.execute(
                        """UPDATE ventilation_events
                           SET pending_end_at=NULL,ended_by_device_id=NULL WHERE id=?""",
                        (int(event[0]),),
                    )
                elif event[2] is None:
                    cursor.execute(
                        """UPDATE ventilation_events
                           SET started_by_device_id=? WHERE id=?""",
                        (device_id, int(event[0])),
                    )
                return
            source_id, temperature = self._selected_outdoor_temperature(cursor)
            cursor.execute(
                """INSERT INTO ventilation_events
                   (room_id,started_at,ended_at,open_room_id,
                    started_outdoor_temperature_c,started_outdoor_source_id,
                    note,created_by,event_origin,started_by_device_id,
                    long_threshold_seconds,pending_end_at)
                   VALUES (?,?,NULL,?,?,?,NULL,NULL,'zigbee_contact',?,?,NULL)""",
                (
                    room_id, observed_at, room_id, temperature, source_id,
                    device_id, ventilation_long_threshold_seconds(),
                ),
            )
            return
        if event is None or (event[1] != "zigbee_contact" and event[2] is None):
            return
        if self._room_has_open_contact(cursor, room_id, excluded_device_id=device_id):
            return
        cursor.execute(
            """UPDATE ventilation_events
               SET pending_end_at=?,ended_by_device_id=? WHERE id=?""",
            (observed_at, device_id, int(event[0])),
        )

    def bootstrap_contact_ventilations(self) -> int:
        """Create missing room events from persisted open contact states at startup."""
        cursor = self.connection.cursor()
        created = 0
        try:
            cursor.execute(
                """SELECT d.id,d.room_id,
                          COALESCE(c.source_observed_at,c.received_at) AS observed_at
                   FROM devices d
                   JOIN zigbee2mqtt_devices z ON z.device_id=d.id
                   JOIN zigbee2mqtt_property_cache c
                     ON c.device_id=d.id AND c.property_name='contact'
                   WHERE d.is_active=1 AND d.device_type='contact_sensor'
                     AND d.room_id IS NOT NULL AND c.numeric_value=0
                   ORDER BY observed_at,d.id"""
            )
            seen_rooms: set[int] = set()
            for device_id, room_id, observed_at in cursor.fetchall():
                room_id = int(room_id)
                if room_id in seen_rooms:
                    continue
                seen_rooms.add(room_id)
                cursor.execute(
                    """SELECT id,started_by_device_id FROM ventilation_events
                       WHERE open_room_id=? FOR UPDATE""",
                    (room_id,),
                )
                existing_event = cursor.fetchone()
                if existing_event is not None:
                    if existing_event[1] is None:
                        cursor.execute(
                            """UPDATE ventilation_events SET started_by_device_id=?
                               WHERE id=?""",
                            (int(device_id), int(existing_event[0])),
                        )
                    continue
                cursor.execute(
                    "SELECT MAX(ended_at) FROM ventilation_events WHERE room_id=?",
                    (room_id,),
                )
                last_end = cursor.fetchone()[0]
                started_at = observed_at or utc_now_naive()
                if last_end is not None and last_end > started_at:
                    started_at = last_end
                self._apply_contact_transition(
                    cursor, int(device_id), Decimal(0), started_at
                )
                created += 1
            self.connection.commit()
            return created
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def reconcile_pending_ventilations(self) -> int:
        """Finish debounced automatic events once all room contacts remain closed."""
        cursor = self.connection.cursor()
        closed = 0
        try:
            cursor.execute(
                """UPDATE ventilation_events v
                   SET v.pending_end_at=UTC_TIMESTAMP(3)
                   WHERE v.ended_at IS NULL
                     AND (v.event_origin='zigbee_contact' OR v.started_by_device_id IS NOT NULL)
                     AND v.pending_end_at IS NULL
                     AND NOT EXISTS (
                       SELECT 1 FROM devices d
                       JOIN zigbee2mqtt_property_cache c
                         ON c.device_id=d.id AND c.property_name='contact'
                       WHERE d.room_id=v.room_id AND d.is_active=1
                         AND d.device_type='contact_sensor' AND c.numeric_value=0
                     )"""
            )
            cursor.execute(
                """SELECT id,room_id,started_at,pending_end_at
                   FROM ventilation_events
                   WHERE ended_at IS NULL
                     AND (event_origin='zigbee_contact' OR started_by_device_id IS NOT NULL)
                     AND pending_end_at IS NOT NULL
                     AND pending_end_at <= UTC_TIMESTAMP(3) - INTERVAL ? SECOND
                   FOR UPDATE""",
                (ventilation_close_delay_seconds(),),
            )
            for event_id, room_id, started_at, pending_end_at in cursor.fetchall():
                if self._room_has_open_contact(cursor, int(room_id)):
                    cursor.execute(
                        "UPDATE ventilation_events SET pending_end_at=NULL WHERE id=?",
                        (int(event_id),),
                    )
                    continue
                source_id, temperature = self._selected_outdoor_temperature(cursor)
                cursor.execute(
                    """UPDATE ventilation_events
                       SET ended_at=IF(? > started_at,?,DATE_ADD(started_at,INTERVAL 1 MICROSECOND)),
                           open_room_id=NULL,pending_end_at=NULL,
                           ended_outdoor_temperature_c=?,ended_outdoor_source_id=?
                       WHERE id=?""",
                    (
                        pending_end_at, pending_end_at, temperature, source_id,
                        int(event_id),
                    ),
                )
                closed += 1
            self.connection.commit()
            return closed
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def cache_state(
        self, friendly_name: str, topic: str, payload: dict[str, Any], retained: bool
    ) -> bool:
        cursor = self.connection.cursor()
        received_at = utc_now_naive()
        source_observed_at = parse_last_seen(payload.get("last_seen"))
        try:
            cursor.execute(
                """SELECT device_id,ieee_address,model_id
                   FROM zigbee2mqtt_devices WHERE friendly_name=?""",
                (friendly_name,),
            )
            row = cursor.fetchone()
            if row is None:
                self.connection.rollback()
                return False
            device_id = int(row[0])
            ieee_address = str(row[1])
            model_id = row[2]
            raw = json_value(payload)
            previous_contact: Decimal | None = None
            if "contact" in payload:
                cursor.execute(
                    """SELECT numeric_value FROM zigbee2mqtt_property_cache
                       WHERE device_id=? AND property_name='contact'""",
                    (device_id,),
                )
                previous_row = cursor.fetchone()
                if previous_row is not None and previous_row[0] is not None:
                    previous_contact = Decimal(str(previous_row[0]))
            for property_name, value in payload.items():
                numeric_value, text_value = scalar_values(value)
                cursor.execute(
                    """INSERT INTO zigbee2mqtt_property_cache
                       (device_id,property_name,value_json,numeric_value,text_value,
                        source_observed_at,received_at,mqtt_topic,retained,raw_payload)
                       VALUES (?,?,?,?,?,?,?,?,?,?)
                       ON DUPLICATE KEY UPDATE value_json=VALUES(value_json),
                        numeric_value=VALUES(numeric_value),text_value=VALUES(text_value),
                        source_observed_at=VALUES(source_observed_at),
                        received_at=VALUES(received_at),mqtt_topic=VALUES(mqtt_topic),
                        retained=VALUES(retained),raw_payload=VALUES(raw_payload)""",
                    (
                        device_id, property_name[:100], json_value(value), numeric_value,
                        text_value, source_observed_at, received_at, topic, retained, raw,
                    ),
                )
                if property_name in TIME_SERIES_PROPERTIES and numeric_value is not None:
                    self._insert_sensor_reading(
                        cursor, device_id, ieee_address, property_name, numeric_value,
                        source_observed_at or received_at, raw,
                    )
                if property_name == "contact" and contact_state_changed(
                    previous_contact, numeric_value
                ):
                    observed_at = source_observed_at or received_at
                    self._insert_sensor_reading(
                        cursor, device_id, ieee_address, property_name, numeric_value,
                        observed_at, raw,
                    )
                    self._apply_contact_transition(
                        cursor, device_id, numeric_value, observed_at
                    )
            cursor.execute(
                "UPDATE zigbee2mqtt_devices SET last_message_at=? WHERE device_id=?",
                (received_at, device_id),
            )
            if is_outdoor_temperature_sensor(model_id) and payload.get("temperature") is not None:
                self._cache_outdoor_temperature(
                    cursor, device_id, ieee_address, friendly_name, payload,
                    source_observed_at or received_at, received_at, raw,
                )
            self.connection.commit()
            return True
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def _cache_outdoor_temperature(
        cursor: mariadb.Cursor,
        device_id: int,
        ieee_address: str,
        friendly_name: str,
        payload: dict[str, Any],
        observed_at: datetime,
        received_at: datetime,
        raw_payload: str,
    ) -> None:
        source_code = f"zigbee_outdoor_{registry_code(ieee_address)}"[:64]
        cursor.execute(
            """INSERT INTO outdoor_temperature_sources
               (source_code,display_name,source_type,is_active,priority,max_age_minutes,
                configuration)
               VALUES (?,?,'zigbee2mqtt',1,1,120,
                       JSON_OBJECT('device_id',?,'ieee_address',?))
               ON DUPLICATE KEY UPDATE display_name=VALUES(display_name),
                is_active=1,priority=1,max_age_minutes=120,
                configuration=VALUES(configuration)""",
            (source_code, friendly_name[:120], device_id, ieee_address),
        )
        cursor.execute(
            "SELECT id FROM outdoor_temperature_sources WHERE source_code=?",
            (source_code,),
        )
        source_id = int(cursor.fetchone()[0])
        event_id = f"{source_code}:{observed_at.isoformat(timespec='milliseconds')}"
        cursor.execute(
            """INSERT IGNORE INTO outdoor_temperature_observations
               (source_id,observed_at,fetched_at,temperature_c,quality,
                source_event_id,raw_payload)
               VALUES (?,?,? ,?,'good',?,?)""",
            (
                source_id, observed_at, received_at, Decimal(str(payload["temperature"])),
                event_id, raw_payload,
            ),
        )

    def set_availability(self, friendly_name: str, availability: str) -> bool:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "UPDATE zigbee2mqtt_devices SET availability=? WHERE friendly_name=?",
                (availability[:20], friendly_name),
            )
            self.connection.commit()
            return cursor.rowcount > 0
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def mark_removed(self, ieee_address: str) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "SELECT device_id FROM zigbee2mqtt_devices WHERE ieee_address=?",
                (ieee_address.casefold(),),
            )
            row = cursor.fetchone()
            if row is not None:
                device_id = int(row[0])
                cursor.execute(
                    "UPDATE zigbee2mqtt_devices SET removed_at=UTC_TIMESTAMP(3) WHERE device_id=?",
                    (device_id,),
                )
                cursor.execute("UPDATE devices SET is_active=0 WHERE id=?", (device_id,))
                cursor.execute("UPDATE sensors SET is_active=0 WHERE device_id=?", (device_id,))
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()


class ZigbeeMessageHandler:
    def __init__(self, repository: ZigbeeRepository, base_topic: str = DEFAULT_BASE_TOPIC) -> None:
        self.repository = repository
        self.base_topic = base_topic.rstrip("/")

    def handle(self, topic: str, payload_bytes: bytes, retained: bool = False) -> str:
        decoded = payload_bytes.decode("utf-8")
        try:
            payload: Any = json.loads(decoded)
        except json.JSONDecodeError:
            payload = decoded
        if topic == f"{self.base_topic}/bridge/devices":
            if not isinstance(payload, list):
                raise ValueError("bridge/devices payload must be a list")
            return f"discovered:{self.repository.sync_devices(payload)}"
        if topic == f"{self.base_topic}/bridge/event":
            if isinstance(payload, dict) and payload.get("type") == "device_leave":
                data = payload.get("data") or {}
                ieee = data.get("ieee_address") or data.get("ieeeAddr")
                if ieee:
                    self.repository.mark_removed(str(ieee))
                    return "removed"
            return "ignored"
        prefix = f"{self.base_topic}/"
        if not topic.startswith(prefix) or topic.startswith(f"{self.base_topic}/bridge/"):
            return "ignored"
        relative = topic[len(prefix):]
        if relative.endswith("/availability"):
            friendly_name = relative.removesuffix("/availability")
            availability = payload.get("state") if isinstance(payload, dict) else payload
            self.repository.set_availability(friendly_name, str(availability))
            return "availability"
        if relative.endswith(("/get", "/set")) or not isinstance(payload, dict):
            return "ignored"
        return "cached" if self.repository.cache_state(relative, topic, payload, retained) else "unknown_device"


def main() -> int:
    load_dotenv(ROOT / ".env")
    base_topic = os.getenv("ZIGBEE2MQTT_BASE_TOPIC", DEFAULT_BASE_TOPIC).rstrip("/")
    repository = ZigbeeRepository()
    bootstrapped = repository.bootstrap_contact_ventilations()
    if bootstrapped:
        print(f"Bootstrapped {bootstrapped} open contact ventilation event(s)", flush=True)
    handler = ZigbeeMessageHandler(repository, base_topic)
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=os.getenv("MQTT_CLIENT_ID", "automation-zigbee2mqtt"),
        protocol=mqtt.MQTTv311,
    )
    username = os.getenv("MQTT_USERNAME")
    if username:
        client.username_pw_set(username, os.getenv("MQTT_PASSWORD"))

    def on_connect(
        mqtt_client: mqtt.Client, _userdata: Any, _flags: Any, reason_code: Any, _properties: Any
    ) -> None:
        if reason_code.is_failure:
            print(f"MQTT connection failed: {reason_code}", flush=True)
            return
        mqtt_client.subscribe(f"{base_topic}/#", qos=1)
        print(f"MQTT connected; subscribed to {base_topic}/#", flush=True)

    def on_message(_client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
        try:
            result = handler.handle(message.topic, message.payload, message.retain)
            if result.startswith("discovered:") or result == "removed":
                print(f"{message.topic}: {result}", flush=True)
        except Exception as error:
            print(
                f"MQTT message error on {message.topic}: {type(error).__name__}: {error}",
                file=sys.stderr,
                flush=True,
            )

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(
        os.getenv("MQTT_HOST", "127.0.0.1"),
        int(os.getenv("MQTT_PORT", "1883")),
        keepalive=60,
    )

    reconcile_stop = threading.Event()

    def reconcile_loop() -> None:
        reconcile_repository = ZigbeeRepository()
        try:
            while not reconcile_stop.wait(5):
                try:
                    load_dotenv(ROOT / ".env", override=True)
                    count = reconcile_repository.reconcile_pending_ventilations()
                    bootstrapped = reconcile_repository.bootstrap_contact_ventilations()
                    if count:
                        print(f"Closed {count} debounced ventilation event(s)", flush=True)
                    if bootstrapped:
                        print(
                            f"Bootstrapped {bootstrapped} open contact ventilation event(s)",
                            flush=True,
                        )
                except Exception as error:
                    print(
                        f"Ventilation reconciliation error: {type(error).__name__}: {error}",
                        file=sys.stderr,
                        flush=True,
                    )
        finally:
            reconcile_repository.close()

    reconcile_thread = threading.Thread(
        target=reconcile_loop, name="ventilation-reconciler", daemon=True
    )
    reconcile_thread.start()

    def stop(_signum: int, _frame: Any) -> None:
        client.disconnect()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        client.loop_forever(retry_first_connection=True)
    finally:
        reconcile_stop.set()
        reconcile_thread.join(timeout=10)
        repository.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
