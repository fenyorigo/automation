#!/usr/bin/env python3

from __future__ import annotations

import asyncio
from functools import wraps
import os
import json
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import mariadb
from dotenv import load_dotenv
from flask import Flask, Response, abort, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from poll_devices import DEFAULT_CONFIG, load_devices
from poll_scheduler import run_cycle
from polling_lock import PollCycleBusy, polling_cycle_lock, polling_operation_active
from climate_control import ClimateControlResult, control_climate
from database_backup import create_database_export, export_directory, list_database_exports


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def dashboard_secret_key() -> str:
    configured = os.getenv("DASHBOARD_SECRET_KEY")
    if configured:
        return configured
    path = ROOT / ".dashboard-secret"
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        value = secrets.token_urlsafe(48)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(value)
            return value
        except FileExistsError:
            return path.read_text(encoding="utf-8").strip()


app = Flask(__name__)
app.secret_key = dashboard_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)
manual_poll_lock = threading.Lock()
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9._-]{3,64}")
PUBLIC_ENDPOINTS = {"static", "health", "login", "setup"}

SOURCE_LABELS = {
    "esp32": "ESP32",
    "computherm": "Computherm",
    "connectlife": "Hisense",
    "manual": "Kézi",
}

DEVICE_GROUPS = (
    ("esp32", "ESP32 hőmérők"),
    ("computherm", "Computherm termosztátok"),
    ("connectlife", "Hisense klímák"),
    ("manual", "Kézi eszközök"),
)

COMPUTHERM_LOCATION = {
    "iot-computherm-emelet": "emelet",
    "iot-computherm-foldszint": "földszint",
}

HISTORY_RANGES = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30}
WEEKDAYS = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"]
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")


def check_ollama() -> dict[str, Any]:
    url = f"{OLLAMA_BASE_URL}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=2.0) as response:
            payload = json.load(response)
        models = sorted(
            item.get("name", "") for item in payload.get("models", []) if item.get("name")
        )
        return {
            "reachable": True,
            "models": models,
            "model_available": OLLAMA_MODEL in models,
            "error": None,
        }
    except (OSError, urllib.error.URLError, ValueError, json.JSONDecodeError) as error:
        return {"reachable": False, "models": [], "model_available": False, "error": str(error)}


def find_gnuplot() -> tuple[str | None, str | None]:
    configured = os.getenv("GNUPLOT_BIN")
    candidate = configured or shutil.which("gnuplot")
    if candidate is None and Path("/opt/homebrew/bin/gnuplot").is_file():
        candidate = "/opt/homebrew/bin/gnuplot"
    if candidate is None:
        return None, "A gnuplot nem található."
    try:
        result = subprocess.run(
            [candidate, "--version"], capture_output=True, text=True, timeout=3, check=True
        )
    except (OSError, subprocess.SubprocessError) as error:
        return None, f"A gnuplot nem indítható: {error}"
    if not result.stdout.startswith("gnuplot 6."):
        return None, f"Nem támogatott gnuplot verzió: {result.stdout.strip()}"
    return candidate, None


GNUPLOT_BIN, GNUPLOT_ERROR = find_gnuplot()


def connect_database() -> mariadb.Connection:
    return mariadb.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "home_automation"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        autocommit=False,
    )


def rows_as_dicts(cursor: mariadb.Cursor) -> list[dict[str, Any]]:
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def user_count() -> int:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM app_users")
        return int(cursor.fetchone()[0])
    finally:
        cursor.close()
        connection.close()


def load_user(user_id: int) -> dict[str, Any] | None:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT id,username,role,is_active,last_login_at,created_at
               FROM app_users WHERE id=?""",
            (user_id,),
        )
        rows = rows_as_dicts(cursor)
        return rows[0] if rows else None
    finally:
        cursor.close()
        connection.close()


def valid_username(value: str) -> bool:
    return USERNAME_PATTERN.fullmatch(value) is not None


def valid_password(value: str) -> bool:
    return len(value) >= 10


def safe_next_url(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return url_for("dashboard")


@app.before_request
def authenticate_request():
    endpoint = request.endpoint
    if endpoint in PUBLIC_ENDPOINTS:
        return None
    user_id = session.get("user_id")
    if user_id is None:
        target = request.full_path.rstrip("?") if request.method == "GET" else None
        return redirect(url_for("login", next=target))
    user = load_user(int(user_id))
    if user is None or not user["is_active"]:
        session.clear()
        return redirect(url_for("login"))
    g.current_user = user
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if endpoint != "logout" and user["role"] != "editor":
            abort(403)
    return None


@app.context_processor
def authentication_context() -> dict[str, Any]:
    user = getattr(g, "current_user", None)
    return {"current_user": user, "can_write": bool(user and user["role"] == "editor")}


def editor_required(function):
    @wraps(function)
    def decorated(*args, **kwargs):
        if g.current_user["role"] != "editor":
            abort(403)
        return function(*args, **kwargs)
    return decorated


def load_history_devices() -> list[dict[str, Any]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT DISTINCT d.id, d.name, d.source_system
            FROM devices d
            JOIN sensors s ON s.device_id = d.id AND s.is_active = 1
            WHERE d.is_active = 1 AND s.sensor_type = 'temperature'
            ORDER BY FIELD(d.source_system, 'esp32', 'computherm', 'connectlife'), d.name
            """
        )
        return rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()


def load_resettable_sensors() -> list[dict[str, Any]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT s.id, s.name, d.name AS device_name, d.hostname,
                   COUNT(sr.id) AS reading_count,
                   MIN(sr.observed_at) AS first_reading_at,
                   MAX(sr.observed_at) AS last_reading_at
            FROM sensors s
            JOIN devices d ON d.id = s.device_id
            LEFT JOIN sensor_readings sr ON sr.sensor_id = s.id
            WHERE s.is_active = 1 AND d.is_active = 1
              AND s.sensor_type = 'temperature'
            GROUP BY s.id, s.name, d.name, d.hostname
            ORDER BY FIELD(d.source_system, 'esp32', 'computherm', 'connectlife'), d.name, s.name
            """
        )
        return rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()


def load_analysis_overview() -> dict[str, Any]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT analysis_date,pipeline_version,status,started_at,completed_at,error_message
               FROM analysis_runs ORDER BY analysis_date DESC,id DESC LIMIT 10"""
        )
        runs = rows_as_dicts(cursor)
        cursor.execute(
            """SELECT a.anomaly_type,a.severity,a.window_started_at,a.window_ended_at,
                      a.localized_z_score,a.status,d.name AS device_name,r.name AS room_name
               FROM anomaly_events a
               LEFT JOIN devices d ON d.id=a.device_id
               LEFT JOIN rooms r ON r.id=a.room_id
               ORDER BY a.window_started_at DESC,a.id DESC LIMIT 20"""
        )
        anomalies = rows_as_dicts(cursor)
        cursor.execute(
            """SELECT summary_date,provider,model,prompt_version,summary_text,
                      validation_status,generation_ms,created_at
               FROM daily_ai_summaries ORDER BY summary_date DESC,id DESC LIMIT 10"""
        )
        summaries = rows_as_dicts(cursor)
        return {"runs": runs, "anomalies": anomalies, "summaries": summaries}
    finally:
        cursor.close()
        connection.close()


def load_temperature_history(device_id: int, hours: int) -> list[tuple[datetime, float]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT sr.observed_at, sr.value
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            WHERE s.device_id = ? AND s.sensor_type = 'temperature'
              AND sr.quality IN ('good', 'valid') AND sr.value IS NOT NULL
              AND sr.observed_at >= UTC_TIMESTAMP(3) - INTERVAL ? HOUR
            ORDER BY sr.observed_at
            """,
            (device_id, hours),
        )
        return [(row[0], float(row[1])) for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()


def load_control_devices() -> list[dict[str, Any]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT d.id, d.name, d.source_system,
              sr.value AS measured_temperature_c,
              ds.power, ds.mode, ds.target_temperature_c, ds.fan_speed,
              ds.fan_mute, ds.sleep, ds.super, ds.swing_up_down,
              req.id AS request_id, req.requested_settings, req.requested_at
            FROM devices d
            LEFT JOIN sensors s ON s.device_id=d.id AND s.is_active=1
            LEFT JOIN sensor_readings sr ON sr.id=(
              SELECT x.id FROM sensor_readings x WHERE x.sensor_id=s.id
              ORDER BY x.observed_at DESC,x.id DESC LIMIT 1)
            LEFT JOIN device_states ds ON ds.id=(
              SELECT x.id FROM device_states x WHERE x.device_id=d.id
              ORDER BY x.observed_at DESC,x.id DESC LIMIT 1)
            LEFT JOIN device_setting_requests req ON req.id=(
              SELECT x.id FROM device_setting_requests x
              WHERE x.device_id=d.id AND x.status='pending'
              ORDER BY x.requested_at DESC,x.id DESC LIMIT 1)
            WHERE d.is_active=1 AND d.source_system IN ('connectlife','computherm')
            ORDER BY FIELD(d.source_system,'computherm','connectlife'),d.name
            """
        )
        devices = rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()
    for device in devices:
        raw = device.pop("requested_settings", None)
        device["requested"] = json.loads(raw) if raw else None
        device["source_label"] = SOURCE_LABELS[device["source_system"]]
    return devices


