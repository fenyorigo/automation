#!/usr/bin/env python3

from __future__ import annotations

import os
import re
from pathlib import Path

import mariadb
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = (
    ("baseline_v1_1", ROOT / "SQL" / "home_automation_schema_v1.0_20260807.sql"),
    ("v1_2_polling", ROOT / "SQL" / "migrations" / "002_home_automation_v1.1_to_v1.2.sql"),
    (
        "v1_3_maintenance",
        ROOT / "SQL" / "migrations" / "003_home_automation_v1.2_to_v1.3.sql",
    ),
    (
        "v1_4_event_history",
        ROOT / "SQL" / "migrations" / "004_home_automation_v1.3_to_v1.4.sql",
    ),
    (
        "v1_5_setting_requests",
        ROOT / "SQL" / "migrations" / "005_home_automation_v1.4_to_v1.5.sql",
    ),
    (
        "v1_6_schedules",
        ROOT / "SQL" / "migrations" / "006_home_automation_v1.5_to_v1.6.sql",
    ),
    (
        "v1_7_outdoor_room",
        ROOT / "SQL" / "migrations" / "007_home_automation_v1.6_to_v1.7.sql",
    ),
    (
        "v1_8_authentication",
        ROOT / "SQL" / "migrations" / "008_home_automation_v1.7_to_v1.8.sql",
    ),
    (
        "v1_9_boiler_room",
        ROOT / "SQL" / "migrations" / "009_home_automation_v1.8_to_v1.9.sql",
    ),
    (
        "v1_10_local_analytics",
        ROOT / "SQL" / "migrations" / "010_home_automation_v1.9_to_v1.10.sql",
    ),
    (
        "v1_11_outdoor_temperature_sources",
        ROOT / "SQL" / "migrations" / "011_home_automation_v1.10_to_v1.11.sql",
    ),
    (
        "v1_12_ventilation_log",
        ROOT / "SQL" / "migrations" / "012_home_automation_v1.11_to_v1.12.sql",
    ),
    (
        "v1_13_single_active_ventilation",
        ROOT / "SQL" / "migrations" / "013_home_automation_v1.12_to_v1.13.sql",
    ),
    (
        "v1_14_manual_climate_log",
        ROOT / "SQL" / "migrations" / "014_home_automation_v1.13_to_v1.14.sql",
    ),
    (
        "v1_15_climate_target_snapshot",
        ROOT / "SQL" / "migrations" / "015_home_automation_v1.14_to_v1.15.sql",
    ),
    (
        "v1_16_event_endpoint_snapshots",
        ROOT / "SQL" / "migrations" / "016_home_automation_v1.15_to_v1.16.sql",
    ),
    (
        "v1_17_climate_control_audit",
        ROOT / "SQL" / "migrations" / "017_home_automation_v1.16_to_v1.17.sql",
    ),
)


def statements(path: Path) -> list[str]:
    sql = "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    )
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def main() -> None:
    load_dotenv(ROOT / ".env")
    database_name = os.getenv("DB_NAME", "home_automation")
    if not re.fullmatch(r"[A-Za-z0-9_]+", database_name):
        raise ValueError("DB_NAME contains unsupported characters")

    connection = mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        autocommit=False,
    )
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.execute(f"USE `{database_name}`")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version VARCHAR(100) NOT NULL,
              applied_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
              PRIMARY KEY (version)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        connection.commit()

        for version, path in MIGRATIONS:
            cursor.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (version,))
            if cursor.fetchone() is not None:
                print(f"already applied: {version}")
                continue
            for statement in statements(path):
                cursor.execute(statement)
            cursor.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
            connection.commit()
            print(f"applied: {version}")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
