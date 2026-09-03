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
    (
        "v1_18_energy_and_detected_climate_events",
        ROOT / "SQL" / "migrations" / "018_home_automation_v1.17_to_v1.18.sql",
    ),
    (
        "v1_19_scheduled_climate_runs",
        ROOT / "SQL" / "migrations" / "019_home_automation_v1.18_to_v1.19.sql",
    ),
    (
        "v1_20_device_registry",
        ROOT / "SQL" / "migrations" / "020_home_automation_v1.19_to_v1.20.sql",
    ),
    (
        "v1_21_device_features",
        ROOT / "SQL" / "migrations" / "021_home_automation_v1.20_to_v1.21.sql",
    ),
    (
        "v1_22_ai_analysis_experiments",
        ROOT / "SQL" / "migrations" / "022_home_automation_v1.21_to_v1.22.sql",
    ),
    (
        "v1_23_climate_fan_speed_control",
        ROOT / "SQL" / "migrations" / "023_home_automation_v1.22_to_v1.23.sql",
    ),
    (
        "v1_24_history_presets",
        ROOT / "SQL" / "migrations" / "024_home_automation_v1.23_to_v1.24.sql",
    ),
    (
        "v1_25_deterministic_reports",
        ROOT / "SQL" / "migrations" / "025_home_automation_v1.24_to_v1.25.sql",
    ),
    (
        "v1_26_programmed_climate_runs",
        ROOT / "SQL" / "migrations" / "026_home_automation_v1.25_to_v1.26.sql",
    ),
    (
        "v1_27_climate_sensor_threshold_operator",
        ROOT / "SQL" / "migrations" / "027_home_automation_v1.26_to_v1.27.sql",
    ),
    (
        "v1_28_climate_sensor_target_reached",
        ROOT / "SQL" / "migrations" / "028_home_automation_v1.27_to_v1.28.sql",
    ),
    (
        "v1_29_sensor_calibration_and_action_temperature",
        ROOT / "SQL" / "migrations" / "029_home_automation_v1.28_to_v1.29.sql",
    ),
    (
        "v1_30_poll_attempt_origin",
        ROOT / "SQL" / "migrations" / "030_home_automation_v1.29_to_v1.30.sql",
    ),
    (
        "v1_31_linux_system_metrics",
        ROOT / "SQL" / "migrations" / "031_home_automation_v1.30_to_v1.31.sql",
    ),
    (
        "v1_32_zigbee2mqtt_discovery",
        ROOT / "SQL" / "migrations" / "032_home_automation_v1.31_to_v1.32.sql",
    ),
    (
        "v1_33_zigbee_outdoor_temperature",
        ROOT / "SQL" / "migrations" / "033_home_automation_v1.32_to_v1.33.sql",
    ),
    (
        "v1_34_energy_billing",
        ROOT / "SQL" / "migrations" / "034_home_automation_v1.33_to_v1.34.sql",
    ),
    (
        "v1_35_energy_entitlement_periods",
        ROOT / "SQL" / "migrations" / "035_home_automation_v1.34_to_v1.35.sql",
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
