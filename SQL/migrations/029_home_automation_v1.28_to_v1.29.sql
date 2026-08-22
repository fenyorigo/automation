-- MariaDB migration: home automation schema v1.28 -> v1.29
-- Purpose: version ESP/DS physical configurations, calibrations and derived temperatures
USE home_automation;

CREATE TABLE sensor_calibrations (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sensor_id BIGINT UNSIGNED NOT NULL,
  physical_configuration VARCHAR(32) NOT NULL,
  copper_tube_length_mm DECIMAL(7,2) NULL,
  calibration_offset_c DECIMAL(8,4) NOT NULL DEFAULT 0,
  calibration_method VARCHAR(64) NOT NULL DEFAULT 'none',
  reference_sensor_id BIGINT UNSIGNED NULL,
  valid_from DATETIME(3) NOT NULL,
  valid_until DATETIME(3) NULL,
  decision_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  filter_tau_seconds INT UNSIGNED NOT NULL DEFAULT 240,
  action_interval_seconds INT UNSIGNED NOT NULL DEFAULT 240,
  calculation_version VARCHAR(32) NOT NULL DEFAULT 'ema_v1',
  evidence_json JSON NULL,
  notes TEXT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_sensor_calibration_start (sensor_id,valid_from),
  KEY idx_sensor_calibration_active (sensor_id,valid_from,valid_until),
  CONSTRAINT fk_sensor_calibration_sensor FOREIGN KEY (sensor_id) REFERENCES sensors(id),
  CONSTRAINT fk_sensor_calibration_reference FOREIGN KEY (reference_sensor_id) REFERENCES sensors(id),
  CONSTRAINT chk_sensor_physical_configuration CHECK (
    physical_configuration IN ('raw','copper_tube','box','copper_tube_box')
  ),
  CONSTRAINT chk_sensor_calibration_interval CHECK (
    valid_until IS NULL OR valid_until > valid_from
  ),
  CONSTRAINT chk_sensor_filter_tau CHECK (filter_tau_seconds > 0),
  CONSTRAINT chk_sensor_action_interval CHECK (action_interval_seconds > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE derived_temperature_readings (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sensor_id BIGINT UNSIGNED NOT NULL,
  raw_reading_id BIGINT UNSIGNED NOT NULL,
  calibration_id BIGINT UNSIGNED NOT NULL,
  observed_at DATETIME(3) NOT NULL,
  calibrated_temperature_c DECIMAL(8,4) NOT NULL,
  filtered_temperature_c DECIMAL(8,4) NOT NULL,
  action_temperature_c DECIMAL(8,4) NULL,
  is_action_point BOOLEAN NOT NULL DEFAULT FALSE,
  source_from DATETIME(3) NOT NULL,
  source_to DATETIME(3) NOT NULL,
  sample_count INT UNSIGNED NOT NULL DEFAULT 1,
  calculation_version VARCHAR(32) NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_derived_raw_calibration (raw_reading_id,calibration_id),
  KEY idx_derived_sensor_time (sensor_id,observed_at),
  KEY idx_derived_action_time (sensor_id,is_action_point,observed_at),
  CONSTRAINT fk_derived_sensor FOREIGN KEY (sensor_id) REFERENCES sensors(id),
  CONSTRAINT fk_derived_raw FOREIGN KEY (raw_reading_id) REFERENCES sensor_readings(id),
  CONSTRAINT fk_derived_calibration FOREIGN KEY (calibration_id) REFERENCES sensor_calibrations(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE derived_temperature_sources (
  derived_reading_id BIGINT UNSIGNED NOT NULL,
  source_sensor_id BIGINT UNSIGNED NOT NULL,
  source_reading_id BIGINT UNSIGNED NOT NULL,
  source_role VARCHAR(32) NOT NULL DEFAULT 'primary',
  source_weight DECIMAL(8,4) NOT NULL DEFAULT 1,
  accepted BOOLEAN NOT NULL DEFAULT TRUE,
  exclusion_reason VARCHAR(255) NULL,
  PRIMARY KEY (derived_reading_id,source_reading_id),
  CONSTRAINT fk_derived_source_result FOREIGN KEY (derived_reading_id)
    REFERENCES derived_temperature_readings(id) ON DELETE CASCADE,
  CONSTRAINT fk_derived_source_sensor FOREIGN KEY (source_sensor_id) REFERENCES sensors(id),
  CONSTRAINT fk_derived_source_reading FOREIGN KEY (source_reading_id) REFERENCES sensor_readings(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
