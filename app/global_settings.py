from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
# Follow a deployment-time symlink so the real file may live in a dedicated,
# service-writable configuration directory while every process can keep using
# ROOT/.env as its stable entry point.
ENV_PATH = (ROOT / ".env").resolve()

# These values are captured while the dashboard process starts. Updating the
# process environment cannot safely change them in an already running server.
RESTART_REQUIRED_KEYS = frozenset({
    "APP_TIMEZONE",
    "DASHBOARD_PORT",
    "DASHBOARD_SECRET_KEY",
})


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
    Setting("CLIMATE_SERVICE_MODE", "Klímaszerviz folyamatban", "false", "boolean", "Minden automatikus klímaszabályt felfüggeszt; a kézi szervizpróbákat nem korlátozza.", validator=lambda value: value in {"true", "false"}),
    Setting("BOILER_SERVICE_MODE", "Gázkazánszerviz folyamatban", "false", "boolean", "Felfüggeszti a fűtési szabályokat és engedélyezi a védett Computherm szerviztesztet.", validator=lambda value: value in {"true", "false"}),
    Setting("BOILER_PANEL_ON_MIN_POWER_W", "Bosch power bekapcsolási teljesítményhatára", "2.0", "number", "Watt; bekapcsolt Nous mellett legalább ekkora friss fogyasztás igazolja a kazán power kapcsolójának bekapcsolt állapotát. A mért nyugalmi fogyasztás kb. 5 W.", number_between(0.1, 100)),
    Setting("COOLING_MIN_ROOM_TEMPERATURE_C", "Hűtés abszolút alsó szobahőmérsékleti korlátja", "25", "number", "Biztonsági korlát; ez alatt hűtési igény nem állhat fenn.", number_between(5, 40)),
    Setting("COOLING_MIN_TARGET_C", "Hűtés legkisebb célhőmérséklete", "25", "number", "Az observer jelzi, ha a klímán ennél kisebb kézi célértéket észlel.", number_between(5, 40)),
    Setting("COOLING_ROOM_REQUEST_ON_C", "Hűtési igény bekapcsolási határa", "27.5", "number", "A cselekedeti helyiséghőmérséklet ettől az értéktől kér hűtést, ha a klíma nem hűt.", number_between(5, 40)),
    Setting("COOLING_ROOM_REQUEST_OFF_C", "Hűtési igény kikapcsolási határa", "27.0", "number", "Már működő hűtésnél eddig az értékig marad fenn az igény; a két határ adja a hiszterézist.", number_between(5, 40)),
    Setting("COOLING_OUTDOOR_ENABLE_C", "Kültéri hűtésengedélyezési határ", "28.1", "number", "Kikapcsolt klíma csak legalább ilyen kültéri hőmérsékletnél indulhatna.", number_between(-30, 60)),
    Setting("COOLING_OUTDOOR_DISABLE_C", "Kültéri hűtésletiltási határ", "27.1", "number", "Eddig a kültéri hőmérsékletig a hűtést leállítaná; a két kültéri határ adja a hiszterézist.", number_between(-30, 60)),
    Setting("COOLING_HISENSE_WEIGHT", "Hisense mérés súlya", "0.20", "number", "A klíma saját, magasabban elhelyezett érzékelőjének súlya a cselekedeti hőmérsékletben.", number_between(0, 0.5)),
    Setting("COOLING_COMPUTHERM_WEIGHT", "Computherm mérés súlya", "0.10", "number", "A Computherm súlya ott, ahol ugyanabban a helyiségben rendelkezésre áll.", number_between(0, 0.5)),
    Setting("COOLING_MAX_DATA_AGE_MINUTES", "Hűtési döntési adat legnagyobb kora", "180", "number", "Perc; ennél régebbi mérés nem kerül a cselekedeti hőmérsékletbe.", integer_between(1, 1440)),
    Setting("COOLING_WINDOW_CLOSE_STABILIZATION_MINUTES", "Ablakzárás utáni hűtési várakozás", "10", "number", "Perc; a legutolsó nyílászáró bezárása után eddig még blokkolt maradna a hűtés.", integer_between(0, 180)),
    Setting("HEATING_MAX_ROOM_TEMPERATURE_C", "Fűtés felső szobahőmérsékleti határa", "22", "number", "Biztonsági korlát; e fölött fűtési igény nem állhat fenn.", number_between(5, 40)),
    Setting("HEATING_MAX_TARGET_C", "Fűtés legnagyobb célhőmérséklete", "22", "number", "Az observer jelzi az ennél magasabb fűtési célértéket.", number_between(5, 40)),
    Setting("HEATING_ROOM_REQUEST_ON_C", "Fűtési igény bekapcsolási határa", "20.0", "number", "A cselekedeti helyiséghőmérséklet ettől lefelé kér fűtést, ha nincs aktív fűtés.", number_between(5, 35)),
    Setting("HEATING_ROOM_REQUEST_OFF_C", "Fűtési igény kikapcsolási határa", "20.5", "number", "Már működő fűtésnél eddig az értékig marad fenn az igény; a két határ adja a hiszterézist.", number_between(5, 35)),
    Setting("HEATING_CLIMATE_MIN_OUTDOOR_C", "Klímás fűtés kültéri alsó határa", "5.0", "number", "Ideiglenes COP-helyettesítő küszöb; alatta az observer a gázfűtést részesíti előnyben.", number_between(-30, 30)),
    Setting("HEATING_MIN_COP", "Klímás fűtés legkisebb elfogadott COP-ja", "2.5", "number", "Döntési alapelv; tényleges COP-görbe hiányában az observer még a kültéri alsó határt használja.", number_between(1, 10)),
    Setting("HEATING_HISENSE_WEIGHT", "Hisense fűtési mérés súlya", "0.20", "number", "A klíma saját érzékelőjének súlya a fűtési cselekedeti hőmérsékletben.", number_between(0, 0.5)),
    Setting("HEATING_COMPUTHERM_WEIGHT", "Computherm fűtési mérés súlya", "0.10", "number", "A Computherm súlya ott, ahol ugyanabban a helyiségben rendelkezésre áll.", number_between(0, 0.5)),
    Setting("HEATING_MAX_DATA_AGE_MINUTES", "Fűtési döntési adat legnagyobb kora", "180", "number", "Perc; ennél régebbi mérés nem kerül a fűtési cselekedeti hőmérsékletbe.", integer_between(1, 1440)),
    Setting("HEATING_WINDOW_CLOSE_STABILIZATION_MINUTES", "Ablakzárás utáni fűtési várakozás", "10", "number", "Perc; a legutolsó nyílászáró bezárása után eddig még blokkolt maradna a fűtés.", integer_between(0, 180)),
    Setting("VENTILATION_LONG_THRESHOLD_MINUTES", "Hosszú szellőztetés határa", "5", "number", "Perc; ennél rövidebb esemény rövid szellőztetésnek számít.", integer_between(1, 180)),
    Setting("VENTILATION_CONTACT_CLOSE_DELAY_SECONDS", "Nyílászáró zárási késleltetése", "30", "number", "Másodperc; kiszűri a nyitott és bukó állás közötti pillanatnyi csukott jelzést.", integer_between(5, 300)),
    Setting("ENERGY_MJ_PER_KWH", "Energiaátváltás: MJ/kWh", "3.6", "number", "1 kWh energiatartalma MJ-ban; a villamos és gázfűtés közös energiaalapú összehasonlításához.", number_between(0.1, 100)),
)


