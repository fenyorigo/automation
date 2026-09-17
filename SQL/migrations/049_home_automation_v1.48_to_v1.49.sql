-- MariaDB migration: home automation schema v1.48 -> v1.49
-- Purpose: avoid filesorts when the dashboard reads the latest value per device
USE home_automation;

ALTER TABLE sensors
  ADD INDEX idx_sensors_device_active_type
    (device_id, is_active, sensor_type, id);

ALTER TABLE sensor_readings
  ADD INDEX idx_sensor_time_id
    (sensor_id, observed_at DESC, id DESC);

ALTER TABLE device_states
  ADD INDEX idx_device_state_time_id
    (device_id, observed_at DESC, id DESC);

ALTER TABLE poll_attempts
  ADD INDEX idx_poll_attempts_device_time_id
    (device_id, attempted_at DESC, id DESC);
