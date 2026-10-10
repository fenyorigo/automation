from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


LOCAL_TIMEZONE = ZoneInfo("Europe/Budapest")
TASMOTA_MONTHLY_HISTORY_DEVICE_IDS = frozenset({"nous-mainit", "nous-auxit"})


def previous_calendar_month_start_utc(
    now: datetime | None = None,
) -> datetime:
    """Return the UTC cutoff that keeps the current and previous local month."""
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    local = current.astimezone(LOCAL_TIMEZONE)
    if local.month == 1:
        year, month = local.year - 1, 12
    else:
        year, month = local.year, local.month - 1
    return datetime(year, month, 1, tzinfo=LOCAL_TIMEZONE).astimezone(UTC).replace(
        tzinfo=None
    )


def tasmota_keeps_monthly_history(device_id: str) -> bool:
    return device_id in TASMOTA_MONTHLY_HISTORY_DEVICE_IDS


def zigbee_property_has_time_series(
    device_type: str | None, property_name: str
) -> bool:
    """Power-meter values stay in the Zigbee cache instead of the time series."""
    return not (
        device_type == "power_meter"
        and property_name in {"power", "current", "voltage", "energy"}
    )
