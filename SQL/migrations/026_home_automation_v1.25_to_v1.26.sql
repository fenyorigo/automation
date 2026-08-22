-- MariaDB migration: home automation schema v1.25 -> v1.26
-- Purpose: multi-step programmed climate runs with sensor-based transitions
USE home_automation;

ALTER TABLE climate_control_schedules
  ADD COLUMN current_step_no SMALLINT UNSIGNED NULL AFTER fan_speed;

ALTER TABLE climate_control_attempts
  MODIFY COLUMN requested_fan_speed ENUM(
    'auto','low','medium_low','medium','medium_high','high','quiet'
  ) NULL;

ALTER TABLE climate_control_schedules
  MODIFY COLUMN fan_speed ENUM(
    'auto','low','medium_low','medium','medium_high','high','quiet'
  ) NOT NULL DEFAULT 'auto';

ALTER TABLE climate_operation_events
  MODIFY COLUMN started_fan_speed ENUM(
    'auto','low','medium_low','medium','medium_high','high','quiet'
  ) NULL,
  MODIFY COLUMN ended_fan_speed ENUM(
    'auto','low','medium_low','medium','medium_high','high','quiet'
  ) NULL;

CREATE TABLE climate_program_steps (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  schedule_id BIGINT UNSIGNED NOT NULL,
  step_no SMALLINT UNSIGNED NOT NULL,
  runtime_minutes SMALLINT UNSIGNED NOT NULL,
  target_temperature_c DECIMAL(4,1) NOT NULL,
  fan_speed ENUM(
    'auto','low','medium_low','medium','medium_high','high','quiet'
  ) NOT NULL,
  transition_type ENUM('duration','sensor_below') NOT NULL DEFAULT 'duration',
  sensor_id BIGINT UNSIGNED NULL,
  threshold_delta_c DECIMAL(3,1) NULL,
  actual_started_at DATETIME(3) NULL,
  actual_ended_at DATETIME(3) NULL,
  transition_reason VARCHAR(100) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_climate_program_step (schedule_id,step_no),
  KEY idx_climate_program_sensor (sensor_id),
  CONSTRAINT chk_climate_program_runtime CHECK (runtime_minutes BETWEEN 1 AND 1440),
  CONSTRAINT chk_climate_program_target CHECK (target_temperature_c BETWEEN 25 AND 30),
  CONSTRAINT chk_climate_program_delta CHECK (
    (transition_type='duration' AND sensor_id IS NULL AND threshold_delta_c IS NULL)
    OR
    (transition_type='sensor_below' AND sensor_id IS NOT NULL
      AND threshold_delta_c BETWEEN 0.5 AND 5.0)
  ),
  CONSTRAINT fk_climate_program_schedule FOREIGN KEY (schedule_id)
    REFERENCES climate_control_schedules(id) ON DELETE CASCADE,
  CONSTRAINT fk_climate_program_sensor FOREIGN KEY (sensor_id)
    REFERENCES sensors(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
