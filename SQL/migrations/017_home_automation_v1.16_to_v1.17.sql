-- MariaDB migration: home automation schema v1.16 -> v1.17
-- Purpose: audited ConnectLife climate control attempts
USE home_automation;

CREATE TABLE climate_control_attempts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  requested_by BIGINT UNSIGNED NOT NULL,
  requested_power TINYINT(1) NOT NULL,
  requested_temperature_c DECIMAL(5,2) NULL,
  status ENUM('requested','rejected','verified','failed') NOT NULL,
  preflight_state JSON NULL,
  verified_state JSON NULL,
  error_code VARCHAR(64) NULL,
  error_message TEXT NULL,
  requested_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  completed_at DATETIME(3) NULL,
  PRIMARY KEY (id),
  KEY idx_climate_control_device_time (device_id,requested_at),
  CONSTRAINT fk_climate_control_device FOREIGN KEY (device_id)
    REFERENCES devices(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_climate_control_user FOREIGN KEY (requested_by)
    REFERENCES app_users(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
