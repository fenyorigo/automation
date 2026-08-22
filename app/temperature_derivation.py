from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DerivedTemperature:
    calibrated: float
    filtered: float
    action: float | None
    is_action_point: bool
    source_from: datetime
    sample_count: int


def ema_alpha(elapsed_seconds: float, tau_seconds: int) -> float:
    if tau_seconds <= 0:
        raise ValueError("tau_seconds must be positive")
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds cannot be negative")
    return 1.0 - math.exp(-elapsed_seconds / tau_seconds)


def derive_temperature(
    *,
    raw_value: float,
    offset_c: float,
    observed_at: datetime,
    tau_seconds: int,
    action_interval_seconds: int,
    previous_filtered: float | None,
    previous_observed_at: datetime | None,
    last_action_at: datetime | None,
    source_from: datetime | None,
    sample_count: int,
) -> DerivedTemperature:
    calibrated = raw_value + offset_c
    if previous_filtered is None or previous_observed_at is None:
        filtered = calibrated
        new_source_from = observed_at
        new_sample_count = 1
    else:
        elapsed = max(0.0, (observed_at - previous_observed_at).total_seconds())
        alpha = ema_alpha(elapsed, tau_seconds)
        filtered = previous_filtered + alpha * (calibrated - previous_filtered)
        if last_action_at is not None and previous_observed_at <= last_action_at:
            new_source_from = observed_at
            new_sample_count = 1
        else:
            new_source_from = source_from or previous_observed_at
            new_sample_count = sample_count + 1

    is_action = (
        last_action_at is None
        or (observed_at - last_action_at).total_seconds() >= action_interval_seconds
    )
    return DerivedTemperature(
        calibrated=calibrated,
        filtered=filtered,
        action=filtered if is_action else None,
        is_action_point=is_action,
        source_from=new_source_from,
        sample_count=new_sample_count,
    )
