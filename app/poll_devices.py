#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import platform
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import broadlink
from connectlife.api import ConnectLifeApi
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "devices.json"
CONNECTLIFE_MODE = {0: "fan", 1: "heat", 2: "cool", 3: "dry", 4: "auto"}
CONNECTLIFE_FAN_SPEED = {
    0: "auto", 1: "quiet", 5: "low", 6: "medium_low", 7: "medium",
    8: "medium_high", 9: "high",
}


@dataclass(frozen=True)
class DeviceConfig:
    source_system: str
    hostname: str
    expected_ip: str
    mac_address: str
    device_id: str
    enabled: bool = True
    connectlife_name: str | None = None
    auid: str | None = None
    device_type_code: str | None = None
    local_hostname: str | None = None
    metrics_transport: str = "auto"
    ssh_user: str = "automation-monitor"
    ssh_identity_file: str = "/var/lib/automation/.ssh/id_ed25519_system_metrics"
    ssh_known_hosts_file: str = "/var/lib/automation/.ssh/known_hosts"


@dataclass
class PollResult:
    source_system: str
    device_id: str
    hostname: str
    observed_at: str
    success: bool
    duration_ms: int = 0
    measurements: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] | None = None
    identity: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def load_devices(path: Path) -> list[DeviceConfig]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported device configuration schema")
    devices = [DeviceConfig(**item) for item in data["devices"]]
    identities = [(item.source_system, item.device_id) for item in devices]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate source_system/device_id in device configuration")
    return [item for item in devices if item.enabled]


def failed(config: DeviceConfig, code: str, error: Exception | str) -> PollResult:
    return PollResult(
        source_system=config.source_system,
        device_id=config.device_id,
        hostname=config.hostname,
        observed_at=utc_now(),
        success=False,
        error_code=code,
        error_message=str(error),
    )


def poll_esp32(config: DeviceConfig, timeout: float) -> PollResult:
    started = time.monotonic()
    url = f"http://{config.hostname}/api/v1/measurements"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.load(response)
        if payload.get("device_id") != config.device_id:
            raise ValueError(f"Unexpected device_id: {payload.get('device_id')!r}")
        measurements = [
            {
                "sensor_id": item["sensor_id"],
                "sensor_type": item["sensor_type"],
                "unit": item["unit"],
                "value": item["value"],
                "quality": item["quality"],
                "error_code": item["error_code"],
                "raw": item,
            }
            for item in payload.get("readings", [])
        ]
        return PollResult(
            source_system=config.source_system,
            device_id=config.device_id,
            hostname=config.hostname,
            observed_at=utc_now(),
            success=True,
            duration_ms=round((time.monotonic() - started) * 1000),
            measurements=measurements,
            identity={"mac_address": config.mac_address},
        )
    except urllib.error.URLError as error:
        return failed(config, "http_unreachable", error)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return failed(config, "invalid_response", error)


def poll_computherm(config: DeviceConfig, timeout: float) -> PollResult:
    started = time.monotonic()
    try:
        device = broadlink.gendevice(
            int(config.device_type_code or "0", 0),
            (config.hostname, 80),
            bytes.fromhex(config.mac_address.replace(":", "")),
            name=config.device_id,
        )
        device.timeout = int(max(timeout, 1))
        device.auth()
        status = device.get_full_status()
        measurements = [
            {
                "sensor_id": f"computherm:{config.device_id}:room_temp",
                "sensor_type": "temperature",
                "unit": "celsius",
                "value": status.get("room_temp"),
                "quality": "good" if status.get("room_temp") is not None else "invalid",
                "error_code": None if status.get("room_temp") is not None else "missing_room_temp",
                "raw": {"property": "room_temp", "value": status.get("room_temp")},
            }
        ]
        state = {
            "power": bool(status.get("power")),
            "mode": "auto" if status.get("auto_mode") else "manual",
            "target_temperature_c": status.get("thermostat_temp"),
            "online": True,
            "active": bool(status.get("active")),
            "auto_mode": bool(status.get("auto_mode")),
            "raw": status,
        }
        return PollResult(
            source_system=config.source_system,
            device_id=config.device_id,
            hostname=config.hostname,
            observed_at=utc_now(),
            success=True,
            duration_ms=round((time.monotonic() - started) * 1000),
            measurements=measurements,
            state=state,
            identity={"mac_address": config.mac_address},
        )
    except Exception as error:  # BroadLink exposes several protocol exception types.
        return failed(config, type(error).__name__, error)


