-- MariaDB migration: home automation schema v1.47 -> v1.48
-- Purpose: separate boiler mains, hot-water and heating states
USE home_automation;

ALTER TABLE devices
  ADD COLUMN manual_hot_water_state TINYINT(1) NULL AFTER manual_power_state,
  ADD COLUMN manual_heating_state TINYINT(1) NULL AFTER manual_hot_water_state;

CREATE TABLE boiler_mode_state_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  previous_hot_water_state TINYINT(1) NULL,
  new_hot_water_state TINYINT(1) NOT NULL,
  previous_heating_state TINYINT(1) NULL,
  new_heating_state TINYINT(1) NOT NULL,
  changed_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_boiler_mode_state_events_device_time (device_id,changed_at),
  CONSTRAINT fk_boiler_mode_state_events_device
    FOREIGN KEY (device_id) REFERENCES devices(id)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- The boiler is currently left without mains after the controlled test.
UPDATE devices
SET manual_power_state=0,manual_hot_water_state=0,manual_heating_state=0
WHERE is_active=1 AND source_system='manual' AND device_type='boiler';
