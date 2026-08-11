from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
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
