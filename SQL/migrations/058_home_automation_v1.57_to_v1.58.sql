-- MariaDB migration: home automation schema v1.57 -> v1.58
-- Purpose: audited Computherm weekly-program updates
USE home_automation;

CREATE TABLE computherm_schedule_changes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  requested_by BIGINT UNSIGNED NOT NULL,
  requested_schedule JSON NOT NULL,
  preflight_state JSON NULL,
  verified_state JSON NULL,
  success TINYINT(1) NOT NULL,
  error_message TEXT NULL,
  requested_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  completed_at DATETIME(3) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_computherm_schedule_device (device_id,requested_at),
  CONSTRAINT fk_computherm_schedule_device FOREIGN KEY (device_id)
    REFERENCES devices(id),
  CONSTRAINT fk_computherm_schedule_user FOREIGN KEY (requested_by)
    REFERENCES app_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
