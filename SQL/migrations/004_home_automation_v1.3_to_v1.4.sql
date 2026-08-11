-- MariaDB migration: home automation schema v1.3 -> v1.4
-- Purpose: separate timestamped manual-state and service histories

USE home_automation;

CREATE TABLE IF NOT EXISTS manual_state_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  previous_power_state TINYINT(1) NOT NULL,
  new_power_state TINYINT(1) NOT NULL,
  changed_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_manual_state_events_device_time (device_id, changed_at),
  CONSTRAINT fk_manual_state_events_device
    FOREIGN KEY (device_id) REFERENCES devices(id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS service_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  serviced_on DATE NOT NULL,
  next_service_due DATE NULL,
  recorded_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  KEY idx_service_events_device_service (device_id, serviced_on),
  KEY idx_service_events_next_due (next_service_due),
  CONSTRAINT fk_service_events_device
    FOREIGN KEY (device_id) REFERENCES devices(id)
    ON DELETE RESTRICT
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