def poll_tasmota(config: DeviceConfig, timeout: float) -> PollResult:
    """Read a Tasmota device without issuing any actuator command."""
    started = time.monotonic()
    url = f"http://{config.hostname}/cm?cmnd=Status%200"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.load(response)
        energy = payload["StatusSNS"]["ENERGY"]
        status = payload.get("StatusSTS", {})
        network = payload.get("StatusNET", {})
        fields = (
            ("power", "power", "Power", "watt"),
            ("apparent_power", "apparent_power", "ApparentPower", "volt_ampere"),
            ("reactive_power", "reactive_power", "ReactivePower", "var"),
            ("power_factor", "factor", "Factor", "ratio"),
            ("voltage", "voltage", "Voltage", "volt"),
            ("current", "current", "Current", "ampere"),
            ("energy_total", "total", "Total", "kilowatt_hour"),
            ("energy_today", "today", "Today", "kilowatt_hour"),
            ("energy_yesterday", "yesterday", "Yesterday", "kilowatt_hour"),
        )
        measurements = []
        for sensor_type, key, api_key, unit in fields:
            value = energy.get(api_key)
            raw = {"property": key, "value": value}
            if key == "total":
                raw["total_start_time"] = energy.get("TotalStartTime")
            measurements.append({
                "sensor_id": f"tasmota:{config.device_id}:{key}",
                "sensor_type": sensor_type,
                "unit": unit,
                "value": value,
                "quality": "good" if value is not None else "invalid",
                "error_code": None if value is not None else f"missing_{key}",
                "raw": raw,
            })
        return PollResult(
            source_system=config.source_system,
            device_id=config.device_id,
            hostname=config.hostname,
            observed_at=utc_now(),
            success=True,
            duration_ms=round((time.monotonic() - started) * 1000),
            measurements=measurements,
            state={
                "power": str(status.get("POWER", "")).upper() == "ON",
                "online": True,
                "active": float(energy.get("Power") or 0) > 0,
                "raw": status,
            },
            identity={
                "mac_address": network.get("Mac") or config.mac_address,
                "firmware_version": payload.get("StatusFWR", {}).get("Version"),
            },
        )
    except urllib.error.URLError as error:
        return failed(config, "http_unreachable", error)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return failed(config, "invalid_response", error)


