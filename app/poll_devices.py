#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import json
import os
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
    0: "auto", 5: "low", 6: "medium_low", 7: "medium",
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
    local = [item for item in devices if item.source_system in {"esp32", "computherm"}]
    connectlife = [item for item in devices if item.source_system == "connectlife"]
    tasks = []
    for item in local:
        function = poll_esp32 if item.source_system == "esp32" else poll_computherm
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
