# Home Automation

Current application release: **1.1.0**.

Local-first home climate and energy monitoring and control for ESP32/DS18B20
sensors, Zigbee2MQTT-based SONOFF sensors, local-MQTT Shelly H&T Gen3 sensors,
Computherm thermostats, Hisense appliances through ConnectLife and Nous/Tasmota
power meters.

The project currently provides:

- periodic and manual polling with a shared process lock;
- MariaDB-backed measurement, state, event and audit history;
- responsive Flask UI with viewer/editor authentication;
- device and zone/room views;
- audited Hisense power, target-temperature and fan-speed control with
  preflight and post-command verification, including scheduled runs;
- ventilation and climate-operation event logs;
- manual temperature readings for visually read instruments;
- multi-device temperature charts, wide CSV export and up to four per-user
  measurement favorites;
- configurable outdoor-temperature sources;
- automatic Zigbee2MQTT discovery and last-known-state display for SONOFF
  temperature, humidity, contact and router devices;
- event-driven Shelly H&T Gen3 temperature, humidity and battery history over
  the local Mosquitto broker, with deep-sleep-aware freshness;
- read-only Nous/Tasmota power, voltage and cumulative-energy polling;
- explicit Europe/Budapest display time while retaining UTC database storage;
- schema migrations and macOS/Fedora service definitions;
- an ESP32 firmware prototype with Wi-Fi provisioning and HTTP measurement API;
- searchable, auditable deterministic reports generated entirely by Python
  rules and templates, without a language model or device-control access.

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
Shelly H&T Gen3 MQTT setup and diagnostics are documented in the
[Shelly MQTT guide](docs/shelly-mqtt.md).
Nous power-meter setup and voltage calibration are described in the
[Nous/Tasmota guide](docs/nous-tasmota.md).
The ongoing ESP32/DS18B20 physical-response experiments are recorded in the
[calibration measurement log](docs/esp32-ds18b20-kalibracios-meresek.md).
Release history is maintained in [CHANGELOG.md](CHANGELOG.md).

## Safety model

Reports are generated entirely by versioned Python rules and fixed templates.
They have read-only data access and cannot control devices. All actual device
actions are deterministic, authenticated, audited, checked against current
state before execution, and verified by reading the affected device afterward.

## Energy reading import

Historical electricity and gas meter readings can be imported from a UTF-8 CSV
with `recorded_at` and `reading_value` columns (an optional `note` column is accepted):

```sh
.venv/bin/python app/import_energy_readings.py readings.csv --meter electricity_main
.venv/bin/python app/import_energy_readings.py gas.csv --meter gas_main --default-time 09:00
```