def load_schedule_context(device_id: int | None = None, profile_id: int | None = None) -> dict[str, Any]:
    devices = load_control_devices()
    device = next((item for item in devices if item["id"] == device_id), devices[0] if devices else None)
    if device is None:
        return {"devices": [], "device": None}
    connection = connect_database(); cursor = connection.cursor()
    try:
        cursor.execute("SELECT id,profile_key,name,version FROM schedule_profiles WHERE device_id=? ORDER BY FIELD(profile_key,'workday1','workday2','workday3','holiday')", (device["id"],))
        profiles = rows_as_dicts(cursor)
        profile = next((item for item in profiles if item["id"] == profile_id), profiles[0])
        cursor.execute("SELECT slot_no,start_time,end_time,requested_settings FROM schedule_windows WHERE profile_id=? ORDER BY start_time", (profile["id"],))
        windows = rows_as_dicts(cursor)
        for window in windows:
            window["settings"] = json.loads(window.pop("requested_settings"))
            window["start_text"] = str(window["start_time"])[:5]
            window["end_text"] = str(window["end_time"])[:5]
        cursor.execute("SELECT weekday,profile_id FROM device_weekly_profile_assignments WHERE device_id=?", (device["id"],))
        weekly = {int(row[0]): int(row[1]) for row in cursor.fetchall()}
        cursor.execute("""SELECT a.assignment_date,a.profile_id,a.note,p.name FROM device_date_profile_assignments a JOIN schedule_profiles p ON p.id=a.profile_id WHERE a.device_id=? AND a.assignment_date>=CURRENT_DATE ORDER BY a.assignment_date LIMIT 30""", (device["id"],))
        overrides = rows_as_dicts(cursor)
    finally:
        cursor.close(); connection.close()
    return {"devices": devices, "device": device, "profiles": profiles, "profile": profile, "windows": windows, "slots": {w["slot_no"]: w for w in windows}, "weekly": weekly, "overrides": overrides}


def parse_window_settings(source: str, slot: int) -> dict[str, Any]:
    prefix = f"slot_{slot}_"
    temperature = float(request.form[prefix + "temperature_c"])
    common = {"power": request.form.get(prefix + "power") == "1", "temperature_c": temperature}
    if source == "connectlife":
        mode = request.form.get(prefix + "mode", "auto")
        fan = request.form.get(prefix + "fan_speed", "auto")
        if not 16 <= temperature <= 30 or mode not in {"cool","heat","dry","fan","auto"} or fan not in {"auto","low","mid_low","mid","mid_high","high"}:
            raise ValueError
        return {**common, "mode": mode, "fan_speed": fan,
                "swing": request.form.get(prefix+"swing")=="1",
                "fast_cool": request.form.get(prefix+"fast_cool")=="1",
                "quiet": request.form.get(prefix+"quiet")=="1"}
    mode = request.form.get(prefix + "control_mode", "manual")
    if not 5 <= temperature <= 22 or mode not in {"manual","auto"}:
        raise ValueError
    return {**common, "control_mode": mode}


def resolve_daily_plan(device_id: int, plan_date: date, persist: bool = True) -> dict[str, Any]:
    connection = connect_database(); cursor = connection.cursor()
    try:
        cursor.execute("""SELECT p.id,p.name,p.version,'date_override' source FROM device_date_profile_assignments a JOIN schedule_profiles p ON p.id=a.profile_id WHERE a.device_id=? AND a.assignment_date=?""", (device_id, plan_date))
        row = cursor.fetchone()
        if row is None:
            cursor.execute("""SELECT p.id,p.name,p.version,'weekly' source FROM device_weekly_profile_assignments a JOIN schedule_profiles p ON p.id=a.profile_id WHERE a.device_id=? AND a.weekday=?""", (device_id, plan_date.weekday()))
            row = cursor.fetchone()
        if row is None:
            raise RuntimeError("Nincs napi profil-hozzárendelés")
        profile_id, profile_name, profile_version, source = row
        cursor.execute("SELECT start_time,end_time,requested_settings FROM schedule_windows WHERE profile_id=? ORDER BY start_time", (profile_id,))
        intervals: list[dict[str, Any]] = []; position = "00:00"
        for start, end, raw in cursor.fetchall():
            start_text, end_text = str(start)[:5], str(end)[:5]
            if position < start_text:
                intervals.append({"from": position, "to": start_text, "settings": {"power": False}})
            intervals.append({"from": start_text, "to": end_text, "settings": json.loads(raw)})
            position = end_text
        if position < "24:00":
            intervals.append({"from": position, "to": "24:00", "settings": {"power": False}})
        snapshot = {"date": plan_date.isoformat(), "profile": profile_name, "intervals": intervals}
        encoded = json.dumps(snapshot, ensure_ascii=False, separators=(",",":"), sort_keys=True)
        cursor.execute("SELECT version,plan_snapshot FROM resolved_daily_plans WHERE device_id=? AND plan_date=? ORDER BY version DESC LIMIT 1", (device_id, plan_date))
        previous = cursor.fetchone()
        version = int(previous[0]) if previous else 0
        changed = previous is None or json.dumps(
            json.loads(previous[1]), ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ) != encoded
        if persist and changed:
            version += 1
            cursor.execute("""INSERT INTO resolved_daily_plans (device_id,plan_date,version,profile_id,profile_version,assignment_source,plan_snapshot) VALUES (?,?,?,?,?,?,?)""", (device_id,plan_date,version,profile_id,profile_version,source,encoded))
            connection.commit()
        return {**snapshot, "version": version, "source": source}
    finally:
        cursor.close(); connection.close()


def load_locations() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute("""SELECT r.id,r.name,z.name zone_name FROM rooms r LEFT JOIN zones z ON z.id=r.zone_id ORDER BY FIELD(z.name,'Emelet','Földszint'),z.name,r.name""")
        rooms=rows_as_dicts(cursor)
        cursor.execute("""SELECT d.id,d.name,d.source_system,d.room_id,r.name room_name,z.name zone_name,(d.source_system IN ('esp32','computherm')) movable FROM devices d LEFT JOIN rooms r ON r.id=d.room_id LEFT JOIN zones z ON z.id=r.zone_id WHERE d.is_active=1 ORDER BY FIELD(d.source_system,'esp32','computherm','connectlife','manual'),d.name""")
        devices=rows_as_dicts(cursor)
    finally: cursor.close(); connection.close()
    return rooms,devices


