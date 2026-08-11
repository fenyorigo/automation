-- MariaDB migration: home automation schema v1.0 -> v1.1
-- Generated: 2026-08-07 UTC
-- Purpose: apply the requested schema refinements to existing tables

USE home_automation;

-- 1. room_source_refs uniqueness: one external room can map to only one canonical room
ALTER TABLE room_source_refs
  DROP INDEX uq_room_source_refs,
  ADD UNIQUE KEY uq_room_source_refs_source (source_system, source_room_id),
  ADD KEY idx_room_source_refs_room (room_id);

-- 2. preserve DS18B20 precision
ALTER TABLE sensor_readings
  MODIFY COLUMN value DECIMAL(8,4) NULL;

-- 3. widen source_event_id and rename created_at to ingested_at for both history tables
ALTER TABLE sensor_readings
  MODIFY COLUMN source_event_id VARCHAR(255) NOT NULL,
  CHANGE COLUMN created_at ingested_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3);

ALTER TABLE device_states
  MODIFY COLUMN source_event_id VARCHAR(255) NOT NULL,
  CHANGE COLUMN created_at ingested_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3);

-- 4. add standalone time indexes for later range queries
ALTER TABLE sensor_readings
  ADD KEY idx_sensor_readings_observed_at (observed_at);

ALTER TABLE device_states
  ADD KEY idx_device_states_observed_at (observed_at);