def values() -> dict[str, str]:
    return {item.key: os.getenv(item.key, item.default) for item in SETTINGS}


def reload_environment() -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Reload values present in .env into the current dashboard process.

    Returns the changed keys and the subset that still requires a process
    restart. Keys removed manually from .env are deliberately not deleted from
    ``os.environ``: an inherited service environment may be their real source.
    """
    if not ENV_PATH.is_file():
        raise ValueError(f"A .env fájl nem található: {ENV_PATH}")

    parsed = dotenv_values(ENV_PATH)
    invalid = sorted(key for key, value in parsed.items() if value is None)
    if invalid:
        raise ValueError(
            "Érték nélküli .env bejegyzés: " + ", ".join(invalid)
        )

    changed: list[str] = []
    for key, value in parsed.items():
        assert value is not None
        if os.environ.get(key) != value:
            changed.append(key)
        os.environ[key] = value

    restart_required = sorted(RESTART_REQUIRED_KEYS.intersection(changed))
    return tuple(sorted(changed)), tuple(restart_required)


def save(values_to_save: dict[str, str]) -> None:
    normalized: dict[str, str] = {}
    for item in SETTINGS:
        value = values_to_save.get(item.key, item.default).strip()
        if item.kind == "boolean": value = "true" if value == "true" else "false"
        if not item.validator(value) or "\n" in value or "\r" in value:
            raise ValueError(f"Érvénytelen érték: {item.label}")
        normalized[item.key] = value

    if float(normalized["COOLING_ROOM_REQUEST_ON_C"].replace(",", ".")) <= float(
        normalized["COOLING_ROOM_REQUEST_OFF_C"].replace(",", ".")
    ):
        raise ValueError("A hűtési igény bekapcsolási határának nagyobbnak kell lennie a kikapcsolási határnál.")
    if float(normalized["COOLING_OUTDOOR_ENABLE_C"].replace(",", ".")) <= float(
        normalized["COOLING_OUTDOOR_DISABLE_C"].replace(",", ".")
    ):
        raise ValueError("A kültéri engedélyezési határnak nagyobbnak kell lennie a letiltási határnál.")
    secondary_weight = sum(
        float(normalized[key].replace(",", "."))
        for key in ("COOLING_HISENSE_WEIGHT", "COOLING_COMPUTHERM_WEIGHT")
    )
    if secondary_weight >= 1:
        raise ValueError("A Hisense és Computherm együttes súlyának 1-nél kisebbnek kell lennie.")
    if float(normalized["HEATING_ROOM_REQUEST_ON_C"].replace(",", ".")) >= float(
        normalized["HEATING_ROOM_REQUEST_OFF_C"].replace(",", ".")
    ):
        raise ValueError("A fűtési igény bekapcsolási határának kisebbnek kell lennie a kikapcsolási határnál.")
    heating_secondary_weight = sum(
        float(normalized[key].replace(",", "."))
        for key in ("HEATING_HISENSE_WEIGHT", "HEATING_COMPUTHERM_WEIGHT")
    )
    if heating_secondary_weight >= 1:
        raise ValueError("A fűtési Hisense és Computherm együttes súlyának 1-nél kisebbnek kell lennie.")

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
