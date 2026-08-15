from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta

import mariadb

from climate_control import ClimateControlResult, control_climate
from polling_lock import PollCycleBusy, polling_cycle_lock


def connect_database() -> mariadb.Connection:
    return mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "home_automation"), user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"], autocommit=False,
    )


def _claim_due() -> dict[str, object] | None:
    connection = connect_database(); cursor = connection.cursor()
    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        cursor.execute(
            """UPDATE climate_control_schedules SET status='scheduled'
               WHERE status='starting' AND updated_at < UTC_TIMESTAMP(3)-INTERVAL 5 MINUTE"""
        )
        cursor.execute(
            """UPDATE climate_control_schedules SET status='running'
               WHERE status='stopping' AND updated_at < UTC_TIMESTAMP(3)-INTERVAL 5 MINUTE"""
        )
        cursor.execute(
            """SELECT s.id,s.device_id,s.starts_at,s.runtime_minutes,
                      s.target_temperature_c,s.fan_speed,s.status,s.created_by,d.room_id,d.source_puid
               FROM climate_control_schedules s JOIN devices d ON d.id=s.device_id
               WHERE (s.status='scheduled' AND s.starts_at<=UTC_TIMESTAMP(3))
                  OR (s.status='running' AND
                      TIMESTAMPADD(MINUTE,s.runtime_minutes,s.actual_started_at)<=UTC_TIMESTAMP(3))
               ORDER BY IF(s.status='running',0,1),s.starts_at,s.id LIMIT 1 FOR UPDATE"""
        )
        row = cursor.fetchone()
        if row is None:
            connection.commit(); return None
        keys = ("id","device_id","starts_at","runtime_minutes","target","fan_speed","status","created_by","room_id","source_puid")
        item = dict(zip(keys, row))
        if item["status"] == "scheduled" and now >= item["starts_at"] + timedelta(minutes=int(item["runtime_minutes"])):
            cursor.execute(
                "UPDATE climate_control_schedules SET status='failed',error_message='A futási ablak a gép távollétében lejárt.' WHERE id=?",
                (item["id"],),
            )
            connection.commit(); return None
        next_status = "starting" if item["status"] == "scheduled" else "stopping"
        cursor.execute("UPDATE climate_control_schedules SET status=? WHERE id=?", (next_status,item["id"]))
        connection.commit(); item["action"] = "start" if next_status == "starting" else "stop"
        return item
    except Exception:
        connection.rollback(); raise
    finally:
        cursor.close(); connection.close()


def _begin_attempt(item: dict[str, object], power: bool) -> int:
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute(
            """INSERT INTO climate_control_attempts
               (device_id,requested_by,requested_power,requested_temperature_c,
                requested_fan_speed,status)
               VALUES (?,?,?,?,?,'requested')""",
            (item["device_id"],item["created_by"],power,
             item["target"] if power else None,item["fan_speed"] if power else None),
        )
        attempt=int(cursor.lastrowid); connection.commit(); return attempt
    except Exception:
        connection.rollback(); raise
    finally: cursor.close(); connection.close()


def _release_claim(item: dict[str, object]) -> None:
    connection=connect_database(); cursor=connection.cursor()
    try:
        status = "scheduled" if item["action"] == "start" else "running"
        cursor.execute("UPDATE climate_control_schedules SET status=? WHERE id=?",(status,item["id"]))
        connection.commit()
    except Exception:
        connection.rollback(); raise
    finally: cursor.close(); connection.close()


