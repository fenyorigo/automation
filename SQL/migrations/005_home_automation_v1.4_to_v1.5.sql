-- MariaDB migration: home automation schema v1.4 -> v1.5
-- Purpose: database-only desired settings with immutable history

USE home_automation;

CREATE TABLE IF NOT EXISTS device_setting_requests (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  source_system VARCHAR(32) NOT NULL,
  requested_settings JSON NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  requested_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  superseded_at DATETIME(3) NULL,
  PRIMARY KEY (id),
  KEY idx_setting_requests_device_time (device_id, requested_at),
  KEY idx_setting_requests_status_time (status, requested_at),
  CONSTRAINT fk_setting_requests_device FOREIGN KEY (device_id) REFERENCES devices(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
