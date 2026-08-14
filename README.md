# Home Automation

Local-first home climate monitoring and control for ESP32/DS18B20 sensors,
Computherm thermostats and Hisense appliances through ConnectLife.

The project currently provides:

- periodic and manual polling with a shared process lock;
- MariaDB-backed measurement, state, event and audit history;
- responsive Flask UI with viewer/editor authentication;
- device and zone/room views;
- audited Hisense power control with preflight and post-command verification;
- ventilation and climate-operation event logs;
- configurable outdoor-temperature sources;
- schema migrations and macOS/Fedora service definitions;
- an ESP32 firmware prototype with Wi-Fi provisioning and HTTP measurement API;
- deterministic analytics scaffolding with an optional, currently disabled
  and strictly non-controlling text-generation layer.

## Setup

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
cp config/devices.example.json config/devices.json
.venv/bin/python app/migrate_database.py
.venv/bin/python app/dashboard.py
```

Fill `.env` and `config/devices.json` with local values. Both files containing
real credentials or device identities are excluded from Git.

See the [Hungarian user guide](docs/hasznalati-utasitas.md),
[polling documentation](docs/polling.md) and
[ESP32 documentation](docs/esp32.md) for details. The planned deterministic
heating and cooling rules are documented separately in the
[decision-logic specification](docs/dontesi-logika.md).

## Safety model

No language model controls devices. The first tested local 1B model was removed
after failing strict output validation. All device actions are deterministic,
authenticated, audited, checked against current state before execution, and
verified by reading the affected device afterward.

## Energy reading import

Historical electricity and gas meter readings can be imported from a UTF-8 CSV
with `recorded_at` and `reading_value` columns (an optional `note` column is accepted):

```sh
.venv/bin/python app/import_energy_readings.py readings.csv --meter electricity_main
.venv/bin/python app/import_energy_readings.py gas.csv --meter gas_main --default-time 09:00
```
