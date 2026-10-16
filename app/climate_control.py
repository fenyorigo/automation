from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from collections.abc import Awaitable, Callable
from typing import Any

from connectlife.api import ConnectLifeApi


FAN_SPEED_VALUES = {
    "auto": "0",
    "low": "5",
    "medium_low": "6",
    "medium": "7",
    "medium_high": "8",
    "high": "9",
    "quiet": "1",
}
FAN_SPEED_CODES = {value: key for key, value in FAN_SPEED_VALUES.items()}
MODE_VALUES = {"fan": "0", "heat": "1", "cool": "2", "dry": "3", "auto": "4"}
MODE_CODES = {value: key for key, value in MODE_VALUES.items()}
FAN_CONTROL_SETTLE_SECONDS = 25.0
FAN_VERIFICATION_INTERVAL_SECONDS = 5.0
FAN_COMMAND_ATTEMPTS = 3
FAN_VERIFICATION_ATTEMPTS = 6
FAN_STABLE_CONFIRMATIONS = 6
FAN_ROLLBACK_VERIFICATION_ATTEMPTS = 4


@dataclass
class ClimateControlResult:
    status: str
    preflight: dict[str, Any]
    verified: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


def state_of(appliance: Any) -> dict[str, Any]:
    status = appliance.status_list
    return {
        "power": bool(status.get("t_power")),
        "target_temperature_c": status.get("t_temp"),
        "mode": MODE_CODES.get(str(status.get("t_work_mode")), str(status.get("t_work_mode"))),
        "fan_speed": (
            "quiet" if str(status.get("t_fan_mute")).lower() in {"1", "true"}
            else FAN_SPEED_CODES.get(str(status.get("t_fan_speed")), str(status.get("t_fan_speed")))
        ),
        "raw": status,
    }


def find_appliance(appliances: Any, wifi_id: str) -> Any:
    identifier = wifi_id.lower()
    matches = [
        item for item in appliances
        if (item.wifi_id or "").lower() == identifier
        or (item.wifi_id or "").lower().endswith(identifier)
    ]
    if not matches:
        raise RuntimeError("A ConnectLife nem adta vissza a kiválasztott klímát.")
    if len(matches) != 1:
        raise RuntimeError("A kiválasztott AUID nem azonosít egyértelműen egy klímát.")
    return matches[0]


