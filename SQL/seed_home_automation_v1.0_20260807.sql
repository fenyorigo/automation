-- Seed data for home automation schema
-- Version: 1.0
-- Generated: 2026-08-07 UTC
-- Purpose: example canonical rows for ESP32, ConnectLife, and Computherm

USE home_automation;

-- Canonical rooms
INSERT INTO rooms (id, name) VALUES
  (1, 'Dolgozó'),
  (2, 'Nappali'),
  (3, 'Konyha')
ON DUPLICATE KEY UPDATE
  name = VALUES(name);

-- Source room mappings
INSERT INTO room_source_refs (room_id, source_system, source_room_id) VALUES
  (1, 'connectlife', 'dolgozo'),
  (1, 'esp32', 'boiler-room-01'),
  (2, 'computherm', 'foldszint_1')
ON DUPLICATE KEY UPDATE
  source_room_id = VALUES(source_room_id);

-- Devices
INSERT INTO devices (id, room_id, source_system, source_device_id, source_puid, name, device_type, model, is_active) VALUES
  (1, 1, 'connectlife', 'dolgozo-climate-01', 'connectlife-puid-001', 'Dolgozó klíma', 'climate', 'Hisense Energy SE', 1),
  (2, 1, 'esp32', 'esp32-gateway-01', 'ESP32-FAKE-001', 'ESP32 DS18B20 gateway #1', 'sensor_gateway', 'WEMOS D1 Mini ESP32', 1),
  (3, 2, 'esp32', 'esp32-gateway-02', 'ESP32-FAKE-002', 'ESP32 DS18B20 gateway #2', 'sensor_gateway', 'WEMOS D1 Mini ESP32', 1),
  (4, 2, 'computherm', 'computherm-26', NULL, 'Computherm-26', 'thermostat', 'E400RF-EM', 1)
ON DUPLICATE KEY UPDATE
  room_id = VALUES(room_id),
  source_puid = VALUES(source_puid),
  name = VALUES(name),
  device_type = VALUES(device_type),
  model = VALUES(model),
  is_active = VALUES(is_active);

-- Sensors
INSERT INTO sensors (id, room_id, device_id, source_system, source_sensor_id, name, sensor_type, unit, is_active) VALUES
  (1, 1, 1, 'connectlife', 'connectlife:dolgozo-climate-01:f_temp_in', 'Dolgozó beltéri hőmérséklet', 'temperature', 'celsius', 1),
  (2, 1, 2, 'esp32', '28-0000111122223333', 'DS18B20 #1 a dolgozó ESP32-n', 'temperature', 'celsius', 1),
  (3, 2, 3, 'esp32', '28-0000111122224444', 'DS18B20 #2 a nappali ESP32-n', 'temperature', 'celsius', 1),
  (4, 2, 4, 'computherm', 'computherm:computherm-26:room_temp', 'Computherm-26 szoba hőmérséklet', 'temperature', 'celsius', 1),
  (5, 2, 4, 'computherm', 'computherm:computherm-26:external_temp', 'Computherm-26 külső hőmérséklet', 'temperature', 'celsius', 1)
ON DUPLICATE KEY UPDATE
  room_id = VALUES(room_id),
  device_id = VALUES(device_id),
  name = VALUES(name),
  sensor_type = VALUES(sensor_type),
  unit = VALUES(unit),
  is_active = VALUES(is_active);

-- Example reading for ESP32
INSERT INTO sensor_readings (
  sensor_id, observed_at, value, quality, error_code, source_system, source_event_id, raw_payload
) VALUES (
  2,
  '2026-08-07 12:34:56.789',
  32.687,
  'valid',
  NULL,
  'esp32',
  'esp32:esp32-gateway-01:ds18b20:20260807T123456789Z',
  JSON_OBJECT('temp_c', 32.6875)
) ON DUPLICATE KEY UPDATE
  value = VALUES(value),
  quality = VALUES(quality),
  error_code = VALUES(error_code),
  raw_payload = VALUES(raw_payload);

-- Example reading for ConnectLife
INSERT INTO sensor_readings (
  sensor_id, observed_at, value, quality, error_code, source_system, source_event_id, raw_payload
) VALUES (
  1,
  '2026-08-07 12:35:00.000',
  28.000,
  'valid',
  NULL,
  'connectlife',
  'connectlife:dolgozo-climate-01:f_temp_in:20260807T123500000Z',
  JSON_OBJECT('property', 'f_temp_in', 'value', '28')
) ON DUPLICATE KEY UPDATE
  value = VALUES(value),
  quality = VALUES(quality),
  error_code = VALUES(error_code),
  raw_payload = VALUES(raw_payload);

-- Example state for ConnectLife
INSERT INTO device_states (
  device_id, observed_at, power, mode, target_temperature_c, fan_speed, fan_mute, eco, sleep, super, swing_up_down, online, active, auto_mode,
  source_system, source_event_id, raw_state
) VALUES (
  1,
  '2026-08-07 12:35:00.000',
  0,
  'heat',
  25.00,
  'auto',
  0,
  0,
  0,
  0,
  1,
  1,
  NULL,
  NULL,
  'connectlife',
  'connectlife:dolgozo-climate-01:state:20260807T123500000Z',
  JSON_OBJECT('t_power', '0', 't_work_mode', '1', 't_temp', '25', 't_fan_speed', '0')
) ON DUPLICATE KEY UPDATE
  power = VALUES(power),
  mode = VALUES(mode),
  target_temperature_c = VALUES(target_temperature_c),
  fan_speed = VALUES(fan_speed),
  fan_mute = VALUES(fan_mute),
  eco = VALUES(eco),
  sleep = VALUES(sleep),
  super = VALUES(super),
  swing_up_down = VALUES(swing_up_down),
  online = VALUES(online),
  active = VALUES(active),
  auto_mode = VALUES(auto_mode),
  raw_state = VALUES(raw_state);

-- Example state for Computherm
INSERT INTO device_states (
  device_id, observed_at, power, mode, target_temperature_c, fan_speed, fan_mute, eco, sleep, super, swing_up_down, online, active, auto_mode,
  source_system, source_event_id, raw_state
) VALUES (
  3,
  '2026-08-07 12:35:00.000',
  1,
  'auto',
  19.00,
  'auto',
  NULL,
  NULL,
  NULL,
  NULL,
  NULL,
  1,
  0,
  1,
  'computherm',
  'computherm:computherm-26:state:20260807T123500000Z',
  JSON_OBJECT('power', 1, 'active', 0, 'thermostat_temp', 19.0, 'auto_mode', 1)
) ON DUPLICATE KEY UPDATE
  power = VALUES(power),
  mode = VALUES(mode),
  target_temperature_c = VALUES(target_temperature_c),
  fan_speed = VALUES(fan_speed),
  fan_mute = VALUES(fan_mute),
  eco = VALUES(eco),
  sleep = VALUES(sleep),
  super = VALUES(super),
  swing_up_down = VALUES(swing_up_down),
  online = VALUES(online),
  active = VALUES(active),
  auto_mode = VALUES(auto_mode),
  raw_state = VALUES(raw_state);
