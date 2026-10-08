from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import mariadb
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class OutdoorSource:
    id: int
    source_code: str
    source_type: str
    priority: int
    configuration: dict[str, Any]


def connect_database() -> mariadb.Connection:
    return mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "home_automation"), user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"], autocommit=False,
    )


def _as_utc_database_time(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _poll_open_meteo(source: OutdoorSource, timeout: float) -> tuple[str, float, dict[str, Any]]:
    query = urllib.parse.urlencode({
        "latitude": float(source.configuration["latitude"]),
        "longitude": float(source.configuration["longitude"]),
        "current": "temperature_2m", "timezone": "UTC",
    })
    request = urllib.request.Request(
        f"https://api.open-meteo.com/v1/forecast?{query}",
        headers={"User-Agent": "home-automation/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    current = payload["current"]
    return _as_utc_database_time(current["time"]), float(current["temperature_2m"]), payload


FORECAST_HOURS = 72
FORECAST_INTERVAL = timedelta(hours=1)
FORECAST_VARIABLES = (
    "temperature_2m",
    "apparent_temperature",
    "cloud_cover",
    "shortwave_radiation",
    "wind_speed_10m",
    "precipitation",
    "weather_code",
)


def _poll_open_meteo_forecast(
    source: OutdoorSource, timeout: float
) -> dict[str, Any]:
    query = urllib.parse.urlencode({
        "latitude": float(source.configuration["latitude"]),
        "longitude": float(source.configuration["longitude"]),
        "hourly": ",".join(FORECAST_VARIABLES),
        "forecast_hours": FORECAST_HOURS,
        "timezone": "UTC",
    })
    request = urllib.request.Request(
        f"https://api.open-meteo.com/v1/forecast?{query}",
        headers={"User-Agent": "home-automation/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def forecast_points(
    payload: dict[str, Any], fetched_at: datetime
) -> list[dict[str, Any]]:
    """Normalize the Open-Meteo parallel hourly arrays into auditable points."""
    hourly = payload["hourly"]
    points: list[dict[str, Any]] = []
    for index, timestamp in enumerate(hourly["time"]):
        valid_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if valid_at.tzinfo is None:
            valid_at = valid_at.replace(tzinfo=UTC)
        valid_at = valid_at.astimezone(UTC)
        points.append({
            "valid_at": valid_at.replace(tzinfo=None),
            "lead_hours": max(
                0.0,
                (valid_at - fetched_at.astimezone(UTC)).total_seconds() / 3600,
            ),
            **{
                variable: hourly.get(variable, [None] * len(hourly["time"]))[index]
                for variable in FORECAST_VARIABLES
            },
        })
    return points


def _forecast_due(cursor: mariadb.Cursor, source_id: int) -> bool:
    cursor.execute(
        """SELECT fetched_at FROM outdoor_weather_forecast_runs
           WHERE source_id=? ORDER BY fetched_at DESC,id DESC LIMIT 1""",
        (source_id,),
    )
    row = cursor.fetchone()
    return row is None or datetime.now(UTC).replace(tzinfo=None) - row[0] >= FORECAST_INTERVAL


def _store_forecast(
    cursor: mariadb.Cursor,
    source: OutdoorSource,
    payload: dict[str, Any],
    fetched_at: datetime,
) -> int:
    points = forecast_points(payload, fetched_at)
    if not points:
        raise ValueError("Open-Meteo forecast contains no hourly points")
    cursor.execute(
        """INSERT INTO outdoor_weather_forecast_runs
             (source_id,fetched_at,forecast_from,forecast_until,point_count,raw_payload)
           VALUES (?,?,?,?,?,?)""",
        (
            source.id,
            fetched_at.astimezone(UTC).replace(tzinfo=None),
            points[0]["valid_at"],
            points[-1]["valid_at"],
            len(points),
            json.dumps(payload, separators=(",", ":")),
        ),
    )
    run_id = int(cursor.lastrowid)
    rows = [
        (
            run_id,
            point["valid_at"],
            point["lead_hours"],
            point["temperature_2m"],
            point["apparent_temperature"],
            point["cloud_cover"],
            point["shortwave_radiation"],
            point["wind_speed_10m"],
            point["precipitation"],
            point["weather_code"],
        )
        for point in points
    ]
    cursor.executemany(
        """INSERT INTO outdoor_weather_forecast_points
             (run_id,valid_at,lead_hours,temperature_c,apparent_temperature_c,
              cloud_cover_percent,shortwave_radiation_wm2,wind_speed_10m_kmh,
              precipitation_mm,weather_code)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    return run_id


def _collect_forecast_if_due(
    cursor: mariadb.Cursor, source: OutdoorSource, timeout: float
) -> None:
    if not _forecast_due(cursor, source.id):
        return
    started = time.monotonic()
    fetched_at = datetime.now(UTC)
    try:
        payload = _poll_open_meteo_forecast(source, timeout)
        run_id = _store_forecast(cursor, source, payload, fetched_at)
        cursor.execute(
            """INSERT INTO outdoor_weather_forecast_poll_attempts
                 (source_id,completed_at,success,duration_ms,run_id)
               VALUES (?,CURRENT_TIMESTAMP(3),1,?,?)""",
            (source.id, round((time.monotonic() - started) * 1000), run_id),
        )
    except Exception as error:
        cursor.execute(
            """INSERT INTO outdoor_weather_forecast_poll_attempts
                 (source_id,completed_at,success,error_code,error_message,duration_ms)
               VALUES (?,CURRENT_TIMESTAMP(3),0,?,?,?)""",
            (
                source.id,
                type(error).__name__,
                str(error),
                round((time.monotonic() - started) * 1000),
            ),
        )


def _active_automatic_sources(cursor: mariadb.Cursor) -> list[OutdoorSource]:
    cursor.execute("""SELECT id,source_code,source_type,priority,configuration
                      FROM outdoor_temperature_sources
                      WHERE is_active=1 AND source_type='open_meteo' ORDER BY priority""")
    sources = []
    for row in cursor.fetchall():
        configuration = json.loads(row[4]) if isinstance(row[4], str) else row[4]
        sources.append(OutdoorSource(int(row[0]), row[1], row[2], int(row[3]), configuration or {}))
    return sources


def poll_active_outdoor_sources(timeout: float = 5.0) -> tuple[int, int]:
    connection = connect_database()
    cursor = connection.cursor()
    successful = attempted = 0
    try:
        for source in _active_automatic_sources(cursor):
            attempted += 1
            started = time.monotonic()
            try:
                observed_at, temperature_c, payload = _poll_open_meteo(source, timeout)
                event_id = f"{source.source_code}:{observed_at.replace(' ', 'T')}"
                cursor.execute("""INSERT IGNORE INTO outdoor_temperature_observations
                                  (source_id,observed_at,temperature_c,quality,source_event_id,raw_payload)
                                  VALUES (?,?,?,'good',?,?)""",
                               (source.id, observed_at, temperature_c, event_id,
                                json.dumps(payload, separators=(",", ":"))))
                cursor.execute("""INSERT INTO outdoor_temperature_poll_attempts
                                  (source_id,completed_at,success,duration_ms)
                                  VALUES (?,CURRENT_TIMESTAMP(3),1,?)""",
                               (source.id, round((time.monotonic() - started) * 1000)))
                _collect_forecast_if_due(cursor, source, timeout)
                successful += 1
            except Exception as error:
                cursor.execute("""INSERT INTO outdoor_temperature_poll_attempts
                                  (source_id,completed_at,success,error_code,error_message,duration_ms)
                                  VALUES (?,CURRENT_TIMESTAMP(3),0,?,?,?)""",
                               (source.id, type(error).__name__, str(error),
                                round((time.monotonic() - started) * 1000)))
            connection.commit()
        return successful, attempted
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    load_dotenv(ROOT / ".env")
    ok, total = poll_active_outdoor_sources()
    print(f"outdoor weather: {ok}/{total} successful")
