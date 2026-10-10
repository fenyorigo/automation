#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import mariadb
from dotenv import load_dotenv

from measurement_retention import (
    TASMOTA_MONTHLY_HISTORY_DEVICE_IDS,
    previous_calendar_month_start_utc,
)


ROOT = Path(__file__).resolve().parents[1]


def connect() -> mariadb.Connection:
    return mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "home_automation"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        autocommit=False,
    )


def delete_batches(
    connection: mariadb.Connection,
    where_sql: str,
    params: tuple[object, ...],
    *,
    batch_size: int,
    pause_seconds: float,
) -> int:
    total = 0
    while True:
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"DELETE FROM sensor_readings WHERE {where_sql} LIMIT {batch_size}",
                params,
            )
            removed = int(cursor.rowcount)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
        total += removed
        if removed < batch_size:
            return total
        if pause_seconds:
            time.sleep(pause_seconds)


def sensor_ids(
    connection: mariadb.Connection,
    source_system: str,
    device_filter: str,
    params: tuple[object, ...] = (),
) -> list[int]:
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""SELECT s.id
                  FROM sensors s JOIN devices d ON d.id=s.device_id
                 WHERE d.source_system=? AND {device_filter}""",
            (source_system, *params),
        )
        return [int(row[0]) for row in cursor.fetchall()]
    finally:
        cursor.close()


def tasmota_device_ids(
    connection: mariadb.Connection, device_filter: str, params: tuple[object, ...]
) -> list[int]:
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""SELECT id FROM devices
                 WHERE source_system='tasmota' AND {device_filter}""",
            params,
        )
        return [int(row[0]) for row in cursor.fetchall()]
    finally:
        cursor.close()


def prune(batch_size: int, pause_seconds: float) -> dict[str, int]:
    connection = connect()
    removed = {"zigbee": 0, "tasmota_monthly": 0, "tasmota_latest": 0}
    try:
        zigbee_ids = sensor_ids(
            connection, "zigbee2mqtt", "d.device_type='power_meter'"
        )
        for sensor_id in zigbee_ids:
            removed["zigbee"] += delete_batches(
                connection,
                "sensor_id=?",
                (sensor_id,),
                batch_size=batch_size,
                pause_seconds=pause_seconds,
            )

        placeholders = ",".join("?" for _ in TASMOTA_MONTHLY_HISTORY_DEVICE_IDS)
        retained_ids = tuple(sorted(TASMOTA_MONTHLY_HISTORY_DEVICE_IDS))
        monthly_ids = sensor_ids(
            connection,
            "tasmota",
            f"d.source_device_id IN ({placeholders})",
            retained_ids,
        )
        cutoff = previous_calendar_month_start_utc()
        for sensor_id in monthly_ids:
            removed["tasmota_monthly"] += delete_batches(
                connection,
                "sensor_id=? AND observed_at<?",
                (sensor_id, cutoff),
                batch_size=batch_size,
                pause_seconds=pause_seconds,
            )

        latest_only_ids = sensor_ids(
            connection,
            "tasmota",
            f"d.source_device_id NOT IN ({placeholders})",
            retained_ids,
        )
        cursor = connection.cursor()
        try:
            for sensor_id in latest_only_ids:
                cursor.execute(
                    "SELECT id FROM sensor_readings WHERE sensor_id=? ORDER BY observed_at DESC,id DESC LIMIT 1",
                    (sensor_id,),
                )
                latest = cursor.fetchone()
                if latest is None:
                    continue
                removed["tasmota_latest"] += delete_batches(
                    connection,
                    "sensor_id=? AND id<>?",
                    (sensor_id, int(latest[0])),
                    batch_size=batch_size,
                    pause_seconds=pause_seconds,
                )
        finally:
            cursor.close()

        monthly_device_ids = tasmota_device_ids(
            connection,
            f"source_device_id IN ({placeholders})",
            retained_ids,
        )
        latest_only_device_ids = tasmota_device_ids(
            connection,
            f"source_device_id NOT IN ({placeholders})",
            retained_ids,
        )
        cursor = connection.cursor()
        try:
            for device_id in monthly_device_ids:
                cursor.execute(
                    "DELETE FROM device_states WHERE device_id=? AND observed_at<?",
                    (device_id, cutoff),
                )
            for device_id in latest_only_device_ids:
                cursor.execute(
                    "SELECT id FROM device_states WHERE device_id=? ORDER BY observed_at DESC,id DESC LIMIT 1",
                    (device_id,),
                )
                latest = cursor.fetchone()
                if latest is not None:
                    cursor.execute(
                        "DELETE FROM device_states WHERE device_id=? AND id<>?",
                        (device_id, int(latest[0])),
                    )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
        return removed
    finally:
        connection.close()


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Prune unneeded plug time series.")
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--pause-seconds", type=float, default=0.05)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    result = prune(args.batch_size, max(0.0, args.pause_seconds))
    print(" ".join(f"{key}={value}" for key, value in result.items()))


if __name__ == "__main__":
    main()
