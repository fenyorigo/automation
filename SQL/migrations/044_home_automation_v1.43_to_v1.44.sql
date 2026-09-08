-- MariaDB migration: home automation schema v1.43 -> v1.44
-- Purpose: audited, restorable Computherm service tests
USE home_automation;

CREATE TABLE thermostat_service_tests (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  started_by BIGINT UNSIGNED NOT NULL,
  status ENUM('active','heat_requested','heat_suppressed','restored','failed') NOT NULL,
  requested_temperature_c DECIMAL(4,1) NOT NULL,
  original_state JSON NOT NULL,
  latest_state JSON NULL,
  error_message TEXT NULL,
  started_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  ended_at DATETIME(3) NULL,
  PRIMARY KEY (id),
  KEY idx_thermostat_service_status (status,started_at),
  CONSTRAINT fk_thermostat_service_device FOREIGN KEY (device_id) REFERENCES devices(id),
  CONSTRAINT fk_thermostat_service_user FOREIGN KEY (started_by) REFERENCES app_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE thermostat_service_commands (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  service_test_id BIGINT UNSIGNED NOT NULL,
  requested_by BIGINT UNSIGNED NOT NULL,
  action ENUM('start','suppress','restore') NOT NULL,
  requested_temperature_c DECIMAL(4,1) NULL,
  preflight_state JSON NULL,
  verified_state JSON NULL,
  success TINYINT(1) NOT NULL,
  error_message TEXT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_thermostat_service_command (service_test_id,created_at),
  CONSTRAINT fk_thermostat_service_command_test FOREIGN KEY (service_test_id)
    REFERENCES thermostat_service_tests(id),
  CONSTRAINT fk_thermostat_service_command_user FOREIGN KEY (requested_by)
    REFERENCES app_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
