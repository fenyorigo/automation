from __future__ import annotations

from typing import Any, Callable

import broadlink


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
