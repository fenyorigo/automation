-- MariaDB migration: home automation schema v1.14 -> v1.15
-- Purpose: snapshot the selected climate target temperature at manual start
USE home_automation;

ALTER TABLE climate_operation_events
  ADD COLUMN target_temperature_c DECIMAL(5,2) NULL AFTER open_device_id;
