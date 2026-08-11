-- MariaDB migration: home automation schema v1.1 -> v1.2
-- Purpose: hostname-based device addressing and poll-attempt logging

USE home_automation;

ALTER TABLE devices
  ADD COLUMN hostname VARCHAR(253) NULL AFTER source_puid,
  ADD COLUMN expected_ip VARCHAR(45) NULL AFTER hostname,
  ADD COLUMN mac_address VARCHAR(17) NULL AFTER expected_ip,
  ADD UNIQUE KEY uq_devices_hostname (hostname),
  ADD KEY idx_devices_mac_address (mac_address);

CREATE TABLE IF NOT EXISTS poll_attempts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NULL,
  source_system VARCHAR(32) NOT NULL,
  source_device_id VARCHAR(100) NOT NULL,
  hostname VARCHAR(253) NOT NULL,
  attempted_at DATETIME(3) NOT NULL,
  completed_at DATETIME(3) NOT NULL,
  duration_ms INT UNSIGNED NOT NULL,
  success TINYINT(1) NOT NULL,
  error_code VARCHAR(100) NULL,
  error_message VARCHAR(1000) NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_poll_attempts_device_time (device_id, attempted_at),
  KEY idx_poll_attempts_source_time (source_system, source_device_id, attempted_at),
  KEY idx_poll_attempts_success_time (success, attempted_at),
  CONSTRAINT fk_poll_attempts_device
    FOREIGN KEY (device_id) REFERENCES devices(id)
    ON DELETE SET NULL
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
