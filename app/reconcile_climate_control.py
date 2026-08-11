#!/usr/bin/env python3
"""Recover audit/event state after a verified ConnectLife write was not persisted."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime

from dotenv import load_dotenv

from climate_control import find_appliance, state_of
from connectlife.api import ConnectLifeApi
from dashboard import ROOT, connect_database


async def current_state(wifi_id: str):
    import os

    api = ConnectLifeApi(os.environ["CONNECTLIFE_USERNAME"], os.environ["CONNECTLIFE_PASSWORD"])
    return state_of(find_appliance(await api.get_appliances(), wifi_id))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-id", type=int, required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--requested-at", help="ISO-8601 timestamp with timezone")
    parser.add_argument("--attempt-id", type=int)
    parser.add_argument("--power", choices=("on", "off"), required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")

    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT room_id,source_puid FROM devices
               WHERE id=? AND source_system='connectlife'""",
            (args.device_id,),
        )
        device = cursor.fetchone()
        cursor.execute("SELECT id FROM app_users WHERE username=? AND is_active=1", (args.username,))
        user = cursor.fetchone()
        if device is None or user is None:
            raise RuntimeError("Unknown device or user")

        verified = asyncio.run(current_state(str(device[1])))
        desired_power = args.power == "on"
        if verified["power"] != desired_power:
            raise RuntimeError("The current device power does not match the recovered command")
        requested_at = (
            datetime.fromisoformat(args.requested_at).astimezone(UTC).replace(tzinfo=None)
            if args.requested_at else None
        )
        now = datetime.now(UTC).replace(tzinfo=None)
        preflight = {"power": not desired_power, "recovered_after_persistence_error": True}
        if args.attempt_id:
            cursor.execute(
                """UPDATE climate_control_attempts SET status='verified',preflight_state=?,
                   verified_state=?,completed_at=? WHERE id=? AND device_id=? AND status='requested'""",
                (json.dumps(preflight), json.dumps(verified, default=str), now,
                 args.attempt_id, args.device_id),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Requested audit attempt not found")
        else:
            if requested_at is None:
                raise RuntimeError("--requested-at is required without --attempt-id")
            cursor.execute(
                """INSERT INTO climate_control_attempts
                   (device_id,requested_by,requested_power,requested_temperature_c,status,
                    preflight_state,verified_state,requested_at,completed_at)
                   VALUES (?,?,?,?, 'verified',?,?,?,?)""",
                (args.device_id, int(user[0]), desired_power,
                 verified.get("target_temperature_c") if desired_power else None,
                 json.dumps(preflight), json.dumps(verified, default=str), requested_at, now),
            )
        cursor.execute(
            """INSERT INTO device_states
               (device_id,observed_at,power,mode,target_temperature_c,online,
                source_system,source_event_id,raw_state)
               VALUES (?,?,?,?,?,1,'connectlife',?,?)""",
            (args.device_id, now, desired_power, str(verified.get("mode")),
             verified.get("target_temperature_c"),
             f"connectlife:recovery:{args.device_id}:{now.strftime('%Y%m%dT%H%M%S%f')}",
             json.dumps(verified["raw"], default=str)),
        )
        if desired_power:
            cursor.execute(
                "SELECT 1 FROM climate_operation_events WHERE device_id=? AND ended_at IS NULL",
                (args.device_id,),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    """INSERT INTO climate_operation_events
                       (device_id,room_id,started_at,open_device_id,
                        started_target_temperature_c,note,created_by)
                       VALUES (?,?,?,?,?,'UI-vezérlés – helyreállított napló',?)""",
                    (args.device_id, int(device[0]), requested_at, args.device_id,
                     verified.get("target_temperature_c"), int(user[0])),
                )
        else:
            cursor.execute(
                """UPDATE climate_operation_events SET ended_at=?,open_device_id=NULL,
                   ended_target_temperature_c=?
                   WHERE device_id=? AND ended_at IS NULL""",
                (now, verified.get("target_temperature_c"), args.device_id),
            )
        connection.commit()
        print(json.dumps({"status": "recovered", "verified": verified}, ensure_ascii=False, default=str))
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