def gnuplot_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render_temperature_svg(points: list[tuple[datetime, float]], title: str) -> bytes:
    if GNUPLOT_BIN is None:
        raise RuntimeError(GNUPLOT_ERROR or "A gnuplot nem érhető el.")
    with tempfile.TemporaryDirectory(prefix="automation-chart-") as temporary:
        directory = Path(temporary)
        data_path = directory / "temperature.dat"
        output_path = directory / "temperature.svg"
        script_path = directory / "chart.gnuplot"
        data_path.write_text(
            "".join(
                f"{int(moment.replace(tzinfo=UTC).timestamp())} {value:.4f}\n"
                for moment, value in points
            ),
            encoding="utf-8",
        )
        script_path.write_text(
            "\n".join(
                [
                    'set terminal svg size 1100,440 dynamic enhanced font "Arial,12"',
                    f'set output "{gnuplot_quote(str(output_path))}"',
                    'set encoding utf8',
                    f'set title "{gnuplot_quote(title)}" textcolor rgb "#14251f"',
                    'set xdata time',
                    'set timefmt "%s"',
                    'set format x "%m.%d\\n%H:%M" timedate',
                    'set ylabel "Hőmérséklet (°C)"',
                    'set grid xtics ytics lc rgb "#dcd9ce"',
                    'set border lc rgb "#60706a"',
                    'set tics textcolor rgb "#60706a"',
                    'set key off',
                    'set margins 11,3,5,4',
                    f'plot "{gnuplot_quote(str(data_path))}" using 1:2 with lines lw 3 lc rgb "#17765b"',
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [GNUPLOT_BIN, str(script_path)], capture_output=True, timeout=10, check=True
        )
        return output_path.read_bytes()


def load_dashboard() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
              d.id, d.name, d.hostname, d.source_system, d.device_type,
              d.room_id, r.name AS room_name, z.name AS zone_name,
              d.managed_manually, d.manual_power_state,
              d.last_service_date, d.next_service_due,
              (SELECT mse.changed_at FROM manual_state_events mse
               WHERE mse.device_id = d.id
               ORDER BY mse.changed_at DESC, mse.id DESC LIMIT 1) AS manual_state_changed_at,
              sr.value AS temperature_c, sr.quality AS measurement_quality,
              sr.observed_at AS measurement_at,
              ds.power, ds.mode, ds.target_temperature_c, ds.fan_speed,
              ds.online AS reported_online, ds.active, ds.observed_at AS state_at,
              pa.success AS poll_success, pa.attempted_at AS last_poll_at,
              pa.duration_ms, pa.error_code, pa.error_message
            FROM devices d
            LEFT JOIN rooms r ON r.id = d.room_id
            LEFT JOIN zones z ON z.id = r.zone_id
            LEFT JOIN sensors s
              ON s.device_id = d.id AND s.is_active = 1
            LEFT JOIN sensor_readings sr
              ON sr.id = (
                SELECT sr2.id FROM sensor_readings sr2
                WHERE sr2.sensor_id = s.id
                ORDER BY sr2.observed_at DESC, sr2.id DESC LIMIT 1
              )
            LEFT JOIN device_states ds
              ON ds.id = (
                SELECT ds2.id FROM device_states ds2
                WHERE ds2.device_id = d.id
                ORDER BY ds2.observed_at DESC, ds2.id DESC LIMIT 1
              )
            LEFT JOIN poll_attempts pa
              ON pa.id = (
                SELECT pa2.id FROM poll_attempts pa2
                WHERE pa2.device_id = d.id
                ORDER BY pa2.attempted_at DESC, pa2.id DESC LIMIT 1
              )
            WHERE d.is_active = 1
            ORDER BY FIELD(d.source_system, 'esp32', 'manual', 'computherm', 'connectlife'), d.name
            """
        )
        devices = rows_as_dicts(cursor)

        cursor.execute(
            """
            SELECT pa.attempted_at, pa.completed_at, pa.duration_ms, pa.success,
                   pa.error_code, pa.error_message, d.name, d.hostname,
                   pa.source_system
            FROM poll_attempts pa
            LEFT JOIN devices d ON d.id = pa.device_id
            ORDER BY pa.attempted_at DESC, pa.id DESC
            LIMIT 40
            """
        )
        attempts = rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()

    for device in devices:
        device["source_label"] = SOURCE_LABELS.get(
            device["source_system"], device["source_system"]
        )
        device["online"] = (
            None if device["managed_manually"] else bool(device["poll_success"])
        )

    computherm_targets = [
        item
        for item in devices
        if item["source_system"] == "computherm"
        and item["poll_success"]
        and item["target_temperature_c"] is not None
    ]
    if computherm_targets:
        minimum = min(float(item["target_temperature_c"]) for item in computherm_targets)
        locations = [
            COMPUTHERM_LOCATION.get(item["hostname"], item["name"])
            for item in computherm_targets
            if float(item["target_temperature_c"]) == minimum
        ]
        for device in devices:
            if device["source_system"] == "manual" and device["device_type"] == "boiler":
                device["derived_target_temperature_c"] = minimum
                device["derived_target_source"] = " és ".join(locations)
    return devices, attempts


def load_room_groups(
    devices: list[dict[str, Any]],
    outdoor_temperature: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT r.id AS room_id,r.name AS room_name,z.id AS zone_id,z.name AS zone_name
               FROM rooms r LEFT JOIN zones z ON z.id=r.zone_id
               ORDER BY FIELD(z.name,'Emelet','Földszint'),z.name,r.name"""
        )
        rooms = rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()

    groups: list[dict[str, Any]] = []
    by_zone: dict[str, dict[str, Any]] = {}
    for room in rooms:
        zone_name = room["zone_name"] or "Zónán kívül"
        group = by_zone.get(zone_name)
        if group is None:
            group = {"name": zone_name, "rooms": []}
            by_zone[zone_name] = group
            groups.append(group)
        room["devices"] = [item for item in devices if item["room_id"] == room["room_id"]]
        room["outdoor_temperature"] = (
            outdoor_temperature if room["room_name"] == "Kültéri" else None
        )
        group["rooms"].append(room)

    unassigned = [item for item in devices if item["room_id"] is None]
    if unassigned:
        group = by_zone.get("Zónán kívül")
        if group is None:
            group = {"name": "Zónán kívül", "rooms": []}
            groups.append(group)
        group["rooms"].append(
            {"room_id": None, "room_name": "Nincs hozzárendelve", "devices": unassigned}
        )
    return groups


def load_device_groups(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = [
        {
            "source_system": source_system,
            "name": name,
            "devices": [
                device for device in devices if device["source_system"] == source_system
            ],
        }
        for source_system, name in DEVICE_GROUPS
    ]
    known_sources = {source_system for source_system, _ in DEVICE_GROUPS}
    other_devices = [
        device for device in devices if device["source_system"] not in known_sources
    ]
    if other_devices:
        groups.append({"source_system": "other", "name": "Egyéb eszközök", "devices": other_devices})
    return [group for group in groups if group["devices"]]


def load_outdoor_sources() -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT s.id,s.source_code,s.display_name,s.source_type,s.is_active,
                      s.priority,s.max_age_minutes,s.configuration,s.updated_at,
                      o.temperature_c,o.observed_at,o.fetched_at,
                      a.success AS last_poll_success,a.attempted_at AS last_poll_at,
                      a.error_code AS last_error_code,a.error_message AS last_error_message
               FROM outdoor_temperature_sources s
               LEFT JOIN outdoor_temperature_observations o ON o.id=(
                 SELECT o2.id FROM outdoor_temperature_observations o2
                 WHERE o2.source_id=s.id ORDER BY o2.observed_at DESC,o2.id DESC LIMIT 1
               )
               LEFT JOIN outdoor_temperature_poll_attempts a ON a.id=(
                 SELECT a2.id FROM outdoor_temperature_poll_attempts a2
                 WHERE a2.source_id=s.id ORDER BY a2.attempted_at DESC,a2.id DESC LIMIT 1
               )
               ORDER BY s.priority"""
        )
        sources = rows_as_dicts(cursor)
        cursor.execute(
            """SELECT s.id,s.source_code,s.display_name,o.temperature_c,o.observed_at,o.fetched_at
               FROM outdoor_temperature_sources s
               JOIN outdoor_temperature_observations o ON o.id=(
                 SELECT o2.id FROM outdoor_temperature_observations o2
                 WHERE o2.source_id=s.id ORDER BY o2.observed_at DESC,o2.id DESC LIMIT 1
               )
               WHERE s.is_active=1
                 AND o.observed_at >= UTC_TIMESTAMP(3) - INTERVAL s.max_age_minutes MINUTE
               ORDER BY s.priority LIMIT 1"""
        )
        selected_rows = rows_as_dicts(cursor)
        return sources, selected_rows[0] if selected_rows else None
    finally:
        cursor.close()
        connection.close()


def load_ventilation_log() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id,name FROM rooms ORDER BY name")
        rooms = rows_as_dicts(cursor)
        cursor.execute(
            """SELECT id,source_code,display_name FROM outdoor_temperature_sources
               ORDER BY priority,display_name"""
        )
        sources = rows_as_dicts(cursor)
        cursor.execute(
            """SELECT v.id,v.room_id,r.name AS room_name,v.started_at,v.ended_at,
                      v.started_outdoor_temperature_c,
                      ss.display_name AS started_source_name,
                      v.ended_outdoor_temperature_c,
                      es.display_name AS ended_source_name,v.note,
                      u.username AS created_by_name
               FROM ventilation_events v
               JOIN rooms r ON r.id=v.room_id
               LEFT JOIN outdoor_temperature_sources ss ON ss.id=v.started_outdoor_source_id
               LEFT JOIN outdoor_temperature_sources es ON es.id=v.ended_outdoor_source_id
               JOIN app_users u ON u.id=v.created_by
               ORDER BY v.started_at DESC,v.id DESC LIMIT 100"""
        )
        return rooms, sources, rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()


def load_climate_operation_log() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT d.id,d.name,r.name AS room_name,d.source_puid,
                      s.power,s.target_temperature_c,s.observed_at AS state_observed_at
               FROM devices d JOIN rooms r ON r.id=d.room_id
               LEFT JOIN device_states s ON s.id=(
                 SELECT s2.id FROM device_states s2 WHERE s2.device_id=d.id
                 ORDER BY s2.observed_at DESC,s2.id DESC LIMIT 1
               )
               WHERE d.is_active=1 AND d.source_system='connectlife'
               ORDER BY r.name,d.name"""
        )
        devices = rows_as_dicts(cursor)
        cursor.execute(
            """SELECT e.id,e.device_id,d.name AS device_name,r.name AS room_name,
                      e.started_at,e.ended_at,e.started_target_temperature_c,
                      e.ended_target_temperature_c,e.note,e.event_origin,
                      COALESCE(u.username,'Automatikus észlelés') AS created_by_name
               FROM climate_operation_events e
               JOIN devices d ON d.id=e.device_id
               JOIN rooms r ON r.id=e.room_id
               LEFT JOIN app_users u ON u.id=e.created_by
               ORDER BY e.started_at DESC,e.id DESC LIMIT 100"""
        )
        events = rows_as_dicts(cursor)
        cursor.execute(
            """SELECT a.requested_at,a.completed_at,a.requested_power,
                      a.requested_temperature_c,a.status,a.error_message,
                      d.name AS device_name,u.username
               FROM climate_control_attempts a
               JOIN devices d ON d.id=a.device_id
               JOIN app_users u ON u.id=a.requested_by
               ORDER BY a.requested_at DESC,a.id DESC LIMIT 30"""
        )
        return devices, events, rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()


def parse_local_datetime(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def load_energy_readings() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT m.id,m.meter_code,m.display_name,m.energy_type,m.unit,
                      r.reading_value,r.recorded_at
               FROM energy_meters m
               LEFT JOIN energy_meter_readings r ON r.id=(
                 SELECT r2.id FROM energy_meter_readings r2 WHERE r2.meter_id=m.id
                 ORDER BY r2.recorded_at DESC,r2.id DESC LIMIT 1
               )
               WHERE m.is_active=1 ORDER BY FIELD(m.energy_type,'electricity','gas')"""
        )
        meters = rows_as_dicts(cursor)
        cursor.execute(
            """SELECT r.id,r.recorded_at,r.reading_value,r.entry_source,r.note,
                      m.display_name,m.energy_type,m.unit,
                      u.username AS recorded_by_name,
                      r.reading_value-LAG(r.reading_value) OVER
                        (PARTITION BY r.meter_id ORDER BY r.recorded_at,r.id) AS consumption
               FROM energy_meter_readings r
               JOIN energy_meters m ON m.id=r.meter_id
               LEFT JOIN app_users u ON u.id=r.recorded_by
               ORDER BY r.recorded_at DESC,r.id DESC LIMIT 200"""
        )
        return meters, rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()


def csrf_token() -> str:
    token = session.get("csrf_token")
    if token is None:
        token = secrets.token_urlsafe(24)
        session["csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


@app.template_filter("temperature")
def format_temperature(value: Any) -> str:
    if value is None:
        return "—"
    number = float(value)
    return f"{number:.1f}".replace(".", ",")


@app.template_filter("local_time")
def format_local_time(value: datetime | None) -> str:
    if value is None:
        return "nincs adat"
    utc_value = value.replace(tzinfo=UTC)
    return utc_value.astimezone().strftime("%Y. %m. %d. %H:%M:%S")


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if user_count() > 0:
        return redirect(url_for("login"))
    if request.remote_addr not in {"127.0.0.1", "::1"}:
        return render_template("setup.html", local_only=True, error=None), 403
    error = None
    if request.method == "POST":
        validate_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not valid_username(username):
            error = "A felhasználónév 3–64 karakter legyen; betű, szám, pont, kötőjel és aláhúzás használható."
        elif not valid_password(password):
            error = "A jelszó legalább 10 karakter hosszú legyen."
        elif password != request.form.get("password_confirm", ""):
            error = "A két jelszó nem egyezik."
        else:
            connection = connect_database()
            cursor = connection.cursor()
            try:
                cursor.execute(
                    """INSERT INTO app_users (username,password_hash,role,is_active)
                       VALUES (?,?,'editor',1)""",
                    (username, generate_password_hash(password)),
                )
                user_id = int(cursor.lastrowid)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()
                connection.close()
            session.clear()
            session.permanent = True
            session["user_id"] = user_id
            return redirect(url_for("dashboard"))
    return render_template("setup.html", local_only=False, error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if user_count() == 0:
        return redirect(url_for("setup"))
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        validate_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        connection = connect_database()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT id,password_hash,role FROM app_users WHERE username=? AND is_active=1",
                (username,),
            )
            row = cursor.fetchone()
            if row is not None and check_password_hash(row[1], password):
                cursor.execute(
                    "UPDATE app_users SET last_login_at=CURRENT_TIMESTAMP(3) WHERE id=?",
                    (row[0],),
                )
                connection.commit()
                session.clear()
                session.permanent = True
                session["user_id"] = int(row[0])
                try:
                    successful, stored, total = asyncio.run(
                        run_cycle(float(os.getenv("POLL_TIMEOUT_SECONDS", "5")))
                    )
                    session["poll_notice"] = {
                        "kind": "success",
                        "message": (
                            f"Bejelentkezési lekérdezés kész: {successful}/{total} sikeres, "
                            f"{stored}/{total} mentve."
                        ),
                    }
                except PollCycleBusy:
                    session["poll_notice"] = {
                        "kind": "warning",
                        "message": "Bejelentkezéskor már futott egy lekérdezési kör; annak eredményét használjuk.",
                    }
                except Exception:
                    app.logger.exception("Login polling failed")
                    session["poll_notice"] = {
                        "kind": "warning",
                        "message": "A bejelentkezés sikerült, de az azonnali lekérdezés nem futott le.",
                    }
                return redirect(safe_next_url(request.form.get("next")))
        finally:
            cursor.close()
            connection.close()
        error = "Hibás felhasználónév vagy jelszó."
    return render_template("login.html", error=error, next_url=safe_next_url(request.args.get("next")))


@app.post("/logout")
def logout():
    validate_csrf()
    session.clear()
    return redirect(url_for("login"))


def load_users() -> list[dict[str, Any]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT id,username,role,is_active,last_login_at,created_at
               FROM app_users ORDER BY username"""
        )
        return rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()


@app.get("/users")
@editor_required
def users():
    return render_template(
        "users.html", users=load_users(), user_notice=session.pop("user_notice", None)
    )


@app.post("/users")
def create_user():
    validate_csrf()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role")
    if not valid_username(username) or not valid_password(password) or role not in {"viewer", "editor"}:
        abort(400)
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """INSERT INTO app_users (username,password_hash,role,is_active)
               VALUES (?,?,?,1)""",
            (username, generate_password_hash(password), role),
        )
        connection.commit()
        session["user_notice"] = {"kind": "success", "message": f"{username} létrehozva."}
    except mariadb.IntegrityError:
        connection.rollback()
        session["user_notice"] = {"kind": "error", "message": "Ez a felhasználónév már létezik."}
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for("users"))


