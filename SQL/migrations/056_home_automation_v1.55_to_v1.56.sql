-- MariaDB migration: home automation schema v1.55 -> v1.56
-- Purpose: durable pending/verified state for manual TRV setting commands
USE home_automation;

CREATE TABLE trv_setting_requests (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  requested_settings JSON NOT NULL,
  requested_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  requested_by BIGINT UNSIGNED NOT NULL,
  status ENUM('pending','verified','expired','failed') NOT NULL DEFAULT 'pending',
  verified_state JSON NULL,
  completed_at DATETIME(3) NULL,
  error_code VARCHAR(100) NULL,
  error_message VARCHAR(1000) NULL,
  PRIMARY KEY (id),
  KEY idx_trv_setting_device_time (device_id,requested_at),
  KEY idx_trv_setting_pending (status,requested_at),
  CONSTRAINT fk_trv_setting_device FOREIGN KEY (device_id)
    REFERENCES devices(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_trv_setting_user FOREIGN KEY (requested_by)
    REFERENCES app_users(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