def _persist(item: dict[str, object], attempt_id: int, power: bool, result: ClimateControlResult) -> None:
    connection=connect_database(); cursor=connection.cursor(); now=datetime.now(UTC).replace(tzinfo=None)
    try:
        achieved = result.status == "verified"
        verified = result.verified
        cursor.execute(
            """UPDATE climate_control_attempts SET status=?,preflight_state=?,verified_state=?,
                      error_code=?,error_message=?,completed_at=? WHERE id=?""",
            ("verified" if achieved else result.status,json.dumps(result.preflight,ensure_ascii=False,default=str),
             json.dumps(verified,ensure_ascii=False,default=str) if verified else None,
             None if achieved else result.error_code,None if achieved else result.error_message,now,attempt_id),
        )
        if not achieved:
            cursor.execute(
                "UPDATE climate_control_schedules SET status='failed',error_message=? WHERE id=?",
                (result.error_message or "Ismeretlen vezérlési hiba",item["id"]),
            )
        elif power:
            event_token=now.strftime("%Y%m%dT%H%M%S%f")
            cursor.execute(
                """INSERT INTO device_states
                   (device_id,observed_at,power,mode,target_temperature_c,fan_speed,online,
                    source_system,source_event_id,raw_state)
                   VALUES (?,?,?,?,?,?,1,'connectlife',?,?)""",
                (item["device_id"],now,verified["power"],str(verified.get("mode")),
                 verified.get("target_temperature_c"),verified.get("fan_speed"),
                 f"connectlife:scheduled-control:{item['device_id']}:{event_token}",
                 json.dumps(verified["raw"],ensure_ascii=False,default=str)),
            )
            cursor.execute(
                """UPDATE climate_control_schedules SET status='running',start_attempt_id=?,
                          actual_started_at=?,error_message=NULL WHERE id=?""",
                (attempt_id,now,item["id"]),
            )
            cursor.execute("SELECT 1 FROM climate_operation_events WHERE device_id=? AND ended_at IS NULL",(item["device_id"],))
            if cursor.fetchone() is None:
                cursor.execute(
                    """INSERT INTO climate_operation_events
                       (device_id,room_id,started_at,open_device_id,started_target_temperature_c,
                        started_fan_speed,note,event_origin,created_by)
                       VALUES (?,?,?,?,?,?,'Időzített UI-vezérlés','ui_control',?)""",
                    (item["device_id"],item["room_id"],now,item["device_id"],
                     verified.get("target_temperature_c"),verified.get("fan_speed"),item["created_by"]),
                )
        else:
            event_token=now.strftime("%Y%m%dT%H%M%S%f")
            cursor.execute(
                """INSERT INTO device_states
                   (device_id,observed_at,power,mode,target_temperature_c,fan_speed,online,
                    source_system,source_event_id,raw_state)
                   VALUES (?,?,?,?,?,?,1,'connectlife',?,?)""",
                (item["device_id"],now,verified["power"],str(verified.get("mode")),
                 verified.get("target_temperature_c"),verified.get("fan_speed"),
                 f"connectlife:scheduled-control:{item['device_id']}:{event_token}",
                 json.dumps(verified["raw"],ensure_ascii=False,default=str)),
            )
            cursor.execute(
                """UPDATE climate_control_schedules SET status='completed',stop_attempt_id=?,
                          actual_ended_at=?,error_message=NULL WHERE id=?""",
                (attempt_id,now,item["id"]),
            )
            cursor.execute(
                """UPDATE climate_operation_events SET ended_at=?,open_device_id=NULL,
                          ended_target_temperature_c=?,ended_fan_speed=?
                          WHERE device_id=? AND ended_at IS NULL""",
                (now,verified.get("target_temperature_c"),result.preflight.get("fan_speed"),
                 item["device_id"]),
            )
        connection.commit()
    except Exception:
        connection.rollback(); raise
    finally: cursor.close(); connection.close()


async def process_due_climate_schedules() -> int:
    processed=0
    while True:
        item = await asyncio.to_thread(_claim_due)
        if item is None: return processed
        power = item["action"] == "start"
        try:
            with polling_cycle_lock(operation="scheduled_climate_control"):
                attempt = await asyncio.to_thread(_begin_attempt,item,power)
                result = await control_climate(
                    str(item["source_puid"]), power,
                    int(item["target"]) if power else None,
                    str(item["fan_speed"]) if power else None,
                )
                await asyncio.to_thread(_persist,item,attempt,power,result)
            processed += 1
        except PollCycleBusy:
            await asyncio.to_thread(_release_claim,item)
            return processed