async def control_climate(
    wifi_id: str, desired_power: bool, temperature_c: int | None,
    fan_speed: str | None = None, *, mode: str | None = None,
    allow_running_update: bool = False,
    progress: Callable[[str, dict[str, Any] | None], Awaitable[None] | None] | None = None,
) -> ClimateControlResult:
    async def report(phase: str, state: dict[str, Any] | None = None) -> None:
        if progress is None:
            return
        pending = progress(phase, state)
        if pending is not None:
            await pending

    username = os.getenv("CONNECTLIFE_USERNAME")
    password = os.getenv("CONNECTLIFE_PASSWORD")
    if not username or not password:
        return ClimateControlResult("failed", {}, error_code="missing_credentials", error_message="Hiányzó ConnectLife hitelesítés.")

    api = ConnectLifeApi(username, password)
    try:
        appliance = find_appliance(await api.get_appliances(), wifi_id)
        preflight = state_of(appliance)
        await report("preflight", preflight)
        if preflight["power"] == desired_power and not (desired_power and allow_running_update):
            action = "bekapcsolva" if desired_power else "kikapcsolva"
            return ClimateControlResult(
                "rejected", preflight, error_code="state_precondition",
                error_message=f"A klíma már {action} állapotban van.",
            )

        properties = {"t_power": "1" if desired_power else "0"}
        if desired_power:
            if mode is not None and mode not in MODE_VALUES:
                return ClimateControlResult(
                    "rejected", preflight, error_code="invalid_mode",
                    error_message="Érvénytelen klíma-üzemmód.",
                )
            if fan_speed not in FAN_SPEED_VALUES:
                return ClimateControlResult(
                    "rejected", preflight, error_code="invalid_fan_speed",
                    error_message="Érvénytelen ventilátorfokozat.",
                )
            properties["t_temp"] = str(temperature_c)
            if mode is not None:
                properties["t_work_mode"] = MODE_VALUES[mode]
        await report("power_mode_target", preflight)
        await api.update_appliance(appliance.puid, properties)

        verified = None
        for _ in range(4):
            await asyncio.sleep(1.5)
            current = find_appliance(await api.get_appliances(), wifi_id)
            verified = state_of(current)
            await report("verify_power", verified)
            power_ok = verified["power"] == desired_power
            temperature_ok = (
                not desired_power
                or float(verified["target_temperature_c"]) == float(temperature_c)
            )
            mode_ok = not desired_power or mode is None or verified["mode"] == mode
            if power_ok and temperature_ok and mode_ok:
                break
        else:
            return ClimateControlResult(
                "failed", preflight, verified, "verification_failed",
                "A parancs után visszaolvasott bekapcsolt állapot, üzemmód "
                "vagy célhőmérséklet nem egyezik a kéréssel.",
            )

        if not desired_power or verified["fan_speed"] == fan_speed:
            return ClimateControlResult("verified", preflight, verified)

        # A ConnectLife alkalmazás is csak a már bekapcsolt klímán engedi a
        # ventilátorfokozat kiválasztását. Kövessük ugyanezt a kétlépcsős
        # folyamatot: a sikeresen visszaolvasott indítás után külön írjuk a
        # ventilátorbeállítást, majd a teljes állapotot ismét ellenőrizzük.
        # Kikapcsolt készülék indításakor a beltéri egységnek rövid idő kell,
        # mire a külön ventilátorparancsot már elfogadja.
        if not preflight["power"]:
            await report("stabilizing_fan", verified)
            await asyncio.sleep(FAN_CONTROL_SETTLE_SECONDS)
        fan_properties = {
            "t_fan_speed": FAN_SPEED_VALUES[fan_speed],
            "t_fan_speed_s": FAN_SPEED_VALUES[fan_speed],
            "t_fan_mute": "1" if fan_speed == "quiet" else "0",
        }
        for _ in range(FAN_COMMAND_ATTEMPTS):
            # A single ConnectLife write can be acknowledged without the
            # appliance retaining the requested fan level.  Re-issue the
            # command within the existing verification window instead of
            # merely polling the wrong state for ninety seconds.
            await report("setting_fan", verified)
            await api.update_appliance(appliance.puid, fan_properties)
            stable_confirmations = 0
            for _ in range(FAN_VERIFICATION_ATTEMPTS):
                await asyncio.sleep(FAN_VERIFICATION_INTERVAL_SECONDS)
                current = find_appliance(await api.get_appliances(), wifi_id)
                verified = state_of(current)
                fan_matches = (
                    verified["power"] == desired_power
                    and float(verified["target_temperature_c"])
                    == float(temperature_c)
                    and (mode is None or verified["mode"] == mode)
                    and verified["fan_speed"] == fan_speed
                )
                if fan_matches:
                    stable_confirmations += 1
                    await report("confirming_fan", verified)
                else:
                    stable_confirmations = 0
                    await report("verify_fan", verified)
                # A ConnectLife-felhő a parancsot rövid időre akkor is
                # visszatükrözheti, ha a beltéri egység végül nem tartja meg.
                # Csak hat egymást követő, öt másodpercenkénti egyezést
                # fogadunk el tartós készülékállapotként.
                if stable_confirmations >= FAN_STABLE_CONFIRMATIONS:
                    return ClimateControlResult("verified", preflight, verified)

        # Do not leave a running appliance in an unintended state after a
        # failed fan change. Restore the known starting level when possible.
        original_fan = preflight.get("fan_speed")
        rollback_succeeded = False
        if original_fan in FAN_SPEED_VALUES and original_fan != verified.get("fan_speed"):
            await report("restoring_fan", verified)
            await api.update_appliance(
                appliance.puid,
                {
                    "t_fan_speed": FAN_SPEED_VALUES[original_fan],
                    "t_fan_speed_s": FAN_SPEED_VALUES[original_fan],
                    "t_fan_mute": "1" if original_fan == "quiet" else "0",
                },
            )
            for _ in range(FAN_ROLLBACK_VERIFICATION_ATTEMPTS):
                await asyncio.sleep(FAN_VERIFICATION_INTERVAL_SECONDS)
                current = find_appliance(await api.get_appliances(), wifi_id)
                verified = state_of(current)
                await report("verify_fan", verified)
                if verified["fan_speed"] == original_fan:
                    rollback_succeeded = True
                    break
        return ClimateControlResult(
            "failed", preflight, verified, "fan_verification_failed",
            "A klíma bekapcsolt, de a visszaolvasott ventilátorfokozat "
            "nem egyezik a kéréssel."
            + (
                " A kiinduló fokozatot visszaállítottuk."
                if rollback_succeeded
                else " A kiinduló fokozat visszaállítása sem igazolható."
            ),
        )
    except Exception as error:
        return ClimateControlResult(
            "failed", locals().get("preflight", {}), error_code=type(error).__name__,
            error_message=str(error),
        )
