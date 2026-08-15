-- MariaDB migration: home automation schema v1.22 -> v1.23
-- Purpose: requested and verified fan speed for direct and scheduled climate control
USE home_automation;

ALTER TABLE climate_control_attempts
  ADD COLUMN requested_fan_speed ENUM(
    'auto','low','medium_low','medium','medium_high','high'
  ) NULL AFTER requested_temperature_c;

ALTER TABLE climate_control_schedules
  ADD COLUMN fan_speed ENUM(
    'auto','low','medium_low','medium','medium_high','high'
  ) NOT NULL DEFAULT 'auto' AFTER target_temperature_c;

ALTER TABLE climate_operation_events
  ADD COLUMN started_fan_speed ENUM(
    'auto','low','medium_low','medium','medium_high','high'
  ) NULL AFTER started_target_temperature_c,
  ADD COLUMN ended_fan_speed ENUM(
    'auto','low','medium_low','medium','medium_high','high'
  ) NULL AFTER ended_target_temperature_c;
