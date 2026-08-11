-- Home automation schema
-- Version: 1.0
-- Generated: 2026-08-07 UTC
-- Purpose: initial MariaDB schema for ESP32, ConnectLife, and Computherm measurements and states

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS home_automation
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE home_automation;

CREATE TABLE IF NOT EXISTS rooms (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
    ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_rooms_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS room_source_refs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  room_id BIGINT UNSIGNED NOT NULL,
  source_system VARCHAR(32) NOT NULL,
  source_room_id VARCHAR(100) NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_room_source_refs_source (source_system, source_room_id),
  KEY idx_room_source_refs_room (room_id),
  CONSTRAINT fk_room_source_refs_room
    FOREIGN KEY (room_id) REFERENCES rooms(id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS devices (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  room_id BIGINT UNSIGNED NULL,
  source_system VARCHAR(32) NOT NULL,
  source_device_id VARCHAR(100) NOT NULL,
  source_puid VARCHAR(100) NULL,
  name VARCHAR(100) NOT NULL,
  device_type VARCHAR(50) NOT NULL DEFAULT 'climate',
  model VARCHAR(100) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
    ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_devices_source (source_system, source_device_id),
  UNIQUE KEY uq_devices_puid (source_system, source_puid),
  KEY idx_devices_room (room_id),
  CONSTRAINT fk_devices_room
    FOREIGN KEY (room_id) REFERENCES rooms(id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sensors (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  room_id BIGINT UNSIGNED NULL,
  device_id BIGINT UNSIGNED NULL,
  source_system VARCHAR(32) NOT NULL,
  source_sensor_id VARCHAR(100) NOT NULL,
  name VARCHAR(100) NOT NULL,
  sensor_type VARCHAR(32) NOT NULL,
  unit VARCHAR(20) NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
    ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_sensors_source (source_system, source_sensor_id),
  KEY idx_sensors_device (device_id),
  KEY idx_sensors_room (room_id),
  CONSTRAINT fk_sensors_room
    FOREIGN KEY (room_id) REFERENCES rooms(id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  CONSTRAINT fk_sensors_device
    FOREIGN KEY (device_id) REFERENCES devices(id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sensor_readings (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sensor_id BIGINT UNSIGNED NOT NULL,
  observed_at DATETIME(3) NOT NULL,
  value DECIMAL(8,4) NULL,
  quality VARCHAR(20) NOT NULL DEFAULT 'valid',
  error_code VARCHAR(50) NULL,
  source_system VARCHAR(32) NOT NULL,
  source_event_id VARCHAR(255) NOT NULL,
  raw_payload JSON NULL,
  ingested_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_sensor_reading_event (sensor_id, source_event_id),
  KEY idx_sensor_time (sensor_id, observed_at),
  KEY idx_sensor_readings_observed_at (observed_at),
  CONSTRAINT fk_sensor_readings_sensor
    FOREIGN KEY (sensor_id) REFERENCES sensors(id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS device_states (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  observed_at DATETIME(3) NOT NULL,
  power TINYINT(1) NULL,
  mode VARCHAR(32) NULL,
  target_temperature_c DECIMAL(5,2) NULL,
  fan_speed VARCHAR(32) NULL,
  fan_mute TINYINT(1) NULL,
  eco TINYINT(1) NULL,
  sleep TINYINT(1) NULL,
  super TINYINT(1) NULL,
  swing_up_down TINYINT(1) NULL,
  online TINYINT(1) NULL,
  active TINYINT(1) NULL,
  auto_mode TINYINT(1) NULL,
  source_system VARCHAR(32) NOT NULL,
  source_event_id VARCHAR(255) NOT NULL,
  raw_state JSON NULL,
  ingested_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_device_state_event (device_id, source_event_id),
  KEY idx_device_state_time (device_id, observed_at),
  KEY idx_device_states_observed_at (observed_at),
  CONSTRAINT fk_device_states_device
    FOREIGN KEY (device_id) REFERENCES devices(id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Notes:
-- 1. All timestamps are UTC and should be stored as DATETIME(3) values in UTC.
-- 2. ESP32 hardware identity is derived from the eFuse-based unique identifier or MAC address and stored in devices.source_puid.
-- 3. devices.source_device_id remains the logical identifier for the ESP32 gateway, while devices.room_id carries the current physical room assignment.
-- 4. DS18B20 sensors must use the factory 64-bit ROM identifier in sensors.source_sensor_id; this guarantees that the same physical sensor cannot be inserted twice.
-- 5. sensors.room_id should be kept in sync with the owning ESP32's room assignment for direct room-based queries.
-- 6. When an ESP32 is moved to a new room, the active sensors attached to that device must have their room_id updated consistently.
-- 7. source_event_id should follow this documented pattern:
--    {source_system}:{source_device_id_or_sensor_id}:{measurement_or_state}:{source_timestamp}
-- 8. For DS18B20 readings, use value = NULL and quality = 'invalid' with an error_code when the sensor is not usable.
-- 9. Fan speed should be stored in normalized form in fan_speed, while the original value remains in raw_state.
