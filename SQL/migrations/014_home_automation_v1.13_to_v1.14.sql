-- MariaDB migration: home automation schema v1.13 -> v1.14
-- Purpose: manually recorded climate start/stop events
USE home_automation;

CREATE TABLE climate_operation_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  device_id BIGINT UNSIGNED NOT NULL,
  room_id BIGINT UNSIGNED NOT NULL,
  started_at DATETIME(3) NOT NULL,
  ended_at DATETIME(3) NULL,
  open_device_id BIGINT UNSIGNED NULL,
  note VARCHAR(500) NULL,
  created_by BIGINT UNSIGNED NOT NULL,
  created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)
    ON UPDATE CURRENT_TIMESTAMP(3),
  PRIMARY KEY (id),
  UNIQUE KEY uq_climate_operation_open_device (open_device_id),
  KEY idx_climate_operation_room_time (room_id,started_at),
  KEY idx_climate_operation_device_time (device_id,started_at),
  CONSTRAINT chk_climate_operation_interval CHECK (ended_at IS NULL OR ended_at > started_at),
  CONSTRAINT fk_climate_operation_device FOREIGN KEY (device_id)
    REFERENCES devices(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_climate_operation_room FOREIGN KEY (room_id)
    REFERENCES rooms(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_climate_operation_user FOREIGN KEY (created_by)
    REFERENCES app_users(id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
