-- MariaDB migration: home automation schema v1.18 -> v1.19
-- Purpose: persistent scheduled climate runs
USE home_automation;

CREATE TABLE climate_control_schedules (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  starts_at DATETIME(3) NOT NULL,
  runtime_minutes SMALLINT UNSIGNED NOT NULL,
  target_temperature_c DECIMAL(4,1) NOT NULL,
  status ENUM('scheduled','starting','running','stopping','completed','cancelled','failed')
    NOT NULL DEFAULT 'scheduled',
  start_attempt_id BIGINT UNSIGNED NULL,
  stop_attempt_id BIGINT UNSIGNED NULL,
  actual_started_at DATETIME(3) NULL,
  actual_ended_at DATETIME(3) NULL,
  error_message VARCHAR(1000) NULL,
  created_by BIGINT UNSIGNED NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_climate_schedule_due (status,starts_at),
  CONSTRAINT chk_climate_schedule_runtime CHECK (runtime_minutes BETWEEN 1 AND 1440),
  CONSTRAINT chk_climate_schedule_target CHECK (target_temperature_c BETWEEN 16 AND 30),
  CONSTRAINT fk_climate_schedule_device FOREIGN KEY (device_id) REFERENCES devices(id),
  CONSTRAINT fk_climate_schedule_user FOREIGN KEY (created_by) REFERENCES app_users(id),
  CONSTRAINT fk_climate_schedule_start_attempt FOREIGN KEY (start_attempt_id) REFERENCES climate_control_attempts(id),
  CONSTRAINT fk_climate_schedule_stop_attempt FOREIGN KEY (stop_attempt_id) REFERENCES climate_control_attempts(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
