#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import csv
from functools import wraps
import io
import os
import json
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import unicodedata
import urllib.error
import urllib.request
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import mariadb
from dotenv import load_dotenv
from flask import Flask, Response, abort, g, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from poll_devices import DEFAULT_CONFIG, load_devices
from poll_scheduler import run_cycle
from polling_lock import PollCycleBusy, polling_cycle_lock, polling_operation_active
from climate_control import FAN_SPEED_VALUES, ClimateControlResult, control_climate
from database_backup import create_database_export, export_directory, list_database_exports
from global_settings import (
    SETTINGS as GLOBAL_SETTINGS,
    reload_environment,
    save as save_global_settings,
    values as global_setting_values,
)
from analysis_experiment import build_evidence
from deterministic_report import GENERATOR_VERSION, generate_report
from version import APP_VERSION


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
LOCAL_TIMEZONE_NAME = os.getenv("APP_TIMEZONE", "Europe/Budapest")
LOCAL_TIMEZONE = ZoneInfo(LOCAL_TIMEZONE_NAME)


def local_now() -> datetime:
    return datetime.now(LOCAL_TIMEZONE)

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
device_config_lock = threading.Lock()
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9._-]{3,64}")
PUBLIC_ENDPOINTS = {"static", "health", "login", "setup"}

SOURCE_LABELS = {
    "esp32": "ESP32",
    "computherm": "Computherm",
    "connectlife": "Hisense",
    "tasmota": "Nous / Tasmota",
    "manual": "Kézi",
    "linux_system": "Linux rendszer",
    "zigbee2mqtt": "Zigbee2MQTT",
    "shelly_mqtt": "Shelly MQTT",
}

DEVICE_GROUPS = (
    ("esp32", "ESP32 hőmérők"),
    ("computherm", "Computherm termosztátok"),
    ("connectlife", "Hisense klímák"),
    ("tasmota", "Nous teljesítménymérők"),
    ("manual", "Kézi eszközök"),
    ("linux_system", "Linux szerverek"),
    ("zigbee2mqtt", "Zigbee eszközök"),
    ("shelly_mqtt", "Shelly MQTT hőmérők"),
)

COMPUTHERM_LOCATION = {
    "iot-computherm-emelet": "emelet",
    "iot-computherm-foldszint": "földszint",
}

OUTDOOR_SOURCE_BADGES = {
    "zigbee2mqtt": "Zigbee eszköz",
    "open_meteo": "Webes lekérdezés",
    "wunderground_pws": "Webes lekérdezés",
    "esp32": "Helyi szenzor",
    "manual": "Kézi adat",
}


def shelly_freshness_status(
    last_measurement_at: datetime | None,
    now_utc: datetime | None = None,
) -> tuple[str, str, bool]:
    """Return CSS class, Hungarian label and usability for a deep-sleep Shelly."""
    if last_measurement_at is None:
        return "offline", "Nincs mérés", False
    now = now_utc or datetime.now(UTC).replace(tzinfo=None)
    age = max(now - last_measurement_at, timedelta(0))
    if age <= timedelta(hours=1):
        return "online", "Friss mérés", True
    if age <= timedelta(hours=2):
        return "warning", "Alvó", True
    if age <= timedelta(hours=4):
        return "delayed", "Jelentés késik", True
    return "offline", "Nincs friss mérés", False

HISTORY_RANGES = {
    "1h": 1,
    "2h": 2,
    "6h": 6,
    "12h": 12,
    "24h": 24,
    "7d": 24 * 7,
    "30d": 24 * 30,
}
WEEKDAYS = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek", "Szombat", "Vasárnap"]
def find_gnuplot() -> tuple[str | None, str | None]:
    configured = os.getenv("GNUPLOT_BIN")
    candidate = configured or shutil.which("gnuplot")
    if candidate is None and Path("/opt/homebrew/bin/gnuplot").is_file():
        candidate = "/opt/homebrew/bin/gnuplot"
    if candidate is None:
        return None, "A gnuplot nem található."
    try:
        result = subprocess.run(
            # The first invocation after a macOS restart may be delayed by
            # Homebrew/font-cache initialization.  Do not disable graphing for
            # the lifetime of the dashboard because of a short startup delay.
            [candidate, "--version"], capture_output=True, text=True, timeout=15, check=True
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
    return {
        "current_user": user,
        "can_write": bool(user and user["role"] == "editor"),
        "app_version": APP_VERSION,
    }


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
            SELECT DISTINCT d.id, d.name, d.source_system, d.polling_enabled
            FROM devices d
            JOIN sensors s ON s.device_id = d.id AND s.is_active = 1
            WHERE d.is_active = 1 AND s.sensor_type = 'temperature'
              AND d.source_system <> 'manual'
            ORDER BY FIELD(d.source_system, 'esp32', 'computherm', 'connectlife'), d.name
            """
        )
        return rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()


def load_history_presets(user_id: int) -> list[dict[str, Any]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT id,name,device_ids,range_key,updated_at
               FROM history_presets WHERE user_id=? ORDER BY id""",
            (user_id,),
        )
        presets = rows_as_dicts(cursor)
        for preset in presets:
            stored = preset["device_ids"]
            preset["device_ids"] = json.loads(stored) if isinstance(stored, str) else stored
        return presets
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


def load_analysis_overview(report_filters: dict[str, str] | None = None) -> dict[str, Any]:
    report_filters = report_filters or {}
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
        conditions = []
        parameters: list[Any] = []
        severity = report_filters.get("severity", "")
        if severity in {"info", "warning", "critical"}:
            conditions.append("dr.severity=?")
            parameters.append(severity)
        query = report_filters.get("q", "").strip()
        if query:
            conditions.append("(dr.title LIKE ? OR dr.report_text LIKE ? OR dr.operator_observation LIKE ?)")
            pattern = f"%{query}%"
            parameters.extend((pattern, pattern, pattern))
        date_from = report_filters.get("date_from", "")
        if date_from:
            conditions.append("dr.created_at>=?")
            parameters.append(datetime.fromisoformat(parse_local_datetime(f"{date_from}T00:00")))
        date_to = report_filters.get("date_to", "")
        if date_to:
            conditions.append("dr.created_at<?")
            next_day = date.fromisoformat(date_to) + timedelta(days=1)
            parameters.append(datetime.fromisoformat(parse_local_datetime(f"{next_day.isoformat()}T00:00")))
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        cursor.execute(
            """SELECT dr.id,dr.window_started_at,dr.window_ended_at,dr.generator_version,
                      dr.severity,dr.title,dr.report_text,dr.findings_json,
                      dr.operator_observation,dr.created_at,u.username
               FROM deterministic_reports dr JOIN app_users u ON u.id=dr.created_by"""
            + where
            + " ORDER BY dr.created_at DESC,dr.id DESC LIMIT 100",
            tuple(parameters),
        )
        reports = rows_as_dicts(cursor)
        for item in reports:
            stored = item.pop("findings_json")
            item["findings"] = json.loads(stored) if isinstance(stored, str) else stored
        return {"runs": runs, "anomalies": anomalies, "reports": reports}
    finally:
        cursor.close()
        connection.close()


