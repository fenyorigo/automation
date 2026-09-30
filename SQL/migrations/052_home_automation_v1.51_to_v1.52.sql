-- MariaDB migration: home automation schema v1.51 -> v1.52
-- Purpose: distinguish exterior openings from non-blocking interior doors

USE home_automation;

ALTER TABLE devices
  ADD COLUMN opening_role ENUM('external','internal') NOT NULL DEFAULT 'external'
    AFTER integration_role,
  ADD COLUMN connected_room_id BIGINT UNSIGNED NULL AFTER room_id,
  ADD KEY idx_devices_connected_room (connected_room_id),
  ADD CONSTRAINT fk_devices_connected_room FOREIGN KEY (connected_room_id)
    REFERENCES rooms(id) ON DELETE RESTRICT ON UPDATE CASCADE;
