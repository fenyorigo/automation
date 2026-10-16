from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from typing import Any

import mariadb

from climate_control import ClimateControlResult, control_climate
from polling_lock import PollCycleBusy, polling_cycle_lock


def connect_database() -> mariadb.Connection:
    return mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "home_automation"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        autocommit=False,
    )


def _claim_next() -> dict[str, Any] | None:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """UPDATE climate_control_attempts
                  SET execution_phase='queued',phase_updated_at=UTC_TIMESTAMP(3),started_at=NULL
                WHERE status='requested' AND execution_phase NOT IN ('queued','completed')
                  AND phase_updated_at < UTC_TIMESTAMP(3)-INTERVAL 5 MINUTE"""
        )
        cursor.execute(
            """SELECT a.id,a.device_id,a.requested_by,a.requested_power,
                      a.requested_temperature_c,a.requested_fan_speed,a.requested_mode,
                      d.room_id,d.source_puid
                 FROM climate_control_attempts a
                 JOIN devices d ON d.id=a.device_id
                WHERE a.status='requested' AND a.execution_phase='queued'
                ORDER BY a.requested_at,a.id LIMIT 1 FOR UPDATE"""
        )
        row = cursor.fetchone()
        if row is None:
            connection.commit()
            return None
        keys = (
            "id", "device_id", "requested_by", "requested_power",
            "requested_temperature_c", "requested_fan_speed", "requested_mode",
            "room_id", "source_puid",
        )
        item = dict(zip(keys, row))
        cursor.execute(
            """UPDATE climate_control_attempts
                  SET execution_phase='preflight',started_at=UTC_TIMESTAMP(3),
                      phase_updated_at=UTC_TIMESTAMP(3)
                WHERE id=? AND status='requested' AND execution_phase='queued'""",
            (item["id"],),
        )
        if cursor.rowcount != 1:
            connection.rollback()
            return None
        connection.commit()
        return item
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def _store_progress(attempt_id: int, phase: str, state: dict[str, Any] | None) -> None:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """UPDATE climate_control_attempts
                  SET execution_phase=?,verified_state=?,phase_updated_at=UTC_TIMESTAMP(3)
                WHERE id=? AND status='requested'""",
            (
                phase,
                json.dumps(state, ensure_ascii=False, default=str) if state else None,
                attempt_id,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def _persist_result(item: dict[str, Any], result: ClimateControlResult) -> None:
    connection = connect_database()
    cursor = connection.cursor()
    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        cursor.execute(
            """UPDATE climate_control_attempts
                  SET status=?,execution_phase='completed',preflight_state=?,verified_state=?,
                      error_code=?,error_message=?,phase_updated_at=?,completed_at=?
                WHERE id=? AND status='requested'""",
            (
                result.status,
                json.dumps(result.preflight, ensure_ascii=False, default=str),
                json.dumps(result.verified, ensure_ascii=False, default=str)
                if result.verified else None,
                result.error_code,
                result.error_message,
                now,
                now,
                item["id"],
            ),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("A háttérben futó klímaparancs auditbejegyzése nem frissíthető.")
        if result.verified is not None:
            verified = result.verified
            token = now.strftime("%Y%m%dT%H%M%S%f")
            cursor.execute(
                """INSERT INTO device_states
                   (device_id,observed_at,power,mode,target_temperature_c,fan_speed,online,
                    source_system,source_event_id,raw_state)
                   VALUES (?,?,?,?,?,?,1,'connectlife',?,?)""",
                (
                    item["device_id"], now, verified["power"], str(verified.get("mode")),
                    verified.get("target_temperature_c"), verified.get("fan_speed"),
                    f"connectlife:queued-control:{item['device_id']}:{token}",
                    json.dumps(verified["raw"], ensure_ascii=False, default=str),
                ),
            )
            if bool(verified.get("power")):
                cursor.execute(
                    "SELECT 1 FROM climate_operation_events WHERE device_id=? AND ended_at IS NULL",
                    (item["device_id"],),
                )
                if cursor.fetchone() is None:
                    cursor.execute(
                        """INSERT INTO climate_operation_events
                           (device_id,room_id,started_at,open_device_id,
                            started_target_temperature_c,started_fan_speed,
                            note,event_origin,created_by)
                           VALUES (?,?,?,?,?,?,'UI-vezérlés','ui_control',?)""",
                        (
                            item["device_id"], item["room_id"], now, item["device_id"],
                            verified.get("target_temperature_c"), verified.get("fan_speed"),
                            item["requested_by"],
                        ),
                    )
            else:
                cursor.execute(
                    """UPDATE climate_operation_events
                          SET ended_at=?,open_device_id=NULL,ended_target_temperature_c=?,
                              ended_fan_speed=?
                        WHERE device_id=? AND ended_at IS NULL""",
                    (
                        now,
                        verified.get("target_temperature_c"),
                        result.preflight.get("fan_speed"),
                        item["device_id"],
                    ),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


async def process_manual_climate_queue() -> int:
    item = await asyncio.to_thread(_claim_next)
    if item is None:
        return 0

    async def progress(phase: str, state: dict[str, Any] | None) -> None:
        await asyncio.to_thread(_store_progress, int(item["id"]), phase, state)

    try:
        with polling_cycle_lock(operation="manual_climate_control"):
            power = bool(item["requested_power"])
            result = await control_climate(
                str(item["source_puid"]),
                power,
                int(item["requested_temperature_c"]) if power else None,
                str(item["requested_fan_speed"]) if power else None,
                mode=str(item["requested_mode"]) if power and item["requested_mode"] else None,
                allow_running_update=True,
                progress=progress,
            )
    except PollCycleBusy:
        await asyncio.to_thread(_store_progress, int(item["id"]), "queued", None)
        return 0
    await asyncio.to_thread(_persist_result, item, result)
    return 1
