-- MariaDB migration: home automation schema v1.44 -> v1.45
-- Purpose: audit the requested operating mode of climate control commands
USE home_automation;

ALTER TABLE climate_control_attempts
  ADD COLUMN requested_mode ENUM('cool','heat','dry','fan','auto') NULL
  AFTER requested_fan_speed;
