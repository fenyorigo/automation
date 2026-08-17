from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo


GENERATOR_VERSION = "deterministic-v1"
SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}


def _local_stamp(value: str | None, timezone_name: str) -> str:
    if not value:
        return "ismeretlen időpont"
    parsed = datetime.fromisoformat(value.removesuffix("Z")).replace(tzinfo=UTC)
    return parsed.astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%d %H:%M")


def _finding(rule_id: str, severity: str, message: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "evidence": evidence,
    }


def generate_report(facts: dict[str, Any], timezone_name: str = "Europe/Budapest") -> dict[str, Any]:
    """Create an auditable Hungarian report without probabilistic text generation."""
    findings: list[dict[str, Any]] = []
    sensors = facts.get("temperature_series") or []
    window = facts.get("window") or {}
    start_label = _local_stamp(window.get("started_at"), timezone_name)
    end_label = _local_stamp(window.get("ended_at"), timezone_name)

    total_samples = sum(int(item.get("sample_count") or 0) for item in sensors)
    if sensors:
        findings.append(
            _finding(
                "temperature_coverage_v1",
                "info",
                f"Az időablakban {len(sensors)} hőmérő összesen {total_samples} érvényes mérési pontját értékeltük.",
                {"sensor_count": len(sensors), "sample_count": total_samples},
            )
        )
    else:
        findings.append(
            _finding(
                "temperature_coverage_v1",
                "warning",
                "Az időablakban nem található értékelhető hőmérsékleti mérés.",
                {"sensor_count": 0, "sample_count": 0},
            )
        )

    for item in sensors:
        sample_count = int(item.get("sample_count") or 0)
        severity = "warning" if sample_count < 2 else "info"
        if sample_count:
            message = (
                f"{item['device']}: {sample_count} mérés, átlag {item['average_c']:.1f} °C, "
                f"minimum {item['minimum_c']:.1f} °C, maximum {item['maximum_c']:.1f} °C, "
                f"nettó változás {item['net_change_c']:+.1f} °C."
            )
        else:
            message = f"{item['device']}: nincs értékelhető mérési pont."
        findings.append(
            _finding(
                "sensor_window_statistics_v1",
                severity,
                message,
                {
                    "device": item.get("device"),
                    "source": item.get("source"),
                    "room": item.get("room"),
                    "zone": item.get("zone"),
                    "sample_count": sample_count,
                    "minimum_c": item.get("minimum_c"),
                    "maximum_c": item.get("maximum_c"),
                    "average_c": item.get("average_c"),
                    "net_change_c": item.get("net_change_c"),
                },
            )
        )

    outdoor = facts.get("outdoor_summary")
    if outdoor:
        findings.append(
            _finding(
                "outdoor_reference_v1",
                "info",
                f"A(z) {outdoor['source']} tájékoztató külső hőmérséklete "
                f"{outdoor['minimum_c']:.1f} és {outdoor['maximum_c']:.1f} °C között változott.",
                dict(outdoor),
            )
        )
    else:
        findings.append(
            _finding(
                "outdoor_reference_v1",
                "info",
                "Az időablakhoz nem áll rendelkezésre külső hőmérsékleti referencia.",
                {"available": False},
            )
        )

    climate_events = facts.get("climate_events") or []
    ventilation_events = facts.get("ventilation_events") or []
    findings.append(
        _finding(
            "environmental_events_v1",
            "info",
            f"Az időablakkal {len(climate_events)} klímaesemény és "
            f"{len(ventilation_events)} szellőztetési esemény fedett át.",
            {
                "climate_event_count": len(climate_events),
                "ventilation_event_count": len(ventilation_events),
                "climate_events": climate_events,
                "ventilation_events": ventilation_events,
            },
        )
    )

    common_drops = facts.get("common_esp32_drop_events") or []
    if common_drops:
        strongest = min(common_drops, key=lambda item: float(item["mean_change_c"]))
        findings.append(
            _finding(
                "common_esp32_drop_v1",
                "info",
                f"{len(common_drops)} olyan mérési időpont volt, amikor legalább három ESP32 "
                f"együtt csökkent; a legerősebb átlagos lépés {strongest['mean_change_c']:+.2f} °C volt.",
                {"event_count": len(common_drops), "strongest_event": strongest, "events": common_drops},
            )
        )

    observation = facts.get("operator_observation")
    if observation:
        findings.append(
            _finding(
                "operator_observation_v1",
                "info",
                f"Kézi megfigyelés: {observation}",
                {"observation": observation, "evidence_type": "manual"},
            )
        )

    severity = max(
        (item["severity"] for item in findings),
        key=lambda value: SEVERITY_ORDER[value],
        default="info",
    )
    title = f"Hőmérsékleti jelentés – {start_label}–{end_label}"
    report_text = "\n".join(item["message"] for item in findings)
    return {
        "generator_version": GENERATOR_VERSION,
        "severity": severity,
        "title": title,
        "report_text": report_text,
        "findings": findings,
    }
