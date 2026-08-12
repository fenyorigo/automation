#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import os
from datetime import UTC, datetime
from pathlib import Path

import mariadb
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]


def normalize_timestamp(value: str, default_time: str) -> str:
    text = value.strip()
    if "T" not in text and " " not in text:
        text = f"{text} {default_time}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = None
        for date_format in ("%Y-%m-%d %H:%M", "%m/%d/%y %H:%M"):
            try:
                parsed = datetime.strptime(text, date_format)
                break
            except ValueError:
                continue
        if parsed is None:
            raise ValueError(f"Nem értelmezhető időpont: {value}")
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone(UTC).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="CSV óraállások importálása.")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--meter", required=True, choices=("electricity_main", "gas_main"))
    parser.add_argument("--default-time", default="09:00")
    args = parser.parse_args()

    connection = mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "home_automation"), user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"], autocommit=False,
    )
    cursor = connection.cursor()
    inserted = skipped = 0
    try:
        cursor.execute("SELECT id FROM energy_meters WHERE meter_code=?", (args.meter,))
        row = cursor.fetchone()
        if row is None:
            raise RuntimeError(f"Ismeretlen mérő: {args.meter}")
        meter_id = int(row[0])
        with args.csv_file.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("A CSV fejléc nélkül nem importálható.")
            for item in reader:
                if "recorded_at" in item:
                    timestamp_text = item["recorded_at"]
                elif "Dátum" in item:
                    timestamp_text = f"{item['Dátum']} {item.get('Idő') or args.default_time}"
                else:
                    raise ValueError("Hiányzó időpont oszlop (recorded_at vagy Dátum/Idő).")
                value_text = item.get("reading_value") or item.get("Mérőállás") or item.get("Óra állás")
                if value_text is None:
                    raise ValueError("Hiányzó óraállás oszlop.")
                recorded_at = normalize_timestamp(timestamp_text, args.default_time)
                reading_value = value_text.strip().replace(",", ".")
                cursor.execute(
                    """INSERT IGNORE INTO energy_meter_readings
                       (meter_id,recorded_at,reading_value,entry_source,note)
                       VALUES (?,?,?,'import',?)""",
                    (meter_id, recorded_at, reading_value, item.get("note") or None),
                )
                if cursor.rowcount:
                    inserted += 1
                else:
                    skipped += 1
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    print(f"Import kész: {inserted} új, {skipped} már meglévő sor.")


if __name__ == "__main__":
    main()