@app.post("/users/<int:user_id>")
def update_user(user_id: int):
    validate_csrf()
    role = request.form.get("role")
    is_active = request.form.get("is_active") == "1"
    password = request.form.get("password", "")
    if role not in {"viewer", "editor"} or (password and not valid_password(password)):
        abort(400)
    if user_id == g.current_user["id"] and (role != "editor" or not is_active):
        session["user_notice"] = {
            "kind": "warning", "message": "A saját szerkesztői hozzáférésed nem kapcsolható ki."
        }
        return redirect(url_for("users"))
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT role,is_active,username FROM app_users WHERE id=? FOR UPDATE", (user_id,))
        row = cursor.fetchone()
        if row is None:
            abort(404)
        if row[0] == "editor" and row[1] and (role != "editor" or not is_active):
            cursor.execute("SELECT COUNT(*) FROM app_users WHERE role='editor' AND is_active=1")
            if int(cursor.fetchone()[0]) <= 1:
                session["user_notice"] = {
                    "kind": "warning", "message": "Az utolsó aktív szerkesztő nem kapcsolható ki."
                }
                connection.rollback()
                return redirect(url_for("users"))
        if password:
            cursor.execute(
                "UPDATE app_users SET role=?,is_active=?,password_hash=? WHERE id=?",
                (role, int(is_active), generate_password_hash(password), user_id),
            )
        else:
            cursor.execute(
                "UPDATE app_users SET role=?,is_active=? WHERE id=?",
                (role, int(is_active), user_id),
            )
        connection.commit()
        session["user_notice"] = {"kind": "success", "message": f"{row[2]} módosítva."}
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for("users"))


