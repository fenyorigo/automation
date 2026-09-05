-- MariaDB migration: home automation schema v1.40 -> v1.41
-- Purpose: contact-driven ventilation and timestamped contact transitions

USE home_automation;

ALTER TABLE ventilation_events
  MODIFY COLUMN created_by BIGINT UNSIGNED NULL,
  ADD COLUMN event_origin ENUM('manual','zigbee_contact') NOT NULL DEFAULT 'manual'
    AFTER created_by,
  ADD COLUMN started_by_device_id BIGINT UNSIGNED NULL AFTER event_origin,
  ADD COLUMN ended_by_device_id BIGINT UNSIGNED NULL AFTER started_by_device_id,
  ADD COLUMN long_threshold_seconds INT UNSIGNED NOT NULL DEFAULT 300
    AFTER ended_by_device_id,
  ADD COLUMN pending_end_at DATETIME(3) NULL AFTER long_threshold_seconds,
  ADD KEY idx_ventilation_pending_end (event_origin,pending_end_at),
  ADD CONSTRAINT fk_ventilation_started_device FOREIGN KEY (started_by_device_id)
    REFERENCES devices(id) ON DELETE SET NULL ON UPDATE CASCADE,
  ADD CONSTRAINT fk_ventilation_ended_device FOREIGN KEY (ended_by_device_id)
    REFERENCES devices(id) ON DELETE SET NULL ON UPDATE CASCADE;
