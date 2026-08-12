-- MariaDB migration: home automation schema v1.17 -> v1.18
-- Purpose: automatically detected climate events and cumulative energy-meter readings
USE home_automation;

ALTER TABLE climate_operation_events
  MODIFY created_by BIGINT UNSIGNED NULL,
  ADD COLUMN event_origin ENUM('manual','ui_control','state_detection') NOT NULL DEFAULT 'manual'
    AFTER note;

UPDATE climate_operation_events
SET event_origin=IF(note='UI-vezérlés','ui_control','manual');

CREATE TABLE energy_meters (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  meter_code VARCHAR(64) NOT NULL,
  display_name VARCHAR(120) NOT NULL,
  energy_type ENUM('electricity','gas') NOT NULL,
  unit ENUM('kWh','m3') NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_meter_code (meter_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE energy_meter_readings (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  meter_id BIGINT UNSIGNED NOT NULL,
  recorded_at DATETIME(3) NOT NULL,
  reading_value DECIMAL(16,3) NOT NULL,
  entry_source ENUM('manual','import') NOT NULL DEFAULT 'manual',
  recorded_by BIGINT UNSIGNED NULL,
  note VARCHAR(500) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_energy_meter_reading_time (meter_id,recorded_at),
  KEY idx_energy_reading_time (recorded_at),
  CONSTRAINT chk_energy_reading_nonnegative CHECK (reading_value >= 0),
  CONSTRAINT fk_energy_reading_meter FOREIGN KEY (meter_id)
    REFERENCES energy_meters(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_energy_reading_user FOREIGN KEY (recorded_by)
    REFERENCES app_users(id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO energy_meters (meter_code,display_name,energy_type,unit) VALUES
  ('electricity_main','Villanyóra','electricity','kWh'),
  ('gas_main','Gázóra','gas','m3');
