from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

from connectlife.api import ConnectLifeApi


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
        "mode": status.get("t_work_mode"),
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
    wifi_id: str, desired_power: bool, temperature_c: int | None
) -> ClimateControlResult:
    username = os.getenv("CONNECTLIFE_USERNAME")
    password = os.getenv("CONNECTLIFE_PASSWORD")
    if not username or not password:
        return ClimateControlResult("failed", {}, error_code="missing_credentials", error_message="Hiányzó ConnectLife hitelesítés.")

    api = ConnectLifeApi(username, password)
    try:
        appliance = find_appliance(await api.get_appliances(), wifi_id)
        preflight = state_of(appliance)
        if preflight["power"] == desired_power:
            action = "bekapcsolva" if desired_power else "kikapcsolva"
            return ClimateControlResult(
                "rejected", preflight, error_code="state_precondition",
                error_message=f"A klíma már {action} állapotban van.",
            )

        properties = {"t_power": "1" if desired_power else "0"}
        if desired_power:
            properties["t_temp"] = str(temperature_c)
        await api.update_appliance(appliance.puid, properties)

        verified = None
        for _ in range(4):
            await asyncio.sleep(1.5)
            current = find_appliance(await api.get_appliances(), wifi_id)
            verified = state_of(current)
            power_ok = verified["power"] == desired_power
            temperature_ok = (
                not desired_power
                or float(verified["target_temperature_c"]) == float(temperature_c)
            )
            if power_ok and temperature_ok:
                return ClimateControlResult("verified", preflight, verified)
        return ClimateControlResult(
            "failed", preflight, verified, "verification_failed",
            "A parancs után visszaolvasott állapot nem egyezik a kéréssel.",
        )
    except Exception as error:
        return ClimateControlResult(
            "failed", locals().get("preflight", {}), error_code=type(error).__name__,
            error_message=str(error),
        )