@app.get("/")
def dashboard() -> str:
    devices, attempts = load_dashboard()
    _, outdoor_temperature = load_outdoor_sources()
    requested_view = request.args.get("view")
    if requested_view in {"device", "room"}:
        session["dashboard_view"] = requested_view
    view_mode = session.get("dashboard_view", "device")
    successful = sum(1 for item in devices if item["online"])
    monitored_count = sum(1 for item in devices if not item["managed_manually"])
    latest_poll = max(
        (item["last_poll_at"] for item in devices if item["last_poll_at"]),
        default=None,
    )
    return render_template(
        "dashboard.html",
        devices=devices,
        attempts=attempts,
        successful=successful,
        monitored_count=monitored_count,
        latest_poll=latest_poll,
        poll_marker=latest_poll.isoformat(timespec="milliseconds") if latest_poll else None,
        poll_notice=session.pop("poll_notice", None),
        view_mode=view_mode,
        device_groups=load_device_groups(devices),
        room_groups=load_room_groups(devices, outdoor_temperature),
    )


@app.get("/poll-status")
def poll_status():
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT MAX(completed_at) FROM poll_attempts")
        latest_poll = cursor.fetchone()[0]
    finally:
        cursor.close()
        connection.close()
    response = jsonify({
        "busy": polling_operation_active(),
        "latest_poll": latest_poll.isoformat(timespec="milliseconds") if latest_poll else None,
    })
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/energy")
def energy() -> str:
    meters, readings = load_energy_readings()
    return render_template(
        "energy.html", meters=meters, readings=readings,
        now_local=datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M"),
        notice=session.pop("energy_notice", None),
    )


@app.get("/backups")
@editor_required
def backups() -> str:
    return render_template(
        "backups.html", exports=list_database_exports(),
        notice=session.pop("backup_notice", None),
    )


@app.post("/backups")
@editor_required
def create_backup():
    validate_csrf()
    try:
        path = create_database_export()
        session["backup_notice"] = {
            "kind": "success", "message": f"Az adatbázismentés elkészült: {path.name}"
        }
    except Exception as error:
        app.logger.exception("Database export failed")
        session["backup_notice"] = {"kind": "error", "message": str(error)}
    return redirect(url_for("backups"))


@app.get("/backups/<path:filename>")
@editor_required
def download_backup(filename: str):
    if not re.fullmatch(r"home_automation_[0-9]{8}T[0-9]{6}Z\.sql\.gz", filename):
        abort(404)
    return send_from_directory(export_directory(), filename, as_attachment=True)


@app.post("/energy/readings")
def create_energy_reading():
    validate_csrf()
    try:
        meter_id = int(request.form["meter_id"])
        recorded_at = parse_local_datetime(request.form["recorded_at"])
        reading_value = Decimal(request.form["reading_value"].replace(",", "."))
        if reading_value < 0:
            raise ValueError
    except (KeyError, TypeError, ValueError, InvalidOperation):
        abort(400)
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT 1 FROM energy_meters WHERE id=? AND is_active=1", (meter_id,))
        if cursor.fetchone() is None:
            abort(400)
        cursor.execute(
            """INSERT INTO energy_meter_readings
               (meter_id,recorded_at,reading_value,entry_source,recorded_by,note)
               VALUES (?,?,?,'manual',?,?)""",
            (meter_id, recorded_at, reading_value, g.current_user["id"],
             request.form.get("note", "").strip() or None),
        )
        connection.commit()
    except mariadb.IntegrityError:
        connection.rollback()
        session["energy_notice"] = {
            "kind": "warning", "message": "Ehhez a mérőhöz erre az időpontra már van óraállás."
        }
        return redirect(url_for("energy"))
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    session["energy_notice"] = {"kind": "success", "message": "Az óraállást rögzítettük."}
    return redirect(url_for("energy"))


@app.post("/poll-now")
def poll_now():
    validate_csrf()
    if not manual_poll_lock.acquire(blocking=False):
        session["poll_notice"] = {
            "kind": "warning",
            "message": "Már folyamatban van egy kézi lekérdezés.",
        }
        return redirect(url_for("dashboard"))
    try:
        timeout = float(os.getenv("POLL_TIMEOUT_SECONDS", "5"))
        successful, stored, monitored_count = asyncio.run(run_cycle(timeout))
        kind = "success" if successful == monitored_count and stored == monitored_count else "warning"
        session["poll_notice"] = {
            "kind": kind,
            "message": (
                f"Kézi lekérdezés kész: {successful}/{monitored_count} sikeres, "
                f"{stored}/{monitored_count} adatbázisba mentve."
            ),
        }
    except PollCycleBusy:
        session["poll_notice"] = {
            "kind": "warning",
            "message": "Már folyamatban van egy automatikus vagy kézi lekérdezés.",
        }
    except Exception as error:
        app.logger.exception("Manual polling failed")
        session["poll_notice"] = {
            "kind": "error",
            "message": f"A kézi lekérdezés sikertelen: {error}",
        }
    finally:
        manual_poll_lock.release()
    return redirect(url_for("dashboard"))


@app.get("/history")
def history() -> str:
    devices = load_history_devices()
    resettable_sensors = load_resettable_sensors()
    history_notice = session.pop("history_notice", None)
    if not devices:
        return render_template(
            "history.html", devices=[], selected=None, range_key="24h", points=[],
            gnuplot_error=GNUPLOT_ERROR, resettable_sensors=resettable_sensors,
            history_notice=history_notice,
        )
    requested_id = request.args.get("device", type=int)
    selected = next((item for item in devices if item["id"] == requested_id), devices[0])
    range_key = request.args.get("range", "24h")
    if range_key not in HISTORY_RANGES:
        range_key = "24h"
    points = load_temperature_history(selected["id"], HISTORY_RANGES[range_key])
    values = [item[1] for item in points]
    stats = None
    if values:
        stats = {"minimum": min(values), "maximum": max(values), "average": sum(values) / len(values)}
    return render_template(
        "history.html", devices=devices, selected=selected, range_key=range_key,
        points=points, stats=stats, gnuplot_error=GNUPLOT_ERROR,
        resettable_sensors=resettable_sensors, history_notice=history_notice,
    )


@app.get("/analysis")
def analysis() -> str:
    return render_template(
        "analysis.html",
        overview=load_analysis_overview(),
        ollama_enabled=OLLAMA_ENABLED,
        ollama_base_url=OLLAMA_BASE_URL,
        ollama_model=OLLAMA_MODEL,
        ollama_status=check_ollama(),
    )


@app.get("/ventilation")
def ventilation() -> str:
    rooms, sources, events = load_ventilation_log()
    _, selected_outdoor = load_outdoor_sources()
    return render_template(
        "ventilation.html", rooms=rooms, sources=sources, events=events,
        selected_outdoor=selected_outdoor,
        now_local=datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M"),
        notice=session.pop("ventilation_notice", None),
    )


