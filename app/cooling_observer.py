from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class CoolingParameters:
    room_on_c: float = 27.5
    room_off_c: float = 27.0
    outdoor_enable_c: float = 28.1
    outdoor_disable_c: float = 27.1
    minimum_room_c: float = 25.0
    minimum_target_c: float = 25.0
    hisense_weight: float = 0.20
    computherm_weight: float = 0.10
    max_data_age_minutes: int = 180
    close_stabilization_minutes: int = 10


def _number(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)).replace(",", "."))


def parameters_from_environment() -> CoolingParameters:
    return CoolingParameters(
        room_on_c=_number("COOLING_ROOM_REQUEST_ON_C", 27.5),
        room_off_c=_number("COOLING_ROOM_REQUEST_OFF_C", 27.0),
        outdoor_enable_c=_number("COOLING_OUTDOOR_ENABLE_C", 28.1),
        outdoor_disable_c=_number("COOLING_OUTDOOR_DISABLE_C", 27.1),
        minimum_room_c=_number("COOLING_MIN_ROOM_TEMPERATURE_C", 25.0),
        minimum_target_c=_number("COOLING_MIN_TARGET_C", 25.0),
        hisense_weight=_number("COOLING_HISENSE_WEIGHT", 0.20),
        computherm_weight=_number("COOLING_COMPUTHERM_WEIGHT", 0.10),
        max_data_age_minutes=int(_number("COOLING_MAX_DATA_AGE_MINUTES", 180)),
        close_stabilization_minutes=int(
            _number("COOLING_WINDOW_CLOSE_STABILIZATION_MINUTES", 10)
        ),
    )


def _fresh(device: dict[str, Any] | None, now: datetime, maximum_age: timedelta) -> bool:
    if not device or device.get("temperature_c") is None:
        return False
    observed_at = device.get("measurement_at")
    return bool(observed_at and now - observed_at <= maximum_age)


def _action_temperature(
    primary: dict[str, Any],
    hisense: dict[str, Any] | None,
    computherm: dict[str, Any] | None,
    params: CoolingParameters,
    now: datetime,
) -> tuple[float, list[dict[str, Any]]]:
    maximum_age = timedelta(minutes=params.max_data_age_minutes)
    primary_value = float(primary["temperature_c"])
    value = primary_value
    sources = [{"name": primary["name"], "value": primary_value, "weight": 1.0}]
    for device, weight in (
        (hisense, params.hisense_weight),
        (computherm, params.computherm_weight),
    ):
        if weight <= 0 or not _fresh(device, now, maximum_age):
            continue
        source_value = float(device["temperature_c"])
        value += weight * (source_value - primary_value)
        sources[0]["weight"] = round(sources[0]["weight"] - weight, 10)
        sources.append({"name": device["name"], "value": source_value, "weight": weight})
    return round(value, 2), sources


