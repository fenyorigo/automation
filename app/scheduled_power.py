from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime, time as clock_time
from typing import Any
from zoneinfo import ZoneInfo

from database import Database
from power_switch_control import PowerSwitchResult, control_tasmota_power


WATER_HEATER_HOSTNAME = "nous-bojler"
RECONCILE_INTERVAL_SECONDS = 60
_next_reconcile_at = 0.0


def _enabled() -> bool:
    return os.getenv("WATER_HEATER_SCHEDULE_ENABLED", "true").lower() == "true"


def _clock(value: str) -> clock_time:
    return datetime.strptime(value, "%H:%M").time()


def water_heater_schedule_details(now: datetime | None = None) -> dict[str, Any]:
    timezone = ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/Budapest"))
    local_now = now.astimezone(timezone) if now else datetime.now(timezone)
    start_text = os.getenv("WATER_HEATER_ON_TIME", "05:00")
    end_text = os.getenv("WATER_HEATER_OFF_TIME", "12:00")
    start = _clock(start_text)
    end = _clock(end_text)
    current = local_now.time().replace(tzinfo=None)
    if start < end:
        desired_power = start <= current < end
    else:
        desired_power = current >= start or current < end
    return {
        "enabled": _enabled(),
        "start": start_text,
        "end": end_text,
        "desired_power": desired_power,
    }


def _record_attempt(
    database: Database,
    device_id: int,
    source_system: str,
    requested_power: bool,
    result: PowerSwitchResult,
) -> None:
    cursor = database.connection.cursor()
    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        cursor.execute(
            """INSERT INTO device_power_control_attempts
                 (device_id,source_system,requested_power,requested_at,requested_by,
                  request_origin,status,preflight_power,verified_power,
                  completed_at,error_code,error_message)
               VALUES (?,?,?,?,NULL,'schedule',?,?,?,?,?,?)""",
            (
                device_id,
                source_system,
                requested_power,
                now,
                result.status,
                result.preflight_power,
                result.verified_power,
                now,
                result.error_code,
                result.error_message,
            ),
        )
        if (
            result.status == "verified"
            and result.verified_power is not None
            and result.preflight_power != result.verified_power
        ):
            token = now.strftime("%Y%m%dT%H%M%S%f")
            cursor.execute(
                """INSERT INTO device_states
                     (device_id,observed_at,power,online,source_system,
                      source_event_id,raw_state)
                   VALUES (?,?,?,1,'tasmota',?,?)""",
                (
                    device_id,
                    now,
                    result.verified_power,
                    f"tasmota:schedule:{device_id}:{token}",
                    json.dumps(
                        {"power": result.verified_power, "origin": "schedule"}
                    ),
                ),
            )
        database.connection.commit()
    except Exception:
        database.connection.rollback()
        raise
    finally:
        cursor.close()


def reconcile_water_heater_schedule(
    now: datetime | None = None, *, force: bool = False
) -> int:
    """Reconcile the dedicated water-heater plug with the automation schedule."""
    global _next_reconcile_at
    monotonic_now = time.monotonic()
    if not force and monotonic_now < _next_reconcile_at:
        return 0
    _next_reconcile_at = monotonic_now + RECONCILE_INTERVAL_SECONDS

    schedule = water_heater_schedule_details(now)
    if not schedule["enabled"]:
        return 0

    database = Database()
    cursor = database.connection.cursor()
    try:
        cursor.execute(
            """SELECT id,source_system,hostname
                 FROM devices
                WHERE is_active=1 AND control_enabled=1
                  AND source_system='tasmota' AND hostname=?
                LIMIT 1""",
            (WATER_HEATER_HOSTNAME,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
    if row is None:
        database.close()
        return 0

    requested_power = bool(schedule["desired_power"])
    try:
        result = control_tasmota_power(str(row[2]), requested_power)
        changed = (
            result.status == "verified"
            and result.preflight_power != result.verified_power
        )
        if changed or result.status != "verified":
            _record_attempt(
                database, int(row[0]), str(row[1]), requested_power, result
            )
        if result.status != "verified":
            detail = result.error_message or result.error_code or result.status
            raise RuntimeError(f"A villanybojler ütemezett kapcsolása sikertelen: {detail}")
        return int(changed)
    finally:
        database.close()
