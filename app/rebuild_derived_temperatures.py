#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import mariadb
from dotenv import load_dotenv

from temperature_derivation import derive_temperature


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_dotenv(ROOT / ".env")
    connection = mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "home_automation"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        autocommit=False,
    )
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT id,sensor_id,calibration_offset_c,valid_from,valid_until,
                   filter_tau_seconds,action_interval_seconds,calculation_version
            FROM sensor_calibrations
            WHERE physical_configuration='copper_tube_box' AND decision_enabled=1
            ORDER BY sensor_id,valid_from
            """
        )
        calibrations = cursor.fetchall()
        for calibration in calibrations:
            (
                calibration_id, sensor_id, offset_c, valid_from, valid_until,
                tau_seconds, interval_seconds, version,
            ) = calibration
            cursor.execute(
                "DELETE FROM derived_temperature_readings WHERE calibration_id=?",
                (calibration_id,),
            )
            cursor.execute(
                """
                SELECT id,observed_at,value FROM sensor_readings
                WHERE sensor_id=? AND quality='good' AND value IS NOT NULL
                  AND observed_at>=? AND (? IS NULL OR observed_at<?)
                ORDER BY observed_at,id
                """,
                (sensor_id, valid_from, valid_until, valid_until),
            )
            readings = cursor.fetchall()
            previous_filtered: float | None = None
            previous_at: datetime | None = None
            last_action_at: datetime | None = None
            source_from: datetime | None = None
            sample_count = 0
            action_count = 0
            for raw_id, observed_at, raw_value in readings:
                result = derive_temperature(
                    raw_value=float(raw_value), offset_c=float(offset_c),
                    observed_at=observed_at, tau_seconds=int(tau_seconds),
                    action_interval_seconds=int(interval_seconds),
                    previous_filtered=previous_filtered,
                    previous_observed_at=previous_at, last_action_at=last_action_at,
                    source_from=source_from, sample_count=sample_count,
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
                        sensor_id, raw_id, calibration_id, observed_at,
                        result.calibrated, result.filtered, result.action,
                        result.is_action_point, result.source_from, observed_at,
                        result.sample_count, version,
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
                    (derived_id, sensor_id, raw_id),
                )
                previous_filtered = result.filtered
                previous_at = observed_at
                source_from = result.source_from
                sample_count = result.sample_count
                if result.is_action_point:
                    last_action_at = observed_at
                    action_count += 1
            print(
                f"calibration {calibration_id}: {len(readings)} filtered readings, "
                f"{action_count} action points"
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
