from __future__ import annotations

import math
import os
from datetime import UTC, datetime, timedelta
from typing import Any


FAN_SPEED_LABELS = {
    "auto": "Automata",
    "quiet": "Csendes",
    "low": "Alacsony",
    "medium_low": "Közepesen alacsony",
    "medium": "Közepes",
    "medium_high": "Közepesen magas",
    "high": "Magas",
}


def _number(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)).replace(",", "."))


def _contact_blockers(
    room_devices: list[dict[str, Any]],
    *,
    now: datetime,
    close_stabilization_minutes: int,
) -> list[str]:
    contacts = [
        item
        for item in room_devices
        if item.get("source_system") == "zigbee2mqtt"
        and item.get("device_type") == "contact_sensor"
        and item.get("opening_role", "external") == "external"
    ]
    unavailable = [item for item in contacts if item.get("online") is False]
    opened = [
        item
        for item in contacts
        if item.get("zigbee_contact_closed") is not None
        and not bool(item.get("zigbee_contact_closed"))
    ]
    unknown = [item for item in contacts if item.get("zigbee_contact_closed") is None]
    blockers: list[str] = []
    if unavailable:
        blockers.append(
            "Nem elérhető nyílászáró-érzékelő: "
            + ", ".join(item["name"] for item in unavailable)
            + "."
        )
    if opened:
        blockers.append(
            "Nyitott nyílászáró: "
            + ", ".join(item["name"] for item in opened)
            + "."
        )
    elif unknown:
        blockers.append(
            "Ismeretlen nyílászáró-állapot: "
            + ", ".join(item["name"] for item in unknown)
            + "."
        )
    elif contacts and close_stabilization_minutes > 0:
        latest_change = max(
            (
                item.get("zigbee_contact_observed_at")
                for item in contacts
                if item.get("zigbee_contact_observed_at") is not None
            ),
            default=None,
        )
        if latest_change and now - latest_change < timedelta(
            minutes=close_stabilization_minutes
        ):
            blockers.append(
                "A legutóbbi nyílászáró-zárás utáni "
                f"{close_stabilization_minutes} perces várakozás tart."
            )
    return blockers


def manual_climate_guard(
    climate_device: dict[str, Any],
    devices: list[dict[str, Any]],
    outdoor: dict[str, Any] | None,
    mode: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate hard opening blocks and overridable outdoor limits."""
    if mode not in {"heat", "cool"}:
        raise ValueError("Nem támogatott klíma-üzemmód.")
    now = now or datetime.now(UTC).replace(tzinfo=None)
    room_id = climate_device.get("room_id")
    room_devices = [item for item in devices if item.get("room_id") == room_id]
    if mode == "heat":
        close_wait = int(_number("HEATING_WINDOW_CLOSE_STABILIZATION_MINUTES", 10))
        target_min = 16
        target_max = math.floor(_number("HEATING_MAX_TARGET_C", 22))
        outdoor_limit = _number("HEATING_CLIMATE_MIN_OUTDOOR_C", 5.0)
        limit_label = "klímás fűtés kültéri alsó határa"
        outdoor_disallowed = (
            outdoor is None
            or outdoor.get("temperature_c") is None
            or float(outdoor["temperature_c"]) < outdoor_limit
        )
    else:
        close_wait = int(_number("COOLING_WINDOW_CLOSE_STABILIZATION_MINUTES", 10))
        target_min = math.ceil(_number("COOLING_MIN_TARGET_C", 25))
        target_max = 30
        outdoor_limit = _number("COOLING_OUTDOOR_ENABLE_C", 28.1)
        limit_label = "hűtés kültéri indítási határa"
        outdoor_disallowed = (
            outdoor is None
            or outdoor.get("temperature_c") is None
            or float(outdoor["temperature_c"]) < outdoor_limit
        )

    blockers = _contact_blockers(
        room_devices,
        now=now,
        close_stabilization_minutes=close_wait,
    )
    outdoor_value = (
        float(outdoor["temperature_c"])
        if outdoor is not None and outdoor.get("temperature_c") is not None
        else None
    )
    if outdoor_value is None:
        outdoor_warning = (
            f"Nincs friss kültéri mérés; a {limit_label} ({outdoor_limit:.1f} °C) "
            "nem ellenőrizhető."
        )
    elif outdoor_disallowed:
        outdoor_warning = (
            f"A kültéri hőmérséklet {outdoor_value:.1f} °C, miközben a "
            f"{limit_label} {outdoor_limit:.1f} °C."
        )
    else:
        outdoor_warning = None

    return {
        "mode": mode,
        "hard_blocked": bool(blockers),
        "blockers": blockers,
        "outdoor_override_required": bool(outdoor_disallowed),
        "outdoor_warning": outdoor_warning,
        "outdoor_temperature_c": outdoor_value,
        "outdoor_limit_c": outdoor_limit,
        "target_min_c": target_min,
        "target_max_c": target_max,
    }


def annotate_manual_climate_controls(
    devices: list[dict[str, Any]],
    outdoor: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(UTC).replace(tzinfo=None)
    for device in devices:
        if (
            device.get("source_system") != "connectlife"
            or not device.get("control_enabled")
            or device.get("room_id") is None
        ):
            continue
        selected_mode = device.get("mode") if device.get("mode") in {"heat", "cool"} else "heat"
        controls = {
            mode: manual_climate_guard(device, devices, outdoor, mode, now=now)
            for mode in ("heat", "cool")
        }
        selected_guard = controls[selected_mode]
        current_target = device.get("target_temperature_c")
        if current_target is None or not (
            selected_guard["target_min_c"]
            <= float(current_target)
            <= selected_guard["target_max_c"]
        ):
            current_target = (
                selected_guard["target_max_c"]
                if selected_mode == "heat"
                else selected_guard["target_min_c"]
            )
        device["manual_climate_control"] = {
            "selected_mode": selected_mode,
            "selected_target_c": int(float(current_target)),
            "selected_fan_speed": (
                device.get("fan_speed")
                if device.get("fan_speed") in FAN_SPEED_LABELS
                else "medium"
            ),
            "modes": controls,
            "fan_speeds": FAN_SPEED_LABELS,
        }
