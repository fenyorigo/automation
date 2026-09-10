from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class HeatingParameters:
    room_on_c: float = 20.0
    room_off_c: float = 20.5
    maximum_room_c: float = 22.0
    maximum_target_c: float = 22.0
    climate_min_outdoor_c: float = 5.0
    minimum_cop: float = 2.5
    hisense_weight: float = 0.20
    computherm_weight: float = 0.10
    max_data_age_minutes: int = 180
    close_stabilization_minutes: int = 10


def _number(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)).replace(",", "."))


def parameters_from_environment() -> HeatingParameters:
    return HeatingParameters(
        room_on_c=_number("HEATING_ROOM_REQUEST_ON_C", 20.0),
        room_off_c=_number("HEATING_ROOM_REQUEST_OFF_C", 20.5),
        maximum_room_c=_number("HEATING_MAX_ROOM_TEMPERATURE_C", 22.0),
        maximum_target_c=_number("HEATING_MAX_TARGET_C", 22.0),
        climate_min_outdoor_c=_number("HEATING_CLIMATE_MIN_OUTDOOR_C", 5.0),
        minimum_cop=_number("HEATING_MIN_COP", 2.5),
        hisense_weight=_number("HEATING_HISENSE_WEIGHT", 0.20),
        computherm_weight=_number("HEATING_COMPUTHERM_WEIGHT", 0.10),
        max_data_age_minutes=int(_number("HEATING_MAX_DATA_AGE_MINUTES", 180)),
        close_stabilization_minutes=int(
            _number("HEATING_WINDOW_CLOSE_STABILIZATION_MINUTES", 10)
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
    params: HeatingParameters,
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
    gas_heating_active: bool = False,
    now: datetime | None = None,
    params: HeatingParameters | None = None,
) -> dict[str, Any] | None:
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

    advice: dict[str, Any] = {
        "room_id": primary["room_id"],
        "room_name": primary["room_name"],
        "primary_device_id": primary["id"],
        "climate_device_id": hisense["id"],
        "status": "insufficient_data",
        "status_label": "Nincs elég friss fűtési adat",
        "heating_demand": False,
        "blockers": [],
        "calculation_version": "heating-observer-v1",
    }
    maximum_age = timedelta(minutes=params.max_data_age_minutes)
    if not _fresh(primary, now, maximum_age):
        advice["blockers"].append("A mérvadó Zigbee-hőmérséklet hiányzik vagy túl régi.")
        return advice

    action_temperature, sources = _action_temperature(
        primary, hisense, computherm, params, now
    )
    climate_heating_active = bool(hisense.get("power")) and hisense.get("mode") == "heat"
    heating_active = climate_heating_active or gas_heating_active
    room_threshold = params.room_off_c if heating_active else params.room_on_c
    heating_demand = (
        action_temperature <= room_threshold
        and action_temperature < params.maximum_room_c
    )
    climate_fresh = bool(hisense.get("poll_success")) and _fresh(
        hisense, now, maximum_age
    )
    advice.update(
        action_temperature_c=action_temperature,
        sources=sources,
        heating_demand=heating_demand,
        heating_active=heating_active,
        climate_heating_active=climate_heating_active,
        room_threshold_c=room_threshold,
        climate_available=climate_fresh,
        target_too_high=(
            hisense.get("mode") == "heat"
            and hisense.get("target_temperature_c") is not None
            and float(hisense["target_temperature_c"]) > params.maximum_target_c
        ),
        maximum_target_c=params.maximum_target_c,
    )

    if outdoor is None or outdoor.get("temperature_c") is None:
        advice["outdoor_temperature_c"] = None
        advice["climate_temperature_eligible"] = False
        advice["blockers"].append("Nincs friss kültéri hőmérséklet.")
    else:
        outdoor_value = float(outdoor["temperature_c"])
        advice["outdoor_temperature_c"] = outdoor_value
        advice["climate_temperature_eligible"] = (
            outdoor_value >= params.climate_min_outdoor_c
        )

    contacts = [
        item
        for item in devices
        if item.get("source_system") == "zigbee2mqtt"
        and item.get("device_type") == "contact_sensor"
    ]
    unavailable = [item for item in contacts if item.get("online") is False]
    opened = [
        item
        for item in contacts
        if item.get("zigbee_contact_closed") is not None
        and not bool(item.get("zigbee_contact_closed"))
    ]
    unknown = [item for item in contacts if item.get("zigbee_contact_closed") is None]
    if unavailable:
        advice["blockers"].append(
            "Nem elérhető nyílászáró-érzékelő: "
            + ", ".join(item["name"] for item in unavailable)
            + "."
        )
    if opened:
        advice["blockers"].append(
            "Nyitott nyílászáró: " + ", ".join(item["name"] for item in opened) + "."
        )
    elif unknown:
        advice["blockers"].append(
            "Ismeretlen nyílászáró-állapot: "
            + ", ".join(item["name"] for item in unknown)
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

    if not heating_demand:
        advice["status"] = "no_demand"
        advice["status_label"] = "Nem kér fűtést"
    elif advice["blockers"]:
        advice["status"] = "blocked"
        advice["status_label"] = "Fűtést kér, de blokkolva"
    elif climate_fresh and advice["climate_temperature_eligible"]:
        advice["status"] = "climate_eligible"
        advice["status_label"] = "Klímával fűthető"
    else:
        advice["status"] = "gas_required"
        advice["status_label"] = "Gázfűtést igényel"
    return advice


def annotate_upstairs_heating(
    devices: list[dict[str, Any]], outdoor: dict[str, Any] | None
) -> dict[str, Any] | None:
    thermostat = next(
        (
            item
            for item in devices
            if item.get("source_system") == "computherm"
            and item.get("zone_name") == "Emelet"
        ),
        None,
    )
    boiler = next(
        (
            item
            for item in devices
            if item.get("source_system") == "manual" and item.get("device_type") == "boiler"
        ),
        None,
    )
    boiler_on = bool(boiler and boiler.get("manual_power_state"))
    thermostat_calling = bool(thermostat and thermostat.get("active"))
    gas_heating_active = boiler_on and thermostat_calling
    params = parameters_from_environment()
    now = datetime.now(UTC).replace(tzinfo=None)

    room_results: list[dict[str, Any]] = []
    room_ids = sorted(
        {
            int(item["room_id"])
            for item in devices
            if item.get("zone_name") == "Emelet" and item.get("room_id") is not None
        }
    )
    for room_id in room_ids:
        room_devices = [item for item in devices if item.get("room_id") == room_id]
        result = evaluate_room(
            room_devices,
            outdoor,
            gas_heating_active=gas_heating_active,
            now=now,
            params=params,
        )
        if result is None:
            continue
        room_results.append(result)
        primary = next(
            item for item in room_devices if item["id"] == result["primary_device_id"]
        )
        primary["heating_advice"] = result

    demanded = [item for item in room_results if item["heating_demand"]]
    actionable = [item for item in demanded if not item["blockers"]]
    gas_required = [item for item in actionable if item["status"] == "gas_required"]
    climate_rooms = [item for item in actionable if item["status"] == "climate_eligible"]
    blocked = [item for item in demanded if item["blockers"]]

    if not demanded:
        status = "would_stop" if gas_heating_active or any(
            item.get("climate_heating_active") for item in room_results
        ) else "no_demand"
        label = "Leállítaná az emeleti fűtést" if status == "would_stop" else "Nincs emeleti fűtési igény"
        preferred_source = "none"
    elif not actionable:
        status, label, preferred_source = "blocked", "Az emeleti fűtési igény blokkolva", "none"
    elif gas_required:
        status, label, preferred_source = "gas", "Gázfűtést választana", "gas"
    else:
        status, label, preferred_source = "climate", "Klímás fűtést választana", "climate"

    zone_advice = {
        "zone_label": "Emeleti",
        "climate_selection": True,
        "status": status,
        "status_label": label,
        "preferred_source": preferred_source,
        "demanded_rooms": [item["room_name"] for item in demanded],
        "climate_rooms": [item["room_name"] for item in climate_rooms],
        "gas_required_rooms": [item["room_name"] for item in gas_required],
        "blocked_rooms": [item["room_name"] for item in blocked],
        "outdoor_temperature_c": outdoor.get("temperature_c") if outdoor else None,
        "climate_min_outdoor_c": params.climate_min_outdoor_c,
        "minimum_cop": params.minimum_cop,
        "thermostat_calling": thermostat_calling,
        "boiler_on": boiler_on,
        "boiler_name": boiler["name"] if boiler else "Bosch kazán",
        "boiler_action_required": preferred_source == "gas" and not boiler_on,
        "mixed_operation_allowed": False,
        "calculation_version": "heating-observer-v1",
    }
    for item in devices:
        if item.get("source_system") == "computherm":
            item["boiler_status"] = {
                "name": boiler["name"] if boiler else "Bosch kazán",
                "is_on": boiler_on,
                "thermostat_calling": bool(item.get("active")),
                "heating_unavailable": bool(item.get("active")) and not boiler_on,
            }
            item["thermostat_target_too_high"] = bool(
                item.get("target_temperature_c") is not None
                and float(item["target_temperature_c"]) > params.maximum_target_c
            )
            item["maximum_heating_target_c"] = params.maximum_target_c
    if thermostat is not None:
        thermostat["heating_zone_advice"] = zone_advice
    return zone_advice


def annotate_ground_floor_heating(
    devices: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Attach the simple, gas-only ground-floor recommendation to its thermostat."""
    thermostat = next(
        (
            item
            for item in devices
            if item.get("source_system") == "computherm"
            and item.get("zone_name") == "Földszint"
        ),
        None,
    )
    if thermostat is None:
        return None
    boiler = next(
        (
            item
            for item in devices
            if item.get("source_system") == "manual"
            and item.get("device_type") == "boiler"
        ),
        None,
    )
    boiler_on = bool(boiler and boiler.get("manual_power_state"))
    thermostat_calling = bool(thermostat.get("active"))
    if thermostat_calling and boiler_on:
        status = "gas"
        label = "Gázfűtés aktív"
    elif thermostat_calling:
        status = "gas_required"
        label = "Fűtést kér, a kazán bekapcsolandó"
    else:
        status = "no_demand"
        label = "Nincs földszinti fűtési igény"

    advice = {
        "zone_label": "Földszinti",
        "climate_selection": False,
        "status": status,
        "status_label": label,
        "preferred_source": "gas" if thermostat_calling else "none",
        "demanded_rooms": [thermostat.get("room_name") or thermostat["name"]]
        if thermostat_calling else [],
        "climate_rooms": [],
        "gas_required_rooms": [thermostat.get("room_name") or thermostat["name"]]
        if thermostat_calling else [],
        "blocked_rooms": [],
        "thermostat_calling": thermostat_calling,
        "boiler_on": boiler_on,
        "boiler_name": boiler["name"] if boiler else "Bosch kazán",
        "boiler_action_required": thermostat_calling and not boiler_on,
        "mixed_operation_allowed": False,
        "calculation_version": "ground-floor-heating-observer-v1",
    }
    thermostat["heating_zone_advice"] = advice
    return advice
