-- MariaDB migration: home automation schema v1.58 -> v1.59
-- Purpose: audit automatic Computherm clock corrections
USE home_automation;

CREATE TABLE computherm_clock_syncs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  trigger_origin VARCHAR(16) NOT NULL,
  drift_seconds INT NOT NULL,
  threshold_seconds INT UNSIGNED NOT NULL,
  requested_local_time VARCHAR(40) NOT NULL,
  preflight_state JSON NOT NULL,
  verified_state JSON NULL,
  success TINYINT(1) NOT NULL,
  error_message TEXT NULL,
  detected_at DATETIME(3) NOT NULL,
  completed_at DATETIME(3) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_computherm_clock_sync_device (device_id,detected_at),
  CONSTRAINT fk_computherm_clock_sync_device FOREIGN KEY (device_id)
    REFERENCES devices(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
