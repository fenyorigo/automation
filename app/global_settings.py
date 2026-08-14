from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


@dataclass(frozen=True)
class Setting:
    key: str
    label: str
    default: str
    kind: str = "text"
    help: str = ""
    validator: Callable[[str], bool] = lambda value: bool(value.strip())


def integer_between(low: int, high: int) -> Callable[[str], bool]:
    def validate(value: str) -> bool:
        try: return low <= int(value) <= high
        except ValueError: return False
    return validate


def number_between(low: float, high: float) -> Callable[[str], bool]:
    def validate(value: str) -> bool:
        try: return low <= float(value.replace(",", ".")) <= high
        except ValueError: return False
    return validate


SETTINGS = (
    Setting("DEFAULT_POLL_INTERVAL_MINUTES", "Alap lekérdezési gyakoriság", "10", "number", "Perc; az összes eszköz alapértékének visszaállításakor ezt használjuk.", integer_between(1, 1440)),
    Setting("POLL_TIMEOUT_SECONDS", "Lekérdezési időkorlát", "5", "number", "Másodperc.", number_between(1, 120)),
    Setting("DATABASE_BACKUP_DIR", "Adatbázismentések könyvtára", str(ROOT / "exports"), "text"),
    Setting("DATABASE_BACKUP_TIME", "Napi mentés időpontja", "03:00", "time", validator=lambda value: re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value) is not None),
    Setting("DATABASE_BACKUP_KEEP", "Megőrzött automatikus mentések", "30", "number", validator=integer_between(1, 3650)),
    Setting("GNUPLOT_BIN", "Gnuplot program elérési útja", "/opt/homebrew/bin/gnuplot", "text"),
    Setting("COOLING_MIN_ROOM_TEMPERATURE_C", "Hűtés alsó szobahőmérsékleti határa", "25", "number", "Előkészített biztonsági korlát; a vezérlési logika még nem használja.", number_between(5, 40)),
    Setting("COOLING_MIN_TARGET_C", "Hűtés legkisebb célhőmérséklete", "25", "number", "Előkészített biztonsági korlát.", number_between(5, 40)),
    Setting("HEATING_MAX_ROOM_TEMPERATURE_C", "Fűtés felső szobahőmérsékleti határa", "22", "number", "Előkészített biztonsági korlát; a vezérlési logika még nem használja.", number_between(5, 40)),
    Setting("HEATING_MAX_TARGET_C", "Fűtés legnagyobb célhőmérséklete", "22", "number", "Előkészített biztonsági korlát.", number_between(5, 40)),
)


def values() -> dict[str, str]:
    return {item.key: os.getenv(item.key, item.default) for item in SETTINGS}


def save(values_to_save: dict[str, str]) -> None:
    normalized: dict[str, str] = {}
    for item in SETTINGS:
        value = values_to_save.get(item.key, item.default).strip()
        if item.kind == "boolean": value = "true" if value == "true" else "false"
        if not item.validator(value) or "\n" in value or "\r" in value:
            raise ValueError(f"Érvénytelen érték: {item.label}")
        normalized[item.key] = value

    original = ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    remaining = dict(normalized)
    output = []
    for line in original:
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line)
        if match and match.group(1) in remaining:
            key = match.group(1); output.append(f"{key}={remaining.pop(key)}\n")
        else:
            output.append(line if line.endswith("\n") else line + "\n")
    if remaining:
        if output and output[-1].strip(): output.append("\n")
        output.append("# UI-ban kezelhető globális beállítások\n")
        output.extend(f"{key}={value}\n" for key, value in remaining.items())

    descriptor, temporary = tempfile.mkstemp(prefix=".env.", dir=ENV_PATH.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.writelines(output); handle.flush(); os.fsync(handle.fileno())
        os.chmod(temporary, ENV_PATH.stat().st_mode)
        os.replace(temporary, ENV_PATH)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    for key, value in normalized.items(): os.environ[key] = value
