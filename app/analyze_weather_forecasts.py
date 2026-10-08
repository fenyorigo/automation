#!/usr/bin/env python3

from __future__ import annotations

import argparse
import bisect
import json
import math
import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import mariadb
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
HORIZON_BUCKETS = (
    (0, 6, "0–6 óra"),
    (6, 12, "6–12 óra"),
    (12, 24, "12–24 óra"),
    (24, 48, "24–48 óra"),
    (48, 73, "48–72 óra"),
)


def connect_database() -> mariadb.Connection:
    return mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "home_automation"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def summarize_errors(errors: list[float]) -> dict[str, float | int | None]:
    if not errors:
        return {"count": 0, "mae_c": None, "bias_c": None, "rmse_c": None}
    return {
        "count": len(errors),
        "mae_c": round(sum(abs(error) for error in errors) / len(errors), 3),
        "bias_c": round(sum(errors) / len(errors), 3),
        "rmse_c": round(math.sqrt(sum(error * error for error in errors) / len(errors)), 3),
    }


def nearest_observation(
    observations: list[tuple[datetime, float]],
    observation_times: list[datetime],
    valid_at: datetime,
) -> tuple[datetime, float] | None:
    if not observations:
        return None
    index = bisect.bisect_left(observation_times, valid_at)
    candidates = observations[max(0, index - 1): min(len(observations), index + 1)]
    return min(candidates, key=lambda item: abs(item[0] - valid_at))


def analyze(days: int, tolerance_minutes: int) -> dict[str, Any]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT id,source_code,display_name FROM outdoor_temperature_sources
               WHERE is_active=1 AND source_type IN ('zigbee2mqtt','esp32','wunderground_pws')
               ORDER BY priority,id LIMIT 1"""
        )
        actual_source = cursor.fetchone()
        if actual_source is None:
            raise RuntimeError("No active local outdoor-temperature source is available")
        cursor.execute(
            """SELECT p.valid_at,p.lead_hours,p.temperature_c
               FROM outdoor_weather_forecast_points p
               JOIN outdoor_weather_forecast_runs r ON r.id=p.run_id
               JOIN outdoor_temperature_sources s ON s.id=r.source_id
               WHERE s.source_type='open_meteo'
                 AND p.valid_at BETWEEN UTC_TIMESTAMP(3) - INTERVAL ? DAY
                                    AND UTC_TIMESTAMP(3)
               ORDER BY p.valid_at""",
            (days,),
        )
        forecasts = cursor.fetchall()
        if not forecasts:
            return {
                "actual_source": actual_source[1],
                "actual_source_name": actual_source[2],
                "paired_points": 0,
                "message": "There are no elapsed forecast points yet.",
                "by_horizon": {},
            }
        first = min(row[0] for row in forecasts) - timedelta(minutes=tolerance_minutes)
        last = max(row[0] for row in forecasts) + timedelta(minutes=tolerance_minutes)
        cursor.execute(
            """SELECT observed_at,temperature_c
               FROM outdoor_temperature_observations
               WHERE source_id=? AND observed_at BETWEEN ? AND ?
               ORDER BY observed_at""",
            (actual_source[0], first, last),
        )
        observations = [(row[0], float(row[1])) for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()

    grouped: dict[str, list[float]] = defaultdict(list)
    all_errors: list[float] = []
    tolerance = timedelta(minutes=tolerance_minutes)
    observation_times = [item[0] for item in observations]
    for valid_at, lead_hours, forecast_temperature in forecasts:
        actual = nearest_observation(observations, observation_times, valid_at)
        if actual is None or abs(actual[0] - valid_at) > tolerance:
            continue
        error = float(forecast_temperature) - actual[1]
        all_errors.append(error)
        lead = float(lead_hours)
        for lower, upper, label in HORIZON_BUCKETS:
            if lower <= lead < upper:
                grouped[label].append(error)
                break
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "actual_source": actual_source[1],
        "actual_source_name": actual_source[2],
        "tolerance_minutes": tolerance_minutes,
        "paired_points": len(all_errors),
        "overall": summarize_errors(all_errors),
        "by_horizon": {
            label: summarize_errors(grouped[label])
            for _lower, _upper, label in HORIZON_BUCKETS
        },
    }


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description="Compare stored Open-Meteo forecasts with the local outdoor sensor."
    )
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--tolerance-minutes", type=int, default=90)
    args = parser.parse_args()
    if args.days < 1 or args.tolerance_minutes < 1:
        parser.error("days and tolerance-minutes must be positive")
    print(json.dumps(analyze(args.days, args.tolerance_minutes), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