@app.post("/ventilation")
def create_ventilation():
    validate_csrf()
    try:
        room_id = int(request.form["room_id"])
        started_at = parse_local_datetime(request.form["started_at"])
    except (KeyError, ValueError):
        abort(400)
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT 1 FROM rooms WHERE id=?", (room_id,))
        if cursor.fetchone() is None:
            abort(400)
        cursor.execute(
            "SELECT 1 FROM ventilation_events WHERE room_id=? AND ended_at IS NULL FOR UPDATE",
            (room_id,),
        )
        if cursor.fetchone() is not None:
            session["ventilation_notice"] = {
                "kind": "warning",
                "message": "Ebben a helyiségben már van aktív szellőztetés.",
            }
            connection.rollback()
            return redirect(url_for("ventilation"))
        cursor.execute(
            """SELECT s.id,o.temperature_c
               FROM outdoor_temperature_sources s
               JOIN outdoor_temperature_observations o ON o.id=(
                 SELECT o2.id FROM outdoor_temperature_observations o2
                 WHERE o2.source_id=s.id ORDER BY o2.observed_at DESC,o2.id DESC LIMIT 1
               )
               WHERE s.is_active=1
                 AND o.observed_at >= UTC_TIMESTAMP(3) - INTERVAL s.max_age_minutes MINUTE
               ORDER BY s.priority LIMIT 1"""
        )
        outdoor = cursor.fetchone()
        source_id = int(outdoor[0]) if outdoor else None
        temperature = float(outdoor[1]) if outdoor else None
        cursor.execute(
            """INSERT INTO ventilation_events
               (room_id,started_at,ended_at,open_room_id,started_outdoor_temperature_c,started_outdoor_source_id,note,created_by)
               VALUES (?,?,?,?,?,?,?,?)""",
            (room_id, started_at, None, room_id, temperature, source_id,
             request.form.get("note", "").strip() or None, g.current_user["id"]),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    session["ventilation_notice"] = {"kind": "success", "message": "A szellőztetést elindítottuk."}
    return redirect(url_for("ventilation"))


@app.post("/ventilation/<int:event_id>/finish")
def finish_ventilation(event_id: int):
    validate_csrf()
    try:
        ended_at = parse_local_datetime(request.form["ended_at"])
    except (KeyError, ValueError):
        abort(400)
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT started_at,ended_at FROM ventilation_events WHERE id=? FOR UPDATE", (event_id,))
        row = cursor.fetchone()
        if row is None:
            abort(404)
        if row[1] is not None or ended_at <= row[0].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]:
            abort(400)
        cursor.execute(
            """SELECT s.id,o.temperature_c
               FROM outdoor_temperature_sources s
               JOIN outdoor_temperature_observations o ON o.id=(
                 SELECT o2.id FROM outdoor_temperature_observations o2
                 WHERE o2.source_id=s.id ORDER BY o2.observed_at DESC,o2.id DESC LIMIT 1
               )
               WHERE s.is_active=1
                 AND o.observed_at >= UTC_TIMESTAMP(3) - INTERVAL s.max_age_minutes MINUTE
               ORDER BY s.priority LIMIT 1"""
        )
        outdoor = cursor.fetchone()
        source_id = int(outdoor[0]) if outdoor else None
        temperature = float(outdoor[1]) if outdoor else None
        cursor.execute(
            """UPDATE ventilation_events SET ended_at=?,open_room_id=NULL,
               ended_outdoor_temperature_c=?,ended_outdoor_source_id=? WHERE id=?""",
            (ended_at, temperature, source_id, event_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    session["ventilation_notice"] = {"kind": "success", "message": "A szellőztetést lezártuk."}
    return redirect(url_for("ventilation"))


@app.get("/climate-log")
def climate_log() -> str:
    devices, events, attempts = load_climate_operation_log()
    return render_template(
        "climate_log.html", devices=devices, events=events, attempts=attempts,
        now_local=datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M"),
        notice=session.pop("climate_log_notice", None),
    )


def begin_climate_control_attempt(
    device_id: int, requested_power: bool, requested_temperature: int | None,
) -> int:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """INSERT INTO climate_control_attempts
               (device_id,requested_by,requested_power,requested_temperature_c,status)
               VALUES (?,?,?,?,'requested')""",
            (device_id, g.current_user["id"], requested_power, requested_temperature),
        )
        attempt_id = int(cursor.lastrowid)
        connection.commit()
        return attempt_id
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def persist_climate_control(
    attempt_id: int, device_id: int, room_id: int, result: ClimateControlResult,
    requested_power: bool, requested_temperature: int | None,
) -> None:
    connection = connect_database()
    cursor = connection.cursor()
    now = datetime.now(UTC).replace(tzinfo=None)
    try:
        cursor.execute(
            """UPDATE climate_control_attempts SET status=?,preflight_state=?,
               verified_state=?,error_code=?,error_message=?,completed_at=?
               WHERE id=? AND device_id=? AND status='requested'""",
            (result.status, json.dumps(result.preflight, ensure_ascii=False, default=str),
             json.dumps(result.verified, ensure_ascii=False, default=str) if result.verified else None,
             result.error_code, result.error_message, now, attempt_id, device_id),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("A vezérlési auditkérés nem frissíthető.")
        if result.status == "verified" and result.verified is not None:
            verified = result.verified
            event_token = now.strftime("%Y%m%dT%H%M%S%f")
            cursor.execute(
                """INSERT INTO device_states
                   (device_id,observed_at,power,mode,target_temperature_c,online,
                    source_system,source_event_id,raw_state)
                   VALUES (?,?,?,?,?,1,'connectlife',?,?)""",
                (device_id, now, verified["power"], str(verified.get("mode")),
                 verified.get("target_temperature_c"),
                 f"connectlife:control:{device_id}:{event_token}",
                 json.dumps(verified["raw"], ensure_ascii=False, default=str)),
            )
            if requested_power:
                cursor.execute(
                    "SELECT 1 FROM climate_operation_events WHERE device_id=? AND ended_at IS NULL",
                    (device_id,),
                )
                if cursor.fetchone() is None:
                    cursor.execute(
                        """INSERT INTO climate_operation_events
                           (device_id,room_id,started_at,open_device_id,
                            started_target_temperature_c,note,event_origin,created_by)
                           VALUES (?,?,?,?,?,'UI-vezérlés','ui_control',?)""",
                        (device_id, room_id, now, device_id,
                         verified.get("target_temperature_c"), g.current_user["id"]),
                    )
            else:
                cursor.execute(
                    """UPDATE climate_operation_events SET ended_at=?,open_device_id=NULL,
                       ended_target_temperature_c=?
                       WHERE device_id=? AND ended_at IS NULL""",
                    (now, verified.get("target_temperature_c"), device_id),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


@app.post("/climate-log/control")
def control_climate_from_ui():
    validate_csrf()
    action = request.form.get("action")
    if action not in {"on", "off"}:
        abort(400)
    desired_power = action == "on"
    try:
        device_id = int(request.form["device_id"])
        if desired_power:
            temperature_value = float(request.form["temperature_c"])
            if not temperature_value.is_integer() or not 16 <= temperature_value <= 30:
                raise ValueError
            temperature = int(temperature_value)
        else:
            temperature = None
    except (KeyError, TypeError, ValueError):
        abort(400)

    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT room_id,source_puid FROM devices
               WHERE id=? AND is_active=1 AND source_system='connectlife'""",
            (device_id,),
        )
        row = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    if row is None or row[0] is None or not row[1]:
        abort(404)

    try:
        with polling_cycle_lock():
            attempt_id = begin_climate_control_attempt(device_id, desired_power, temperature)
            result = asyncio.run(control_climate(str(row[1]), desired_power, temperature))
            try:
                persist_climate_control(
                    attempt_id, device_id, int(row[0]), result, desired_power, temperature
                )
            except Exception:
                app.logger.exception(
                    "Climate command completed but result persistence failed (attempt_id=%s)",
                    attempt_id,
                )
                session["climate_log_notice"] = {
                    "kind": "error",
                    "message": (
                        "A klímaparancs lefutott, de az eredmény naplózása sikertelen. "
                        f"Auditazonosító: {attempt_id}. Ne ismételd meg a parancsot; frissítsd az oldalt."
                    ),
                }
                return redirect(url_for("climate_log"))
    except PollCycleBusy:
        session["climate_log_notice"] = {
            "kind": "warning", "message": "Lekérdezés van folyamatban; a klímaparancs nem indult el."
        }
        return redirect(url_for("climate_log"))

    if result.status == "verified":
        action_label = "bekapcsolását" if desired_power else "kikapcsolását"
        session["climate_log_notice"] = {
            "kind": "success", "message": f"A klíma {action_label} visszaolvasással ellenőriztük."
        }
    elif result.status == "rejected":
        session["climate_log_notice"] = {"kind": "warning", "message": result.error_message}
    else:
        session["climate_log_notice"] = {
            "kind": "error", "message": f"A klímaparancs sikertelen: {result.error_message}"
        }
    return redirect(url_for("climate_log"))


@app.post("/climate-log")
def start_climate_operation():
    validate_csrf()
    try:
        device_id = int(request.form["device_id"])
        started_at = parse_local_datetime(request.form["started_at"])
    except (KeyError, ValueError):
        abort(400)
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT d.room_id,
                      (SELECT s.target_temperature_c FROM device_states s
                       WHERE s.device_id=d.id ORDER BY s.observed_at DESC,s.id DESC LIMIT 1)
               FROM devices d
               WHERE d.id=? AND d.is_active=1 AND d.source_system='connectlife' FOR UPDATE""",
            (device_id,),
        )
        row = cursor.fetchone()
        if row is None or row[0] is None:
            abort(400)
        cursor.execute(
            "SELECT 1 FROM climate_operation_events WHERE device_id=? AND ended_at IS NULL FOR UPDATE",
            (device_id,),
        )
        if cursor.fetchone() is not None:
            session["climate_log_notice"] = {
                "kind": "warning", "message": "Ehhez a klímához már tartozik aktív esemény."
            }
            connection.rollback()
            return redirect(url_for("climate_log"))
        cursor.execute(
            """INSERT INTO climate_operation_events
               (device_id,room_id,started_at,ended_at,open_device_id,started_target_temperature_c,note,created_by)
               VALUES (?,?,?,NULL,?,?,?,?)""",
            (device_id, int(row[0]), started_at, device_id, row[1],
             request.form.get("note", "").strip() or None, g.current_user["id"]),
        )
        connection.commit()
    except mariadb.IntegrityError:
        connection.rollback()
        session["climate_log_notice"] = {
            "kind": "warning", "message": "Ehhez a klímához már tartozik aktív esemény."
        }
        return redirect(url_for("climate_log"))
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    session["climate_log_notice"] = {"kind": "success", "message": "A klíma indítását rögzítettük."}
    return redirect(url_for("climate_log"))


@app.post("/climate-log/<int:event_id>/finish")
def finish_climate_operation(event_id: int):
    validate_csrf()
    try:
        ended_at = parse_local_datetime(request.form["ended_at"])
    except (KeyError, ValueError):
        abort(400)
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT started_at,ended_at,device_id FROM climate_operation_events WHERE id=? FOR UPDATE",
            (event_id,),
        )
        row = cursor.fetchone()
        if row is None:
            abort(404)
        if row[1] is not None or ended_at <= row[0].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]:
            abort(400)
        cursor.execute(
            """SELECT target_temperature_c FROM device_states
               WHERE device_id=? ORDER BY observed_at DESC,id DESC LIMIT 1""",
            (row[2],),
        )
        target_row = cursor.fetchone()
        ended_target = target_row[0] if target_row else None
        cursor.execute(
            """UPDATE climate_operation_events SET ended_at=?,open_device_id=NULL,
               ended_target_temperature_c=? WHERE id=?""",
            (ended_at, ended_target, event_id),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    session["climate_log_notice"] = {"kind": "success", "message": "A klíma leállítását rögzítettük."}
    return redirect(url_for("climate_log"))


@app.post("/history/reset")
def reset_sensor_history():
    validate_csrf()
    try:
        sensor_ids = sorted({int(value) for value in request.form.getlist("sensor_id")})
    except ValueError:
        abort(400)
    if not sensor_ids:
        session["history_notice"] = {
            "kind": "warning",
            "message": "Nem választottál ki szenzort.",
        }
        return redirect(url_for("history"))

    placeholders = ",".join("?" for _ in sensor_ids)
    try:
        with polling_cycle_lock():
            connection = connect_database()
            cursor = connection.cursor()
            try:
                cursor.execute(
                    f"""SELECT id FROM sensors
                        WHERE id IN ({placeholders}) AND is_active = 1
                          AND sensor_type = 'temperature' FOR UPDATE""",
                    tuple(sensor_ids),
                )
                allowed_ids = sorted(int(row[0]) for row in cursor.fetchall())
                if allowed_ids != sensor_ids:
                    abort(400)
                cursor.execute(
                    f"DELETE FROM sensor_readings WHERE sensor_id IN ({placeholders})",
                    tuple(sensor_ids),
                )
                deleted_count = cursor.rowcount
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()
                connection.close()
    except PollCycleBusy:
        session["history_notice"] = {
            "kind": "warning",
            "message": "A nullázás most nem végezhető el, mert lekérdezés van folyamatban.",
        }
        return redirect(url_for("history"))

    session["history_notice"] = {
        "kind": "success",
        "message": (
            f"{len(sensor_ids)} szenzor {deleted_count} korábbi mérési értékét töröltük."
        ),
    }
    return redirect(url_for("history"))


@app.get("/history/chart.svg")
def history_chart() -> Response:
    devices = load_history_devices()
    requested_id = request.args.get("device", type=int)
    selected = next((item for item in devices if item["id"] == requested_id), None)
    if selected is None:
        abort(404)
    range_key = request.args.get("range", "24h")
    if range_key not in HISTORY_RANGES:
        abort(400)
    points = load_temperature_history(selected["id"], HISTORY_RANGES[range_key])
    if not points:
        abort(404)
    try:
        svg = render_temperature_svg(points, f"{selected['name']} – hőmérséklet")
    except (RuntimeError, OSError, subprocess.SubprocessError):
        abort(503)
    response = Response(svg, mimetype="image/svg+xml")
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/settings")
def settings() -> str:
    devices = load_control_devices()
    requested_id = request.args.get("device", type=int)
    selected = next((item for item in devices if item["id"] == requested_id), devices[0] if devices else None)
    return render_template("settings.html", devices=devices, selected=selected)


@app.get("/outdoor-sources")
def outdoor_sources() -> str:
    sources, selected = load_outdoor_sources()
    return render_template(
        "outdoor_sources.html", sources=sources, selected=selected,
        notice=session.pop("outdoor_source_notice", None),
    )


@app.post("/outdoor-sources")
def save_outdoor_sources():
    validate_csrf()
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id FROM outdoor_temperature_sources ORDER BY id FOR UPDATE")
        source_ids = [int(row[0]) for row in cursor.fetchall()]
        priorities: list[int] = []
        updates: list[tuple[bool, int, int, int]] = []
        for source_id in source_ids:
            priority = int(request.form[f"priority_{source_id}"])
            max_age = int(request.form[f"max_age_{source_id}"])
            if not 1 <= priority <= 999 or not 1 <= max_age <= 1440:
                raise ValueError
            priorities.append(priority)
            updates.append((request.form.get(f"active_{source_id}") == "1", priority, max_age, source_id))
        if len(priorities) != len(set(priorities)):
            raise ValueError
        for is_active, priority, max_age, source_id in updates:
            cursor.execute("""UPDATE outdoor_temperature_sources
                              SET is_active=?,priority=?,max_age_minutes=? WHERE id=?""",
                           (is_active, priority, max_age, source_id))
        connection.commit()
    except (KeyError, ValueError):
        connection.rollback()
        abort(400)
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    session["outdoor_source_notice"] = {
        "kind": "success", "message": "A külső hőmérséklet-források beállításait elmentettük."
    }
    return redirect(url_for("outdoor_sources"))


@app.get("/schedules")
def schedules() -> str:
    context = load_schedule_context(request.args.get("device", type=int), request.args.get("profile", type=int))
    if context.get("device"):
        context["today_plan"] = resolve_daily_plan(
            context["device"]["id"], datetime.now().astimezone().date(),
            persist=g.current_user["role"] == "editor",
        )
    return render_template("schedules.html", weekdays=WEEKDAYS, **context)


@app.get("/locations")
def locations() -> str:
    rooms,devices=load_locations()
    return render_template("locations.html",rooms=rooms,devices=devices)


@app.post("/locations/<int:device_id>")
def save_location(device_id: int):
    validate_csrf()
    try: room_id=int(request.form["room_id"])
    except (KeyError,ValueError): abort(400)
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute("SELECT room_id FROM devices WHERE id=? AND is_active=1 AND source_system IN ('esp32','computherm') FOR UPDATE",(device_id,)); row=cursor.fetchone()
        if row is None: abort(404)
        cursor.execute("SELECT 1 FROM rooms WHERE id=?",(room_id,))
        if cursor.fetchone() is None: abort(400)
        old_room=row[0]
        if old_room != room_id:
            cursor.execute("UPDATE device_room_history SET valid_to=CURRENT_TIMESTAMP(3) WHERE device_id=? AND valid_to IS NULL",(device_id,))
            cursor.execute("UPDATE devices SET room_id=? WHERE id=?",(room_id,device_id))
            cursor.execute("UPDATE sensors SET room_id=? WHERE device_id=?",(room_id,device_id))
            cursor.execute("INSERT INTO device_room_history (device_id,room_id,change_reason) VALUES (?,?,?)",(device_id,room_id,request.form.get("reason") or 'Kézi áthelyezés'))
        connection.commit()
    except Exception: connection.rollback(); raise
    finally: cursor.close(); connection.close()
    return redirect(url_for("locations",saved="yes"))


@app.post("/schedules/<int:device_id>/profiles/<int:profile_id>")
def save_schedule_profile(device_id: int, profile_id: int):
    validate_csrf(); context = load_schedule_context(device_id, profile_id)
    if not context.get("device") or context["profile"]["id"] != profile_id:
        abort(404)
    windows = []
    try:
        for slot in range(1, 7):
            if request.form.get(f"slot_{slot}_enabled") != "1": continue
            start, end = request.form[f"slot_{slot}_start"], request.form[f"slot_{slot}_end"]
            if not start or not end or start >= end: raise ValueError
            windows.append((slot,start,end,parse_window_settings(context["device"]["source_system"],slot)))
        ordered = sorted(windows, key=lambda item: item[1])
        if any(ordered[i][1] < ordered[i-1][2] for i in range(1,len(ordered))): raise ValueError
    except (KeyError, ValueError):
        abort(400)
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute("DELETE FROM schedule_windows WHERE profile_id=?",(profile_id,))
        for slot,start,end,value in windows:
            cursor.execute("INSERT INTO schedule_windows (profile_id,slot_no,start_time,end_time,requested_settings) VALUES (?,?,?,?,?)",(profile_id,slot,start,end,json.dumps(value,ensure_ascii=False)))
        cursor.execute("UPDATE schedule_profiles SET version=version+1 WHERE id=? AND device_id=?",(profile_id,device_id)); connection.commit()
    except Exception: connection.rollback(); raise
    finally: cursor.close(); connection.close()
    resolve_daily_plan(device_id, datetime.now().astimezone().date())
    return redirect(url_for("schedules",device=device_id,profile=profile_id,saved="profile"))


@app.post("/schedules/<int:device_id>/weekly")
def save_weekly_schedule(device_id: int):
    validate_csrf(); context=load_schedule_context(device_id)
    allowed={p["id"] for p in context.get("profiles",[])}
    values=[]
    try:
        for day in range(7):
            profile_id=int(request.form[f"weekday_{day}"])
            if profile_id not in allowed: raise ValueError
            values.append((day,profile_id))
    except (KeyError,ValueError): abort(400)
    connection=connect_database(); cursor=connection.cursor()
    try:
        for day,pid in values: cursor.execute("UPDATE device_weekly_profile_assignments SET profile_id=? WHERE device_id=? AND weekday=?",(pid,device_id,day))
        connection.commit()
    finally: cursor.close(); connection.close()
    resolve_daily_plan(device_id,datetime.now().astimezone().date())
    return redirect(url_for("schedules",device=device_id,saved="weekly"))


@app.post("/schedules/<int:device_id>/dates")
def save_date_schedule(device_id: int):
    validate_csrf(); context=load_schedule_context(device_id); allowed={p["id"] for p in context.get("profiles",[])}
    try:
        assignment_date=date.fromisoformat(request.form["assignment_date"]); profile_id=int(request.form["profile_id"])
        if profile_id not in allowed: raise ValueError
    except (KeyError,ValueError): abort(400)
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute("""INSERT INTO device_date_profile_assignments (device_id,assignment_date,profile_id,note) VALUES (?,?,?,?) ON DUPLICATE KEY UPDATE profile_id=VALUES(profile_id),note=VALUES(note)""",(device_id,assignment_date,profile_id,request.form.get("note") or None)); connection.commit()
    finally: cursor.close(); connection.close()
    if assignment_date==datetime.now().astimezone().date(): resolve_daily_plan(device_id,assignment_date)
    return redirect(url_for("schedules",device=device_id,saved="date"))


def form_boolean(name: str) -> bool:
    return request.form.get(name) == "1"


@app.post("/settings/<int:device_id>")
def save_settings(device_id: int):
    validate_csrf()
    devices = load_control_devices()
    device = next((item for item in devices if item["id"] == device_id), None)
    if device is None:
        abort(404)
    try:
        temperature = float(request.form["temperature_c"])
    except (KeyError, ValueError):
        abort(400)

    if device["source_system"] == "connectlife":
        mode = request.form.get("mode")
        fan_speed = request.form.get("fan_speed")
        sleep = request.form.get("sleep")
        if not 16 <= temperature <= 30 or mode not in {"cool", "heat", "dry", "fan", "auto"}:
            abort(400)
        if fan_speed not in {"auto", "low", "mid_low", "mid", "mid_high", "high"}:
            abort(400)
        if sleep not in {"off", "general", "elder", "young", "kid"}:
            abort(400)
        settings_value = {
            "power": form_boolean("power"), "temperature_c": temperature,
            "mode": mode, "fan_speed": fan_speed, "swing": form_boolean("swing"),
            "fast_cool": form_boolean("fast_cool"), "quiet": form_boolean("quiet"),
            "sleep": sleep,
        }
    else:
        control_mode = request.form.get("control_mode")
        if not 5 <= temperature <= 22 or control_mode not in {"manual", "auto"}:
            abort(400)
        settings_value = {
            "power": form_boolean("power"), "temperature_c": temperature,
            "control_mode": control_mode,
        }

    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """UPDATE device_setting_requests SET status='superseded',
               superseded_at=CURRENT_TIMESTAMP(3)
               WHERE device_id=? AND status='pending'""", (device_id,)
        )
        cursor.execute(
            """INSERT INTO device_setting_requests
               (device_id,source_system,requested_settings,status)
               VALUES (?,?,?,'pending')""",
            (device_id, device["source_system"], json.dumps(settings_value, ensure_ascii=False)),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for("settings", device=device_id, saved="yes"))