def evaluate_room(
    devices: list[dict[str, Any]],
    outdoor: dict[str, Any] | None,
    *,
    now: datetime | None = None,
    params: CoolingParameters | None = None,
) -> dict[str, Any] | None:
    """Return a read-only cooling recommendation for one upstairs room."""
    now = now or datetime.now(UTC).replace(tzinfo=None)
    params = params or parameters_from_environment()
    primary = next(
        (
            item
            for item in devices
            if item.get("source_system") == "zigbee2mqtt"
            and item.get("device_type") == "temperature_sensor"
        ),
        None,
    )
    hisense = next(
        (item for item in devices if item.get("source_system") == "connectlife"), None
    )
    computherm = next(
        (item for item in devices if item.get("source_system") == "computherm"), None
    )
    if primary is None or hisense is None:
        return None

    maximum_age = timedelta(minutes=params.max_data_age_minutes)
    advice: dict[str, Any] = {
        "primary_device_id": primary["id"],
        "climate_device_id": hisense["id"],
        "status": "insufficient_data",
        "status_label": "Nincs elég friss adat",
        "cooling_demand": False,
        "blockers": [],
        "calculation_version": "cooling-observer-v1",
    }
    if not _fresh(primary, now, maximum_age):
        advice["blockers"].append("A mérvadó Zigbee-hőmérséklet hiányzik vagy túl régi.")
        return advice

    action_temperature, sources = _action_temperature(
        primary, hisense, computherm, params, now
    )
    cooling_active = bool(hisense.get("power")) and hisense.get("mode") == "cool"
    room_threshold = params.room_off_c if cooling_active else params.room_on_c
    cooling_demand = (
        action_temperature >= room_threshold
        and action_temperature > params.minimum_room_c
    )
    advice.update(
        action_temperature_c=action_temperature,
        sources=sources,
        cooling_active=cooling_active,
        cooling_demand=cooling_demand,
        room_threshold_c=room_threshold,
        target_correction_needed=(
            hisense.get("target_temperature_c") is not None
            and float(hisense["target_temperature_c"]) < params.minimum_target_c
        ),
        minimum_target_c=params.minimum_target_c,
    )

    if outdoor is None or outdoor.get("temperature_c") is None:
        advice["blockers"].append("Nincs friss kültéri hőmérséklet.")
        outdoor_value = None
    else:
        outdoor_value = float(outdoor["temperature_c"])
        outdoor_threshold = (
            params.outdoor_disable_c if cooling_active else params.outdoor_enable_c
        )
        advice["outdoor_temperature_c"] = outdoor_value
        advice["outdoor_threshold_c"] = outdoor_threshold
        if outdoor_value < outdoor_threshold:
            advice["blockers"].append(
                f"A kültéri hőmérséklet {outdoor_threshold:.1f} °C alatt van."
            )

    contacts = [
        item
        for item in devices
        if item.get("source_system") == "zigbee2mqtt"
        and item.get("device_type") == "contact_sensor"
    ]
    unavailable_contacts = [item for item in contacts if item.get("online") is False]
    open_contacts = [
        item
        for item in contacts
        if item.get("zigbee_contact_closed") is not None
        and not bool(item.get("zigbee_contact_closed"))
    ]
    unknown_contacts = [item for item in contacts if item.get("zigbee_contact_closed") is None]
    if unavailable_contacts:
        advice["blockers"].append(
            "Nem elérhető nyílászáró-érzékelő: "
            + ", ".join(item["name"] for item in unavailable_contacts)
            + "."
        )
    if open_contacts:
        advice["blockers"].append(
            "Nyitott nyílászáró: " + ", ".join(item["name"] for item in open_contacts) + "."
        )
    elif unknown_contacts:
        advice["blockers"].append(
            "Ismeretlen nyílászáró-állapot: "
            + ", ".join(item["name"] for item in unknown_contacts)
            + "."
        )
    elif contacts and params.close_stabilization_minutes > 0:
        latest_change = max(
            (
                item.get("zigbee_contact_observed_at")
                for item in contacts
                if item.get("zigbee_contact_observed_at") is not None
            ),
            default=None,
        )
        if latest_change and now - latest_change < timedelta(
            minutes=params.close_stabilization_minutes
        ):
            advice["blockers"].append(
                f"A legutóbbi nyílászáró-zárás utáni {params.close_stabilization_minutes} perces várakozás tart."
            )

    if cooling_active:
        if not cooling_demand or advice["blockers"]:
            advice["status"] = "would_stop"
            advice["status_label"] = "Leállítaná a hűtést"
        else:
            advice["status"] = "would_keep_on"
            advice["status_label"] = "Folytatná a hűtést"
    elif cooling_demand and advice["blockers"]:
        advice["status"] = "blocked"
        advice["status_label"] = "Hűtést kér, de blokkolva"
    elif cooling_demand:
        advice["status"] = "would_start"
        advice["status_label"] = "Elindítaná a hűtést"
    else:
        advice["status"] = "would_keep_off"
        advice["status_label"] = "Nem indítana hűtést"
    return advice


def annotate_upstairs_cooling(
    devices: list[dict[str, Any]], outdoor: dict[str, Any] | None
) -> list[dict[str, Any]]:
    by_room: dict[int, list[dict[str, Any]]] = {}
    for device in devices:
        if device.get("zone_name") == "Emelet" and device.get("room_id") is not None:
            by_room.setdefault(int(device["room_id"]), []).append(device)

    advice_items = []
    now = datetime.now(UTC).replace(tzinfo=None)
    params = parameters_from_environment()
    for room_devices in by_room.values():
        advice = evaluate_room(room_devices, outdoor, now=now, params=params)
        if advice is None:
            continue
        advice_items.append(advice)
        for device in room_devices:
            if device["id"] == advice["primary_device_id"]:
                device["cooling_advice"] = advice
                device["cooling_action_temperature_c"] = advice.get("action_temperature_c")
    return advice_items