def load_temperature_history(
    device_id: int, started_at: datetime, ended_at: datetime
) -> list[tuple[datetime, float]]:
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
              AND sr.observed_at >= ? AND sr.observed_at < ?
            ORDER BY sr.observed_at
            """,
            (device_id, started_at, ended_at),
        )
        return [(row[0], float(row[1])) for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()


def load_temperature_export_rows(
    devices: list[dict[str, Any]], started_at: datetime, ended_at: datetime
) -> list[list[Any]]:
    if not devices:
        return []
    device_ids = [int(device["id"]) for device in devices]
    placeholders = ",".join("?" for _ in device_ids)
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""
            SELECT d.id, sr.observed_at, sr.value
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            JOIN devices d ON d.id = s.device_id
            WHERE d.id IN ({placeholders})
              AND s.sensor_type = 'temperature'
              AND sr.quality IN ('good', 'valid') AND sr.value IS NOT NULL
              AND sr.observed_at >= ? AND sr.observed_at < ?
            ORDER BY sr.observed_at, sr.id
            """,
            (*device_ids, started_at, ended_at),
        )
        measurements = [
            (int(row[0]), row[1], float(row[2])) for row in cursor.fetchall()
        ]
    finally:
        cursor.close()
        connection.close()

    rows: list[list[Any]] = []
    cluster: dict[int, float] = {}
    cluster_times: list[datetime] = []
    last_time: datetime | None = None

    def finish_cluster() -> None:
        if not cluster_times:
            return
        ordered = sorted(cluster_times)
        representative = ordered[len(ordered) // 2]
        rows.append(
            [representative]
            + [cluster.get(device_id) for device_id in device_ids]
        )

    for device_id, observed_at, value in measurements:
        starts_new_cluster = bool(
            cluster_times
            and (
                device_id in cluster
                or (last_time is not None and observed_at - last_time > timedelta(seconds=45))
            )
        )
        if starts_new_cluster:
            finish_cluster()
            cluster = {}
            cluster_times = []
        cluster[device_id] = value
        cluster_times.append(observed_at)
        last_time = observed_at
    finish_cluster()
    return rows


def load_manual_temperature_devices() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT d.id, d.name, r.name AS room_name, z.name AS zone_name
            FROM devices d
            LEFT JOIN rooms r ON r.id = d.room_id
            LEFT JOIN zones z ON z.id = COALESCE(r.zone_id, d.zone_id)
            LEFT JOIN device_types dt ON dt.id = d.device_type_id
            WHERE d.is_active = 1
              AND d.access_mode = 'manual_visual'
              AND d.capability_mode = 'manual_read'
              AND (dt.code = 'temperature_sensor' OR d.device_type = 'temperature_sensor')
            ORDER BY z.name, r.name, d.name
            """
        )
        devices = rows_as_dicts(cursor)
        cursor.execute(
            """
            SELECT sr.observed_at, sr.value, sr.ingested_at,
                   d.name AS device_name, r.name AS room_name,
                   u.username AS recorded_by_name,
                   JSON_UNQUOTE(JSON_EXTRACT(sr.raw_payload, '$.note')) AS note
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            JOIN devices d ON d.id = s.device_id
            LEFT JOIN rooms r ON r.id = d.room_id
            LEFT JOIN app_users u
              ON u.id = JSON_UNQUOTE(JSON_EXTRACT(sr.raw_payload, '$.recorded_by'))
            WHERE sr.source_system = 'manual'
              AND s.sensor_type = 'temperature'
            ORDER BY sr.observed_at DESC, sr.id DESC
            LIMIT 100
            """
        )
        return devices, rows_as_dicts(cursor)
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


def load_registry() -> dict[str, list[dict[str, Any]]]:
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute("SELECT id,name,is_active FROM zones ORDER BY FIELD(name,'Emelet','Földszint','Zónán kívüli'),name")
        zones=rows_as_dicts(cursor)
        cursor.execute("""SELECT r.id,r.name,r.zone_id,r.is_active,z.name zone_name FROM rooms r LEFT JOIN zones z ON z.id=r.zone_id ORDER BY FIELD(z.name,'Emelet','Földszint','Zónán kívüli'),z.name,r.name""")
        rooms=rows_as_dicts(cursor)
        cursor.execute("SELECT id,code,name,is_active FROM device_types ORDER BY name")
        device_types=rows_as_dicts(cursor)
        cursor.execute("SELECT id,code,name,is_active FROM manufacturers ORDER BY name")
        manufacturers=rows_as_dicts(cursor)
        cursor.execute("""SELECT d.*,r.name room_name,COALESCE(r.zone_id,d.zone_id) effective_zone_id,
            z.name zone_name,dt.name device_type_name,m.name manufacturer_name
          FROM devices d LEFT JOIN rooms r ON r.id=d.room_id
          LEFT JOIN zones z ON z.id=COALESCE(r.zone_id,d.zone_id)
          LEFT JOIN device_types dt ON dt.id=d.device_type_id
          LEFT JOIN manufacturers m ON m.id=d.manufacturer_id
          ORDER BY d.is_active DESC,FIELD(d.source_system,'esp32','computherm','connectlife','manual'),d.name""")
        devices=rows_as_dicts(cursor)
        for device in devices:
            cursor.execute("SELECT mode_code,display_name FROM device_supported_modes WHERE device_id=? ORDER BY display_name",(device["id"],))
            device["modes"]=rows_as_dicts(cursor)
            cursor.execute("SELECT speed_code,display_name FROM device_supported_fan_speeds WHERE device_id=? ORDER BY display_name",(device["id"],))
            device["fan_speeds"]=rows_as_dicts(cursor)
            cursor.execute("SELECT feature_code,display_name FROM device_supported_features WHERE device_id=? ORDER BY display_name",(device["id"],))
            device["features"]=rows_as_dicts(cursor)
    finally: cursor.close(); connection.close()
    return {"zones":zones,"rooms":rooms,"device_types":device_types,
            "manufacturers":manufacturers,"devices":devices}


def audit_registry(cursor, entity_type: str, entity_id: int, action: str, changes: dict[str, Any]):
    cursor.execute(
        "INSERT INTO registry_audit_log (entity_type,entity_id,action,changes_json,changed_by) VALUES (?,?,?,?,?)",
        (entity_type,entity_id,action,json.dumps(changes,ensure_ascii=False),g.current_user["id"]),
    )


def sync_device_config(values: dict[str, Any]) -> None:
    """Mirror registry integration fields into the poller's JSON configuration."""
    with device_config_lock:
        with DEFAULT_CONFIG.open(encoding="utf-8") as handle:
            document = json.load(handle)
        if document.get("schema_version") != 1 or not isinstance(document.get("devices"), list):
            raise ValueError("Érvénytelen devices.json formátum.")

        source_system = str(values["source_system"])
        source_device_id = str(values["source_device_id"])
        entry = next(
            (
                item for item in document["devices"]
                if item.get("source_system") == source_system
                and item.get("device_id") == source_device_id
            ),
            None,
        )
        if entry is None:
            if source_system not in {"esp32", "tasmota", "linux_system"}:
                return
            entry = {"source_system": source_system, "device_id": source_device_id}
            document["devices"].append(entry)

        entry.update({
            "hostname": values["hostname"] or source_device_id,
            "expected_ip": values["expected_ip"] or "",
            "mac_address": values["mac_address"] or "",
            "enabled": bool(values["polling_enabled"] and values["is_active"]),
        })

        descriptor, temporary = tempfile.mkstemp(
            prefix="devices.", suffix=".json", dir=DEFAULT_CONFIG.parent, text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, DEFAULT_CONFIG)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise


def optional_int(value: str | None) -> int | None:
    return int(value) if value and value.strip() else None


def registry_code(value: str) -> str:
    normalized=unicodedata.normalize("NFKD",value.strip()).encode("ascii","ignore").decode()
    code=re.sub(r"[^a-z0-9]+","_",normalized.lower()).strip("_")
    if not code: raise ValueError("Érvénytelen kód")
    return code


def gnuplot_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render_temperature_svg(
    series: list[tuple[str, list[tuple[datetime, float]]]],
    title: str,
    started_at: datetime,
    ended_at: datetime,
) -> bytes:
    if GNUPLOT_BIN is None:
        raise RuntimeError(GNUPLOT_ERROR or "A gnuplot nem érhető el.")
    with tempfile.TemporaryDirectory(prefix="automation-chart-") as temporary:
        directory = Path(temporary)
        output_path = directory / "temperature.svg"
        script_path = directory / "chart.gnuplot"
        data_paths = []
        for index, (name, points) in enumerate(series):
            data_path = directory / f"temperature-{index}.dat"
            data_path.write_text(
                "".join(
                    f"{moment.replace(tzinfo=UTC).astimezone(LOCAL_TIMEZONE).strftime('%Y-%m-%dT%H:%M:%S')} {value:.4f}\n"
                    for moment, value in points
                ),
                encoding="utf-8",
            )
            data_paths.append((name, data_path, len(points)))
        palette = ["#17765b", "#d65a31", "#386cb0", "#9b59b6", "#c49a00", "#5b6770", "#e157a0", "#2f9e44"]
        plots = [
            (
                f'"{gnuplot_quote(str(path))}" using 1:2 '
                + ("with points pt 7 ps 1.4" if point_count == 1 else "with lines lw 2.5")
                + f' lc rgb "{palette[index % len(palette)]}" title "{gnuplot_quote(name)}"'
            )
            for index, (name, path, point_count) in enumerate(data_paths)
        ]
        local_started_at = started_at.replace(tzinfo=UTC).astimezone(LOCAL_TIMEZONE)
        local_ended_at = ended_at.replace(tzinfo=UTC).astimezone(LOCAL_TIMEZONE)
        x_range = (
            f'["{local_started_at.strftime("%Y-%m-%dT%H:%M:%S")}":'
            f'"{local_ended_at.strftime("%Y-%m-%dT%H:%M:%S")}"]'
        )
        script_path.write_text(
            "\n".join(
                [
                    'set terminal svg size 1100,440 dynamic enhanced font "Arial,12"',
                    f'set output "{gnuplot_quote(str(output_path))}"',
                    'set encoding utf8',
                    f'set title "{gnuplot_quote(title)}" offset 0,1.2 textcolor rgb "#14251f"',
                    'set xdata time',
                    'set timefmt "%Y-%m-%dT%H:%M:%S"',
                    f'set xrange {x_range}',
                    'set format x "%m.%d\\n%H:%M" timedate',
                    'set ylabel "Hőmérséklet (°C)"',
                    'set grid xtics ytics lc rgb "#dcd9ce"',
                    'set border lc rgb "#60706a"',
                    'set tics textcolor rgb "#60706a"',
                    'set key outside top center horizontal box opaque offset 0,-0.5',
                    'set margins 11,3,5,8',
                    "plot " + ", \\\n     ".join(plots),
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [GNUPLOT_BIN, str(script_path)], capture_output=True, timeout=10, check=True
        )
        return output_path.read_bytes()


def load_dashboard(
    attempt_origin: str = "all",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
              d.id, d.name, d.hostname, d.source_system, d.device_type,d.model,
              dt.name AS device_type_name,
              d.room_id, r.name AS room_name, z.name AS zone_name,
              d.managed_manually, d.manual_power_state, d.access_mode,
              d.capability_mode, d.polling_enabled,
              d.poll_interval_seconds,
              d.last_service_date, d.next_service_due,
              zd.availability AS zigbee_availability,
              zd.zigbee_type, zd.model_id AS zigbee_model,
              zd.last_message_at AS mqtt_message_at,
              (SELECT MAX(zpc.source_observed_at)
                 FROM zigbee2mqtt_property_cache zpc
                WHERE zpc.device_id=d.id) AS zigbee_last_seen,
              (SELECT zpc.numeric_value
                 FROM zigbee2mqtt_property_cache zpc
                WHERE zpc.device_id=d.id AND zpc.property_name='linkquality') AS zigbee_linkquality,
              (SELECT zpc.numeric_value
                 FROM zigbee2mqtt_property_cache zpc
                WHERE zpc.device_id=d.id AND zpc.property_name='temperature') AS zigbee_temperature_c,
              (SELECT zpc.numeric_value
                 FROM zigbee2mqtt_property_cache zpc
                WHERE zpc.device_id=d.id AND zpc.property_name='humidity') AS zigbee_humidity_percent,
              (SELECT zpc.numeric_value
                 FROM zigbee2mqtt_property_cache zpc
                WHERE zpc.device_id=d.id AND zpc.property_name='battery') AS zigbee_battery_percent,
              (SELECT MAX(msr.observed_at)
                 FROM sensors ms JOIN sensor_readings msr ON msr.sensor_id=ms.id
                WHERE ms.device_id=d.id AND ms.is_active=1
                  AND ms.sensor_type IN ('temperature','humidity','battery','battery_voltage'))
                AS shelly_last_measurement_at,
              (SELECT hsr.value
                 FROM sensors hs JOIN sensor_readings hsr ON hsr.sensor_id=hs.id
                WHERE hs.device_id=d.id AND hs.is_active=1 AND hs.sensor_type='humidity'
                ORDER BY hsr.observed_at DESC,hsr.id DESC LIMIT 1) AS shelly_humidity_percent,
              (SELECT bsr.value
                 FROM sensors bs JOIN sensor_readings bsr ON bsr.sensor_id=bs.id
                WHERE bs.device_id=d.id AND bs.is_active=1 AND bs.sensor_type='battery'
                ORDER BY bsr.observed_at DESC,bsr.id DESC LIMIT 1) AS shelly_battery_percent,
              (SELECT vsr.value
                 FROM sensors vbs JOIN sensor_readings vsr ON vsr.sensor_id=vbs.id
                WHERE vbs.device_id=d.id AND vbs.is_active=1
                  AND vbs.sensor_type='battery_voltage'
                ORDER BY vsr.observed_at DESC,vsr.id DESC LIMIT 1) AS shelly_battery_voltage,
              (SELECT mse.changed_at FROM manual_state_events mse
               WHERE mse.device_id = d.id
               ORDER BY mse.changed_at DESC, mse.id DESC LIMIT 1) AS manual_state_changed_at,
              sr.value AS temperature_c, s.sensor_type AS measurement_type,
              s.unit AS measurement_unit, sr.quality AS measurement_quality,
              sr.observed_at AS measurement_at,
              dtr.action_temperature_c,
              dtr.observed_at AS action_measurement_at,
              sc.calibration_offset_c,
              sc.filter_tau_seconds,
              sc.calculation_version AS temperature_calculation_version,
              (SELECT er.value
                 FROM sensors es
                 JOIN sensor_readings er ON er.sensor_id=es.id
                WHERE es.device_id=d.id AND es.is_active=1
                  AND es.sensor_type='energy_total'
                ORDER BY er.observed_at DESC,er.id DESC LIMIT 1) AS energy_total_kwh,
              (SELECT JSON_UNQUOTE(JSON_EXTRACT(er.raw_payload,'$.total_start_time'))
                 FROM sensors es
                 JOIN sensor_readings er ON er.sensor_id=es.id
                WHERE es.device_id=d.id AND es.is_active=1
                  AND es.sensor_type='energy_total'
                  AND JSON_EXTRACT(er.raw_payload,'$.total_start_time') IS NOT NULL
                ORDER BY er.observed_at DESC,er.id DESC LIMIT 1) AS energy_total_started_at,
              (SELECT vr.value
                 FROM sensors vs
                 JOIN sensor_readings vr ON vr.sensor_id=vs.id
                WHERE vs.device_id=d.id AND vs.is_active=1
                  AND vs.sensor_type='voltage'
                ORDER BY vr.observed_at DESC,vr.id DESC LIMIT 1) AS voltage_v,
              (SELECT lr.value
                 FROM sensors ls
                 JOIN sensor_readings lr ON lr.sensor_id=ls.id
                WHERE ls.device_id=d.id AND ls.is_active=1
                  AND ls.sensor_type='load_1m'
                ORDER BY lr.observed_at DESC,lr.id DESC LIMIT 1) AS load_1m,
              (SELECT lr.value
                 FROM sensors ls
                 JOIN sensor_readings lr ON lr.sensor_id=ls.id
                WHERE ls.device_id=d.id AND ls.is_active=1
                  AND ls.sensor_type='load_5m'
                ORDER BY lr.observed_at DESC,lr.id DESC LIMIT 1) AS load_5m,
              (SELECT lr.value
                 FROM sensors ls
                 JOIN sensor_readings lr ON lr.sensor_id=ls.id
                WHERE ls.device_id=d.id AND ls.is_active=1
                  AND ls.sensor_type='load_15m'
                ORDER BY lr.observed_at DESC,lr.id DESC LIMIT 1) AS load_15m,
              ds.power, ds.mode, ds.target_temperature_c, ds.fan_speed,
              ds.online AS reported_online, ds.active, ds.observed_at AS state_at,
              pa.success AS poll_success, pa.attempted_at AS last_poll_at,
              pa.duration_ms, pa.error_code, pa.error_message
            FROM devices d
            LEFT JOIN device_types dt ON dt.id=d.device_type_id
            LEFT JOIN rooms r ON r.id = d.room_id
            LEFT JOIN zones z ON z.id = COALESCE(r.zone_id,d.zone_id)
            LEFT JOIN zigbee2mqtt_devices zd ON zd.device_id=d.id
            LEFT JOIN sensors s
              ON s.device_id = d.id AND s.is_active = 1
             AND ((d.source_system = 'tasmota' AND s.sensor_type = 'power')
               OR (d.source_system NOT IN ('tasmota','zigbee2mqtt')
                   AND s.sensor_type = 'temperature')
               OR (d.source_system = 'zigbee2mqtt'
                   AND d.device_type <> 'power_meter' AND s.sensor_type = 'temperature'))
            LEFT JOIN sensor_readings sr
              ON sr.id = (
                SELECT sr2.id FROM sensor_readings sr2
                WHERE sr2.sensor_id = s.id
                ORDER BY sr2.observed_at DESC, sr2.id DESC LIMIT 1
              )
            LEFT JOIN derived_temperature_readings dtr
              ON dtr.id = (
                SELECT dtr2.id FROM derived_temperature_readings dtr2
                WHERE dtr2.sensor_id = s.id AND dtr2.is_action_point = 1
                  AND dtr2.action_temperature_c IS NOT NULL
                ORDER BY dtr2.observed_at DESC, dtr2.id DESC LIMIT 1
              )
            LEFT JOIN sensor_calibrations sc ON sc.id = dtr.calibration_id
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
            ORDER BY FIELD(d.source_system, 'esp32', 'manual', 'computherm', 'connectlife', 'tasmota'), d.name
            """
        )
        devices = rows_as_dicts(cursor)

        attempt_where = "" if attempt_origin == "all" else "WHERE pa.poll_origin = ?"
        attempt_params: tuple[str, ...] = () if attempt_origin == "all" else (attempt_origin,)
        cursor.execute(
            f"""
            SELECT pa.attempted_at, pa.completed_at, pa.duration_ms, pa.success,
                   pa.error_code, pa.error_message, d.name, d.hostname,
                   pa.source_system, pa.poll_origin
            FROM poll_attempts pa
            LEFT JOIN devices d ON d.id = pa.device_id
            {attempt_where}
            ORDER BY pa.attempted_at DESC, pa.id DESC
            LIMIT 40
            """,
            attempt_params,
        )
        attempts = rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()

    for device in devices:
        device["source_label"] = SOURCE_LABELS.get(
            device["source_system"], device["source_system"]
        )
        device["is_manual_visual"] = device["access_mode"] == "manual_visual"
        if device["source_system"] == "zigbee2mqtt":
            freshness_limit = (
                timedelta(hours=2)
                if str(device["zigbee_type"] or "").casefold() == "enddevice"
                else timedelta(minutes=2)
            )
            mqtt_fresh = bool(
                device["mqtt_message_at"]
                and datetime.now(UTC).replace(tzinfo=None) - device["mqtt_message_at"]
                <= freshness_limit
            )
            device["online"] = (
                device["zigbee_availability"] != "offline" and mqtt_fresh
            )
            if device["zigbee_temperature_c"] is not None:
                device["temperature_c"] = device["zigbee_temperature_c"]
                device["measurement_at"] = (
                    device["zigbee_last_seen"] or device["mqtt_message_at"]
                )
        elif device["source_system"] == "shelly_mqtt":
            (
                device["shelly_status_class"],
                device["shelly_status_label"],
                device["online"],
            ) = shelly_freshness_status(
                device["shelly_last_measurement_at"]
            )
        else:
            device["online"] = (
                None if device["is_manual_visual"] else bool(device["poll_success"])
            )
        device["measurement_is_stale"] = bool(
            device["measurement_at"]
            and datetime.now(UTC).replace(tzinfo=None) - device["measurement_at"]
            > timedelta(hours=1)
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
            """SELECT s.id,s.source_code,s.display_name,s.source_type,
                      o.temperature_c,o.observed_at,o.fetched_at
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
        selected = selected_rows[0] if selected_rows else None
        if selected is not None:
            selected["source_badge"] = OUTDOOR_SOURCE_BADGES.get(
                selected["source_type"], selected["source_type"]
            )
        return sources, selected
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


def load_climate_operation_log() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT d.id,d.name,d.room_id,r.name AS room_name,d.source_puid,
                      s.power,s.target_temperature_c,s.fan_speed,
                      s.observed_at AS state_observed_at
               FROM devices d JOIN rooms r ON r.id=d.room_id
               LEFT JOIN device_states s ON s.id=(
                 SELECT s2.id FROM device_states s2 WHERE s2.device_id=d.id
                 ORDER BY s2.observed_at DESC,s2.id DESC LIMIT 1
               )
               WHERE d.is_active=1 AND d.source_system='connectlife'
               ORDER BY r.name,d.name"""
        )
        devices = rows_as_dicts(cursor)
        for device in devices:
            cursor.execute(
                """SELECT s.id,s.name,d.name AS device_name
                   FROM sensors s
                   LEFT JOIN devices d ON d.id=s.device_id
                   WHERE s.is_active=1 AND s.sensor_type='temperature'
                     AND COALESCE(s.room_id,d.room_id)=?
                   ORDER BY d.name,s.name""",
                (device["room_id"],),
            )
            device["temperature_sensors"] = rows_as_dicts(cursor)
        cursor.execute(
            """SELECT e.id,e.device_id,d.name AS device_name,r.name AS room_name,
                      e.started_at,e.ended_at,e.started_target_temperature_c,
                      e.started_fan_speed,e.ended_target_temperature_c,
                      e.ended_fan_speed,e.note,e.event_origin,
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
                      a.requested_temperature_c,a.requested_fan_speed,
                      a.status,a.error_message,
                      d.name AS device_name,u.username
               FROM climate_control_attempts a
               JOIN devices d ON d.id=a.device_id
               JOIN app_users u ON u.id=a.requested_by
               ORDER BY a.requested_at DESC,a.id DESC LIMIT 30"""
        )
        attempts = rows_as_dicts(cursor)
        cursor.execute(
            """SELECT s.id,s.starts_at,s.runtime_minutes,s.target_temperature_c,s.fan_speed,s.status,
                      s.current_step_no,
                      s.actual_started_at,s.actual_ended_at,s.error_message,
                      d.name AS device_name,r.name AS room_name,u.username
               FROM climate_control_schedules s JOIN devices d ON d.id=s.device_id
               JOIN rooms r ON r.id=d.room_id JOIN app_users u ON u.id=s.created_by
               ORDER BY s.starts_at DESC,s.id DESC LIMIT 50"""
        )
        schedules = rows_as_dicts(cursor)
        for schedule in schedules:
            cursor.execute(
                """SELECT ps.step_no,ps.runtime_minutes,ps.target_temperature_c,
                          ps.fan_speed,ps.transition_type,ps.threshold_delta_c,
                          ps.threshold_operator,
                          ps.actual_started_at,ps.actual_ended_at,ps.transition_reason,
                          COALESCE(sd.name,psn.name) AS sensor_name
                   FROM climate_program_steps ps
                   LEFT JOIN sensors sn ON sn.id=ps.sensor_id
                   LEFT JOIN devices sd ON sd.id=sn.device_id
                   LEFT JOIN sensors psn ON psn.id=ps.sensor_id
                   WHERE ps.schedule_id=? ORDER BY ps.step_no""",
                (schedule["id"],),
            )
            schedule["steps"] = rows_as_dicts(cursor)
        return devices, events, attempts, schedules
    finally:
        cursor.close()
        connection.close()


def parse_local_datetime(value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LOCAL_TIMEZONE)
    parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def history_window(range_key: str, local_start: str) -> tuple[datetime, datetime]:
    hours = HISTORY_RANGES[range_key]
    if local_start:
        started_at = datetime.fromisoformat(parse_local_datetime(local_start))
        return started_at, started_at + timedelta(hours=hours)
    ended_at = datetime.now(UTC).replace(tzinfo=None)
    return ended_at - timedelta(hours=hours), ended_at


def load_energy_readings(
    energy_type: str = "all",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    year = local_now().year
    year_started_at = datetime(year, 1, 1, tzinfo=LOCAL_TIMEZONE).astimezone(UTC).replace(tzinfo=None)
    next_year_at = datetime(year + 1, 1, 1, tzinfo=LOCAL_TIMEZONE).astimezone(UTC).replace(tzinfo=None)
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """SELECT m.id,m.meter_code,m.display_name,m.energy_type,m.unit,
                      r.reading_value,r.recorded_at,
                      first_year.reading_value AS year_first_value,
                      first_year.recorded_at AS year_started_at,
                      last_year.reading_value AS year_last_value,
                      last_year.reading_value-first_year.reading_value
                        AS year_consumption
               FROM energy_meters m
               LEFT JOIN energy_meter_readings r ON r.id=(
                 SELECT r2.id FROM energy_meter_readings r2 WHERE r2.meter_id=m.id
                 ORDER BY r2.recorded_at DESC,r2.id DESC LIMIT 1
               )
               LEFT JOIN energy_meter_readings first_year ON first_year.id=(
                 SELECT fy.id FROM energy_meter_readings fy
                  WHERE fy.meter_id=m.id AND fy.recorded_at>=? AND fy.recorded_at<?
                  ORDER BY fy.recorded_at,fy.id LIMIT 1
               )
               LEFT JOIN energy_meter_readings last_year ON last_year.id=(
                 SELECT ly.id FROM energy_meter_readings ly
                  WHERE ly.meter_id=m.id AND ly.recorded_at>=? AND ly.recorded_at<?
                  ORDER BY ly.recorded_at DESC,ly.id DESC LIMIT 1
               )
               WHERE m.is_active=1 ORDER BY FIELD(m.energy_type,'electricity','gas')""",
            (year_started_at, next_year_at, year_started_at, next_year_at),
        )
        meters = rows_as_dicts(cursor)
        reading_filter = ""
        parameters: tuple[Any, ...] = ()
        if energy_type in {"electricity", "gas"}:
            reading_filter = "WHERE m.energy_type=?"
            parameters = (energy_type,)
        cursor.execute(
            f"""SELECT r.id,r.meter_id,r.recorded_at,r.reading_value,r.entry_source,r.note,
                      m.display_name,m.energy_type,m.unit,
                      u.username AS recorded_by_name,
                      r.reading_value-LAG(r.reading_value) OVER
                        (PARTITION BY r.meter_id ORDER BY r.recorded_at,r.id) AS consumption
               FROM energy_meter_readings r
               JOIN energy_meters m ON m.id=r.meter_id
               LEFT JOIN app_users u ON u.id=r.recorded_by
               {reading_filter}
               ORDER BY r.recorded_at DESC,r.id DESC LIMIT 200""",
            parameters,
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
    return utc_value.astimezone(LOCAL_TIMEZONE).strftime("%Y. %m. %d. %H:%M:%S")


@app.template_filter("local_datetime_input")
def format_local_datetime_input(value: datetime | None) -> str:
    if value is None:
        return ""
    utc_value = value.replace(tzinfo=UTC)
    return utc_value.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m-%dT%H:%M")


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
    requested_attempt_origin = request.args.get("poll_origin")
    if requested_attempt_origin in {"all", "automatic", "manual"}:
        session["dashboard_poll_origin"] = requested_attempt_origin
    attempt_origin = session.get("dashboard_poll_origin", "all")
    devices, attempts = load_dashboard(attempt_origin)
    _, outdoor_temperature = load_outdoor_sources()
    requested_view = request.args.get("view")
    if requested_view in {"device", "room"}:
        session["dashboard_view"] = requested_view
    view_mode = session.get("dashboard_view", "device")
    requested_temperature = request.args.get("temperature")
    if requested_temperature in {"raw", "action"}:
        session["dashboard_temperature"] = requested_temperature
    temperature_mode = session.get("dashboard_temperature", "raw")
    has_active_esp32 = any(device["source_system"] == "esp32" for device in devices)
    now_utc = datetime.now(UTC).replace(tzinfo=None)
    for device in devices:
        use_action = temperature_mode == "action" and device["source_system"] == "esp32"
        if use_action:
            device["display_temperature_c"] = device["action_temperature_c"]
            device["display_temperature_at"] = device["action_measurement_at"]
            device["display_temperature_kind"] = "Cselekedeti hőmérséklet"
            device["display_temperature_available"] = device["action_temperature_c"] is not None
        else:
            device["display_temperature_c"] = device["temperature_c"]
            device["display_temperature_at"] = device["measurement_at"]
            device["display_temperature_kind"] = "Nyers mérés"
            device["display_temperature_available"] = device["temperature_c"] is not None
        device["display_temperature_is_stale"] = bool(
            device["display_temperature_at"]
            and now_utc - device["display_temperature_at"] > timedelta(hours=1)
        )
    successful = sum(1 for item in devices if item["online"])
    monitored_count = sum(1 for item in devices if item["polling_enabled"])
    latest_poll = max(
        (item["last_poll_at"] for item in devices if item["last_poll_at"]),
        default=None,
    )
    return render_template(
        "dashboard.html",
        devices=devices,
        attempts=attempts,
        attempt_origin=attempt_origin,
        successful=successful,
        monitored_count=monitored_count,
        latest_poll=latest_poll,
        poll_marker=latest_poll.isoformat(timespec="milliseconds") if latest_poll else None,
        poll_notice=session.pop("poll_notice", None),
        view_mode=view_mode,
        temperature_mode=temperature_mode,
        has_active_esp32=has_active_esp32,
        outdoor_temperature=outdoor_temperature,
        device_groups=load_device_groups(devices),
        room_groups=load_room_groups(devices, outdoor_temperature),
    )


def load_polling_settings() -> tuple[list[dict[str, Any]], int]:
    default_seconds = int(os.getenv("DEFAULT_POLL_INTERVAL_MINUTES", "10")) * 60
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT d.id,d.name,d.hostname,d.source_system,d.polling_enabled,
                   d.poll_interval_seconds,d.is_active,r.name AS room_name,
                   z.name AS zone_name
            FROM devices d
            LEFT JOIN rooms r ON r.id=d.room_id
            LEFT JOIN zones z ON z.id=COALESCE(r.zone_id,d.zone_id)
            ORDER BY
              (d.polling_enabled=1 AND d.poll_interval_seconds <> ?) DESC,
              d.polling_enabled DESC,d.poll_interval_seconds,d.name
            """,
            (default_seconds,),
        )
        devices = rows_as_dicts(cursor)
    finally:
        cursor.close()
        connection.close()
    for device in devices:
        device["is_custom_interval"] = bool(device["polling_enabled"]) and (
            device["poll_interval_seconds"] != default_seconds
        )
        device["source_label"] = SOURCE_LABELS.get(
            device["source_system"], device["source_system"]
        )
    return devices, default_seconds


@app.get("/polling-settings")
def polling_settings() -> str:
    devices, default_seconds = load_polling_settings()
    return render_template(
        "polling_settings.html",
        devices=devices,
        custom_devices=[item for item in devices if item["is_custom_interval"]],
        default_minutes=default_seconds // 60,
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
    energy_type = request.args.get("meter", "all")
    if energy_type not in {"all", "electricity", "gas"}:
        energy_type = "all"
    meters, readings = load_energy_readings(energy_type)
    try:
        edit_reading_id = int(request.args["edit"])
    except (KeyError, TypeError, ValueError):
        edit_reading_id = None
    return render_template(
        "energy.html", meters=meters, readings=readings,
        now_local=local_now().strftime("%Y-%m-%dT%H:%M"),
        current_year=local_now().year,
        energy_type=energy_type,
        edit_reading_id=edit_reading_id,
        notice=session.pop("energy_notice", None),
    )


@app.get("/manual-measurements")
def manual_measurements() -> str:
    devices, readings = load_manual_temperature_devices()
    return render_template(
        "manual_measurements.html",
        devices=devices,
        readings=readings,
        now_local=local_now().strftime("%Y-%m-%dT%H:%M"),
        notice=session.pop("manual_measurement_notice", None),
    )


@app.post("/manual-measurements")
@editor_required
def create_manual_measurement():
    validate_csrf()
    try:
        device_id = int(request.form["device_id"])
        observed_at = parse_local_datetime(request.form["observed_at"])
        value = Decimal(request.form["temperature_c"].replace(",", "."))
        if value < Decimal("-55") or value > Decimal("125"):
            raise ValueError
    except (KeyError, TypeError, ValueError, InvalidOperation):
        abort(400)

    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT d.name, d.room_id
            FROM devices d
            LEFT JOIN device_types dt ON dt.id = d.device_type_id
            WHERE d.id = ? AND d.is_active = 1
              AND d.access_mode = 'manual_visual'
              AND d.capability_mode = 'manual_read'
              AND (dt.code = 'temperature_sensor' OR d.device_type = 'temperature_sensor')
            FOR UPDATE
            """,
            (device_id,),
        )
        device = cursor.fetchone()
        if device is None:
            abort(400)
        source_sensor_id = f"device-{device_id}-temperature"
        cursor.execute(
            """
            INSERT INTO sensors
              (room_id,device_id,source_system,source_sensor_id,name,sensor_type,unit,is_active)
            VALUES (?,?,'manual',?,?,'temperature','celsius',1)
            ON DUPLICATE KEY UPDATE device_id=VALUES(device_id),room_id=VALUES(room_id),
              name=VALUES(name),unit='celsius',is_active=1
            """,
            (device[1], device_id, source_sensor_id, f"{device[0]} temperature"),
        )
        cursor.execute(
            "SELECT id FROM sensors WHERE source_system='manual' AND source_sensor_id=?",
            (source_sensor_id,),
        )
        sensor_id = cursor.fetchone()[0]
        event_id = f"manual:{source_sensor_id}:{secrets.token_hex(12)}"
        raw_payload = json.dumps(
            {
                "entry_source": "manual",
                "recorded_by": int(g.current_user["id"]),
                "note": request.form.get("note", "").strip() or None,
            },
            ensure_ascii=False,
        )
        cursor.execute(
            """
            INSERT INTO sensor_readings
              (sensor_id,observed_at,value,quality,error_code,source_system,source_event_id,raw_payload)
            VALUES (?,?,?,'valid',NULL,'manual',?,?)
            """,
            (sensor_id, observed_at, value, event_id, raw_payload),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    session["manual_measurement_notice"] = {
        "kind": "success", "message": "A kézi hőmérsékletmérést rögzítettük."
    }
    return redirect(url_for("manual_measurements"))


@app.get("/backups")
@editor_required
def backups() -> str:
    return render_template(
        "backups.html", exports=list_database_exports(),
        notice=session.pop("backup_notice", None),
    )


@app.route("/global-settings", methods=["GET", "POST"])
@editor_required
def global_settings() -> str:
    if request.method == "POST":
        validate_csrf()
        try:
            save_global_settings(dict(request.form))
            global GNUPLOT_BIN, GNUPLOT_ERROR
            GNUPLOT_BIN, GNUPLOT_ERROR = find_gnuplot()
            session["global_settings_notice"] = {"kind":"success","message":"A globális beállításokat elmentettük a .env fájlba."}
        except ValueError as error:
            session["global_settings_notice"] = {"kind":"error","message":str(error)}
        return redirect(url_for("global_settings"))
    return render_template("global_settings.html",settings=GLOBAL_SETTINGS,values=global_setting_values(),notice=session.pop("global_settings_notice",None))


@app.post("/global-settings/reload")
@editor_required
def reload_global_settings():
    validate_csrf()
    try:
        changed, restart_required = reload_environment()
        global GNUPLOT_BIN, GNUPLOT_ERROR
        GNUPLOT_BIN, GNUPLOT_ERROR = find_gnuplot()
        if restart_required:
            message = (
                f"A .env fájlt újratöltöttük; {len(changed)} érték változott. "
                "Az alábbi beállításokhoz az alkalmazást is újra kell indítani: "
                + ", ".join(restart_required)
                + "."
            )
            kind = "warning"
        elif changed:
            message = f"A .env fájlt újratöltöttük; {len(changed)} érték azonnal frissült."
            kind = "success"
        else:
            message = "A .env fájlt újratöltöttük; nem találtunk változást."
            kind = "success"
        session["global_settings_notice"] = {"kind": kind, "message": message}
    except (OSError, ValueError) as error:
        session["global_settings_notice"] = {"kind": "error", "message": str(error)}
    return redirect(url_for("global_settings"))


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
@editor_required
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


@app.post("/energy/readings/<int:reading_id>/edit")
@editor_required
def edit_energy_reading(reading_id: int):
    validate_csrf()
    try:
        meter_id = int(request.form["meter_id"])
        recorded_at = parse_local_datetime(request.form["recorded_at"])
        reading_value = Decimal(request.form["reading_value"].replace(",", "."))
        if reading_value < 0:
            raise ValueError
    except (KeyError, TypeError, ValueError, InvalidOperation):
        abort(400)
    note = request.form.get("note", "").strip() or None
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT 1 FROM energy_meter_readings WHERE id=? FOR UPDATE", (reading_id,)
        )
        if cursor.fetchone() is None:
            abort(404)
        cursor.execute("SELECT 1 FROM energy_meters WHERE id=? AND is_active=1", (meter_id,))
        if cursor.fetchone() is None:
            abort(400)
        cursor.execute(
            """UPDATE energy_meter_readings
               SET meter_id=?,recorded_at=?,reading_value=?,entry_source='manual',
                   recorded_by=?,note=?
               WHERE id=?""",
            (meter_id, recorded_at, reading_value, g.current_user["id"], note, reading_id),
        )
        connection.commit()
    except mariadb.IntegrityError:
        connection.rollback()
        session["energy_notice"] = {
            "kind": "warning", "message": "Ehhez a mérőhöz erre az időpontra már van óraállás."
        }
        return redirect(url_for("energy", edit=reading_id) + f"#reading-{reading_id}")
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    session["energy_notice"] = {"kind": "success", "message": "Az óraállást javítottuk."}
    return redirect(url_for("energy") + f"#reading-{reading_id}")


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
        successful, stored, monitored_count = asyncio.run(
            run_cycle(timeout, poll_origin="manual")
        )
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
    presets = load_history_presets(int(g.current_user["id"]))
    resettable_sensors = load_resettable_sensors()
    history_notice = session.pop("history_notice", None)
    if not devices:
        return render_template(
            "history.html", devices=[], selected_devices=[], range_key="24h", history_start="", series=[],
            gnuplot_error=GNUPLOT_ERROR, resettable_sensors=resettable_sensors,
            history_notice=history_notice, presets=presets,
        )
    requested_ids = list(dict.fromkeys(request.args.getlist("device", type=int)))
    range_key = request.args.get("range", "24h")
    preset_id = request.args.get("preset", type=int)
    if preset_id is not None:
        preset = next((item for item in presets if item["id"] == preset_id), None)
        if preset is None:
            abort(404)
        requested_ids = [int(item) for item in preset["device_ids"]]
        range_key = preset["range_key"]
    selected_devices = [item for item in devices if item["id"] in requested_ids]
    if not selected_devices:
        selected_devices = [devices[0]]
    if range_key not in HISTORY_RANGES:
        range_key = "24h"
    history_start = request.args.get("start", "").strip()
    try:
        started_at, ended_at = history_window(range_key, history_start)
    except ValueError:
        abort(400, "Érvénytelen kezdő időpont.")
    series = []
    for device in selected_devices:
        points = load_temperature_history(device["id"], started_at, ended_at)
        values = [item[1] for item in points]
        stats = None
        if values:
            stats = {"minimum": min(values), "maximum": max(values), "average": sum(values) / len(values)}
        series.append({"device": device, "points": points, "stats": stats})
    return render_template(
        "history.html", devices=devices, selected_devices=selected_devices, range_key=range_key,
        history_start=history_start,
        series=series, gnuplot_error=GNUPLOT_ERROR,
        resettable_sensors=resettable_sensors, history_notice=history_notice,
        presets=presets,
    )


@app.get("/history/export.csv")
def export_history_csv() -> Response:
    available = load_history_devices()
    requested_ids = list(dict.fromkeys(request.args.getlist("device", type=int)))
    selected = [device for device in available if device["id"] in requested_ids]
    if not selected:
        abort(400, "Legalább egy eszközt ki kell választani.")
    range_key = request.args.get("range", "24h")
    if range_key not in HISTORY_RANGES:
        abort(400, "Érvénytelen időtáv.")
    history_start = request.args.get("start", "").strip()
    try:
        started_at, ended_at = history_window(range_key, history_start)
    except ValueError:
        abort(400, "Érvénytelen kezdő időpont.")

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(["idő", *[device["name"] for device in selected]])
    for row in load_temperature_export_rows(selected, started_at, ended_at):
        local_time = row[0].replace(tzinfo=UTC).astimezone(LOCAL_TIMEZONE)
        writer.writerow(
            [local_time.strftime("%Y-%m-%d %H:%M:%S")]
            + ["" if value is None else f"{value:.4f}" for value in row[1:]]
        )
    filename = f"homerseklet_{local_now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = Response("\ufeff" + output.getvalue(), content_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/history/presets")
@editor_required
def save_history_preset():
    validate_csrf()
    name = request.form.get("preset_name", "").strip()
    requested_ids = list(dict.fromkeys(request.form.getlist("device", type=int)))
    range_key = request.form.get("range", "")
    if not name:
        session["history_notice"] = {
            "kind": "warning", "message": "A kedvenc mentéséhez adj nevet az összeállításnak."
        }
        return redirect(url_for("history"))
    if len(name) > 80:
        session["history_notice"] = {
            "kind": "warning", "message": "A kedvenc neve legfeljebb 80 karakter lehet."
        }
        return redirect(url_for("history"))
    if not requested_ids:
        session["history_notice"] = {
            "kind": "warning", "message": "A kedvenchez legalább egy eszközt válassz ki."
        }
        return redirect(url_for("history"))
    if range_key not in HISTORY_RANGES:
        session["history_notice"] = {
            "kind": "warning", "message": "A kiválasztott időtáv nem érvényes."
        }
        return redirect(url_for("history"))
    allowed_ids = {item["id"] for item in load_history_devices()}
    if any(device_id not in allowed_ids for device_id in requested_ids):
        session["history_notice"] = {
            "kind": "warning", "message": "A kijelölés már nem elérhető eszközt tartalmaz."
        }
        return redirect(url_for("history"))

    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT id FROM history_presets WHERE user_id=? AND name=? FOR UPDATE",
            (g.current_user["id"], name),
        )
        existing = cursor.fetchone()
        if existing is None:
            cursor.execute(
                "SELECT COUNT(*) FROM history_presets WHERE user_id=? FOR UPDATE",
                (g.current_user["id"],),
            )
            if int(cursor.fetchone()[0]) >= 4:
                connection.rollback()
                session["history_notice"] = {
                    "kind": "warning",
                    "message": "Legfeljebb négy mérési kedvenc menthető. Törölj egyet az új felvétele előtt.",
                }
                return redirect(url_for("history"))
            cursor.execute(
                """INSERT INTO history_presets (user_id,name,device_ids,range_key)
                   VALUES (?,?,?,?)""",
                (g.current_user["id"], name, json.dumps(requested_ids), range_key),
            )
            preset_id = int(cursor.lastrowid)
        else:
            preset_id = int(existing[0])
            cursor.execute(
                """UPDATE history_presets SET device_ids=?,range_key=?
                   WHERE id=? AND user_id=?""",
                (json.dumps(requested_ids), range_key, preset_id, g.current_user["id"]),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    session["history_notice"] = {
        "kind": "success", "message": f'A(z) „{name}” mérési kedvencet elmentettük.'
    }
    return redirect(url_for("history", preset=preset_id))


@app.post("/history/presets/<int:preset_id>/delete")
@editor_required
def delete_history_preset(preset_id: int):
    validate_csrf()
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "DELETE FROM history_presets WHERE id=? AND user_id=?",
            (preset_id, g.current_user["id"]),
        )
        changed = cursor.rowcount
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()
    if not changed:
        abort(404)
    session["history_notice"] = {"kind": "success", "message": "A mérési kedvencet töröltük."}
    return redirect(url_for("history"))


@app.get("/analysis")
def analysis() -> str:
    report_filters = {
        "q": request.args.get("q", "").strip()[:100],
        "severity": request.args.get("severity", "").strip(),
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
    }
    if report_filters["severity"] not in {"", "info", "warning", "critical"}:
        report_filters["severity"] = ""
    for key in ("date_from", "date_to"):
        if report_filters[key]:
            try:
                date.fromisoformat(report_filters[key])
            except ValueError:
                report_filters[key] = ""
    return render_template(
        "analysis.html",
        overview=load_analysis_overview(report_filters),
        report_filters=report_filters,
        generator_version=GENERATOR_VERSION,
        now_local=local_now().strftime("%Y-%m-%dT%H:%M"),
        default_analysis_start=(local_now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M"),
        analysis_notice=session.pop("analysis_notice",None),
    )


@app.post("/analysis/reports")
@editor_required
def create_deterministic_report():
    validate_csrf()
    try:
        started_at=datetime.fromisoformat(parse_local_datetime(request.form["started_at"]))
        ended_at=datetime.fromisoformat(parse_local_datetime(request.form["ended_at"]))
        if ended_at <= started_at or ended_at-started_at > timedelta(days=7): raise ValueError
    except (KeyError,ValueError):
        session["analysis_notice"] = {
            "kind": "warning",
            "message": "Érvényes, legfeljebb hét napos jelentési időablakot adj meg.",
        }
        return redirect(url_for("analysis"))
    observation=request.form.get("operator_observation","").strip()[:2000] or None
    connection=connect_database(); cursor=connection.cursor()
    try:
        facts=build_evidence(cursor,started_at,ended_at,observation)
        report=generate_report(facts, LOCAL_TIMEZONE_NAME)
        cursor.execute(
            """INSERT INTO deterministic_reports
               (window_started_at,window_ended_at,generator_version,severity,title,
                report_text,findings_json,facts_json,operator_observation,created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                started_at, ended_at, GENERATOR_VERSION, report["severity"], report["title"],
                report["report_text"], json.dumps(report["findings"],ensure_ascii=False,default=str),
                json.dumps(facts,ensure_ascii=False,default=str), observation,g.current_user["id"],
            ),
        )
        connection.commit()
        session["analysis_notice"]={
            "kind":"success",
            "message":"A determinisztikus jelentés elkészült és bekerült az adatbázisba.",
        }
    except Exception: connection.rollback(); raise
    finally: cursor.close(); connection.close()
    return redirect(url_for("analysis"))


@app.get("/ventilation")
def ventilation() -> str:
    rooms, sources, events = load_ventilation_log()
    _, selected_outdoor = load_outdoor_sources()
    return render_template(
        "ventilation.html", rooms=rooms, sources=sources, events=events,
        selected_outdoor=selected_outdoor,
        now_local=local_now().strftime("%Y-%m-%dT%H:%M"),
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
    devices, events, attempts, schedules = load_climate_operation_log()
    return render_template(
        "climate_log.html", devices=devices, events=events, attempts=attempts, schedules=schedules,
        now_local=local_now().strftime("%Y-%m-%dT%H:%M"),
        notice=session.pop("climate_log_notice", None),
    )


def begin_climate_control_attempt(
    device_id: int, requested_power: bool, requested_temperature: int | None,
    requested_fan_speed: str | None,
) -> int:
    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """INSERT INTO climate_control_attempts
               (device_id,requested_by,requested_power,requested_temperature_c,
                requested_fan_speed,status)
               VALUES (?,?,?,?,?,'requested')""",
            (device_id, g.current_user["id"], requested_power, requested_temperature,
             requested_fan_speed),
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
    requested_fan_speed: str | None,
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
                   (device_id,observed_at,power,mode,target_temperature_c,fan_speed,online,
                    source_system,source_event_id,raw_state)
                   VALUES (?,?,?,?,?,?,1,'connectlife',?,?)""",
                (device_id, now, verified["power"], str(verified.get("mode")),
                 verified.get("target_temperature_c"), verified.get("fan_speed"),
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
                            started_target_temperature_c,started_fan_speed,
                            note,event_origin,created_by)
                           VALUES (?,?,?,?,?,?,'UI-vezérlés','ui_control',?)""",
                        (device_id, room_id, now, device_id,
                         verified.get("target_temperature_c"), verified.get("fan_speed"),
                         g.current_user["id"]),
                    )
            else:
                cursor.execute(
                    """UPDATE climate_operation_events SET ended_at=?,open_device_id=NULL,
                       ended_target_temperature_c=?,ended_fan_speed=?
                       WHERE device_id=? AND ended_at IS NULL""",
                    (now, verified.get("target_temperature_c"),
                     result.preflight.get("fan_speed"), device_id),
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
            fan_speed = request.form["fan_speed"]
            if fan_speed not in FAN_SPEED_VALUES:
                raise ValueError
        else:
            temperature = None
            fan_speed = None
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
            attempt_id = begin_climate_control_attempt(
                device_id, desired_power, temperature, fan_speed
            )
            result = asyncio.run(
                control_climate(str(row[1]), desired_power, temperature, fan_speed)
            )
            try:
                persist_climate_control(
                    attempt_id, device_id, int(row[0]), result, desired_power,
                    temperature, fan_speed
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


@app.post("/climate-log/schedules")
def create_climate_schedule():
    validate_csrf()
    try:
        device_id = int(request.form["device_id"])
        runtimes = [int(value) for value in request.form.getlist("runtime_minutes[]")]
        temperatures = [int(value) for value in request.form.getlist("temperature_c[]")]
        fan_speeds = request.form.getlist("fan_speed[]")
        transitions = request.form.getlist("transition_type[]")
        sensor_values = request.form.getlist("sensor_id[]")
        condition_values = request.form.getlist("sensor_condition[]")
        lengths = {len(runtimes),len(temperatures),len(fan_speeds),len(transitions),len(sensor_values),len(condition_values)}
        if lengths != {len(runtimes)} or not 1 <= len(runtimes) <= 8:
            raise ValueError
        starts_at = parse_local_datetime(request.form["starts_at"])
        starts = datetime.fromisoformat(starts_at)
    except (KeyError, TypeError, ValueError):
        abort(400)
    now = datetime.now(UTC).replace(tzinfo=None)
    if starts < now - timedelta(minutes=5):
        abort(400)
    steps: list[dict[str, Any]] = []
    try:
        for runtime, temperature, fan_speed, transition, sensor_value, condition_value in zip(
            runtimes, temperatures, fan_speeds, transitions, sensor_values, condition_values
        ):
            if not 1 <= runtime <= 1440 or not 25 <= temperature <= 30 or fan_speed not in FAN_SPEED_VALUES:
                raise ValueError
            if transition not in {"duration","sensor_below"}:
                raise ValueError
            sensor_id = int(sensor_value) if transition == "sensor_below" else None
            condition_map={"0.0":(Decimal("0.0"),"at_least"),
                           "0.5":(Decimal("0.5"),"at_least"),
                           "1.0":(Decimal("1.0"),"at_least"),
                           "gt_1.5":(Decimal("1.5"),"greater_than")}
            if transition == "sensor_below" and condition_value not in condition_map:
                raise ValueError
            delta,operator=condition_map[condition_value] if transition == "sensor_below" else (None,None)
            steps.append({"runtime":runtime,"temperature":temperature,"fan_speed":fan_speed,
                          "transition":transition,"sensor_id":sensor_id,"delta":delta,
                          "operator":operator})
    except (ValueError, InvalidOperation):
        abort(400)
    if starts < now:
        starts = now
        starts_at = starts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute(
            """SELECT room_id FROM devices WHERE id=? AND is_active=1
               AND source_system='connectlife' AND room_id IS NOT NULL AND source_puid IS NOT NULL""",
            (device_id,),
        )
        device_row = cursor.fetchone()
        if device_row is None: abort(404)
        sensor_ids = {step["sensor_id"] for step in steps if step["sensor_id"] is not None}
        if sensor_ids:
            placeholders = ",".join("?" for _ in sensor_ids)
            cursor.execute(
                f"""SELECT s.id FROM sensors s LEFT JOIN devices d ON d.id=s.device_id
                    WHERE s.id IN ({placeholders}) AND s.is_active=1
                      AND s.sensor_type='temperature' AND COALESCE(s.room_id,d.room_id)=?""",
                (*sensor_ids,device_row[0]),
            )
            if {int(row[0]) for row in cursor.fetchall()} != sensor_ids:
                abort(400)
        cursor.execute(
            """SELECT 1 FROM climate_control_schedules
               WHERE device_id=? AND status IN ('scheduled','starting','running','stopping')
               FOR UPDATE""", (device_id,),
        )
        if cursor.fetchone() is not None:
            connection.rollback()
            session["climate_log_notice"]={"kind":"warning","message":"Ehhez a klímához már tartozik függő vagy futó program."}
            return redirect(url_for("climate_log"))
        cursor.execute(
            """INSERT INTO climate_control_schedules
               (device_id,starts_at,runtime_minutes,target_temperature_c,fan_speed,current_step_no,created_by)
               VALUES (?,?,?,?,?,NULL,?)""",
            (device_id,starts_at,steps[0]["runtime"],steps[0]["temperature"],
             steps[0]["fan_speed"],g.current_user["id"]),
        )
        schedule_id = int(cursor.lastrowid)
        for step_no, step in enumerate(steps, 1):
            cursor.execute(
                """INSERT INTO climate_program_steps
                   (schedule_id,step_no,runtime_minutes,target_temperature_c,fan_speed,
                    transition_type,sensor_id,threshold_delta_c,threshold_operator)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (schedule_id,step_no,step["runtime"],step["temperature"],step["fan_speed"],
                 step["transition"],step["sensor_id"],step["delta"],step["operator"]),
            )
        connection.commit()
    except Exception:
        connection.rollback(); raise
    finally: cursor.close(); connection.close()
    session["climate_log_notice"]={"kind":"success","message":"A programozott klímafutást elmentettük."}
    return redirect(url_for("climate_log"))


@app.post("/climate-log/schedules/<int:schedule_id>/cancel")
def cancel_climate_schedule(schedule_id: int):
    validate_csrf(); connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute(
            """UPDATE climate_control_schedules SET status='cancelled'
               WHERE id=? AND status='scheduled'""", (schedule_id,),
        )
        changed=cursor.rowcount; connection.commit()
    except Exception:
        connection.rollback(); raise
    finally: cursor.close(); connection.close()
    session["climate_log_notice"]={
        "kind":"success" if changed else "warning",
        "message":"A programot töröltük." if changed else "A program már nem törölhető.",
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


def delete_sensor_measurements(cursor, sensor_ids: list[int]) -> int:
    """Delete readings and any derived-temperature rows that depend on them."""
    if not sensor_ids:
        return 0
    placeholders = ",".join("?" for _ in sensor_ids)
    reading_filter = f"SELECT id FROM sensor_readings WHERE sensor_id IN ({placeholders})"
    cursor.execute(
        f"""DELETE FROM derived_temperature_readings
             WHERE sensor_id IN ({placeholders})
                OR raw_reading_id IN ({reading_filter})
                OR id IN (
                    SELECT derived_reading_id FROM derived_temperature_sources
                     WHERE source_sensor_id IN ({placeholders})
                        OR source_reading_id IN ({reading_filter})
                )""",
        tuple(sensor_ids) * 4,
    )
    cursor.execute(
        f"DELETE FROM sensor_readings WHERE sensor_id IN ({placeholders})",
        tuple(sensor_ids),
    )
    return max(cursor.rowcount, 0)


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
                deleted_count = delete_sensor_measurements(cursor, sensor_ids)
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
    requested_ids = list(dict.fromkeys(request.args.getlist("device", type=int)))
    selected_devices = [item for item in devices if item["id"] in requested_ids]
    if not selected_devices:
        abort(404)
    range_key = request.args.get("range", "24h")
    if range_key not in HISTORY_RANGES:
        abort(400)
    local_start = request.args.get("start", "").strip()
    try:
        started_at, ended_at = history_window(range_key, local_start)
    except ValueError:
        abort(400)
    series = [
        (device["name"], load_temperature_history(device["id"], started_at, ended_at))
        for device in selected_devices
    ]
    series = [(name, points) for name, points in series if points]
    if not series:
        abort(404)
    try:
        svg = render_temperature_svg(
            series, "Hőmérsékletek összehasonlítása", started_at, ended_at
        )
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
            context["device"]["id"], local_now().date(),
            persist=g.current_user["role"] == "editor",
        )
    return render_template("schedules.html", weekdays=WEEKDAYS, **context)


@app.get("/locations")
def locations() -> str:
    return render_template(
        "locations.html", **load_registry(),
        default_poll_minutes=int(os.getenv("DEFAULT_POLL_INTERVAL_MINUTES", "10")),
        notice=session.pop("registry_notice",None),
    )


@app.post("/registry/zones")
def create_zone():
    validate_csrf(); name=request.form.get("name","").strip()
    if not name: abort(400)
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute("INSERT INTO zones (name) VALUES (?)",(name,)); audit_registry(cursor,"zone",cursor.lastrowid,"created",{"name":name}); connection.commit()
    except mariadb.IntegrityError: connection.rollback(); session["registry_notice"]={"kind":"warning","message":"Ez a zóna már létezik."}
    finally: cursor.close(); connection.close()
    return redirect(url_for("locations"))


@app.post("/registry/rooms")
def create_room():
    validate_csrf(); name=request.form.get("name","").strip()
    try: zone_id=int(request.form["zone_id"])
    except (KeyError,ValueError): abort(400)
    if not name: abort(400)
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute("SELECT 1 FROM zones WHERE id=? AND is_active=1",(zone_id,))
        if cursor.fetchone() is None: abort(400)
        cursor.execute("INSERT INTO rooms (zone_id,name) VALUES (?,?)",(zone_id,name)); audit_registry(cursor,"room",cursor.lastrowid,"created",{"name":name,"zone_id":zone_id}); connection.commit()
    except mariadb.IntegrityError: connection.rollback(); session["registry_notice"]={"kind":"warning","message":"Ez a helyiség már létezik."}
    finally: cursor.close(); connection.close()
    return redirect(url_for("locations"))


@app.post("/registry/zones/<int:zone_id>")
def save_zone(zone_id: int):
    validate_csrf(); name=request.form.get("name","").strip()
    if not name: abort(400)
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute("SELECT 1 FROM zones WHERE id=?",(zone_id,))
        if cursor.fetchone() is None: abort(404)
        cursor.execute("UPDATE zones SET name=?,is_active=? WHERE id=?",(name,int(request.form.get("is_active")=="1"),zone_id))
        audit_registry(cursor,"zone",zone_id,"updated",{"name":name,"is_active":request.form.get("is_active")=="1"}); connection.commit()
    except Exception: connection.rollback(); raise
    finally: cursor.close(); connection.close()
    return redirect(url_for("locations"))


@app.post("/registry/rooms/<int:room_id>")
def save_room(room_id: int):
    validate_csrf(); name=request.form.get("name","").strip()
    try: zone_id=int(request.form["zone_id"])
    except (KeyError,ValueError): abort(400)
    if not name: abort(400)
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute("SELECT 1 FROM rooms WHERE id=?",(room_id,))
        if cursor.fetchone() is None: abort(404)
        cursor.execute("UPDATE rooms SET name=?,zone_id=?,is_active=? WHERE id=?",(name,zone_id,int(request.form.get("is_active")=="1"),room_id))
        cursor.execute("UPDATE devices SET zone_id=? WHERE room_id=?",(zone_id,room_id))
        audit_registry(cursor,"room",room_id,"updated",{"name":name,"zone_id":zone_id,"is_active":request.form.get("is_active")=="1"}); connection.commit()
    except Exception: connection.rollback(); raise
    finally: cursor.close(); connection.close()
    return redirect(url_for("locations"))


@app.post("/registry/device-types")
def create_device_type():
    return create_registry_lookup("device_types","device_type")


@app.post("/registry/manufacturers")
def create_manufacturer():
    return create_registry_lookup("manufacturers","manufacturer")


def create_registry_lookup(table: str, entity_type: str):
    validate_csrf(); name=request.form.get("name","").strip()
    if not name: abort(400)
    code=registry_code(name); connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute(f"INSERT INTO {table} (code,name) VALUES (?,?)",(code,name)); audit_registry(cursor,entity_type,cursor.lastrowid,"created",{"code":code,"name":name}); connection.commit()
    except mariadb.IntegrityError: connection.rollback(); session["registry_notice"]={"kind":"warning","message":"Ez a törzsadat már létezik."}
    finally: cursor.close(); connection.close()
    return redirect(url_for("locations"))


def device_form_values() -> dict[str, Any]:
    room_id=optional_int(request.form.get("room_id")); zone_id=optional_int(request.form.get("zone_id"))
    interval=int(request.form.get("poll_interval_minutes","10"))*60
    if not 60 <= interval <= 86400: raise ValueError
    return {
      "name":request.form["name"].strip(),"source_system":request.form["source_system"],
      "source_device_id":request.form["source_device_id"].strip(),"room_id":room_id,"zone_id":zone_id,
      "device_type_id":int(request.form["device_type_id"]),"manufacturer_id":int(request.form["manufacturer_id"]),
      "access_mode":request.form["access_mode"],"capability_mode":request.form["capability_mode"],
      "integration_role":request.form["integration_role"],
      "hostname":request.form.get("hostname","").strip() or None,"expected_ip":request.form.get("expected_ip","").strip() or None,
      "mac_address":request.form.get("mac_address","").strip().lower() or None,"ip_assignment":request.form["ip_assignment"],
      "polling_enabled":int(request.form.get("polling_enabled")=="1"),"control_enabled":int(request.form.get("control_enabled")=="1"),
      "poll_interval_seconds":interval,"min_target":request.form.get("min_target","").strip() or None,
      "max_target":request.form.get("max_target","").strip() or None,"is_active":int(request.form.get("is_active")=="1"),
    }


def save_device_capabilities(cursor, device_id: int):
    cursor.execute("DELETE FROM device_supported_modes WHERE device_id=?",(device_id,))
    cursor.execute("DELETE FROM device_supported_fan_speeds WHERE device_id=?",(device_id,))
    cursor.execute("DELETE FROM device_supported_features WHERE device_id=?",(device_id,))
    for code,label in (("cool","Hűtés"),("heat","Fűtés"),("dry","Szárítás"),("fan","Ventilátor"),("auto","Automata")):
        if code in request.form.getlist("modes"): cursor.execute("INSERT INTO device_supported_modes VALUES (?,?,?)",(device_id,code,label))
    for code,label in (("auto","Automata"),("low","Alacsony"),("medium_low","Közepesen alacsony"),("medium","Közepes"),("medium_high","Középmagas"),("high","Magas")):
        if code in request.form.getlist("fan_speeds"): cursor.execute("INSERT INTO device_supported_fan_speeds VALUES (?,?,?)",(device_id,code,label))
    for code,label in (("swing","Hinta"),("super","Gyors üzem"),("quiet","Csendes"),("sleep","Alvás")):
        if code in request.form.getlist("features"): cursor.execute("INSERT INTO device_supported_features VALUES (?,?,?)",(device_id,code,label))


@app.post("/registry/devices")
def create_device():
    validate_csrf()
    try: values=device_form_values()
    except (KeyError,ValueError): abort(400)
    if not values["name"] or not values["source_device_id"]: abort(400)
    connection=connect_database(); cursor=connection.cursor(); created=False
    try:
        if values["room_id"]:
            cursor.execute("SELECT zone_id FROM rooms WHERE id=? AND is_active=1",(values["room_id"],)); row=cursor.fetchone()
            if row is None: abort(400)
            values["zone_id"]=row[0]
        cursor.execute("""INSERT INTO devices (room_id,zone_id,source_system,source_device_id,hostname,expected_ip,mac_address,name,device_type,device_type_id,manufacturer_id,access_mode,capability_mode,integration_role,ip_assignment,polling_enabled,control_enabled,poll_interval_seconds,min_target_temperature_c,max_target_temperature_c,is_active)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",(values["room_id"],values["zone_id"],values["source_system"],values["source_device_id"],values["hostname"],values["expected_ip"],values["mac_address"],values["name"],"other",values["device_type_id"],values["manufacturer_id"],values["access_mode"],values["capability_mode"],values["integration_role"],values["ip_assignment"],values["polling_enabled"],values["control_enabled"],values["poll_interval_seconds"],values["min_target"],values["max_target"],values["is_active"])); device_id=cursor.lastrowid
        save_device_capabilities(cursor,device_id); audit_registry(cursor,"device",device_id,"created",values); connection.commit(); created=True
    except mariadb.IntegrityError as error: connection.rollback(); session["registry_notice"]={"kind":"error","message":f"Az eszköz nem vehető fel: {error}"}
    finally: cursor.close(); connection.close()
    if created:
        try:
            sync_device_config(values)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            session["registry_notice"]={"kind":"warning","message":f"Az eszköz adatbázisba került, de a pollerkonfiguráció nem frissült: {error}"}
    return redirect(url_for("locations"))


@app.post("/registry/devices/<int:device_id>")
def save_device(device_id: int):
    validate_csrf()
    try: values=device_form_values()
    except (KeyError,ValueError): abort(400)
    connection=connect_database(); cursor=connection.cursor()
    try:
        cursor.execute("SELECT room_id FROM devices WHERE id=? FOR UPDATE",(device_id,)); row=cursor.fetchone()
        if row is None: abort(404)
        if values["room_id"]:
            cursor.execute("SELECT zone_id FROM rooms WHERE id=? AND is_active=1",(values["room_id"],)); room=cursor.fetchone()
            if room is None: abort(400)
            values["zone_id"]=room[0]
        if row[0] != values["room_id"]:
            cursor.execute("UPDATE device_room_history SET valid_to=CURRENT_TIMESTAMP(3) WHERE device_id=? AND valid_to IS NULL",(device_id,))
            cursor.execute("UPDATE sensors SET room_id=? WHERE device_id=?",(values["room_id"],device_id))
            if values["room_id"]: cursor.execute("INSERT INTO device_room_history (device_id,room_id,change_reason) VALUES (?,?,?)",(device_id,values["room_id"],request.form.get("reason") or 'Nyilvántartási módosítás'))
        cursor.execute("""UPDATE devices SET room_id=?,zone_id=?,name=?,source_system=?,source_device_id=?,device_type_id=?,manufacturer_id=?,access_mode=?,capability_mode=?,integration_role=?,hostname=?,expected_ip=?,mac_address=?,ip_assignment=?,polling_enabled=?,control_enabled=?,poll_interval_seconds=?,min_target_temperature_c=?,max_target_temperature_c=?,is_active=? WHERE id=?""",(values["room_id"],values["zone_id"],values["name"],values["source_system"],values["source_device_id"],values["device_type_id"],values["manufacturer_id"],values["access_mode"],values["capability_mode"],values["integration_role"],values["hostname"],values["expected_ip"],values["mac_address"],values["ip_assignment"],values["polling_enabled"],values["control_enabled"],values["poll_interval_seconds"],values["min_target"],values["max_target"],values["is_active"],device_id))
        save_device_capabilities(cursor,device_id); audit_registry(cursor,"device",device_id,"updated",values)
        connection.commit()
    except Exception: connection.rollback(); raise
    finally: cursor.close(); connection.close()
    try:
        sync_device_config(values)
        session["registry_notice"]={"kind":"success","message":f"{values['name']} adatai és pollerkonfigurációja elmentve."}
    except (OSError, ValueError, json.JSONDecodeError) as error:
        session["registry_notice"]={"kind":"warning","message":f"Az adatbázis frissült, de a pollerkonfiguráció nem: {error}"}
    return redirect(url_for("locations"))


@app.post("/registry/devices/<int:device_id>/reset-measurements")
def reset_device_measurements(device_id: int):
    """Delete an individual device's measurements without deleting its registry data."""
    validate_csrf()
    try:
        with polling_cycle_lock():
            connection = connect_database()
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "SELECT name,source_system FROM devices WHERE id=? FOR UPDATE",
                    (device_id,),
                )
                device = cursor.fetchone()
                if device is None:
                    abort(404)
                device_name, source_system = str(device[0]), str(device[1])

                cursor.execute(
                    "SELECT id FROM sensors WHERE device_id=? FOR UPDATE", (device_id,)
                )
                sensor_ids = [int(row[0]) for row in cursor.fetchall()]
                deleted_count = 0
                if sensor_ids:
                    deleted_count = delete_sensor_measurements(cursor, sensor_ids)

                # A collector restart must not recreate the deleted Zigbee
                # measurements from its last-value cache.
                if source_system == "zigbee2mqtt":
                    cursor.execute(
                        """DELETE FROM zigbee2mqtt_property_cache
                           WHERE device_id=?
                             AND property_name IN ('temperature','humidity','battery')""",
                        (device_id,),
                    )
                    cursor.execute(
                        """DELETE o FROM outdoor_temperature_observations o
                           JOIN outdoor_temperature_sources s ON s.id=o.source_id
                           WHERE s.source_type='zigbee2mqtt'
                             AND CAST(JSON_UNQUOTE(JSON_EXTRACT(
                                   s.configuration,'$.device_id')) AS UNSIGNED)=?""",
                        (device_id,),
                    )

                audit_registry(
                    cursor, "device", device_id, "measurements_reset",
                    {"deleted_readings": deleted_count},
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()
                connection.close()
    except PollCycleBusy:
        session["registry_notice"] = {
            "kind": "warning",
            "message": "A mérések most nem törölhetők, mert lekérdezés van folyamatban.",
        }
        return redirect(url_for("locations", _anchor=f"device-{device_id}"))

    session["registry_notice"] = {
        "kind": "success",
        "message": (
            f"{device_name}: {deleted_count} mérési rekordot töröltünk. "
            "Az eszköz, a szenzorok és a helytörténet megmaradtak."
        ),
    }
    return redirect(url_for("locations", _anchor=f"device-{device_id}"))


@app.post("/registry/reset-poll-intervals")
def reset_poll_intervals():
    validate_csrf(); connection=connect_database(); cursor=connection.cursor()
    try:
        default_seconds=int(os.getenv("DEFAULT_POLL_INTERVAL_MINUTES","10"))*60
        cursor.execute("UPDATE devices SET poll_interval_seconds=? WHERE polling_enabled=1 AND access_mode='network'",(default_seconds,))
        audit_registry(cursor,"device",0,"poll_intervals_reset",{"seconds":default_seconds,"affected":cursor.rowcount}); connection.commit()
    except Exception: connection.rollback(); raise
    finally: cursor.close(); connection.close()
    session["registry_notice"]={"kind":"success","message":f"Minden hálózaton lekérdezett eszköz alapértéke ismét {default_seconds//60} perc."}
    return redirect(url_for("locations"))


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
    resolve_daily_plan(device_id, local_now().date())
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
    resolve_daily_plan(device_id,local_now().date())
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
    if assignment_date==local_now().date(): resolve_daily_plan(device_id,assignment_date)
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
    except (KeyError, ValueError):
        abort(400)

    next_due = None

    connection = connect_database()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT 1 FROM devices
            WHERE id = ? AND is_active = 1
              AND (source_system = 'connectlife' OR device_type = 'boiler')
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