def validate_csrf() -> None:
    if not secrets.compare_digest(request.form.get("csrf_token", ""), csrf_token()):
        abort(400)


@app.post("/devices/<int:device_id>/power")
def update_power(device_id: int):
    validate_csrf()

    power_value = request.form.get("manual_power_state")
    if power_value not in {"0", "1"}:
        abort(400)
    new_state = int(power_value)

    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT manual_power_state FROM devices
            WHERE id = ? AND is_active = 1 AND managed_manually = 1
            FOR UPDATE
            """,
            (device_id,),
        )
        row = cursor.fetchone()
        if row is None:
            abort(404)
        previous_state = int(bool(row[0]))
        changed = previous_state != new_state
        if changed:
            cursor.execute(
                "UPDATE devices SET manual_power_state = ? WHERE id = ?",
                (new_state, device_id),
            )
            cursor.execute(
                """
                INSERT INTO manual_state_events
                  (device_id, previous_power_state, new_power_state)
                VALUES (?, ?, ?)
                """,
                (device_id, previous_state, new_state),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    result = "power_saved" if changed else "power_unchanged"
    return redirect(url_for("dashboard", saved=result) + f"#device-{device_id}")


@app.post("/devices/<int:device_id>/service")
def record_service(device_id: int):
    validate_csrf()
    try:
        serviced_on = date.fromisoformat(request.form["last_service_date"])
        next_due_text = request.form.get("next_service_due", "")
        next_due = date.fromisoformat(next_due_text) if next_due_text else None
    except (KeyError, ValueError):
        abort(400)

    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT 1 FROM devices
            WHERE id = ? AND is_active = 1
              AND source_system IN ('connectlife', 'manual')
            FOR UPDATE
            """,
            (device_id,),
        )
        if cursor.fetchone() is None:
            abort(404)
        cursor.execute(
            """
            UPDATE devices
            SET last_service_date = ?, next_service_due = ?
            WHERE id = ?
            """,
            (serviced_on, next_due, device_id),
        )
        cursor.execute(
            """
            INSERT INTO service_events (device_id, serviced_on, next_service_due)
            VALUES (?, ?, ?)
            """,
            (device_id, serviced_on, next_due),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    return redirect(url_for("dashboard", saved="service_saved") + f"#device-{device_id}")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "gnuplot": "ok" if GNUPLOT_BIN else "unavailable",
        "gnuplot_path": GNUPLOT_BIN,
    }


if __name__ == "__main__":
    if GNUPLOT_ERROR:
        app.logger.warning(GNUPLOT_ERROR)
    else:
        app.logger.info("gnuplot ready: %s", GNUPLOT_BIN)
    app.run(host="0.0.0.0", port=int(os.getenv("DASHBOARD_PORT", "8081")), debug=False)
