from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import broadlink


DAY_NAMES_HU = {
    1: "Hétfő",
    2: "Kedd",
    3: "Szerda",
    4: "Csütörtök",
    5: "Péntek",
    6: "Szombat",
    7: "Vasárnap",
}


def connect_device(config: dict[str, Any], factory: Callable[..., Any] = broadlink.gendevice):
    device = factory(
        int(str(config["device_type_code"]), 0),
        (str(config["hostname"]), 80),
        bytes.fromhex(str(config["mac_address"]).replace(":", "")),
        name=str(config["source_device_id"]),
    )
    device.timeout = 5
    device.auth()
    return device


def snapshot(device: Any) -> dict[str, Any]:
    return dict(device.get_full_status())


def clock_details(state: dict[str, Any]) -> dict[str, Any]:
    """Return a display-safe CT400 clock extracted from a full status payload."""
    try:
        hour = int(state["hour"])
        minute = int(state["min"])
        second = int(state["sec"])
        day = int(state["dayofweek"])
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        return {"time": None, "day": None, "day_name": None}
    return {
        "time": f"{hour:02d}:{minute:02d}:{second:02d}",
        "day": day,
        "day_name": DAY_NAMES_HU.get(day, f"Ismeretlen ({day})"),
    }


def weekly_program(state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Normalize the six weekday and two weekend CT400 schedule entries."""
    result: dict[str, list[dict[str, Any]]] = {"weekday": [], "weekend": []}
    for group, expected_count in (("weekday", 6), ("weekend", 2)):
        entries = state.get(group)
        if not isinstance(entries, list):
            continue
        for entry in entries[:expected_count]:
            if not isinstance(entry, dict):
                continue
            try:
                hour = int(entry["start_hour"])
                minute = int(entry["start_minute"])
                temperature = float(entry["temp"])
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except (KeyError, TypeError, ValueError):
                continue
            result[group].append(
                {
                    "time": f"{hour:02d}:{minute:02d}",
                    "temperature_c": temperature,
                }
            )
    return result


def validate_weekly_program(
    weekday: list[dict[str, Any]],
    weekend: list[dict[str, Any]],
    *,
    minimum_temperature_c: float = 5.0,
    maximum_temperature_c: float = 35.0,
) -> dict[str, list[dict[str, Any]]]:
    """Validate and normalize the CT400's ordered 6+2 schedule entries."""
    program: dict[str, list[dict[str, Any]]] = {}
    for group, entries, expected_count in (
        ("weekday", weekday, 6),
        ("weekend", weekend, 2),
    ):
        if len(entries) != expected_count:
            raise ValueError(
                f"A {group} programnak pontosan {expected_count} periódust kell tartalmaznia."
            )
        normalized: list[dict[str, Any]] = []
        previous_minute: int | None = None
        for entry in entries:
            try:
                hour = int(entry["start_hour"])
                minute = int(entry["start_minute"])
                temperature = float(entry["temp"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("Érvénytelen Computherm-programérték.") from error
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("A periódus kezdőideje érvénytelen.")
            minute_of_day = hour * 60 + minute
            if previous_minute is not None and minute_of_day < previous_minute:
                raise ValueError(
                    "A periódusok kezdőidejének időrendben kell maradnia."
                )
            if not minimum_temperature_c <= temperature <= maximum_temperature_c:
                raise ValueError(
                    "A célhőmérséklet kívül esik a CT400 beállított határain."
                )
            if abs(temperature * 2 - round(temperature * 2)) > 0.0001:
                raise ValueError("A célhőmérséklet csak 0,5 °C-os lépésben adható meg.")
            normalized.append(
                {
                    "start_hour": hour,
                    "start_minute": minute,
                    "temp": temperature,
                }
            )
            previous_minute = minute_of_day
        program[group] = normalized
    return program


def set_weekly_program(
    device: Any,
    weekday: list[dict[str, Any]],
    weekend: list[dict[str, Any]],
    preflight: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """Write and verify the complete CT400 weekly program."""
    preflight = preflight or snapshot(device)
    requested = validate_weekly_program(
        weekday,
        weekend,
        minimum_temperature_c=float(preflight.get("svl", 5)),
        maximum_temperature_c=float(preflight.get("svh", 35)),
    )
    device.set_schedule(requested["weekday"], requested["weekend"])
    verified = snapshot(device)
    expected_display = {
        group: [
            {
                "time": f"{entry['start_hour']:02d}:{entry['start_minute']:02d}",
                "temperature_c": entry["temp"],
            }
            for entry in requested[group]
        ]
        for group in ("weekday", "weekend")
    }
    if weekly_program(verified) != expected_display:
        raise RuntimeError("A CT400 nem igazolta vissza a teljes heti programot.")
    return preflight, verified, requested


def sync_clock(
    device: Any,
    requested_local_time: datetime,
    preflight: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Set the CT400 clock and verify the result with an immediate read-back."""
    preflight = preflight or snapshot(device)
    device.set_time(
        requested_local_time.hour,
        requested_local_time.minute,
        requested_local_time.second,
        requested_local_time.isoweekday(),
    )
    verified = snapshot(device)
    clock = clock_details(verified)
    if clock["time"] is None:
        raise RuntimeError("A CT400 nem adott vissza ellenőrizhető időadatot.")
    observed_seconds = (
        int(verified["hour"]) * 3600
        + int(verified["min"]) * 60
        + int(verified["sec"])
    )
    requested_seconds = (
        requested_local_time.hour * 3600
        + requested_local_time.minute * 60
        + requested_local_time.second
    )
    drift = abs(observed_seconds - requested_seconds)
    drift = min(drift, 86400 - drift)
    if int(verified["dayofweek"]) != requested_local_time.isoweekday() or drift > 5:
        raise RuntimeError("A CT400 nem igazolta vissza a szinkronizált időt és napot.")
    return preflight, verified


def validate_powered(state: dict[str, Any]) -> None:
    if not bool(state.get("power")):
        raise RuntimeError("A Computherm ki van kapcsolva; a teszt nem indítható.")


def set_advanced_from(device: Any, state: dict[str, Any], *, svh: int | None = None) -> None:
    device.set_advanced(
        int(state["loop_mode"]), int(state["sensor"]), int(state["osv"]),
        int(state["dif"]), int(svh if svh is not None else state["svh"]),
        int(state["svl"]), float(state["room_temp_adj"]), int(state["fre"]),
        int(state["poweron"]),
    )


def start_test(
    device: Any, target_c: float, original: dict[str, Any] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    original = original or snapshot(device)
    validate_powered(original)
    if not 5 <= target_c <= 35:
        raise ValueError("A teszt célhőmérséklete 5 és 35 °C között lehet.")
    if target_c > float(original["svh"]):
        set_advanced_from(device, original, svh=int(target_c + 0.999))
    device.set_mode(0, int(original["loop_mode"]), int(original["sensor"]))
    device.set_temp(target_c)
    verified = snapshot(device)
    validate_powered(verified)
    if bool(verified.get("auto_mode")) or float(verified["thermostat_temp"]) != target_c:
        raise RuntimeError("A Computherm nem igazolta vissza a kézi teszt-célértéket.")
    return original, verified


def suppress_heat(device: Any, original: dict[str, Any]) -> dict[str, Any]:
    current = snapshot(device)
    validate_powered(current)
    target = max(float(current.get("svl", 5)), float(current["room_temp"]) - 1.0)
    device.set_mode(0, int(current["loop_mode"]), int(current["sensor"]))
    device.set_temp(target)
    return snapshot(device)


def restore_test(device: Any, original: dict[str, Any]) -> dict[str, Any]:
    current = snapshot(device)
    validate_powered(current)
    set_advanced_from(device, original)
    device.set_temp(float(original["thermostat_temp"]))
    device.set_mode(
        int(bool(original["auto_mode"])), int(original["loop_mode"]), int(original["sensor"])
    )
    verified = snapshot(device)
    validate_powered(verified)
    if bool(verified.get("auto_mode")) != bool(original["auto_mode"]):
        raise RuntimeError("A Computherm nem igazolta vissza az eredeti szabályozási módot.")
    if float(verified["thermostat_temp"]) != float(original["thermostat_temp"]):
        raise RuntimeError("A Computherm nem igazolta vissza az eredeti célhőmérsékletet.")
    return verified
