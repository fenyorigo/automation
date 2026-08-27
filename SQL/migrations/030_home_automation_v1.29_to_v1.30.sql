-- MariaDB migration: home automation schema v1.29 -> v1.30
-- Purpose: record whether a polling attempt was automatic or manually requested

USE home_automation;

ALTER TABLE poll_attempts
  ADD COLUMN poll_origin ENUM('automatic','manual') NOT NULL DEFAULT 'automatic'
    AFTER hostname,
  ADD KEY idx_poll_attempts_origin_time (poll_origin, attempted_at);
