-- MariaDB migration: home automation schema v1.12 -> v1.13
-- Purpose: enforce at most one active ventilation event per room
USE home_automation;

ALTER TABLE ventilation_events
  ADD COLUMN open_room_id BIGINT UNSIGNED NULL AFTER ended_at,
  ADD UNIQUE KEY uq_ventilation_open_room (open_room_id);

UPDATE ventilation_events SET open_room_id=room_id WHERE ended_at IS NULL;
