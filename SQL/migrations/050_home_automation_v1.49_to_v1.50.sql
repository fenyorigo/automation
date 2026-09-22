-- MariaDB migration: home automation schema v1.49 -> v1.50
-- Purpose: distinguish user and automation initiated power switching
USE home_automation;

ALTER TABLE device_power_control_attempts
  MODIFY requested_by BIGINT UNSIGNED NULL,
  ADD COLUMN request_origin ENUM('ui','schedule') NOT NULL DEFAULT 'ui'
    AFTER requested_by;