def _read_temperature_file(path: Path) -> float | None:
    try:
        value = float(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    if abs(value) > 1000:
        value /= 1000
    return value if -50 <= value <= 150 else None


def read_linux_cpu_temperature(sys_class: Path = Path("/sys/class")) -> float | None:
    """Return the package CPU temperature from standard Linux sysfs interfaces."""
    hwmon_candidates: list[tuple[int, Path]] = []
    for directory in sorted((sys_class / "hwmon").glob("hwmon*")):
        try:
            driver = (directory / "name").read_text(encoding="utf-8").strip().lower()
        except OSError:
            continue
        if driver not in {"coretemp", "k10temp", "zenpower"}:
            continue
        for input_path in directory.glob("temp*_input"):
            label_path = input_path.with_name(input_path.name.replace("_input", "_label"))
            try:
                label = label_path.read_text(encoding="utf-8").strip().lower()
            except OSError:
                label = ""
            priority = 0 if any(word in label for word in ("package", "tctl")) else 1
            hwmon_candidates.append((priority, input_path))
    for _, path in sorted(hwmon_candidates, key=lambda item: (item[0], str(item[1]))):
        value = _read_temperature_file(path)
        if value is not None:
            return value

    thermal_candidates: list[tuple[int, Path]] = []
    for directory in sorted((sys_class / "thermal").glob("thermal_zone*")):
        try:
            zone_type = (directory / "type").read_text(encoding="utf-8").strip().lower()
        except OSError:
            continue
        if zone_type in {"x86_pkg_temp", "cpu-thermal", "cpu_thermal"}:
            thermal_candidates.append((0, directory / "temp"))
    for _, path in sorted(thermal_candidates, key=lambda item: (item[0], str(item[1]))):
        value = _read_temperature_file(path)
        if value is not None:
            return value
    return None


def _linux_measurements(config: DeviceConfig, payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_temperature = payload.get("cpu_temperature_c")
    cpu_temperature = None if raw_temperature is None else float(raw_temperature)
    if cpu_temperature is not None and not math.isfinite(cpu_temperature):
        raise ValueError("Non-finite CPU temperature")
    measurements = [{
        "sensor_id": f"linux:{config.device_id}:cpu_temperature",
        "sensor_type": "temperature",
        "unit": "celsius",
        "value": cpu_temperature,
        "quality": "good" if cpu_temperature is not None else "invalid",
        "error_code": None if cpu_temperature is not None else "cpu_temperature_unavailable",
        "raw": {"property": "cpu_temperature", "value": cpu_temperature},
    }]
    for period in ("1m", "5m", "15m"):
        value = float(payload[f"load_{period}"])
        if not math.isfinite(value):
            raise ValueError(f"Non-finite load_{period}")
        measurements.append({
            "sensor_id": f"linux:{config.device_id}:load_{period}",
            "sensor_type": f"load_{period}",
            "unit": "load",
            "value": round(float(value), 3),
            "quality": "good",
            "error_code": None,
            "raw": {"property": f"load_{period}", "value": value},
        })
    return measurements


def _local_linux_payload() -> dict[str, Any]:
    cpu_temperature = read_linux_cpu_temperature()
    load_1m, load_5m, load_15m = os.getloadavg()
    return {
        "schema_version": 1,
        "hostname": socket.gethostname().split(".", 1)[0],
        "kernel": platform.release(),
        "cpu_count": os.cpu_count(),
        "cpu_temperature_c": cpu_temperature,
        "load_1m": load_1m,
        "load_5m": load_5m,
        "load_15m": load_15m,
    }


def _remote_linux_payload(config: DeviceConfig, timeout: float) -> dict[str, Any]:
    target = config.expected_ip or config.hostname
    command = [
        "/usr/bin/ssh", "-T",
        "-i", config.ssh_identity_file,
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={max(1, round(timeout))}",
        "-o", "StrictHostKeyChecking=yes",
        "-o", f"UserKnownHostsFile={config.ssh_known_hosts_file}",
        f"{config.ssh_user}@{target}",
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, timeout=max(timeout + 2, 3), check=False
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or f"ssh exited with {completed.returncode}"
        raise ConnectionError(detail)
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Unsupported remote metrics response schema")
    return payload


def poll_linux_system(config: DeviceConfig, timeout: float) -> PollResult:
    """Collect Linux metrics locally or through a restricted SSH forced command."""
    started = time.monotonic()
    actual_hostname = socket.gethostname().split(".", 1)[0].casefold()
    expected_hostname = (config.local_hostname or config.hostname).split(".", 1)[0].casefold()
    transport = config.metrics_transport.casefold()
    if transport not in {"auto", "local", "ssh"}:
        return failed(config, "invalid_metrics_transport", transport)
    use_local = transport == "local" or (transport == "auto" and actual_hostname == expected_hostname)
    try:
        if use_local:
            if actual_hostname != expected_hostname:
                return failed(
                    config, "local_host_mismatch",
                    f"Configured for {expected_hostname}, running on {actual_hostname}",
                )
            payload = _local_linux_payload()
        else:
            payload = _remote_linux_payload(config, timeout)
        remote_hostname = str(payload.get("hostname", "")).split(".", 1)[0].casefold()
        if remote_hostname != expected_hostname:
            raise ValueError(
                f"Expected host {expected_hostname}, remote reported {remote_hostname or 'empty hostname'}"
            )
        measurements = _linux_measurements(config, payload)
    except subprocess.TimeoutExpired as error:
        return failed(config, "ssh_timeout", error)
    except (ConnectionError, OSError) as error:
        return failed(config, "ssh_failed", error)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        return failed(config, "invalid_response", error)

    return PollResult(
        source_system=config.source_system,
        device_id=config.device_id,
        hostname=config.hostname,
        observed_at=utc_now(),
        success=True,
        duration_ms=round((time.monotonic() - started) * 1000),
        measurements=measurements,
        identity={
            "hostname": payload["hostname"],
            "kernel": payload.get("kernel"),
            "cpu_count": payload.get("cpu_count"),
        },
    )


async def poll_connectlife(configs: list[DeviceConfig]) -> list[PollResult]:
    if not configs:
        return []
    username = os.getenv("CONNECTLIFE_USERNAME")
    password = os.getenv("CONNECTLIFE_PASSWORD")
    if not username or not password:
        return [failed(item, "missing_credentials", "CONNECTLIFE credentials are not set") for item in configs]

    started = time.monotonic()
    try:
        appliances = await ConnectLifeApi(username, password).get_appliances()
    except Exception as error:
        return [failed(item, type(error).__name__, error) for item in configs]

    by_wifi_id = {item.wifi_id.lower(): item for item in appliances if item.wifi_id}
    by_name = {item.device_nickname.casefold(): item for item in appliances}
    results: list[PollResult] = []
    for config in configs:
        appliance = by_wifi_id.get((config.auid or "").lower())
        if appliance is None and config.connectlife_name:
            appliance = by_name.get(config.connectlife_name.casefold())
        if appliance is None:
            results.append(failed(config, "device_not_found", "No matching ConnectLife appliance"))
            continue
        if config.connectlife_name and appliance.device_nickname.casefold() != config.connectlife_name.casefold():
            results.append(failed(config, "identity_mismatch", appliance.device_nickname))
            continue

        status = appliance.status_list
        temperature = status.get("f_temp_in")
        measurements = [{
            "sensor_id": f"connectlife:{config.device_id}:f_temp_in",
            "sensor_type": "temperature",
            "unit": "celsius",
            "value": temperature,
            "quality": "good" if temperature is not None else "invalid",
            "error_code": None if temperature is not None else "missing_f_temp_in",
            "raw": {"property": "f_temp_in", "value": temperature},
        }]
        state = {
            "power": bool(status.get("t_power")),
            "mode": CONNECTLIFE_MODE.get(status.get("t_work_mode"), "unknown"),
            "target_temperature_c": status.get("t_temp"),
            "fan_speed": CONNECTLIFE_FAN_SPEED.get(
                status.get("t_fan_speed"), str(status.get("t_fan_speed"))
            ),
            "fan_mute": bool(status.get("t_fan_mute")),
            "eco": bool(status.get("t_eco")),
            "sleep": status.get("t_sleep"),
            "super": bool(status.get("t_super")),
            "swing_up_down": bool(status.get("t_up_down")),
            "online": bool(appliance.offline_state),
            "raw": status,
        }
        results.append(PollResult(
            source_system=config.source_system,
            device_id=config.device_id,
            hostname=config.hostname,
            observed_at=utc_now(),
            success=True,
            duration_ms=round((time.monotonic() - started) * 1000),
            measurements=measurements,
            state=state,
            identity={
                "auid": config.auid,
                "connectlife_name": appliance.device_nickname,
            },
        ))
    return results


async def poll_all(devices: list[DeviceConfig], timeout: float) -> list[PollResult]:
    local = [
        item for item in devices
        if item.source_system in {"esp32", "computherm", "tasmota", "linux_system"}
    ]
    connectlife = [item for item in devices if item.source_system == "connectlife"]
    tasks = []
    for item in local:
        function = {
            "esp32": poll_esp32,
            "computherm": poll_computherm,
            "tasmota": poll_tasmota,
            "linux_system": poll_linux_system,
        }[item.source_system]
        tasks.append(asyncio.to_thread(function, item, timeout))
    local_results = await asyncio.gather(*tasks)
    cloud_results = await poll_connectlife(connectlife)
    return [*local_results, *cloud_results]


def json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Poll every configured home-automation device once.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--store", action="store_true", help="Persist results to MariaDB")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    results = await poll_all(load_devices(args.config), args.timeout)
    if args.store:
        from database import Database

        configs = {(item.source_system, item.device_id): item for item in load_devices(args.config)}
        database = Database()
        try:
            for result in results:
                config = configs[(result.source_system, result.device_id)]
                try:
                    database.persist(config, result, result.duration_ms)
                except Exception as error:
                    result.success = False
                    result.error_code = "database_error"
                    result.error_message = str(error)
        finally:
            database.close()
    output: Any = [asdict(item) for item in results]
    if args.summary:
        output = [
            {
                "source_system": item.source_system,
                "device_id": item.device_id,
                "success": item.success,
                "temperature": (
                    item.measurements[0].get("value") if item.measurements else None
                ),
                "online": item.state.get("online") if item.state else None,
                "error_code": item.error_code,
            }
            for item in results
        ]
    print(json.dumps(output, ensure_ascii=False, indent=2, default=json_default))
    return 0 if all(item.success for item in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
